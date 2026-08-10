from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.stage7_candidate import (
    build_stage7_candidate_packet,
    verify_stage7_candidate,
)
from agent_reliability_arena.transports.base import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "examples" / "stage7_candidate"
CATALOG = ROOT / "examples" / "live_prompt_catalog.json"
MODEL_ID = "gpt-5.5-2026-04-23"
SOURCE_DATE = "2026-08-10"
SOURCE_REFERENCE = "https://developers.openai.com/api/docs/models/gpt-5.5"


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def rewrite_packet_digest(packet: dict[str, object]) -> None:
    unsigned = dict(packet)
    unsigned.pop("packet_digest", None)
    packet["packet_digest"] = canonical_json_sha256(unsigned)


class Stage7DisabledCandidateTests(unittest.TestCase):
    def test_committed_candidate_verifies_and_remains_disabled(self) -> None:
        committed = read_json(CANDIDATE / "packet.json")
        rebuilt = build_stage7_candidate_packet(CANDIDATE, CATALOG)
        self.assertEqual(
            committed["preflight_manifest_digest"],
            rebuilt["preflight_manifest_digest"],
        )
        self.assertEqual(committed["packet_digest"], rebuilt["packet_digest"])

        result = verify_stage7_candidate(CANDIDATE, CATALOG)

        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["model_id"], MODEL_ID)
        self.assertEqual(result["scenario_ids"], ["success"])
        self.assertEqual(result["planned_call_ceiling"], 8)
        self.assertEqual(result["max_reserved_total_tokens"], 16384)
        self.assertEqual(result["reserved_cost_minor_units"], 96)
        self.assertEqual(result["proposed_hard_ceiling_minor_units"], 100)
        self.assertEqual(result["conservative_price_bound_minor_units"], 50)
        self.assertEqual(result["currency"], "USD")
        self.assertFalse(result["external_execution_enabled"])
        self.assertFalse(result["operator_approved"])
        self.assertFalse(result["provider_called"])

    def test_committed_inputs_lock_snapshot_source_and_budget(self) -> None:
        experiment = read_json(CANDIDATE / "experiment.json")
        policy = read_json(CANDIDATE / "policy.disabled.json")
        price = read_json(CANDIDATE / "price-source.json")
        packet = read_json(CANDIDATE / "packet.json")

        self.assertEqual(experiment["model_id"], MODEL_ID)
        self.assertEqual(experiment["model_version"], MODEL_ID)
        self.assertEqual(experiment["scenarios"], ["success"])
        self.assertEqual(policy["provider"], "openai-responses")
        self.assertEqual(policy["model_id"], MODEL_ID)
        self.assertEqual(policy["model_version"], MODEL_ID)
        self.assertEqual(policy["scenario_ids"], ["success"])
        self.assertEqual(policy["max_calls"], 8)
        self.assertEqual(policy["max_requested_output_tokens"], 2068)
        self.assertEqual(policy["reserved_total_tokens_per_call"], 2048)
        self.assertEqual(policy["max_reserved_total_tokens"], 16384)
        self.assertEqual(policy["reserved_cost_per_call_minor_units"], 12)
        self.assertEqual(policy["max_cost_minor_units"], 100)
        self.assertFalse(policy["external_execution_enabled"])
        self.assertEqual(price["source_date"], SOURCE_DATE)
        self.assertEqual(price["currency"], "USD")
        self.assertEqual(price["input_per_million_minor_units"], 500)
        self.assertEqual(price["output_per_million_minor_units"], 3000)
        self.assertEqual(price["source_reference"], SOURCE_REFERENCE)
        self.assertEqual(packet["prepared_date"], SOURCE_DATE)
        self.assertFalse(packet["operator_approved"])
        self.assertFalse(packet["provider_called"])

    def test_rejects_policy_enablement_and_operator_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "candidate"
            shutil.copytree(CANDIDATE, root)
            policy = read_json(root / "policy.disabled.json")
            policy["external_execution_enabled"] = True
            write_json(root / "policy.disabled.json", policy)
            with self.assertRaisesRegex(ValueError, "disabled"):
                verify_stage7_candidate(root, CATALOG)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "candidate"
            shutil.copytree(CANDIDATE, root)
            packet = read_json(root / "packet.json")
            packet["operator_approved"] = True
            rewrite_packet_digest(packet)
            write_json(root / "packet.json", packet)
            with self.assertRaisesRegex(ValueError, "operator_approved"):
                verify_stage7_candidate(root, CATALOG)

    def test_rejects_model_provider_scenario_and_budget_drift(self) -> None:
        mutations = (
            ("model_id", "other-model"),
            ("provider", "other-provider"),
            ("scenario_ids", ["false_success"]),
            ("reserved_cost_per_call_minor_units", 5),
        )
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "candidate"
                shutil.copytree(CANDIDATE, root)
                policy = read_json(root / "policy.disabled.json")
                policy[key] = value
                write_json(root / "policy.disabled.json", policy)
                with self.assertRaises(ValueError):
                    verify_stage7_candidate(root, CATALOG)

    def test_rejects_price_currency_and_rate_drift(self) -> None:
        mutations = (
            ("currency", "GBP"),
            ("output_per_million_minor_units", 6000),
        )
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "candidate"
                shutil.copytree(CANDIDATE, root)
                price = read_json(root / "price-source.json")
                price[key] = value
                write_json(root / "price-source.json", price)
                with self.assertRaises(ValueError):
                    verify_stage7_candidate(root, CATALOG)

    def test_rejects_recomputed_packet_claim_drift(self) -> None:
        mutations = (
            ("provider_called", True),
            ("external_execution_enabled", True),
            ("model_id", "rewritten-model"),
            ("conservative_price_bound_minor_units", 1),
        )
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "candidate"
                shutil.copytree(CANDIDATE, root)
                packet = read_json(root / "packet.json")
                packet[key] = value
                rewrite_packet_digest(packet)
                write_json(root / "packet.json", packet)
                with self.assertRaises(ValueError):
                    verify_stage7_candidate(root, CATALOG)

    def test_rejects_duplicate_json_and_symlinked_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "candidate"
            shutil.copytree(CANDIDATE, root)
            (root / "packet.json").write_text(
                '{"schema_version":"x","schema_version":"y"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify_stage7_candidate(root, CATALOG)

        if hasattr(os, "symlink"):
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                root = base / "candidate"
                shutil.copytree(CANDIDATE, root)
                packet = root / "packet.json"
                external = base / "real-packet.json"
                shutil.copy2(packet, external)
                packet.unlink()
                try:
                    packet.symlink_to(external)
                except (OSError, NotImplementedError):
                    return
                with self.assertRaisesRegex(ValueError, "non-symlink"):
                    verify_stage7_candidate(root, CATALOG)

    def test_repository_script_is_provider_free_and_does_not_echo_environment_key(self) -> None:
        marker = "SHOULD_NOT_BE_READ_OR_PRINTED"
        env = dict(os.environ)
        env["OPENAI_API_KEY"] = marker
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_stage7_candidate.py")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertFalse(output["provider_called"])
        self.assertFalse(output["external_execution_enabled"])
        self.assertFalse(output["operator_approved"])
        self.assertNotIn(marker, completed.stdout)
        self.assertNotIn(marker, completed.stderr)

        source = (ROOT / "scripts" / "verify_stage7_candidate.py").read_text(encoding="utf-8")
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertNotIn("OpenAIResponsesTransport", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)


if __name__ == "__main__":
    unittest.main()
