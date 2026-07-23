from __future__ import annotations

import json
from pathlib import Path

from agent_reliability_arena.supply_chain import verify_supply_chain_package


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    print(json.dumps(verify_supply_chain_package(ROOT), indent=2, sort_keys=True))
