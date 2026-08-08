from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_history_boundary.py"
WORKFLOW = ROOT / ".github" / "workflows" / "history-boundary.yml"
GUIDE = ROOT / "docs" / "REPOSITORY_HISTORY_BOUNDARY.md"

SPEC = importlib.util.spec_from_file_location("verify_history_boundary", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
HISTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HISTORY)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class HistoryBoundaryTests(unittest.TestCase):
    def build_repository(self, root: Path) -> tuple[str, str, str, str]:
        git(root, "init", "--initial-branch=main")
        git(root, "config", "user.name", "History Boundary Test")
        git(root, "config", "user.email", "history-boundary@example.invalid")

        parent = commit_file(root, "base.txt", "base\n", "base")
        boundary = commit_file(root, "boundary.txt", "clean\n", "clean boundary")
        boundary_tree = git(root, "rev-parse", f"{boundary}^{{tree}}")
        head = commit_file(root, "head.txt", "head\n", "head")
        return parent, boundary, boundary_tree, head

    def test_valid_clean_lineage_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            parent, boundary, tree, head = self.build_repository(repo)

            result = HISTORY.verify(
                repo,
                boundary_commit=boundary,
                boundary_parent=parent,
                boundary_tree=tree,
            )

            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["head"], head)
            self.assertEqual(result["boundary_commit"], boundary)
            self.assertEqual(result["remote_branches_checked"], 0)

    def test_unknown_boundary_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            parent, _, tree, _ = self.build_repository(repo)

            with self.assertRaises(HISTORY.HistoryBoundaryError):
                HISTORY.verify(
                    repo,
                    boundary_commit="0" * 40,
                    boundary_parent=parent,
                    boundary_tree=tree,
                )

    def test_parent_or_tree_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            parent, boundary, tree, head = self.build_repository(repo)

            with self.assertRaisesRegex(
                HISTORY.HistoryBoundaryError,
                "parent changed",
            ):
                HISTORY.verify(
                    repo,
                    boundary_commit=boundary,
                    boundary_parent=head,
                    boundary_tree=tree,
                )

            with self.assertRaisesRegex(
                HISTORY.HistoryBoundaryError,
                "tree no longer matches",
            ):
                HISTORY.verify(
                    repo,
                    boundary_commit=boundary,
                    boundary_parent=parent,
                    boundary_tree="f" * 40,
                )

    def test_remote_branch_outside_boundary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            parent, boundary, tree, head = self.build_repository(repo)
            git(repo, "update-ref", "refs/remotes/origin/main", head)
            git(repo, "update-ref", "refs/remotes/origin/stale", parent)

            with self.assertRaisesRegex(
                HISTORY.HistoryBoundaryError,
                "does not descend",
            ):
                HISTORY.verify(
                    repo,
                    boundary_commit=boundary,
                    boundary_parent=parent,
                    boundary_tree=tree,
                    verify_remote_branches=True,
                )

    def test_workflow_fetches_complete_writable_history(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "fetch-depth: 0",
            "+refs/heads/*:refs/remotes/origin/*",
            "--verify-remote-branches",
            "permissions:\n  contents: read",
        ):
            self.assertIn(marker, text)

    def test_workflow_emits_fresh_report_only_branch_lifecycle_summary(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        command = (
            "python scripts/ci/report_branch_lifecycle.py "
            "--policy branch-lifecycle-policy.json "
            "--provenance branch-lifecycle-provenance.json "
            "--output /tmp/branch-lifecycle.json"
        )
        self.assertIn(command, text)
        self.assertIn("deletion_authorized", text)
        self.assertIn("destructive_actions_supported", text)
        self.assertNotIn("git push", text)
        self.assertNotIn("git update-ref", text)

    def test_workflow_retains_exact_report_as_short_lived_read_only_evidence(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            "name: branch-lifecycle-report-${{ github.run_attempt }}",
            "path: /tmp/branch-lifecycle.json",
            "if-no-files-found: error",
            "retention-days: 14",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("actions: write", text)

    def test_recovery_guide_requires_a_fresh_clone(self) -> None:
        text = GUIDE.read_text(encoding="utf-8")
        for marker in (
            "Use a **fresh clone**",
            "must not be merged, rebased or force-pushed",
            "Do not merge an old branch",
            "provider-side garbage collection",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
