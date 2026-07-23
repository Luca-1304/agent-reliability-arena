from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .supply_chain import SupplyChainError, verify_supply_chain_package


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arena-verify-supply-chain",
        description="Verify the deterministic public SBOM and supply-chain security package.",
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    args = parser.parse_args(argv)

    try:
        summary = verify_supply_chain_package(args.root)
    except SupplyChainError as exc:
        parser.exit(1, f"supply-chain verification failed: {exc}\n")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(verify_main())
