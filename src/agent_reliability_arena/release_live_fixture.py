from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import ExperimentConfig
from .live_orchestration import LiveGeneralOrchestrator, LiveSpecialistOrchestrator
from .live_requests import PromptCatalog
from .transports import (
    ModelCallRequest,
    ModelCallResult,
    ModelUsage,
    RecordingTransport,
    verify_transport_ledger,
)

_EVIDENCE_REFS = ["source_report.json", "observation.json", "evaluation.json"]


def _compact(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _general_output(config: ExperimentConfig) -> dict[str, object]:
    return {
        "action": "write_file",
        "path": config.contract.path,
        "content": config.contract.content,
        "completion_claimed": True,
        "rationale": "The bounded contract action is explicit.",
    }


def _strategy_output(config: ExperimentConfig) -> dict[str, object]:
    return {
        "contract_summary": f"Write exact UTF-8 content to {config.contract.path}.",
        "required_postcondition": "Independent path, size, digest and content match.",
        "permitted_actions": ["write_file"],
        "anticipated_failures": list(config.scenarios),
        "retryable_failures": [
            "false_success",
            "partial_write",
            "timeout_before_write",
            "rollback",
        ],
        "terminal_failures": ["path_traversal", "symlink_escape"],
        "stop_conditions": ["verified", "attempt_limit", "security_rejection"],
    }


def _operator_output(config: ExperimentConfig, attempt_number: int) -> dict[str, object]:
    return {
        "approved_action": "write_file",
        "path": config.contract.path,
        "content": config.contract.content,
        "attempt_number": attempt_number,
        "rationale": "Execute only the approved exact contract action.",
    }


def _audit_output(decision: str, conflicts: list[str]) -> dict[str, object]:
    return {
        "decision": decision,
        "source_assessment": "Assessment derived from the supplied source report.",
        "observation_assessment": "Assessment derived from independent state evidence.",
        "conflicts": conflicts,
        "evidence_refs": _EVIDENCE_REFS,
    }


def _recovery_output(scenario_id: str) -> dict[str, object]:
    return {
        "failure_class": scenario_id,
        "retry_justified": True,
        "proposed_action": "write_file",
        "remaining_attempts": 1,
        "refusal_reason": None,
    }


def _synthesis_output(status: str, completion_claimed: bool) -> dict[str, object]:
    return {
        "completion_claimed": completion_claimed,
        "verified_status": status,
        "summary": "Summary limited to supplied independent evidence.",
        "limitations": ["Controlled provider-free release fixture."],
        "evidence_refs": ["evaluation.json", "observation.json"],
    }


class _ReleaseScriptedTransport:
    provider = "release-scripted-role-provider"

    def __init__(self, outputs: dict[str, dict[str, object]]) -> None:
        self.outputs = outputs
        self.calls: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if request.call_id not in self.outputs:
            raise AssertionError(f"Unexpected release role call: {request.call_id}")
        self.calls.append(request.call_id)
        output_text = _compact(self.outputs[request.call_id])
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"release-response-{len(self.calls)}",
            model_id=request.model_id,
            output_text=output_text,
            status="completed",
            latency_ms=1,
            usage=ModelUsage(input_tokens=10, output_tokens=10, total_tokens=20),
            raw_response_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"release-scripted-{len(self.calls)}",
            provider_processing_ms=1,
        )


def _general_success_outputs(config: ExperimentConfig) -> dict[str, dict[str, object]]:
    return {
        f"{config.experiment_id}--general--success--general--1": _general_output(config),
    }


def _specialist_recovery_outputs(config: ExperimentConfig) -> dict[str, dict[str, object]]:
    scenario = "false_success"
    prefix = f"{config.experiment_id}--specialist--{scenario}--"
    return {
        prefix + "strategist--1": _strategy_output(config),
        prefix + "operator--1": _operator_output(config, 1),
        prefix + "auditor--1": _audit_output(
            "recover",
            ["reported_success_without_matching_state"],
        ),
        prefix + "recovery--1": _recovery_output(scenario),
        prefix + "operator--2": _operator_output(config, 2),
        prefix + "auditor--2": _audit_output("accept", []),
        prefix + "synthesiser--1": _synthesis_output("VERIFIED_COMPLETE", True),
    }


def _specialist_security_outputs(config: ExperimentConfig) -> dict[str, dict[str, object]]:
    scenario = "path_traversal"
    prefix = f"{config.experiment_id}--specialist--{scenario}--"
    return {
        prefix + "strategist--1": _strategy_output(config),
        prefix + "operator--1": _operator_output(config, 1),
        prefix + "auditor--1": _audit_output("fail", []),
        prefix + "synthesiser--1": _synthesis_output("FAILED", False),
    }


def verify_provider_free_live_orchestration_release(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    root: Path,
) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)

    general_transport = _ReleaseScriptedTransport(_general_success_outputs(config))
    general_ledger = root / "general-success-calls.jsonl"
    general = LiveGeneralOrchestrator(
        RecordingTransport(general_transport, general_ledger)
    ).run(config, catalog, "success", root / "general-success-sandbox")
    assert general.verified_complete
    assert general.completion_claimed
    assert len(general.role_calls) == 1
    assert len(general.attempts) == 1
    assert verify_transport_ledger(general_ledger)["records"] == 1

    recovery_transport = _ReleaseScriptedTransport(_specialist_recovery_outputs(config))
    recovery_ledger = root / "specialist-recovery-calls.jsonl"
    recovery = LiveSpecialistOrchestrator(
        RecordingTransport(recovery_transport, recovery_ledger)
    ).run(config, catalog, "false_success", root / "specialist-recovery-sandbox")
    assert recovery.verified_complete
    assert recovery.completion_claimed
    assert recovery.recovered
    assert len(recovery.role_calls) == 7
    assert len(recovery.attempts) == 2
    assert verify_transport_ledger(recovery_ledger)["records"] == 7

    security_transport = _ReleaseScriptedTransport(_specialist_security_outputs(config))
    security_ledger = root / "specialist-security-calls.jsonl"
    security = LiveSpecialistOrchestrator(
        RecordingTransport(security_transport, security_ledger)
    ).run(config, catalog, "path_traversal", root / "specialist-security-sandbox")
    assert not security.verified_complete
    assert not security.completion_claimed
    assert security.security_rejected
    assert not security.recovered
    assert len(security.role_calls) == 4
    assert len(security.attempts) == 1
    assert verify_transport_ledger(security_ledger)["records"] == 4
    assert not any("recovery" in call_id for call_id in security_transport.calls)

    return {
        "scenarios": 3,
        "role_calls": len(general.role_calls) + len(recovery.role_calls) + len(security.role_calls),
        "ledgers": 3,
        "recovery_verified": recovery.recovered,
        "terminal_security_verified": security.security_rejected,
    }
