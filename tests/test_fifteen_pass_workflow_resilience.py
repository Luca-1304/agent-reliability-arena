from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"
CI_TOOLS = ROOT / "requirements" / "ci-tools.txt"


class FifteenPassWorkflowResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_reliability_surfaces_trigger_the_stress_gate(self) -> None:
        required_paths = {
            '      - ".github/workflows/fifteen-pass-verification.yml"',
            '      - "scripts/ci/reliability_gate.py"',
            '      - "requirements/ci-tools.txt"',
            '      - "tests/test_reliability_gate.py"',
            '      - "src/**"',
            '      - "tests/**"',
            '      - "scripts/**"',
            '      - "examples/**"',
            '      - "security/**"',
            '      - "release/**"',
            '      - "reference_runs/**"',
            '      - "web/**"',
            '      - "docs/**"',
            '      - "citation/**"',
            '      - "requirements/**"',
            '      - "pyproject.toml"',
            '      - "README.md"',
            '      - "CHANGELOG.md"',
            '      - "ROADMAP.md"',
        }
        missing = sorted(path for path in required_paths if path not in self.workflow)
        self.assertEqual(missing, [], f"Stress gate does not cover: {missing}")
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("push:", self.workflow)
        self.assertIn("branches: [main]", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)

    def test_workflow_is_a_thin_adapter_to_the_repository_runner(self) -> None:
        required_contract = {
            "python scripts/ci/reliability_gate.py",
            "--passes 15",
            "--python-label",
            "--workspace",
            "--work-root",
            "--diagnostics-dir",
            'python-version: ["3.10", "3.13"]',
        }
        missing = sorted(item for item in required_contract if item not in self.workflow)
        self.assertEqual(missing, [], f"Workflow adapter lacks: {missing}")
        self.assertNotIn("for pass_number in $(seq 1 15)", self.workflow)
        self.assertNotIn("run_pass()", self.workflow)

    def test_external_actions_are_pinned_to_immutable_full_length_shas(self) -> None:
        expected = {
            "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
            "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        }
        for action, sha in expected.items():
            self.assertRegex(
                self.workflow,
                rf"uses:\s+{re.escape(action)}@{sha}\s+#\s+v[0-9]",
                f"{action} must be pinned to the reviewed immutable release commit",
            )
        self.assertNotRegex(self.workflow, r"uses:\s+[^@\s]+@v\d")

    def test_workflow_uses_least_privilege_and_non_persistent_checkout(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("id-token: write", self.workflow)

    def test_ci_toolchain_is_exact_hash_locked_and_dependency_complete(self) -> None:
        self.assertIn(
            "python -m pip install --disable-pip-version-check --no-input --require-hashes -r requirements/ci-tools.txt",
            self.workflow,
        )
        self.assertIn(
            "python -m pip install --disable-pip-version-check --no-input --no-build-isolation --editable .",
            self.workflow,
        )
        self.assertTrue(CI_TOOLS.is_file(), f"missing CI toolchain lock: {CI_TOOLS}")
        entries = [
            line.strip()
            for line in CI_TOOLS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(len(entries), 4)
        names = {entry.split("==", 1)[0].lower() for entry in entries}
        self.assertEqual(names, {"packaging", "pip", "setuptools", "wheel"})
        for entry in entries:
            self.assertRegex(entry, r"^[A-Za-z0-9_.-]+==[^\s]+\s+--hash=sha256:[0-9a-f]{64}$")

    def test_diagnostics_and_summary_survive_every_outcome(self) -> None:
        self.assertGreaterEqual(self.workflow.count("if: always()"), 2)
        self.assertIn("summary.md", self.workflow)
        self.assertIn("$GITHUB_STEP_SUMMARY", self.workflow)
        self.assertIn("fifteen-pass-diagnostics-", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)
        self.assertIn("retention-days: 30", self.workflow)
        self.assertIn("${{ github.run_attempt }}", self.workflow)

    def test_environment_and_concurrency_are_controlled(self) -> None:
        required_contract = {
            "TZ: UTC",
            "LC_ALL: C.UTF-8",
            "LANG: C.UTF-8",
            "PYTHONUNBUFFERED: \"1\"",
            "PYTHONDONTWRITEBYTECODE: \"1\"",
            "PIP_DISABLE_PIP_VERSION_CHECK: \"1\"",
            "SOURCE_DATE_EPOCH: \"315532800\"",
            "cancel-in-progress: true",
            "timeout-minutes: 360",
            "fail-fast: false",
        }
        missing = sorted(item for item in required_contract if item not in self.workflow)
        self.assertEqual(missing, [], f"Workflow environment lacks: {missing}")


if __name__ == "__main__":
    unittest.main()
