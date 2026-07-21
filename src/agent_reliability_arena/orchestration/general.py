from __future__ import annotations

from pathlib import Path

from ..config import ExperimentConfig
from ..models import ArenaAttempt, ArenaRun
from ..reliability.bridge import VerifierBridge, prepare_empty_root


class GeneralOrchestrator:
    name = "fixture-general-v1"

    def __init__(self, bridge: VerifierBridge | None = None) -> None:
        self.bridge = bridge or VerifierBridge()

    def run(self, config: ExperimentConfig, scenario_id: str, root: Path) -> ArenaRun:
        prepare_empty_root(root)
        sandbox_result = self.bridge.execute(config, scenario_id, root)
        attempt = ArenaAttempt.from_sandbox_result(sandbox_result, 1)
        return ArenaRun(
            run_id=f"{config.experiment_id}--general--{scenario_id}",
            condition="general",
            scenario_id=scenario_id,
            config_digest=config.digest,
            contract_digest=config.contract.digest,
            fairness_fingerprint=config.fairness_fingerprint("general"),
            attempts=(attempt,),
            final_status=sandbox_result.evaluation.status.value,
            completion_claimed=sandbox_result.report.completion_claimed,
            logical_model_calls=1,
            recovered=False,
            security_rejected=sandbox_result.security_rejected,
        )
