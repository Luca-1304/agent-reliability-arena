from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.release_private_pilot_fixture import (
    verify_provider_free_private_pilot_release,
)


ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_reference_run_has_locked_metrics_and_manifest(self) -> None:
        reference = ROOT / "reference_runs" / "fixture-v1"
        metrics = json.loads((reference / "aggregate_metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(metrics["evidence_status"], "deterministic_fixture")
        self.assertEqual(metrics["conditions"]["general"]["verified_complete"], 2)
        self.assertEqual(metrics["conditions"]["specialist"]["verified_complete"], 6)
        self.assertEqual(metrics["paired"]["additional_logical_model_calls"], 36)
        from agent_reliability_arena.artifacts import verify_manifest
        self.assertTrue(verify_manifest(reference))

    def test_release_verifier_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/verify_release.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tests_expected_minimum"], 50)
        self.assertGreaterEqual(payload["tests_discovered"], 50)
        self.assertEqual(payload["release_candidate_version"], "0.2.0rc2")
        self.assertEqual(payload["release_candidate_documents_verified"], 6)
        self.assertTrue(payload["reference_manifest_verified"])
        self.assertEqual(payload["specialist_verified"], 6)
        self.assertEqual(payload["transport_ledger_records_verified"], 1)
        self.assertTrue(payload["transport_ledger_digest_verified"])
        self.assertEqual(payload["live_request_templates_verified"], 64)
        self.assertTrue(payload["live_request_preflight_digest_verified"])
        self.assertEqual(payload["pilot_preflight_calls_verified"], 8)
        self.assertTrue(payload["pilot_preflight_digest_verified"])
        self.assertTrue(payload["pilot_external_execution_disabled_verified"])
        self.assertEqual(payload["live_role_outputs_verified"], 6)
        self.assertTrue(payload["live_role_output_digests_verified"])
        self.assertEqual(payload["live_orchestration_scenarios_verified"], 3)
        self.assertEqual(payload["live_orchestration_role_calls_verified"], 12)
        self.assertEqual(payload["live_orchestration_ledgers_verified"], 3)
        self.assertTrue(payload["live_orchestration_recovery_verified"])
        self.assertTrue(payload["live_orchestration_terminal_security_verified"])

    def test_private_pilot_runner_release_rehearsal(self) -> None:
        config = ExperimentConfig.from_dict(
            json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
        )
        catalog = PromptCatalog.from_dict(
            json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
        )
        with tempfile.TemporaryDirectory() as directory:
            summary = verify_provider_free_private_pilot_release(
                config,
                catalog,
                Path(directory) / "private-pilot",
            )
        self.assertEqual(summary["scenario"], "success")
        self.assertEqual(summary["conditions"], 2)
        self.assertEqual(summary["role_calls"], 5)
        self.assertEqual(summary["ledger_records"], 5)
        self.assertEqual(summary["private_artifacts"], 7)
        self.assertFalse(summary["comparative_claim_permitted"])


if __name__ == "__main__":
    unittest.main()
