from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.disclosure_export import (
    PriceSource,
    build_disclosure_safe_empirical_export,
    verify_disclosure_safe_empirical_export,
    write_private_evidence_index,
)
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.pilot_policy import PilotPolicy
from agent_reliability_arena.private_pilot import run_private_paired_pilot
from agent_reliability_arena.release_private_pilot_fixture import verify_provider_free_private_pilot_release
from agent_reliability_arena.transports import ModelCallRequest, ModelCallResult, ModelUsage


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "fixture_experiment.json"
CATALOG = ROOT / "examples" / "live_prompt_catalog.json"
SENSITIVE = "SENSITIVE_MARKER_1304_DO_NOT_PUBLISH"
PRIVATE_PROMPT = "PRIVATE PROMPT SENTENCE MUST REMAIN PRIVATE"
UNIX_PATH = "/home/example/private/provider-run.json"
WINDOWS_PATH = r"C:\\Users\\Example\\private\\provider-run.json"


def load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(json.loads(CONFIG.read_text(encoding="utf-8")))


def load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(json.loads(CATALOG.read_text(encoding="utf-8")))


class _InvalidOutputTransport:
    provider = "release-disclosure-abort-provider"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        output = f"not-json {SENSITIVE} {PRIVATE_PROMPT} {UNIX_PATH} {WINDOWS_PATH}"
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"private-abort-response-{self.calls}",
            model_id=request.model_id,
            output_text=output,
            status="completed",
            latency_ms=7,
            usage=ModelUsage(
                input_tokens=13,
                output_tokens=9,
                total_tokens=22,
                cached_input_tokens=2,
                reasoning_tokens=1,
            ),
            raw_response_sha256=hashlib.sha256(output.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"private-abort-provider-{self.calls}",
            provider_processing_ms=4,
        )


def build_private_batch(root: Path) -> tuple[Path, dict[str, object]]:
    config = load_config()
    catalog = load_catalog()
    root.mkdir(parents=True)

    completed = root / "run-completed"
    verify_provider_free_private_pilot_release(config, catalog, completed)
    (completed / "operator-notes.md").write_text(
        f"{SENSITIVE}\n{PRIVATE_PROMPT}\n{UNIX_PATH}\n{WINDOWS_PATH}\n",
        encoding="utf-8",
    )

    aborted = root / "run-aborted"
    policy = PilotPolicy(
        provider="release-disclosure-abort-provider",
        model_id=config.model_id,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        scenario_ids=("success",),
        max_calls=8,
        max_requested_output_tokens=2068,
        reserved_total_tokens_per_call=1024,
        max_reserved_total_tokens=8192,
        currency="GBP",
        reserved_cost_per_call_minor_units=1,
        max_cost_minor_units=8,
        external_execution_enabled=True,
    )
    transport = _InvalidOutputTransport()
    try:
        run_private_paired_pilot(
            config,
            catalog,
            policy,
            transport,
            aborted,
            reviewed_policy_digest=policy.digest,
            external_execution_approved=True,
        )
    except Exception:
        pass
    else:
        raise AssertionError("Invalid scripted output unexpectedly completed.")
    assert transport.calls == 1
    assert (aborted / "abort.json").is_file()
    assert (aborted / "transport-calls.jsonl").is_file()
    (aborted / "operator-notes.md").write_text(
        f"failed private note {SENSITIVE} {PRIVATE_PROMPT} {UNIX_PATH} {WINDOWS_PATH}\n",
        encoding="utf-8",
    )

    index = write_private_evidence_index(root)
    return root / "private-evidence-index.json", index


class DisclosureExportTests(unittest.TestCase):
    def test_export_preserves_completed_aborted_counts_and_omits_private_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "private-set"
            index_path, index = build_private_batch(private_root)
            export = build_disclosure_safe_empirical_export(private_root, index_path=index_path)
            verified = verify_disclosure_safe_empirical_export(export)

            self.assertEqual(export["schema_version"], "arena-disclosure-safe-export-v1")
            self.assertEqual(export["private_index_digest"], index["index_digest"])
            self.assertEqual(export["aggregate"]["runs_total"], 2)
            self.assertEqual(export["aggregate"]["completed_runs"], 1)
            self.assertEqual(export["aggregate"]["aborted_runs"], 1)
            self.assertEqual(export["aggregate"]["conditions_total"], 2)
            self.assertEqual(export["aggregate"]["verified_complete_conditions"], 2)
            self.assertEqual(export["aggregate"]["transport_result_records"], 6)
            self.assertEqual(export["aggregate"]["transport_error_records"], 0)
            self.assertEqual(export["aggregate"]["input_tokens"], 63)
            self.assertEqual(export["aggregate"]["output_tokens"], 59)
            self.assertEqual(export["aggregate"]["total_tokens"], 122)
            self.assertEqual(export["aggregate"]["cached_input_tokens"], 2)
            self.assertEqual(export["aggregate"]["reasoning_tokens"], 1)
            self.assertFalse(export["comparative_claim_permitted"])
            self.assertTrue(verified["bundle_digest_verified"])
            self.assertEqual(verified["runs_verified"], 2)

            runs = {run["run_id"]: run for run in export["runs"]}
            self.assertEqual(runs["run-completed"]["status"], "completed")
            self.assertEqual(runs["run-aborted"]["status"], "aborted")
            self.assertEqual(runs["run-aborted"]["abort"]["stage"], "general")
            self.assertEqual(runs["run-aborted"]["abort"]["error_type"], "LiveOrchestrationError")
            self.assertNotIn("error_message", runs["run-aborted"]["abort"])
            self.assertEqual(len(runs["run-completed"]["source_commitment_sha256"]), 64)
            self.assertEqual(len(runs["run-aborted"]["source_commitment_sha256"]), 64)

            serialised = json.dumps(export, sort_keys=True, ensure_ascii=False)
            for prohibited in (
                SENSITIVE,
                PRIVATE_PROMPT,
                UNIX_PATH,
                WINDOWS_PATH,
                "instructions",
                "input_text",
                "output_text",
                "refusal_text",
                "provider_request_id",
                "client_request_id",
                "response_id",
                "operator-notes.md",
            ):
                self.assertNotIn(prohibited, serialised)
            self.assertEqual(
                export["redaction_record"],
                {
                    "authentication_material": "excluded",
                    "local_machine_identifiers": "excluded",
                    "operator_notes": "excluded",
                    "private_file_manifest": "committed_by_digest_only",
                    "provider_payloads": "excluded",
                    "raw_transport_ledger": "committed_by_digest_only",
                    "role_inputs_and_prompts": "excluded",
                    "role_outputs": "excluded",
                },
            )

    def test_index_rejects_added_removed_and_tampered_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "tampered-set"
            index_path, _ = build_private_batch(private_root)
            notes = private_root / "run-completed" / "operator-notes.md"
            notes.write_text(notes.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "commitment"):
                build_disclosure_safe_empirical_export(private_root, index_path=index_path)

        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "added-set"
            index_path, _ = build_private_batch(private_root)
            (private_root / "run-added-later").mkdir()
            with self.assertRaisesRegex(ValueError, "run set"):
                build_disclosure_safe_empirical_export(private_root, index_path=index_path)

        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "removed-set"
            index_path, _ = build_private_batch(private_root)
            for path in sorted((private_root / "run-aborted").rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            (private_root / "run-aborted").rmdir()
            with self.assertRaisesRegex(ValueError, "run set"):
                build_disclosure_safe_empirical_export(private_root, index_path=index_path)

    def test_public_verifier_rejects_outcome_and_digest_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "private-set"
            index_path, _ = build_private_batch(private_root)
            export = build_disclosure_safe_empirical_export(private_root, index_path=index_path)

            tampered_count = copy.deepcopy(export)
            tampered_count["aggregate"]["aborted_runs"] = 0
            with self.assertRaisesRegex(ValueError, "bundle digest"):
                verify_disclosure_safe_empirical_export(tampered_count)

            tampered_outcome = copy.deepcopy(export)
            tampered_outcome["runs"][0]["conditions"]["general"]["verified_complete"] = False
            unsigned = dict(tampered_outcome)
            unsigned.pop("bundle_digest")
            tampered_outcome["bundle_digest"] = hashlib.sha256(
                json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            with self.assertRaisesRegex(ValueError, "aggregate"):
                verify_disclosure_safe_empirical_export(tampered_outcome)

    def test_price_source_is_separate_dated_metadata_and_sensitive_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "private-set"
            index_path, _ = build_private_batch(private_root)
            price = PriceSource(
                source_name="Provider public pricing page",
                source_date="2026-07-22",
                currency="GBP",
                input_per_million_minor_units=25,
                output_per_million_minor_units=200,
                source_reference="pricing-snapshot-2026-07-22",
            )
            export = build_disclosure_safe_empirical_export(
                private_root,
                index_path=index_path,
                price_source=price,
            )
            self.assertEqual(export["price_source"], price.to_dict())
            self.assertNotIn("measured_cost", json.dumps(export))

            with self.assertRaisesRegex(ValueError, "sensitive"):
                PriceSource(
                    source_name=SENSITIVE,
                    source_date="2026-07-22",
                    currency="GBP",
                    input_per_million_minor_units=25,
                    output_per_million_minor_units=200,
                    source_reference="pricing-snapshot",
                )

    def test_cli_export_and_public_replay_are_provider_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "private-set"
            index_path, _ = build_private_batch(private_root)
            output = Path(directory) / "public-export.json"
            environment = dict(os.environ)
            environment["ARENA_TEST_SENSITIVE"] = SENSITIVE
            result = subprocess.run(
                [
                    "arena-export-live-evidence",
                    "--private-root",
                    str(private_root),
                    "--index",
                    str(index_path),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertNotIn(SENSITIVE, result.stdout + result.stderr + output.read_text(encoding="utf-8"))

            replay = subprocess.run(
                ["arena-verify-live-export", "--input", str(output)],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(replay.returncode, 0, replay.stderr)
            payload = json.loads(replay.stdout)
            self.assertTrue(payload["bundle_digest_verified"])
            self.assertEqual(payload["runs_verified"], 2)
            self.assertFalse(payload["provider_called"])
            self.assertNotIn(SENSITIVE, replay.stdout + replay.stderr)


if __name__ == "__main__":
    unittest.main()
