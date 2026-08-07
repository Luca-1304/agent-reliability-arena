from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_policy import load_policy
from scripts.ci.workflow_contract import read_workflow_contract
from scripts.ci.verify_ci_policy import verify_workflow_against_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "reliability-policy.json"
DEEP_WORKFLOW = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"


class CiPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy(POLICY)
        self.workflow_text = DEEP_WORKFLOW.read_text(encoding="utf-8")

    def _violations_after(self, old: str, new: str):
        self.assertIn(old, self.workflow_text, f"mutation anchor missing: {old!r}")
        mutated = self.workflow_text.replace(old, new, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(mutated, encoding="utf-8")
            contract = read_workflow_contract(path)
            return verify_workflow_against_policy(contract, self.policy, role="deep")

    def _codes(self, violations) -> set[str]:
        return {item.code for item in violations}

    def test_deep_workflow_matches_policy(self) -> None:
        contract = read_workflow_contract(DEEP_WORKFLOW)
        violations = verify_workflow_against_policy(contract, self.policy, role="deep")
        self.assertEqual(violations, [])

    def test_contents_write_is_rejected(self) -> None:
        violations = self._violations_after("contents: read", "contents: write")
        self.assertIn("permissions-exceed-policy", self._codes(violations))

    def test_persisted_checkout_credentials_are_rejected(self) -> None:
        violations = self._violations_after("persist-credentials: false", "persist-credentials: true")
        self.assertIn("checkout-persists-credentials", self._codes(violations))

    def test_artifact_retention_above_policy_is_rejected(self) -> None:
        violations = self._violations_after("retention-days: 14", "retention-days: 60")
        self.assertIn("artifact-retention", self._codes(violations))

    def test_artifact_upload_without_always_is_rejected(self) -> None:
        violations = self._violations_after(
            "if: always() && steps.diagnostic_redaction.outcome == 'success' && steps.diagnostic_scan.outcome == 'success'",
            "if: steps.diagnostic_redaction.outcome == 'success' && steps.diagnostic_scan.outcome == 'success'",
        )
        self.assertIn("artifact-missing-always", self._codes(violations))

    def test_job_timeout_above_policy_is_rejected(self) -> None:
        violations = self._violations_after("timeout-minutes: 180", "timeout-minutes: 360")
        self.assertIn("job-timeout", self._codes(violations))

    def test_missing_policy_trigger_surface_is_rejected(self) -> None:
        violations = self._violations_after('      - "citation/**"\n', "")
        self.assertIn("missing-trigger-surface", self._codes(violations))

    def test_unpinned_external_action_is_rejected(self) -> None:
        violations = self._violations_after(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/checkout@v7",
        )
        self.assertIn("action-not-sha-pinned", self._codes(violations))


if __name__ == "__main__":
    unittest.main()
