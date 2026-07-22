from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.release_repeated_fixture import (
    verify_provider_free_repeated_experiment_release,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = ExperimentConfig.from_dict(
        json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
    )
    catalog = PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )
    with tempfile.TemporaryDirectory() as directory:
        result = verify_provider_free_repeated_experiment_release(
            config,
            catalog,
            Path(directory),
        )
    assert result["planned_trials"] == 4
    assert result["completed_trials"] == 4
    assert result["general_first_trials"] == 2
    assert result["specialist_first_trials"] == 2
    assert result["paused_calls"] == 5
    assert result["resumed_calls"] == 15
    assert result["total_calls"] == 20
    assert result["verified_ledger_records"] == 20
    assert result["measured_total_tokens"] == 400
    assert result["measured_wall_clock_latency_ms"] == 20
    assert result["terminal_abort_preserved"] is True
    assert result["terminal_resume_refused"] is True
    assert result["provider_called"] is False
    assert result["comparative_claim_permitted"] is False
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
