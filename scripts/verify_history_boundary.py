from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


BOUNDARY_COMMIT = "2fe7d730a688f020e878e24d711d8f153e0cfcbb"
BOUNDARY_PARENT = "7b60bae190f11703e20126286dfc5eb7fd5df8e1"
BOUNDARY_TREE = "1874dbd5fe601748b22e4e9dea0d84657e399dd4"


class HistoryBoundaryError(RuntimeError):
    """Raised when repository history no longer satisfies the clean-lineage contract."""


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise HistoryBoundaryError("git is required to verify repository history.") from exc

    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise HistoryBoundaryError(f"git {' '.join(args)}: {detail}")
    return completed


def _resolve(repo: Path, expression: str) -> str:
    return _git(repo, "rev-parse", expression).stdout.strip()


def _require_ancestor(repo: Path, ancestor: str, descendant: str, label: str) -> None:
    completed = _git(
        repo,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )
    if completed.returncode == 1:
        raise HistoryBoundaryError(
            f"{label} does not descend from the clean repository history boundary."
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unable to compare ancestry"
        raise HistoryBoundaryError(f"Could not verify {label}: {detail}")


def verify(
    repo: Path = Path("."),
    *,
    boundary_commit: str = BOUNDARY_COMMIT,
    boundary_parent: str = BOUNDARY_PARENT,
    boundary_tree: str = BOUNDARY_TREE,
    verify_remote_branches: bool = False,
) -> dict[str, object]:
    root = Path(repo).resolve()
    inside = _git(root, "rev-parse", "--is-inside-work-tree").stdout.strip()
    if inside != "true":
        raise HistoryBoundaryError(f"Not a Git work tree: {root}")

    resolved_boundary = _resolve(root, f"{boundary_commit}^{{commit}}")
    if resolved_boundary != boundary_commit:
        raise HistoryBoundaryError("The configured history boundary resolves unexpectedly.")

    parent_record = _git(
        root,
        "rev-list",
        "--parents",
        "-n",
        "1",
        boundary_commit,
    ).stdout.split()
    expected_parent_record = [boundary_commit, boundary_parent]
    if parent_record != expected_parent_record:
        raise HistoryBoundaryError(
            "The clean history boundary parent changed or gained an additional parent."
        )

    resolved_tree = _resolve(root, f"{boundary_commit}^{{tree}}")
    if resolved_tree != boundary_tree:
        raise HistoryBoundaryError("The clean history boundary tree no longer matches.")

    head = _resolve(root, "HEAD")
    _require_ancestor(root, boundary_commit, head, "HEAD")

    branches_checked = 0
    if verify_remote_branches:
        refs = _git(
            root,
            "for-each-ref",
            "--format=%(refname)",
            "refs/remotes/origin",
        ).stdout.splitlines()
        branch_refs = sorted(ref for ref in refs if ref != "refs/remotes/origin/HEAD")
        if not branch_refs:
            raise HistoryBoundaryError("No fetched origin branches were available to verify.")
        for ref in branch_refs:
            _require_ancestor(root, boundary_commit, ref, ref)
            branches_checked += 1

    return {
        "schema_version": "repository-history-boundary-v1",
        "status": "verified",
        "head": head,
        "boundary_commit": boundary_commit,
        "boundary_parent": boundary_parent,
        "boundary_tree": boundary_tree,
        "remote_branches_checked": branches_checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed if repository history leaves the approved clean lineage."
    )
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--verify-remote-branches", action="store_true")
    args = parser.parse_args()

    try:
        result = verify(
            args.repo,
            verify_remote_branches=args.verify_remote_branches,
        )
    except HistoryBoundaryError as exc:
        parser.exit(1, f"history boundary verification failed: {exc}\n")

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
