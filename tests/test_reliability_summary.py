from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.summarize_reliability import summarize, summarize_files


class ReliabilitySummaryTests(unittest.TestCase):
    def test_required_gate_failure_blocks_summary(self) -> None:
        result = summarize(
            [
                {"role": "fast", "required": True, "status": "passed"},
                {"role": "deep", "required": True, "status": "failed"},
                {"role": "scheduled", "required": False, "status": "failed"},
            ]
        )
        self.assertEqual(result.decision, "blocked")
        self.assertIn("deep", result.blocking_roles)

    def test_scheduled_failure_is_advisory_by_default(self) -> None:
        result = summarize(
            [
                {"role": "fast", "required": True, "status": "passed"},
                {"role": "deep", "required": True, "status": "passed"},
                {"role": "specialist", "required": True, "status": "passed"},
                {"role": "scheduled", "required": False, "status": "failed"},
            ]
        )
        self.assertEqual(result.decision, "verified-with-advisory")
        self.assertEqual(result.advisory_roles, ("scheduled",))

    def test_missing_required_manifest_blocks_instead_of_becoming_pass(self) -> None:
        result = summarize(
            [
                {"role": "fast", "required": True, "status": "passed"},
                {"role": "deep", "required": True, "status": "passed"},
            ]
        )
        self.assertEqual(result.decision, "blocked")
        self.assertIn("specialist", result.missing_required_roles)

    def test_unknown_required_status_blocks(self) -> None:
        result = summarize(
            [
                {"role": "fast", "required": True, "status": "passed"},
                {"role": "deep", "required": True, "status": "unknown"},
                {"role": "specialist", "required": True, "status": "passed"},
            ]
        )
        self.assertEqual(result.decision, "blocked")
        self.assertIn("deep", result.blocking_roles)

    def test_duplicate_role_is_ambiguous_and_blocks(self) -> None:
        result = summarize(
            [
                {"role": "fast", "required": True, "status": "passed"},
                {"role": "fast", "required": True, "status": "passed"},
                {"role": "deep", "required": True, "status": "passed"},
                {"role": "specialist", "required": True, "status": "passed"},
            ]
        )
        self.assertEqual(result.decision, "blocked")
        self.assertIn("fast", result.duplicate_roles)

    def test_observational_timing_statistics_report_median_and_worst(self) -> None:
        result = summarize(
            [
                {
                    "role": "fast",
                    "required": True,
                    "status": "passed",
                    "commands": [
                        {"duration_seconds": 1.0},
                        {"duration_seconds": 3.0},
                    ],
                    "passes": [
                        {"duration_seconds": 10.0},
                        {"duration_seconds": 14.0},
                    ],
                },
                {
                    "role": "deep",
                    "required": True,
                    "status": "passed",
                    "commands": [{"duration_seconds": 5.0}],
                    "passes": [{"duration_seconds": 18.0}],
                },
                {"role": "specialist", "required": True, "status": "passed"},
            ]
        )
        self.assertEqual(result.decision, "verified")
        self.assertEqual(result.timings["command_samples"], 3)
        self.assertEqual(result.timings["median_command_seconds"], 3.0)
        self.assertEqual(result.timings["max_command_seconds"], 5.0)
        self.assertEqual(result.timings["pass_samples"], 3)
        self.assertEqual(result.timings["median_pass_seconds"], 14.0)
        self.assertEqual(result.timings["max_pass_seconds"], 18.0)
        self.assertEqual(result.observations, ())

    def test_slow_observation_requires_ten_explicit_prior_samples(self) -> None:
        current = [
            {
                "role": "fast",
                "required": True,
                "status": "passed",
                "timings": {"total_seconds": 100.0},
            },
            {"role": "deep", "required": True, "status": "passed"},
            {"role": "specialist", "required": True, "status": "passed"},
        ]
        nine = [{"total_seconds": 50.0}] * 9
        ten = [{"total_seconds": 50.0}] * 10
        self.assertEqual(summarize(current, prior_samples=nine).observations, ())
        self.assertIn(
            "slower-than-recent-median",
            summarize(current, prior_samples=ten).observations,
        )

    def test_file_aggregation_rejects_non_object_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bad.json"
            path.write_text(json.dumps(["not", "a", "manifest"]), encoding="utf-8")
            result = summarize_files([path])
            self.assertEqual(result.decision, "blocked")
            self.assertTrue(result.input_errors)


if __name__ == "__main__":
    unittest.main()
