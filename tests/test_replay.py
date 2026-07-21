from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.artifacts import write_experiment_artifacts
from agent_reliability_arena.orchestration.general import GeneralOrchestrator
from agent_reliability_arena.orchestration.specialist import SpecialistOrchestrator
from agent_reliability_arena.replay import replay_experiment
from tests.helpers import config


class ReplayTests(unittest.TestCase):
    def test_replay_is_read_only_and_returns_locked_metrics(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            items = []
            for condition, orchestrator in (
                ("general", GeneralOrchestrator()),
                ("specialist", SpecialistOrchestrator()),
            ):
                for scenario in cfg.scenarios:
                    items.append(orchestrator.run(cfg, scenario, base / "sandbox" / condition / scenario))
            output = base / "artifacts"
            write_experiment_artifacts(cfg, items, output)
            before = {p.relative_to(output).as_posix(): p.stat().st_mtime_ns for p in output.rglob("*") if p.is_file()}
            replay = replay_experiment(output)
            after = {p.relative_to(output).as_posix(): p.stat().st_mtime_ns for p in output.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertTrue(replay["manifest_verified"])
            self.assertEqual(replay["evidence_status"], "deterministic_fixture")
            self.assertEqual(replay["general_verified"], 2)
            self.assertEqual(replay["specialist_verified"], 6)
            self.assertEqual(replay["paired_runs"], 8)


if __name__ == "__main__":
    unittest.main()
