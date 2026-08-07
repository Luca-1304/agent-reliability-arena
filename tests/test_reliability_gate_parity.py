from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from agent_reliability_arena import cli


class ReliabilityGateParityTests(unittest.TestCase):
    def test_reliability_mode_normalizes_only_top_level_output_path(self) -> None:
        payload = {
            "evidence_status": "deterministic_fixture",
            "manifest_verified": True,
            "output": "/tmp/pass-01/editable-artifacts",
            "paired_runs": 8,
            "total_runs": 16,
        }
        with patch.dict(os.environ, {cli.RELIABILITY_STABLE_OUTPUT_ENV: "1"}, clear=False):
            normalized = cli._stable_reliability_payload(payload)

        self.assertEqual(normalized["output"], cli.RELIABILITY_OUTPUT_MARKER)
        self.assertEqual(normalized["paired_runs"], 8)
        self.assertEqual(normalized["total_runs"], 16)
        self.assertTrue(normalized["manifest_verified"])
        self.assertEqual(payload["output"], "/tmp/pass-01/editable-artifacts")

    def test_normal_cli_mode_preserves_real_output_path(self) -> None:
        payload = {"output": "/tmp/real-output", "scenarios": 8}
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(cli._stable_reliability_payload(payload), payload)

    def test_reliability_mode_does_not_hide_non_path_semantic_drift(self) -> None:
        left = {"output": "/tmp/editable-public.json", "scenarios": 8}
        right = {"output": "/tmp/wheel-public.json", "scenarios": 9}
        with patch.dict(os.environ, {cli.RELIABILITY_STABLE_OUTPUT_ENV: "1"}, clear=False):
            normalized_left = cli._stable_reliability_payload(left)
            normalized_right = cli._stable_reliability_payload(right)

        self.assertEqual(normalized_left["output"], normalized_right["output"])
        self.assertNotEqual(normalized_left, normalized_right)


if __name__ == "__main__":
    unittest.main()
