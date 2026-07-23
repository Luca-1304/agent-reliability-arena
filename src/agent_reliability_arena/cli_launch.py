from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .launch_package import verify_launch_package


def verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the digest-pinned public launch and career conversion package."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing showcase/launch-package-manifest.json.",
    )
    args = parser.parse_args(argv)
    try:
        summary = verify_launch_package(args.root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(verify_main())
