from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.disclosure_export import (
    PriceSource,
    build_disclosure_safe_empirical_export,
    verify_disclosure_safe_empirical_export,
    write_disclosure_safe_empirical_export,
    write_private_evidence_index,
)
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.pilot_policy import PilotPolicy
from agent_reliability_arena.private_pilot import run_private_paired_pilot
from agent_reliability_arena.release_private_pilot_fixture import (
    verify_provider_free_private_pilot_release,
)
from agent_reliability_arena.transports import ModelCallRequest, ModelCallResult, ModelUsage


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = "RELEASE_PRIVATE_MARKER_1304"
PRIVATE_PROMPT = "RELEASE PRIVATE PROMPT MUST NOT BE EXPORTED"
PRIVATE_PATH = "/home/example/private/release-evidence.json"


class _ReleaseAbortTransport:
    provider = "release-disclosure-abort-provider"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        output = f"not-json {SENSITIVE} {PRIVATE_PROMPT} {PRIVATE_PATH}"
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"release-abort-{self.calls}",
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
            provider_request_id=f"release-abort-provider-{self.calls}",
            provider_processing_ms=4,
        )


def _load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(
        json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
    )


def _load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )


def _build_private_evidence(root: Path) -> None:
    config = _load_config()
    catalog = _load_catalog()
    root.mkdir(parents=True)

    completed = root / "release-completed"
    verify_provider_free_private_pilot_release(config, catalog, completed)
    (completed / "operator-notes.md").write_text(
        f"{SENSITIVE}\n{PRIVATE_PROMPT}\n{PRIVATE_PATH}\n",
        encoding="utf-8",
    )

    aborted = root / "release-aborted"
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
    transport = _ReleaseAbortTransport()
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
        raise AssertionError("The scripted invalid provider output unexpectedly completed.")
    assert transport.calls == 1
    assert (aborted / "abort.json").is_file()
    assert (aborted / "transport-calls.jsonl").is_file()
    (aborted / "operator-notes.md").write_text(
        f"{SENSITIVE}\n{PRIVATE_PROMPT}\n{PRIVATE_PATH}\n",
        encoding="utf-8",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        private_root = temporary / "private-evidence"
        _build_private_evidence(private_root)
        index = write_private_evidence_index(private_root)
        price = PriceSource(
            source_name="Release fixture pricing snapshot",
            source_date="2026-07-22",
            currency="GBP",
            input_per_million_minor_units=25,
            output_per_million_minor_units=200,
            source_reference="release-fixture-price-source",
        )
        export = build_disclosure_safe_empirical_export(
            private_root,
            index_path=private_root / "private-evidence-index.json",
            price_source=price,
        )
        output = temporary / "public-evidence.json"
        written = write_disclosure_safe_empirical_export(
            private_root,
            output,
            index_path=private_root / "private-evidence-index.json",
            price_source=price,
        )
        assert written == export
        verification = verify_disclosure_safe_empirical_export(output)

        aggregate = export["aggregate"]
        assert isinstance(aggregate, dict)
        assert aggregate["runs_total"] == 2
        assert aggregate["completed_runs"] == 1
        assert aggregate["aborted_runs"] == 1
        assert aggregate["conditions_total"] == 2
        assert aggregate["verified_complete_conditions"] == 2
        assert aggregate["transport_result_records"] == 6
        assert aggregate["input_tokens"] == 63
        assert aggregate["output_tokens"] == 59
        assert aggregate["total_tokens"] == 122
        assert aggregate["cached_input_tokens"] == 2
        assert aggregate["reasoning_tokens"] == 1
        assert verification["bundle_digest_verified"] is True
        assert verification["runs_verified"] == 2
        assert export["private_index_digest"] == index["index_digest"]
        assert export["comparative_claim_permitted"] is False
        assert export["provider_called"] is False

        serialised = output.read_text(encoding="utf-8")
        for prohibited in (
            SENSITIVE,
            PRIVATE_PROMPT,
            PRIVATE_PATH,
            "instructions",
            "input_text",
            "output_text",
            "provider_request_id",
            "client_request_id",
            "response_id",
            "operator-notes.md",
        ):
            assert prohibited not in serialised, prohibited

        print(
            json.dumps(
                {
                    "schema_version": export["schema_version"],
                    "private_runs_indexed": aggregate["runs_total"],
                    "completed_runs_preserved": aggregate["completed_runs"],
                    "aborted_runs_preserved": aggregate["aborted_runs"],
                    "public_runs_verified": verification["runs_verified"],
                    "bundle_digest_verified": verification["bundle_digest_verified"],
                    "sensitive_content_excluded": True,
                    "provider_called": False,
                    "comparative_claim_permitted": False,
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
