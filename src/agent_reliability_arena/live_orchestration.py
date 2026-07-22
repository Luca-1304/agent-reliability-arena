from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ExperimentConfig
from .live_requests import LiveRequestFactory, PromptCatalog
from .live_role_outputs import (
    GeneralProposal,
    OperatorProposal,
    ParsedRoleOutput,
    parse_live_role_output,
)
from .models import ArenaAttempt
from .reliability.bridge import VerifierBridge, prepare_empty_root
from .schemas import AuditRecord, RecoveryRecord, StrategyPlan, SynthesisRecord
from .orchestration.policies import RETRYABLE_SCENARIOS, TERMINAL_SECURITY_SCENARIOS
from .transports import ModelCallRequest, ModelCallResult, ModelTransport


class LiveOrchestrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveRoleCallRecord:
    call_id: str
    role: str
    attempt_number: int
    request_digest: str
    response_id: str
    response_status: str
    raw_response_sha256: str
    raw_output_sha256: str
    canonical_output_sha256: str
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "call_id": self.call_id,
            "role": self.role,
            "attempt_number": self.attempt_number,
            "request_digest": self.request_digest,
            "response_id": self.response_id,
            "response_status": self.response_status,
            "raw_response_sha256": self.raw_response_sha256,
            "raw_output_sha256": self.raw_output_sha256,
            "canonical_output_sha256": self.canonical_output_sha256,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class LiveScenarioExecution:
    experiment_id: str
    condition: str
    scenario_id: str
    config_digest: str
    contract_digest: str
    role_calls: tuple[LiveRoleCallRecord, ...]
    attempts: tuple[ArenaAttempt, ...]
    final_status: str
    completion_claimed: bool
    recovered: bool
    security_rejected: bool

    @property
    def verified_complete(self) -> bool:
        return self.final_status == "VERIFIED_COMPLETE"

    @property
    def false_completion(self) -> bool:
        return self.completion_claimed and not self.verified_complete

    @property
    def silent_verified_completion(self) -> bool:
        return self.verified_complete and not self.completion_claimed

    @property
    def logical_model_calls(self) -> int:
        return len(self.role_calls)

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "condition": self.condition,
            "scenario_id": self.scenario_id,
            "config_digest": self.config_digest,
            "contract_digest": self.contract_digest,
            "role_calls": [record.to_dict() for record in self.role_calls],
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "final_status": self.final_status,
            "completion_claimed": self.completion_claimed,
            "verified_complete": self.verified_complete,
            "false_completion": self.false_completion,
            "silent_verified_completion": self.silent_verified_completion,
            "logical_model_calls": self.logical_model_calls,
            "recovered": self.recovered,
            "security_rejected": self.security_rejected,
        }


def _require_completed_result(request: ModelCallRequest, result: object) -> ModelCallResult:
    if not isinstance(result, ModelCallResult):
        raise LiveOrchestrationError("Transport did not return a ModelCallResult.")
    if result.call_id != request.call_id:
        raise LiveOrchestrationError("Transport result call_id does not match the request.")
    if result.request_digest != request.digest:
        raise LiveOrchestrationError("Transport result request_digest does not match the request.")
    if result.model_id != request.model_id:
        raise LiveOrchestrationError("Transport result model_id does not match the request.")
    if result.status != "completed":
        raise LiveOrchestrationError(f"Role call did not complete: status={result.status!r}.")
    if result.refusal_text is not None:
        raise LiveOrchestrationError("Role call returned a refusal.")
    if result.incomplete_reason is not None:
        raise LiveOrchestrationError("Role call returned an incomplete response.")
    if not result.output_text:
        raise LiveOrchestrationError("Role call returned no output text.")
    return result


def _invoke_role(
    factory: LiveRequestFactory,
    transport: ModelTransport,
    *,
    condition: str,
    role: str,
    scenario_id: str,
    attempt_number: int,
    role_payload: dict[str, object],
) -> tuple[LiveRoleCallRecord, ParsedRoleOutput]:
    request = factory.build(
        condition=condition,
        role=role,
        scenario_id=scenario_id,
        attempt_number=attempt_number,
        role_payload=role_payload,
    )
    result = _require_completed_result(request, transport.complete(request))
    try:
        parsed = parse_live_role_output(
            role,
            result.output_text,
            expected_attempt_number=attempt_number if role == "operator" else None,
        )
    except ValueError as exc:
        raise LiveOrchestrationError(f"Invalid {role} output: {exc}") from exc
    return (
        LiveRoleCallRecord(
            call_id=request.call_id,
            role=role,
            attempt_number=attempt_number,
            request_digest=request.digest,
            response_id=result.response_id,
            response_status=result.status,
            raw_response_sha256=result.raw_response_sha256,
            raw_output_sha256=parsed.raw_sha256,
            canonical_output_sha256=parsed.canonical_sha256,
            payload=dict(parsed.payload),
        ),
        parsed,
    )


def _validate_exact_contract(config: ExperimentConfig, proposal: OperatorProposal | GeneralProposal) -> None:
    if proposal.path != config.contract.path or proposal.content != config.contract.content:
        raise LiveOrchestrationError(
            "Proposed file action does not match the exact configured contract."
        )


def _authoritative_audit(result: Any, *, can_retry: bool) -> tuple[str, tuple[str, ...]]:
    conflicts: list[str] = []
    if result.report.reported_success and not result.observation.matches_contract:
        conflicts.append("reported_success_without_matching_state")
    if not result.report.reported_success and result.observation.matches_contract:
        conflicts.append("source_failure_but_postcondition_verified")
    if result.observation.matches_contract:
        decision = "accept"
    elif result.security_rejected:
        decision = "fail"
    elif can_retry:
        decision = "recover"
    else:
        decision = "fail"
    return decision, tuple(conflicts)


def _validate_audit(audit: AuditRecord, expected_decision: str, expected_conflicts: tuple[str, ...]) -> None:
    if audit.decision != expected_decision:
        raise LiveOrchestrationError(
            f"Auditor decision {audit.decision!r} does not match authoritative decision {expected_decision!r}."
        )
    if audit.conflicts != expected_conflicts:
        raise LiveOrchestrationError("Auditor conflicts do not match authoritative evidence conflicts.")
    expected_refs = ("source_report.json", "observation.json", "evaluation.json")
    if audit.evidence_refs != expected_refs:
        raise LiveOrchestrationError("Auditor evidence_refs do not match the required evidence set.")


def _validate_strategy(strategy: StrategyPlan, scenario_id: str) -> None:
    if scenario_id not in strategy.anticipated_failures:
        raise LiveOrchestrationError("Strategist did not anticipate the active scenario.")
    if scenario_id in RETRYABLE_SCENARIOS and scenario_id not in strategy.retryable_failures:
        raise LiveOrchestrationError("Strategist omitted the active retryable scenario.")
    if scenario_id in TERMINAL_SECURITY_SCENARIOS and scenario_id not in strategy.terminal_failures:
        raise LiveOrchestrationError("Strategist omitted the active terminal security scenario.")


def _validate_recovery(recovery: RecoveryRecord, scenario_id: str) -> None:
    if recovery.failure_class != scenario_id:
        raise LiveOrchestrationError("Recovery failure_class does not match the active scenario.")
    if not recovery.retry_justified:
        raise LiveOrchestrationError("Recovery refused an evidence-authorised retry.")
    if recovery.proposed_action != "write_file" or recovery.remaining_attempts != 1:
        raise LiveOrchestrationError("Recovery output does not match the one-attempt write policy.")


def _validate_synthesis(synthesis: SynthesisRecord, final_status: str) -> None:
    if synthesis.verified_status != final_status:
        raise LiveOrchestrationError("Synthesis verified_status does not match final verifier status.")
    expected_claim = final_status == "VERIFIED_COMPLETE"
    if synthesis.completion_claimed != expected_claim:
        raise LiveOrchestrationError("Synthesis completion claim does not match final verifier status.")
    if synthesis.evidence_refs != ("evaluation.json", "observation.json"):
        raise LiveOrchestrationError("Synthesis evidence_refs do not match final verifier evidence.")


def _evidence_payload(result: Any) -> dict[str, object]:
    return {
        "source_report": result.report.to_dict(),
        "observation": result.observation.to_dict(),
        "evaluation": result.evaluation.to_dict(),
        "security_rejected": bool(result.security_rejected),
    }


class LiveGeneralOrchestrator:
    def __init__(self, transport: ModelTransport, bridge: VerifierBridge | None = None) -> None:
        self.transport = transport
        self.bridge = bridge or VerifierBridge()

    def run(
        self,
        config: ExperimentConfig,
        catalog: PromptCatalog,
        scenario_id: str,
        root: Path,
    ) -> LiveScenarioExecution:
        prepare_empty_root(root)
        factory = LiveRequestFactory(config, catalog)
        call, parsed = _invoke_role(
            factory,
            self.transport,
            condition="general",
            role="general",
            scenario_id=scenario_id,
            attempt_number=1,
            role_payload={
                "phase": "general",
                "contract_digest": config.contract.digest,
            },
        )
        proposal = parsed.value
        if not isinstance(proposal, GeneralProposal):
            raise LiveOrchestrationError("General role did not produce a GeneralProposal.")
        if proposal.action != "write_file":
            raise LiveOrchestrationError("General role proposed no executable bounded action.")
        _validate_exact_contract(config, proposal)
        result = self.bridge.execute(config, scenario_id, root)
        attempt = ArenaAttempt.from_sandbox_result(result, 1)
        return LiveScenarioExecution(
            experiment_id=config.experiment_id,
            condition="general",
            scenario_id=scenario_id,
            config_digest=config.digest,
            contract_digest=config.contract.digest,
            role_calls=(call,),
            attempts=(attempt,),
            final_status=result.evaluation.status.value,
            completion_claimed=proposal.completion_claimed,
            recovered=False,
            security_rejected=result.security_rejected,
        )


class LiveSpecialistOrchestrator:
    def __init__(self, transport: ModelTransport, bridge: VerifierBridge | None = None) -> None:
        self.transport = transport
        self.bridge = bridge or VerifierBridge()

    def run(
        self,
        config: ExperimentConfig,
        catalog: PromptCatalog,
        scenario_id: str,
        root: Path,
    ) -> LiveScenarioExecution:
        prepare_empty_root(root)
        factory = LiveRequestFactory(config, catalog)
        role_calls: list[LiveRoleCallRecord] = []

        strategy_call, strategy_parsed = _invoke_role(
            factory,
            self.transport,
            condition="specialist",
            role="strategist",
            scenario_id=scenario_id,
            attempt_number=1,
            role_payload={
                "contract": config.contract.to_dict(),
                "scenarios": list(config.scenarios),
            },
        )
        role_calls.append(strategy_call)
        strategy = strategy_parsed.value
        if not isinstance(strategy, StrategyPlan):
            raise LiveOrchestrationError("Strategist did not produce a StrategyPlan.")
        _validate_strategy(strategy, scenario_id)

        operator_call, operator_parsed = _invoke_role(
            factory,
            self.transport,
            condition="specialist",
            role="operator",
            scenario_id=scenario_id,
            attempt_number=1,
            role_payload={
                "strategy": strategy.to_dict(),
                "contract": config.contract.to_dict(),
            },
        )
        role_calls.append(operator_call)
        operator = operator_parsed.value
        if not isinstance(operator, OperatorProposal):
            raise LiveOrchestrationError("Operator did not produce an OperatorProposal.")
        _validate_exact_contract(config, operator)

        first = self.bridge.execute(config, scenario_id, root)
        attempts = [ArenaAttempt.from_sandbox_result(first, 1)]
        can_retry = (
            config.max_mutation_attempts > 1
            and scenario_id in RETRYABLE_SCENARIOS
            and not first.security_rejected
            and not first.observation.matches_contract
        )
        expected_decision, expected_conflicts = _authoritative_audit(first, can_retry=can_retry)

        audit_call, audit_parsed = _invoke_role(
            factory,
            self.transport,
            condition="specialist",
            role="auditor",
            scenario_id=scenario_id,
            attempt_number=1,
            role_payload=_evidence_payload(first),
        )
        role_calls.append(audit_call)
        audit = audit_parsed.value
        if not isinstance(audit, AuditRecord):
            raise LiveOrchestrationError("Auditor did not produce an AuditRecord.")
        _validate_audit(audit, expected_decision, expected_conflicts)

        final = first
        recovered = False
        if expected_decision == "recover":
            recovery_call, recovery_parsed = _invoke_role(
                factory,
                self.transport,
                condition="specialist",
                role="recovery",
                scenario_id=scenario_id,
                attempt_number=1,
                role_payload={
                    "audit": audit.to_dict(),
                    "remaining_attempts": 1,
                },
            )
            role_calls.append(recovery_call)
            recovery = recovery_parsed.value
            if not isinstance(recovery, RecoveryRecord):
                raise LiveOrchestrationError("Recovery did not produce a RecoveryRecord.")
            _validate_recovery(recovery, scenario_id)

            second_operator_call, second_operator_parsed = _invoke_role(
                factory,
                self.transport,
                condition="specialist",
                role="operator",
                scenario_id=scenario_id,
                attempt_number=2,
                role_payload={
                    "recovery": recovery.to_dict(),
                    "contract": config.contract.to_dict(),
                },
            )
            role_calls.append(second_operator_call)
            second_operator = second_operator_parsed.value
            if not isinstance(second_operator, OperatorProposal):
                raise LiveOrchestrationError("Second operator did not produce an OperatorProposal.")
            _validate_exact_contract(config, second_operator)

            final = self.bridge.execute(config, "success", root)
            attempts.append(ArenaAttempt.from_sandbox_result(final, 2))
            recovered = (not first.observation.matches_contract) and final.observation.matches_contract
            second_decision, second_conflicts = _authoritative_audit(final, can_retry=False)

            second_audit_call, second_audit_parsed = _invoke_role(
                factory,
                self.transport,
                condition="specialist",
                role="auditor",
                scenario_id=scenario_id,
                attempt_number=2,
                role_payload=_evidence_payload(final),
            )
            role_calls.append(second_audit_call)
            second_audit = second_audit_parsed.value
            if not isinstance(second_audit, AuditRecord):
                raise LiveOrchestrationError("Second auditor did not produce an AuditRecord.")
            _validate_audit(second_audit, second_decision, second_conflicts)

        final_status = final.evaluation.status.value
        synthesis_call, synthesis_parsed = _invoke_role(
            factory,
            self.transport,
            condition="specialist",
            role="synthesiser",
            scenario_id=scenario_id,
            attempt_number=1,
            role_payload={
                "final_evidence": _evidence_payload(final),
                "recovered": recovered,
            },
        )
        role_calls.append(synthesis_call)
        synthesis = synthesis_parsed.value
        if not isinstance(synthesis, SynthesisRecord):
            raise LiveOrchestrationError("Synthesiser did not produce a SynthesisRecord.")
        _validate_synthesis(synthesis, final_status)

        return LiveScenarioExecution(
            experiment_id=config.experiment_id,
            condition="specialist",
            scenario_id=scenario_id,
            config_digest=config.digest,
            contract_digest=config.contract.digest,
            role_calls=tuple(role_calls),
            attempts=tuple(attempts),
            final_status=final_status,
            completion_claimed=synthesis.completion_claimed,
            recovered=recovered,
            security_rejected=any(attempt.security_rejected for attempt in attempts),
        )
