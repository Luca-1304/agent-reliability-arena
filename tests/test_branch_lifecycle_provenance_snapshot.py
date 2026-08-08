from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.ci.branch_lifecycle import (
    BranchLifecyclePolicyError,
    load_branch_lifecycle_policy,
    load_branch_provenance,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "branch-lifecycle-policy.json"
PROVENANCE_PATH = ROOT / "branch-lifecycle-provenance.json"
HISTORY_WORKFLOW = ROOT / ".github/workflows/history-boundary.yml"

EXPECTED_PROVENANCE = {
    "ci/future-proof-repeated-verification": ("merged", None),
    "ci/reliability-gate-v2": ("merged", None),
    "design/layered-reliability-assurance": ("merged", None),
    "docs/branch-protection-contract": ("merged", None),
    "feature/clean-room-concurrency-specialists-main": ("merged", None),
    "feature/determinism-reproducibility-specialists": ("merged", None),
    "feature/layered-reliability-workflows": ("merged", None),
    "feature/policy-driven-deep-gate": ("merged", None),
    "feature/privacy-safe-diagnostic-scanner": ("merged", None),
    "feature/reliability-evidence-contract": ("merged", None),
    "feature/reliability-policy-foundation": ("merged", None),
    "feature/structural-ci-policy": ("merged", None),
    "plan/layered-reliability-assurance": ("closed_unmerged", 95),
}


class BranchLifecycleProvenanceSnapshotTests(unittest.TestCase):
    def test_reviewed_provenance_covers_exact_legacy_uncertainty_set(self) -> None:
        payload = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "branch-lifecycle-provenance-v1")
        self.assertEqual(set(payload["branches"]), set(EXPECTED_PROVENANCE))
        provenance = load_branch_provenance(
            PROVENANCE_PATH,
            known_branches=set(EXPECTED_PROVENANCE),
        )
        for branch, (state, superseded_by) in EXPECTED_PROVENANCE.items():
            with self.subTest(branch=branch):
                self.assertEqual(provenance[branch].pr_state, state)
                self.assertEqual(provenance[branch].superseded_by, superseded_by)
                self.assertFalse(provenance[branch].retain_as_evidence)
                self.assertIsNone(provenance[branch].retention_reason)

    def test_core_control_plane_tdd_branches_remain_explicitly_retained(self) -> None:
        policy = load_branch_lifecycle_policy(POLICY_PATH)
        for branch in (
            "feature/branch-lifecycle-reporting",
            "feature/branch-provenance-enrichment",
        ):
            self.assertIn(branch, policy.explicit_retained_branches)

    def test_history_workflow_consumes_reviewed_provenance_without_write_authority(self) -> None:
        text = HISTORY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "--provenance branch-lifecycle-provenance.json",
            text,
        )
        self.assertIn("permissions:\n  contents: read", text)
        self.assertNotIn("actions: write", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("git update-ref", text)


if __name__ == "__main__":
    unittest.main()
