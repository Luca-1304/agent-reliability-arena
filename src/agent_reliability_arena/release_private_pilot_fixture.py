from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import ExperimentConfig
from .live_requests import PromptCatalog
from .pilot_policy import PilotPolicy
from .private_pilot import run_private_paired_pilot
from .transports import ModelCallRequest, ModelCallResult, ModelUsage


_PROVIDER = "release-private-pilot-provider"
_EVIDENCE_REFS = ["source_report.json", "observation.json", "evaluation.json"]


def _compact(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _outputs(config: ExperimentConfig) -> dict[str, dict[str, object]]:
    general = f"{config.experiment_id}--general--success--general--1"
    prefix = f"{config.experiment_id}--specialist--success--"
    return {
        general: {
            "action": "write_file",
            "path": config.contract.path,
            "content": config.contract.content,
            "completion_claimed": True,
            "rationale": "The exact bounded action is explicit.",
        },
        prefix + "strategist--1": {
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
        },
        prefix + "operator--1": {
            "approved_action": "write_file",
            "path": config.contract.path,
            "content": config.contract.content,
            "attempt_number": 1,
            "rationale": "Execute only the approved exact contract action.",
        },
        prefix + "auditor--1": {
            "decision": "accept",
            "source_assessment": "The source reported success.",
            "observation_assessment": "Independent state matches the contract.",
            "conflicts": [],
            "evidence_refs": _EVIDENCE_REFS,
        },
        prefix + "synthesiser--1": {
            "completion_claimed": True,
            "verified_status": "VERIFIED_COMPLETE",
            "summary": "Independent evidence verified the exact contract.",
            "limitations": ["Single controlled provider-free private-pilot rehearsal."],
            "evidence_refs": ["evaluation.json", "observation.json"],
        },
    }


class _PrivatePilotScriptedTransport:
    provider = _PROVIDER

    def __init__(self, config: ExperimentConfig) -> None:
        self.outputs = _outputs(config)
        self.calls: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if request.call_id not in self.outputs:
            raise AssertionError(f"Unexpected private-pilot release call: {request.call_id}")
        self.calls.append(request.call_id)
        output_text = _compact(self.outputs[request.call_id])
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"private-pilot-release-{len(self.calls)}",
            model_id=request.model_id,
            output_text=output_text,
            status="completed",
            latency_ms=1,
            usage=ModelUsage(input_tokens=10, output_tokens=10, total_tokens=20),
            raw_response_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"private-pilot-release-request-{len(self.calls)}",
            provider_processing_ms=1,
        )


def verify_provider_free_private_pilot_release(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    root: Path,
) -> dict[str, object]:
    policy = PilotPolicy(
        provider=_PROVIDER,
        model_id=config.model_id,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        scenario_ids=("success",),
        max_calls=8,
        max_requested_output_tokens=2068,
        reserved_total_tokens_per_call=1024,
        max_reserved_total_tokens=8192,
        currency="GBP",
        reserved_cost_per_call_minor_units=1,
        max_cost_minor_units=8,
        external_execution_enabled=True,
    )
    transport = _PrivatePilotScriptedTransport(config)
    summary = run_private_paired_pilot(
        config,
        catalog,
        policy,
        transport,
        root,
        reviewed_policy_digest=policy.digest,
        external_execution_approved=True,
    )
    assert summary["status"] == "completed"
    assert summary["scenario_id"] == "success"
    assert summary["conditions"]["general"]["verified_complete"] is True
    assert summary["conditions"]["specialist"]["verified_complete"] is True
    assert summary["ledger"]["records"] == 5
    assert summary["ledger"]["results"] == 5
    assert summary["ledger"]["errors"] == 0
    assert summary["gate"]["calls_started"] == 5
    assert summary["gate"]["unique_calls_started"] == 5
    assert summary["comparative_claim_permitted"] is False
    assert len(transport.calls) == 5
    required = (
        "preflight.json",
        "policy.json",
        "run-start.json",
        "general/result.json",
        "specialist/result.json",
        "transport-calls.jsonl",
        "verification-summary.json",
    )
    assert all((root / relative).is_file() for relative in required)
    return {
        "scenario": summary["scenario_id"],
        "conditions": 2,
        "role_calls": len(transport.calls),
        "ledger_records": summary["ledger"]["records"],
        "private_artifacts": len(required),
        "comparative_claim_permitted": summary["comparative_claim_permitted"],
    }
