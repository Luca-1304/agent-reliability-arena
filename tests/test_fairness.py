from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.orchestration.general import GeneralOrchestrator
from agent_reliability_arena.orchestration.specialist import SpecialistOrchestrator
from agent_reliability_arena.orchestration.policies import assert_fair_pair
from tests.helpers import config


class FairnessTests(unittest.TestCase):
    def test_pair_has_identical_task_contract_scenario_and_model_controls(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            general = GeneralOrchestrator().run(cfg, "false_success", root / "general")
            specialist = SpecialistOrchestrator().run(cfg, "false_success", root / "specialist")
        assert_fair_pair(general, specialist)
        self.assertEqual(general.fairness_fingerprint, specialist.fairness_fingerprint)
        self.assertEqual(general.scenario_id, specialist.scenario_id)
        self.assertEqual(general.contract_digest, specialist.contract_digest)

    def test_fairness_check_rejects_mismatched_scenario(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            general = GeneralOrchestrator().run(cfg, "success", root / "general")
            specialist = SpecialistOrchestrator().run(cfg, "rollback", root / "specialist")
        with self.assertRaisesRegex(ValueError, "scenario"):
            assert_fair_pair(general, specialist)


if __name__ == "__main__":
    unittest.main()
