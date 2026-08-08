from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ci.branch_lifecycle import (
    BranchGitEvidence,
    BranchLifecyclePolicyError,
    BranchProvenance,
    classify_branch,
    classify_remote_branches,
    load_branch_lifecycle_policy,
    load_branch_provenance,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "branch-lifecycle-policy.json"
SOURCE_PATH = ROOT / "scripts/ci/branch_lifecycle.py"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


class BranchLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_branch_lifecycle_policy(POLICY_PATH)
        self.base = BranchGitEvidence(
            branch="feature/example",
            tip_sha="1" * 40,
            default_tip_sha="2" * 40,
            ancestor_of_default=False,
            ahead=3,
            behind=4,
        )

    def test_policy_is_permanently_report_only(self) -> None:
        self.assertFalse(self.policy.destructive_actions_supported)
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        payload["destructive_actions_supported"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(BranchLifecyclePolicyError):
                load_branch_lifecycle_policy(path)

    def test_explicit_evidence_retention_outranks_other_classes(self) -> None:
        provenance = BranchProvenance(
            pr_state="merged",
            superseded_by=101,
            retain_as_evidence=True,
            retention_reason="Preserve TDD red/green history",
            note=None,
        )
        row = classify_branch(self.base, self.policy, provenance)
        self.assertEqual(row.lifecycle_class, "historical-evidence-retain")
        self.assertFalse(row.deletion_authorized)

    def test_open_pr_outranks_cleanup_candidate(self) -> None:
        evidence = BranchGitEvidence(
            branch="tmp/live-work",
            tip_sha="1" * 40,
            default_tip_sha="2" * 40,
            ancestor_of_default=False,
            ahead=1,
            behind=0,
        )
        provenance = BranchProvenance(
            pr_state="open",
            superseded_by=None,
            retain_as_evidence=False,
            retention_reason=None,
            note=None,
        )
        row = classify_branch(evidence, self.policy, provenance)
        self.assertEqual(row.lifecycle_class, "active")
        self.assertFalse(row.deletion_authorized)

    def test_release_prefix_is_retained(self) -> None:
        evidence = BranchGitEvidence(
            branch="release/v9-review",
            tip_sha="1" * 40,
            default_tip_sha="2" * 40,
            ancestor_of_default=False,
            ahead=5,
            behind=2,
        )
        row = classify_branch(evidence, self.policy, None)
        self.assertEqual(row.lifecycle_class, "release-archive-retain")

    def test_merged_or_superseded_provenance_is_review_candidate_not_delete_authority(self) -> None:
        provenance = BranchProvenance(
            pr_state="merged",
            superseded_by=None,
            retain_as_evidence=False,
            retention_reason=None,
            note=None,
        )
        row = classify_branch(self.base, self.policy, provenance)
        self.assertEqual(row.lifecycle_class, "merged-superseded-candidate")
        self.assertFalse(row.deletion_authorized)

    def test_temporary_prefix_is_review_candidate_only(self) -> None:
        evidence = BranchGitEvidence(
            branch="temp/old-inspection",
            tip_sha="1" * 40,
            default_tip_sha="2" * 40,
            ancestor_of_default=False,
            ahead=2,
            behind=6,
        )
        row = classify_branch(evidence, self.policy, None)
        self.assertEqual(row.lifecycle_class, "temporary-obsolete-candidate")
        self.assertFalse(row.deletion_authorized)

    def test_squash_like_non_ancestor_remains_uncertain_without_provenance(self) -> None:
        row = classify_branch(self.base, self.policy, None)
        self.assertEqual(row.lifecycle_class, "uncertain")
        self.assertFalse(row.deletion_authorized)

    def test_ancestor_of_main_can_be_merged_candidate_but_never_authorized(self) -> None:
        evidence = BranchGitEvidence(
            branch="feature/fully-merged",
            tip_sha="1" * 40,
            default_tip_sha="2" * 40,
            ancestor_of_default=True,
            ahead=0,
            behind=7,
        )
        row = classify_branch(evidence, self.policy, None)
        self.assertEqual(row.lifecycle_class, "merged-superseded-candidate")
        self.assertFalse(row.deletion_authorized)

    def test_provenance_rejects_unknown_branch_and_invalid_state(self) -> None:
        payload = {
            "schema_version": "branch-lifecycle-provenance-v1",
            "branches": {
                "missing/branch": {
                    "pr_state": "destroyed",
                    "superseded_by": None,
                    "retain_as_evidence": False,
                    "retention_reason": None,
                    "note": None,
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "provenance.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(BranchLifecyclePolicyError):
                load_branch_provenance(path, known_branches={"feature/example"})

    def test_remote_report_contains_each_non_default_branch_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            work = root / "work"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "init", "-b", "main", str(work)], check=True, stdout=subprocess.PIPE)
            _git(work, "config", "user.name", "Branch Test")
            _git(work, "config", "user.email", "branch-test@example.invalid")
            (work / "base.txt").write_text("base\n", encoding="utf-8")
            _git(work, "add", "base.txt")
            _git(work, "commit", "-m", "base")
            _git(work, "remote", "add", "origin", str(remote))
            _git(work, "push", "-u", "origin", "main")

            _git(work, "checkout", "-b", "feature/merged")
            (work / "merged.txt").write_text("merged\n", encoding="utf-8")
            _git(work, "add", "merged.txt")
            _git(work, "commit", "-m", "merged")
            _git(work, "push", "-u", "origin", "feature/merged")
            _git(work, "checkout", "main")
            _git(work, "merge", "--no-ff", "feature/merged", "-m", "merge feature")
            _git(work, "push", "origin", "main")

            _git(work, "checkout", "-b", "tmp/diverged")
            (work / "tmp.txt").write_text("tmp\n", encoding="utf-8")
            _git(work, "add", "tmp.txt")
            _git(work, "commit", "-m", "tmp")
            _git(work, "push", "-u", "origin", "tmp/diverged")
            _git(work, "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*")

            report = classify_remote_branches(work, self.policy, provenance={})

        names = [row.branch for row in report.branches]
        self.assertEqual(names, ["feature/merged", "tmp/diverged"])
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(not row.deletion_authorized for row in report.branches))
        classes = {row.branch: row.lifecycle_class for row in report.branches}
        self.assertEqual(classes["feature/merged"], "merged-superseded-candidate")
        self.assertEqual(classes["tmp/diverged"], "temporary-obsolete-candidate")

    def test_classifier_source_has_no_destructive_git_invocation(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            '"push"',
            '"update-ref"',
            '"branch", "-D"',
            '"tag", "-d"',
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
