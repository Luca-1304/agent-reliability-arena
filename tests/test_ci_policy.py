from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_policy import load_policy
from scripts.ci.workflow_contract import read_workflow_contract
from scripts.ci.verify_ci_policy import verify_workflow_against_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "reliability-policy.json"
WORKFLOWS = ROOT / ".github" / "workflows"
DEEP_WORKFLOW = WORKFLOWS / "fifteen-pass-verification.yml"
FAST_WORKFLOW = WORKFLOWS / "reliability-fast.yml"
SPECIALIST_WORKFLOW = WORKFLOWS / "reliability-specialists.yml"
SCHEDULED_WORKFLOW = WORKFLOWS / "reliability-ecosystem.yml"
EXPECTED_WORKFLOW_ROLES = {
    "fast": ("reliability-fast.yml",),
    "deep": ("fifteen-pass-verification.yml",),
    "specialist": ("reliability-specialists.yml",),
    "scheduled": ("reliability-ecosystem.yml",),
}


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

    def test_policy_declares_exact_workflow_roles(self) -> None:
        raw_roles = self.policy.raw["workflow_roles"]
        actual = {role: tuple(files) for role, files in raw_roles.items()}
        self.assertEqual(actual, EXPECTED_WORKFLOW_ROLES)

    def test_every_declared_role_workflow_exists_and_matches_policy(self) -> None:
        paths = {
            "fast": FAST_WORKFLOW,
            "deep": DEEP_WORKFLOW,
            "specialist": SPECIALIST_WORKFLOW,
            "scheduled": SCHEDULED_WORKFLOW,
        }
        for role, path in paths.items():
            with self.subTest(role=role):
                self.assertTrue(path.is_file(), f"missing {role} workflow: {path.name}")
                contract = read_workflow_contract(path)
                violations = verify_workflow_against_policy(contract, self.policy, role=role)
                self.assertEqual(violations, [])

    def test_deep_gate_has_no_schedule_trigger(self) -> None:
        contract = read_workflow_contract(DEEP_WORKFLOW)
        self.assertNotIn("schedule", contract.triggers)
        self.assertEqual(contract.triggers.get("schedule"), None)

    def test_scheduled_gate_is_advisory_and_not_a_merge_trigger(self) -> None:
        contract = read_workflow_contract(SCHEDULED_WORKFLOW)
        self.assertIn("schedule", contract.triggers)
        self.assertIn("workflow_dispatch", contract.triggers)
        self.assertNotIn("pull_request", contract.triggers)
        self.assertNotIn("push", contract.triggers)
        self.assertEqual(contract.triggers["schedule"].crons, ("17 4 * * 2",))
        self.assertFalse(self.policy.raw["scheduled"]["blocking_by_default"])

    def test_fast_gate_does_not_invoke_deep_repetition(self) -> None:
        text = FAST_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("run_deep_reliability.py", text)
        self.assertNotIn("reliability_gate.py --passes 15", text)
        self.assertNotIn("seq 1 15", text)

    def test_specialist_gate_invokes_each_primary_specialist_exactly_once(self) -> None:
        text = SPECIALIST_WORKFLOW.read_text(encoding="utf-8")
        for tool in (
            "verify_reproducible_build.py",
            "verify_determinism.py",
            "verify_clean_room.py",
            "verify_concurrency.py",
        ):
            with self.subTest(tool=tool):
                self.assertEqual(text.count(tool), 1)
        for job_id in (
            "reproducible-build",
            "explicit-determinism",
            "clean-room",
            "concurrency-isolation",
            "diagnostic-security",
        ):
            with self.subTest(job_id=job_id):
                self.assertIn(f"  {job_id}:\n", text)

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
        old = (
            "      - name: Upload sanitised scanned reliability evidence\n"
            "        if: always() && steps.diagnostic_redaction.outcome == 'success' && steps.diagnostic_scan.outcome == 'success'"
        )
        new = (
            "      - name: Upload sanitised scanned reliability evidence\n"
            "        if: steps.diagnostic_redaction.outcome == 'success' && steps.diagnostic_scan.outcome == 'success'"
        )
        violations = self._violations_after(old, new)
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
