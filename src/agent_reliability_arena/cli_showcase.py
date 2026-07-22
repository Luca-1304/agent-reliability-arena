from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .showcase_release import verify_showcase_release


def verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the disclosure-safe public showcase package without provider access."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing showcase/publication-manifest.json.",
    )
    args = parser.parse_args(argv)
    try:
        summary = verify_showcase_release(args.root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0
