from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

try:
    from scripts.ci.branch_lifecycle import (
        BranchLifecyclePolicyError,
        classify_remote_branches,
        collect_remote_branch_evidence,
        load_branch_lifecycle_policy,
        load_branch_provenance,
    )
except ModuleNotFoundError:  # Direct execution from scripts/ci.
    from branch_lifecycle import (  # type: ignore[no-redef]
        BranchLifecyclePolicyError,
        classify_remote_branches,
        collect_remote_branch_evidence,
        load_branch_lifecycle_policy,
        load_branch_provenance,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify fetched remote branches without authorizing or performing cleanup."
    )
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--policy", type=Path, default=Path("branch-lifecycle-policy.json"))
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        policy = load_branch_lifecycle_policy(args.policy)
        _, evidence = collect_remote_branch_evidence(args.repo, policy)
        known = {row.branch for row in evidence}
        provenance = (
            load_branch_provenance(args.provenance, known_branches=known)
            if args.provenance is not None
            else {}
        )
        report = classify_remote_branches(args.repo, policy, provenance)
        payload = report.to_dict()
    except BranchLifecyclePolicyError as exc:
        payload = {
            "schema_version": "branch-lifecycle-report-v1",
            "status": "failed",
            "destructive_actions_supported": False,
            "deletion_authorized": False,
            "error": str(exc),
        }
        print(json.dumps(payload, sort_keys=True))
        return 1

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        output = args.output
        if output.exists() or output.is_symlink():
            raise SystemExit(f"refusing to overwrite existing report: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
