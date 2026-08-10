from __future__ import annotations

import json
import sys
from pathlib import Path

from agent_reliability_arena.stage7_candidate import verify_stage7_candidate


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        result = verify_stage7_candidate(
            ROOT / "examples" / "stage7_candidate",
            ROOT / "examples" / "live_prompt_catalog.json",
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
