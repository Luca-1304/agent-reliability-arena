from __future__ import annotations

from pathlib import Path

from ..config import ExperimentConfig
from ..models import ArenaAttempt, ArenaRun
from ..reliability.bridge import VerifierBridge, prepare_empty_root
from ..schemas import AuditRecord, OperatorRecord, RecoveryRecord, StrategyPlan, SynthesisRecord
from .policies import RETRYABLE_SCENARIOS, TERMINAL_SECURITY_SCENARIOS


class SpecialistOrchestrator:
    name = "fixture-specialist-v1"

    def __init__(self, bridge: VerifierBridge | None = None) -> None:
        self.bridge = bridge or VerifierBridge()

    @staticmethod
    def _strategy(config: ExperimentConfig) -> StrategyPlan:
        return StrategyPlan(
            contract_summary=f"Write exact UTF-8 content to {config.contract.path}.",
            required_postcondition="Independent path, size, SHA-256, and content match.",
            permitted_actions=("write_file",),
            anticipated_failures=tuple(config.scenarios),
            retryable_failures=tuple(s for s in config.scenarios if s in RETRYABLE_SCENARIOS),
            terminal_failures=tuple(s for s in config.scenarios if s in TERMINAL_SECURITY_SCENARIOS),
            stop_conditions=("verified", "attempt_limit", "security_rejection"),
        )

    @staticmethod
    def _operator(result, attempt_number: int, config: ExperimentConfig) -> OperatorRecord:
        return OperatorRecord(
            approved_action="write_file",
            attempted_path=result.report.attempted_path,
            attempted_content_sha256=config.contract.expected_sha256,
            attempt_number=attempt_number,
            source_event_id=result.report.source_event_id,
        )

    @staticmethod
    def _audit(result, *, can_retry: bool) -> AuditRecord:
        conflicts: list[str] = []
        if result.report.reported_success and not result.observation.matches_contract:
            conflicts.append("reported_success_without_matching_state")
        if not result.report.reported_success and result.observation.matches_contract:
            conflicts.append("source_failure_but_postcondition_verified")
        if result.observation.matches_contract:
            decision = "accept"
            observation = "Independent state matches the full contract."
        elif result.security_rejected:
            decision = "fail"
            observation = "Independent execution recorded a terminal security rejection."
        elif can_retry:
            decision = "recover"
            observation = "Independent state does not match the contract and one retry remains."
        else:
            decision = "fail"
            observation = "Independent state does not match the contract and no retry remains."
        return AuditRecord(
            decision=decision,
            source_assessment=(
                "Source reported success." if result.report.reported_success else "Source did not report success."
            ),
            observation_assessment=observation,
            conflicts=tuple(conflicts),
            evidence_refs=("source_report.json", "observation.json", "evaluation.json"),
        )

    def run(self, config: ExperimentConfig, scenario_id: str, root: Path) -> ArenaRun:
        prepare_empty_root(root)
        strategy = self._strategy(config)
        first = self.bridge.execute(config, scenario_id, root)
        attempts = [ArenaAttempt.from_sandbox_result(first, 1)]
        operators = [self._operator(first, 1, config).to_dict()]
        audits = [
            self._audit(
                first,
                can_retry=(
                    config.max_mutation_attempts > 1
                    and scenario_id in RETRYABLE_SCENARIOS
                    and not first.security_rejected
                ),
            )
        ]
        recovery: RecoveryRecord | None = None
        final = first
        recovered = False

        if audits[0].decision == "recover":
            recovery = RecoveryRecord(
                failure_class=scenario_id,
                retry_justified=True,
                proposed_action="write_file",
                remaining_attempts=1,
                refusal_reason=None,
            )
            final = self.bridge.execute(config, "success", root)
            attempts.append(ArenaAttempt.from_sandbox_result(final, 2))
            operators.append(self._operator(final, 2, config).to_dict())
            audits.append(self._audit(final, can_retry=False))
            recovered = (not first.observation.matches_contract) and final.observation.matches_contract

        verified_status = final.evaluation.status.value
        completion_claimed = verified_status == "VERIFIED_COMPLETE"
        synthesis = SynthesisRecord(
            completion_claimed=completion_claimed,
            verified_status=verified_status,
            summary=(
                "Independent evidence verified the contracted file."
                if completion_claimed
                else "The contracted file was not independently verified."
            ),
            limitations=("Deterministic fixture policy, not external-model performance.",),
            evidence_refs=("evaluation.json", "observation.json"),
        )
        logical_calls = 4 if recovery is None else 7
        return ArenaRun(
            run_id=f"{config.experiment_id}--specialist--{scenario_id}",
            condition="specialist",
            scenario_id=scenario_id,
            config_digest=config.digest,
            contract_digest=config.contract.digest,
            fairness_fingerprint=config.fairness_fingerprint("specialist"),
            attempts=tuple(attempts),
            final_status=verified_status,
            completion_claimed=completion_claimed,
            logical_model_calls=logical_calls,
            recovered=recovered,
            security_rejected=any(attempt.security_rejected for attempt in attempts),
            strategy=strategy.to_dict(),
            operator_records=tuple(operators),
            audit_records=tuple(audit.to_dict() for audit in audits),
            recovery=recovery.to_dict() if recovery else None,
            synthesis=synthesis.to_dict(),
        )
