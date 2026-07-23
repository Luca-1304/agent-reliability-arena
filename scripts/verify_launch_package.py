from __future__ import annotations

import json
from pathlib import Path

from agent_reliability_arena.launch_package import verify_launch_package


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print(json.dumps(verify_launch_package(ROOT), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
