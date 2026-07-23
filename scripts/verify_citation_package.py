from __future__ import annotations

import json
from pathlib import Path

from agent_reliability_arena.citation_package import verify_citation_package


if __name__ == "__main__":
    print(json.dumps(verify_citation_package(Path.cwd()), indent=2, sort_keys=True))
