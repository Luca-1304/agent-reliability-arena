from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_reliability_arena.pages_site import PagesSiteError, stage_pages_site


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify and stage the exact disclosure-safe GitHub Pages artifact."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--output", type=Path, required=True, help="New staging directory.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = stage_pages_site(args.root, args.output)
    except PagesSiteError as exc:
        raise SystemExit(f"Pages staging refused: {exc}") from exc
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
