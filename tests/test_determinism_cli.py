from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.verify_determinism import main, verify_pair
from scripts.ci.reliability_policy import load_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "reliability-policy.json"


class DeterminismCliTests(unittest.TestCase):
    def test_verify_pair_uses_named_policy_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.json"
            right = root / "right.json"
            left.write_text('{"b":2,"a":1}\n', encoding="utf-8")
            right.write_text('{"a":1,"b":2}\n', encoding="utf-8")
            report = verify_pair(
                policy=load_policy(POLICY),
                output_key="fixture_run",
                left=left,
                right=right,
            )
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["output_key"], "fixture_run")

    def test_cli_writes_failure_report_for_semantic_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.json"
            right = root / "right.json"
            output = root / "report.json"
            left.write_text('{"value":1}\n', encoding="utf-8")
            right.write_text('{"value":2}\n', encoding="utf-8")
            code = main(
                [
                    "--policy",
                    str(POLICY),
                    "--output-key",
                    "fixture_run",
                    "--left",
                    str(left),
                    "--right",
                    str(right),
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(code, 1)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertIn("/value", payload["comparison"]["diff"])


if __name__ == "__main__":
    unittest.main()
