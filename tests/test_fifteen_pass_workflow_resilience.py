from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"


class FifteenPassWorkflowResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_reliability_surfaces_trigger_the_stress_gate(self) -> None:
        required_paths = {
            '      - "src/**"',
            '      - "tests/**"',
            '      - "scripts/**"',
            '      - "examples/**"',
            '      - "security/**"',
            '      - "release/**"',
            '      - "reference_runs/**"',
            '      - "web/**"',
            '      - "docs/**"',
            '      - "pyproject.toml"',
            '      - "README.md"',
            '      - "CHANGELOG.md"',
            '      - "ROADMAP.md"',
        }
        missing = sorted(path for path in required_paths if path not in self.workflow)
        self.assertEqual(missing, [], f"Stress gate does not cover: {missing}")

    def test_each_pass_has_a_controlled_environment_and_diagnostics(self) -> None:
        required_contract = {
            "TZ: UTC",
            "LC_ALL: C.UTF-8",
            "LANG: C.UTF-8",
            "PYTHONHASHSEED",
            "environment.txt",
            "failure.txt",
            "pass-${pass_number}.log",
        }
        missing = sorted(item for item in required_contract if item not in self.workflow)
        self.assertEqual(missing, [], f"Repeated verification lacks: {missing}")

    def test_diagnostics_survive_a_failed_run(self) -> None:
        self.assertIn("if: always()", self.workflow)
        self.assertIn("uses: actions/upload-artifact@v7", self.workflow)
        self.assertIn("fifteen-pass-diagnostics-", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)


if __name__ == "__main__":
    unittest.main()
