from __future__ import annotations

from pathlib import Path

from completion_verifier.sandbox import SandboxReferenceRunner
from completion_verifier.sandbox.models import SandboxRunResult

from ..config import ExperimentConfig


def prepare_empty_root(root: Path) -> None:
    if root.exists():
        if not root.is_dir():
            raise FileExistsError("Run root must be an empty directory.")
        if any(root.iterdir()):
            raise FileExistsError("Run root must be empty before execution.")
    else:
        root.mkdir(parents=True)


class VerifierBridge:
    def __init__(self) -> None:
        self._runner = SandboxReferenceRunner()

    def execute(
        self,
        config: ExperimentConfig,
        scenario_id: str,
        root: Path,
    ) -> SandboxRunResult:
        return self._runner.run(scenario_id, config.contract, root)
