from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import ExperimentConfig
from .live_orchestration import LiveOrchestrationError
from .live_requests import PromptCatalog
from .pilot_policy import PilotPolicy
from .repeated_analysis import analyse_repeated_experiment
from .repeated_plan import build_counterbalanced_plan
from .repeated_runner import run_private_repeated_experiment
from .transports import ModelCallRequest, ModelCallResult, ModelUsage


_PROVIDER = "release-repeated-provider"
_EVIDENCE_REFS = ["source_report.json", "observation.json", "evaluation.json"]


def _compact(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _success_outputs(config: ExperimentConfig) -> dict[str, dict[str, object]]:
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
            "limitations": ["Provider-free repeated-experiment release fixture."],
            "evidence_refs": ["evaluation.json", "observation.json"],
        },
    }


class _RepeatedScriptedTransport:
    provider = _PROVIDER

    def __init__(
        self,
        config: ExperimentConfig,
        *,
        invalid_general: bool = False,
    ) -> None:
        self.outputs = _success_outputs(config)
        if invalid_general:
            general = f"{config.experiment_id}--general--success--general--1"
            self.outputs[general] = {"invalid": "general output"}
        self.calls: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if request.call_id not in self.outputs:
            raise AssertionError(f"Unexpected repeated-release call: {request.call_id}")
        self.calls.append(request.call_id)
        output_text = _compact(self.outputs[request.call_id])
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"repeated-release-{len(self.calls)}",
            model_id=request.model_id,
            output_text=output_text,
            status="completed",
            latency_ms=1,
            usage=ModelUsage(input_tokens=10, output_tokens=10, total_tokens=20),
            raw_response_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"repeated-release-request-{len(self.calls)}",
            provider_processing_ms=1,
        )


def _policy(config: ExperimentConfig) -> PilotPolicy:
    return PilotPolicy(
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


def verify_provider_free_repeated_experiment_release(
    config: ExperimentConfig,
    catalog: PromptCatalog,
    root: Path,
) -> dict[str, object]:
    base = Path(root)
    completed_root = base / "completed"
    aborted_root = base / "aborted"
    policy = _policy(config)
    plan = build_counterbalanced_plan(
        config,
        catalog,
        policy,
        scenario_ids=("success",),
        repetitions_per_scenario=4,
        starting_seed=1304,
    )

    first_transport = _RepeatedScriptedTransport(config)
    paused = run_private_repeated_experiment(
        config,
        catalog,
        plan,
        policy,
        first_transport,
        completed_root,
        reviewed_plan_digest=plan.digest,
        reviewed_policy_template_digest=policy.digest,
        external_execution_approved=True,
        max_new_trials=1,
    )
    assert paused["status"] == "paused"
    assert paused["completed_trials"] == 1
    assert len(first_transport.calls) == 5

    second_transport = _RepeatedScriptedTransport(config)
    summary = run_private_repeated_experiment(
        config,
        catalog,
        plan,
        policy,
        second_transport,
        completed_root,
        reviewed_plan_digest=plan.digest,
        reviewed_policy_template_digest=policy.digest,
        external_execution_approved=True,
    )
    assert summary["status"] == "completed"
    assert summary["planned_trials"] == 4
    assert summary["completed_trials"] == 4
    assert len(second_transport.calls) == 15
    analysis = analyse_repeated_experiment(completed_root, plan, catalog)
    assert analysis["trials"] == {"planned": 4, "completed": 4, "aborted": 0}
    assert analysis["outcomes"]["both_complete"] == 4
    assert analysis["measurements"]["logical_model_calls"] == 20
    assert analysis["measurements"]["total_tokens"] == 400
    assert analysis["measurements"]["wall_clock_latency_ms"] == 20
    assert analysis["comparative_claim_permitted"] is False

    order_counts = plan.order_counts["success"]
    assert order_counts["general_first"] == 2
    assert order_counts["specialist_first"] == 2
    for trial in plan.trials:
        assert (completed_root / trial.trial_id / "verification-summary.json").is_file()
        assert (completed_root / trial.trial_id / "transport-calls.jsonl").is_file()

    abort_plan = build_counterbalanced_plan(
        config,
        catalog,
        policy,
        scenario_ids=("success",),
        repetitions_per_scenario=2,
        starting_seed=2304,
    )
    abort_transport = _RepeatedScriptedTransport(config, invalid_general=True)
    try:
        run_private_repeated_experiment(
            config,
            catalog,
            abort_plan,
            policy,
            abort_transport,
            aborted_root,
            reviewed_plan_digest=abort_plan.digest,
            reviewed_policy_template_digest=policy.digest,
            external_execution_approved=True,
        )
    except LiveOrchestrationError:
        pass
    else:
        raise AssertionError("Invalid repeated-release output unexpectedly completed.")
    assert (aborted_root / "experiment-abort.json").is_file()
    assert (aborted_root / "trial-0001" / "abort.json").is_file()

    terminal_resume_refused = False
    try:
        run_private_repeated_experiment(
            config,
            catalog,
            abort_plan,
            policy,
            _RepeatedScriptedTransport(config),
            aborted_root,
            reviewed_plan_digest=abort_plan.digest,
            reviewed_policy_template_digest=policy.digest,
            external_execution_approved=True,
        )
    except ValueError as exc:
        assert "terminal" in str(exc).lower()
        terminal_resume_refused = True
    assert terminal_resume_refused

    return {
        "planned_trials": summary["planned_trials"],
        "completed_trials": summary["completed_trials"],
        "general_first_trials": order_counts["general_first"],
        "specialist_first_trials": order_counts["specialist_first"],
        "paused_calls": len(first_transport.calls),
        "resumed_calls": len(second_transport.calls),
        "total_calls": len(first_transport.calls) + len(second_transport.calls),
        "verified_ledger_records": analysis["measurements"]["logical_model_calls"],
        "measured_total_tokens": analysis["measurements"]["total_tokens"],
        "measured_wall_clock_latency_ms": analysis["measurements"]["wall_clock_latency_ms"],
        "terminal_abort_preserved": True,
        "terminal_resume_refused": terminal_resume_refused,
        "provider_called": False,
        "comparative_claim_permitted": analysis["comparative_claim_permitted"],
    }
