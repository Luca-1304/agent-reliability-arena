from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


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
        self.assertTrue(payload["reference_manifest_verified"])
        self.assertEqual(payload["specialist_verified"], 6)
        self.assertEqual(payload["transport_ledger_records_verified"], 1)
        self.assertTrue(payload["transport_ledger_digest_verified"])
        self.assertEqual(payload["live_request_templates_verified"], 64)
        self.assertTrue(payload["live_request_preflight_digest_verified"])


if __name__ == "__main__":
    unittest.main()
