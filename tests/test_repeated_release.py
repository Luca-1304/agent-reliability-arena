from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.release_repeated_fixture import (
    verify_provider_free_repeated_experiment_release,
)


ROOT = Path(__file__).resolve().parents[1]


class RepeatedReleaseFixtureTests(unittest.TestCase):
    def test_provider_free_repeated_release_covers_resume_analysis_and_terminal_abort(self) -> None:
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

        self.assertEqual(result["planned_trials"], 4)
        self.assertEqual(result["completed_trials"], 4)
        self.assertEqual(result["general_first_trials"], 2)
        self.assertEqual(result["specialist_first_trials"], 2)
        self.assertEqual(result["paused_calls"], 5)
        self.assertEqual(result["resumed_calls"], 15)
        self.assertEqual(result["total_calls"], 20)
        self.assertEqual(result["verified_ledger_records"], 20)
        self.assertEqual(result["measured_total_tokens"], 400)
        self.assertEqual(result["measured_wall_clock_latency_ms"], 20)
        self.assertTrue(result["terminal_abort_preserved"])
        self.assertTrue(result["terminal_resume_refused"])
        self.assertFalse(result["provider_called"])
        self.assertFalse(result["comparative_claim_permitted"])


if __name__ == "__main__":
    unittest.main()
