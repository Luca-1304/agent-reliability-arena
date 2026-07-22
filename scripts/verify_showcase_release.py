from __future__ import annotations

import json
from pathlib import Path

from agent_reliability_arena.showcase_release import verify_showcase_release


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print(json.dumps(verify_showcase_release(ROOT), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
