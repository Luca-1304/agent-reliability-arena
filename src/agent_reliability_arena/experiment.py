from __future__ import annotations

import tempfile
from pathlib import Path

from .artifacts import write_experiment_artifacts
from .config import ExperimentConfig
from .models import ArenaRun
from .orchestration.general import GeneralOrchestrator
from .orchestration.specialist import SpecialistOrchestrator


def execute_fixture_experiment(config: ExperimentConfig, output: Path) -> dict[str, object]:
    runs: list[ArenaRun] = []
    with tempfile.TemporaryDirectory(prefix="arena-sandbox-") as directory:
        root = Path(directory)
        for condition, orchestrator in (
            ("general", GeneralOrchestrator()),
            ("specialist", SpecialistOrchestrator()),
        ):
            for scenario in config.scenarios:
                runs.append(orchestrator.run(config, scenario, root / condition / scenario))
    return write_experiment_artifacts(config, runs, output)
