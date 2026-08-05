from __future__ import annotations

import argparse
import json
from pathlib import Path

from .citation_package import CitationPackageError, verify_citation_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the citation-ready technical report and provenance package."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    return parser


def verify_main() -> int:
    args = build_parser().parse_args()
    try:
        summary = verify_citation_package(args.root)
    except CitationPackageError as exc:
        raise SystemExit(f"Citation package verification refused: {exc}") from exc
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(verify_main())
