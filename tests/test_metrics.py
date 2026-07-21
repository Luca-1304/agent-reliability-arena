from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.metrics import aggregate_metrics, pair_runs
from agent_reliability_arena.orchestration.general import GeneralOrchestrator
from agent_reliability_arena.orchestration.specialist import SpecialistOrchestrator
from tests.helpers import config


def all_runs():
    cfg = config()
    general = []
    specialist = []
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    for scenario in cfg.scenarios:
        general.append(GeneralOrchestrator().run(cfg, scenario, root / "general" / scenario))
        specialist.append(SpecialistOrchestrator().run(cfg, scenario, root / "specialist" / scenario))
    return temp, general, specialist


class MetricTests(unittest.TestCase):
    def test_exact_fixture_metrics(self) -> None:
        temp, general, specialist = all_runs()
        self.addCleanup(temp.cleanup)
        metrics = aggregate_metrics(general + specialist)
        self.assertEqual(metrics["evidence_status"], "deterministic_fixture")
        self.assertEqual(metrics["conditions"]["general"]["total_runs"], 8)
        self.assertEqual(metrics["conditions"]["general"]["verified_complete"], 2)
        self.assertEqual(metrics["conditions"]["general"]["claimed_completion"], 4)
        self.assertEqual(metrics["conditions"]["general"]["false_completion"], 3)
        self.assertEqual(metrics["conditions"]["general"]["false_completion_rate"], 0.75)
        self.assertEqual(metrics["conditions"]["general"]["claim_precision"], 0.25)
        self.assertEqual(metrics["conditions"]["general"]["silent_verified_completion"], 1)
        self.assertEqual(metrics["conditions"]["general"]["logical_model_calls"], 8)
        self.assertEqual(metrics["conditions"]["specialist"]["verified_complete"], 6)
        self.assertEqual(metrics["conditions"]["specialist"]["false_completion"], 0)
        self.assertEqual(metrics["conditions"]["specialist"]["claim_precision"], 1.0)
        self.assertEqual(metrics["conditions"]["specialist"]["recovered"], 4)
        self.assertEqual(metrics["conditions"]["specialist"]["recovery_rate"], 1.0)
        self.assertEqual(metrics["conditions"]["specialist"]["logical_model_calls"], 44)
        self.assertEqual(metrics["conditions"]["specialist"]["mean_logical_model_calls"], 5.5)
        self.assertEqual(metrics["paired"]["verified_completion_gain"], 4)
        self.assertEqual(metrics["paired"]["false_completion_reduction"], 3)
        self.assertEqual(metrics["paired"]["additional_logical_model_calls"], 36)
        self.assertEqual(
            metrics["paired"]["specialist_improved_scenarios"],
            ["false_success", "partial_write", "rollback", "timeout_before_write"],
        )

    def test_pairs_are_sorted_and_fair(self) -> None:
        temp, general, specialist = all_runs()
        self.addCleanup(temp.cleanup)
        pairs = pair_runs(list(reversed(general)), specialist)
        self.assertEqual([pair["scenario_id"] for pair in pairs], sorted(config().scenarios))
        self.assertTrue(all(pair["fairness_verified"] for pair in pairs))
        false_pair = next(pair for pair in pairs if pair["scenario_id"] == "false_success")
        self.assertEqual(false_pair["general_status"], "FAILED")
        self.assertEqual(false_pair["specialist_status"], "VERIFIED_COMPLETE")
        self.assertEqual(false_pair["specialist_extra_logical_calls"], 6)

    def test_missing_or_duplicate_pair_is_rejected(self) -> None:
        temp, general, specialist = all_runs()
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(ValueError, "same scenario set"):
            pair_runs(general[:-1], specialist)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pair_runs(general + [general[0]], specialist)


if __name__ == "__main__":
    unittest.main()
