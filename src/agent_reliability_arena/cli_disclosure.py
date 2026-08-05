from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .disclosure_export import (
    PriceSource,
    verify_disclosure_safe_empirical_export,
    write_disclosure_safe_empirical_export,
)


def _load_price_source(path: Path | None) -> PriceSource | None:
    if path is None:
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PriceSource.from_dict(raw)


def export_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a disclosure-safe public bundle from an indexed private evidence set."
    )
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--price-source", type=Path)
    args = parser.parse_args(argv)
    try:
        export = write_disclosure_safe_empirical_export(
            args.private_root,
            args.output,
            index_path=args.index,
            price_source=_load_price_source(args.price_source),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    aggregate = export["aggregate"]
    assert isinstance(aggregate, dict)
    print(
        json.dumps(
            {
                "bundle_digest": export["bundle_digest"],
                "runs": aggregate["runs_total"],
                "completed_runs": aggregate["completed_runs"],
                "aborted_runs": aggregate["aborted_runs"],
                "provider_called": False,
                "comparative_claim_permitted": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a disclosure-safe public empirical bundle without provider access."
    )
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = verify_disclosure_safe_empirical_export(args.input)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0
