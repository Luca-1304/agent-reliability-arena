from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"
CI_TOOLS = ROOT / "requirements" / "ci-tools.txt"
POLICY = ROOT / "reliability-policy.json"


class FifteenPassWorkflowResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_workflow_is_a_thin_adapter_to_policy_governed_runner(self) -> None:
        required_contract = {
            "python scripts/ci/verify_ci_policy.py",
            "python scripts/ci/run_deep_reliability.py",
            "--policy reliability-policy.json",
            "--python-label",
            "--source-sha",
            "--tested-sha",
            "--workspace",
            "--work-root",
            "--diagnostics-dir",
            'python-version: ["3.10", "3.13"]',
        }
        missing = sorted(item for item in required_contract if item not in self.workflow)
        self.assertEqual(missing, [], f"Workflow adapter lacks: {missing}")
        self.assertIn("github.event.pull_request.head.sha", self.workflow)
        self.assertIn("$GITHUB_SHA", self.workflow)
        self.assertNotIn("--passes 15", self.workflow)
        self.assertNotIn("for pass_number in $(seq 1 15)", self.workflow)
        self.assertNotIn("run_pass()", self.workflow)

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
        self.assertGreaterEqual(self.workflow.count("if: always()"), 6)
        self.assertIn("summary.md", self.workflow)
        self.assertIn("$GITHUB_STEP_SUMMARY", self.workflow)
        self.assertIn("fifteen-pass-diagnostics-", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)
        self.assertIn("manifest.json", self.policy["diagnostics"]["required_files"])
        self.assertIn("${{ github.run_attempt }}", self.workflow)

    def test_diagnostics_are_sanitised_and_scanned_before_publication(self) -> None:
        redactor = "python scripts/ci/redact_diagnostic_paths.py"
        scanner = "python scripts/ci/scan_diagnostics.py"
        publish_summary = "- name: Publish reliability evidence summary"
        upload_full = "- name: Upload sanitised scanned reliability evidence"
        upload_blocked = "- name: Upload redacted control reports only"
        enforce = "- name: Enforce privacy-safe diagnostic publication"
        for marker in (redactor, scanner, publish_summary, upload_full, upload_blocked, enforce):
            self.assertIn(marker, self.workflow)
        self.assertLess(self.workflow.index(redactor), self.workflow.index(scanner))
        self.assertLess(self.workflow.index(scanner), self.workflow.index(publish_summary))
        self.assertLess(self.workflow.index(scanner), self.workflow.index(upload_full))
        self.assertIn("steps.diagnostic_redaction.outcome == 'success'", self.workflow)
        self.assertIn("steps.diagnostic_redaction.outcome == 'failure'", self.workflow)
        self.assertIn("steps.diagnostic_scan.outcome == 'success'", self.workflow)
        self.assertIn("steps.diagnostic_scan.outcome == 'failure'", self.workflow)
        self.assertIn("diagnostic-redaction-report.json", self.workflow)
        self.assertIn("diagnostic-scan-report.json", self.workflow)
        self.assertNotIn("Upload complete reliability evidence", self.workflow)

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
            "fail-fast: false",
        }
        missing = sorted(item for item in required_contract if item not in self.workflow)
        self.assertEqual(missing, [], f"Workflow environment lacks: {missing}")
        self.assertEqual(self.policy["deep_gate"]["timezone"], "UTC")
        self.assertEqual(self.policy["deep_gate"]["locale"], "C.UTF-8")


if __name__ == "__main__":
    unittest.main()
