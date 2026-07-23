from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_reliability_arena.github_prerelease import (
    GithubPrereleaseError,
    build_github_prerelease_bundle,
    verify_github_prerelease_contract,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the GitHub prerelease contract and optionally build its exact asset bundle."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--dist", type=Path, help="Built distribution directory.")
    parser.add_argument("--output", type=Path, help="New prerelease bundle directory.")
    parser.add_argument("--source-commit", help="Exact lowercase 40-character source commit SHA.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.dist is None and args.output is None and args.source_commit is None:
            summary = verify_github_prerelease_contract(args.root)
        elif args.dist is not None and args.output is not None and args.source_commit is not None:
            summary = build_github_prerelease_bundle(
                args.root,
                args.dist,
                args.output,
                source_commit=args.source_commit,
            )
        else:
            raise GithubPrereleaseError(
                "--dist, --output and --source-commit must be supplied together when building a bundle."
            )
    except GithubPrereleaseError as exc:
        raise SystemExit(f"GitHub prerelease verification refused: {exc}") from exc
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
