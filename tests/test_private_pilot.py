from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_orchestration import LiveOrchestrationError
from agent_reliability_arena.live_requests import LiveRequestFactory, PromptCatalog
from agent_reliability_arena.pilot_policy import (
    PilotExecutionGate,
    PilotGateError,
    PilotPolicy,
    build_pilot_preflight,
)
from agent_reliability_arena.private_pilot import run_private_paired_pilot
from agent_reliability_arena.transports import ModelCallRequest, ModelCallResult, ModelUsage


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_REFS = ["source_report.json", "observation.json", "evaluation.json"]


def load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(
        json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
    )


def load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )


def policy_for(config: ExperimentConfig, *, enabled: bool = True, scenarios: tuple[str, ...] = ("success",)) -> PilotPolicy:
    return PilotPolicy(
        provider="private-scripted-provider",
        model_id=config.model_id,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        scenario_ids=scenarios,
        max_calls=8 * len(scenarios),
        max_requested_output_tokens=2068 * len(scenarios),
        reserved_total_tokens_per_call=1024,
        max_reserved_total_tokens=8192 * len(scenarios),
        currency="GBP",
        reserved_cost_per_call_minor_units=1,
        max_cost_minor_units=8 * len(scenarios),
        external_execution_enabled=enabled,
    )


def compact(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def success_outputs(config: ExperimentConfig) -> dict[str, dict[str, object]]:
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
            "retryable_failures": ["false_success", "partial_write", "timeout_before_write", "rollback"],
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
            "evidence_refs": EVIDENCE_REFS,
        },
        prefix + "synthesiser--1": {
            "completion_claimed": True,
            "verified_status": "VERIFIED_COMPLETE",
            "summary": "Independent evidence verified the exact contract.",
            "limitations": ["Single controlled provider-free rehearsal."],
            "evidence_refs": ["evaluation.json", "observation.json"],
        },
    }


class ScriptedTransport:
    provider = "private-scripted-provider"

    def __init__(self, outputs: dict[str, dict[str, object]]) -> None:
        self.outputs = outputs
        self.calls: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls.append(request.call_id)
        if request.call_id not in self.outputs:
            raise AssertionError(f"Unexpected private-pilot call: {request.call_id}")
        output_text = compact(self.outputs[request.call_id])
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"private-response-{len(self.calls)}",
            model_id=request.model_id,
            output_text=output_text,
            status="completed",
            latency_ms=2,
            usage=ModelUsage(input_tokens=10, output_tokens=10, total_tokens=20),
            raw_response_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"private-request-{len(self.calls)}",
            provider_processing_ms=1,
        )


class PrivatePilotRunnerTests(unittest.TestCase):
    def test_provider_free_success_writes_and_verifies_private_evidence(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = policy_for(config)
        transport = ScriptedTransport(success_outputs(config))
        secret = "sk-private-test-secret"
        previous = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = secret
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "pilot"
                summary = run_private_paired_pilot(
                    config,
                    catalog,
                    policy,
                    transport,
                    root,
                    reviewed_policy_digest=policy.digest,
                    external_execution_approved=True,
                )
                self.assertEqual(summary["status"], "completed")
                self.assertEqual(summary["scenario_id"], "success")
                self.assertTrue(summary["conditions"]["general"]["verified_complete"])
                self.assertTrue(summary["conditions"]["specialist"]["verified_complete"])
                self.assertEqual(summary["ledger"]["records"], 5)
                self.assertEqual(summary["ledger"]["errors"], 0)
                self.assertEqual(summary["gate"]["calls_started"], 5)
                self.assertEqual(len(transport.calls), 5)
                self.assertFalse(any("recovery" in call_id or call_id.endswith("--2") for call_id in transport.calls))
                for relative in (
                    "preflight.json",
                    "policy.json",
                    "run-start.json",
                    "general/result.json",
                    "specialist/result.json",
                    "transport-calls.jsonl",
                    "verification-summary.json",
                ):
                    self.assertTrue((root / relative).is_file(), relative)
                combined = b"".join(path.read_bytes() for path in root.rglob("*") if path.is_file())
                self.assertNotIn(secret.encode("utf-8"), combined)
        finally:
            if previous is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous

    def test_abort_preserves_recorded_call_and_rejects_directory_reuse(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = policy_for(config)
        outputs = success_outputs(config)
        general_id = f"{config.experiment_id}--general--success--general--1"
        outputs[general_id] = {"not": "a valid general output"}
        transport = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pilot"
            with self.assertRaises(LiveOrchestrationError):
                run_private_paired_pilot(
                    config,
                    catalog,
                    policy,
                    transport,
                    root,
                    reviewed_policy_digest=policy.digest,
                    external_execution_approved=True,
                )
            abort = json.loads((root / "abort.json").read_text(encoding="utf-8"))
            self.assertEqual(abort["status"], "aborted")
            self.assertEqual(abort["stage"], "general")
            self.assertEqual(abort["ledger"]["records"], 1)
            self.assertFalse((root / "verification-summary.json").exists())
            with self.assertRaisesRegex(ValueError, "empty"):
                run_private_paired_pilot(
                    config,
                    catalog,
                    policy,
                    ScriptedTransport(success_outputs(config)),
                    root,
                    reviewed_policy_digest=policy.digest,
                    external_execution_approved=True,
                )

    def test_gate_rejects_unplanned_and_duplicate_calls_before_provider(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = policy_for(config)
        preflight = build_pilot_preflight(config, catalog, policy)
        transport = ScriptedTransport(success_outputs(config))
        gate = PilotExecutionGate(
            transport,
            policy,
            reviewed_policy_digest=policy.digest,
            external_execution_approved=True,
            allowed_calls=preflight["calls"],
        )
        factory = LiveRequestFactory(config, catalog)
        request = factory.build(
            condition="general",
            role="general",
            scenario_id="success",
            attempt_number=1,
            role_payload={"phase": "general", "contract_digest": config.contract.digest},
        )
        gate.complete(request)
        with self.assertRaisesRegex(PilotGateError, "already started"):
            gate.complete(request)
        unplanned = ModelCallRequest(**(request.to_dict() | {"call_id": "unplanned-call"}))
        with self.assertRaisesRegex(PilotGateError, "preflight"):
            gate.complete(unplanned)
        self.assertEqual(transport.calls, [request.call_id])

    def test_runner_requires_one_enabled_scenario_and_clean_root(self) -> None:
        config = load_config()
        catalog = load_catalog()
        transport = ScriptedTransport(success_outputs(config))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "exactly one"):
                run_private_paired_pilot(
                    config,
                    catalog,
                    policy_for(config, scenarios=("success", "false_success")),
                    transport,
                    Path(directory) / "many",
                    reviewed_policy_digest=policy_for(config, scenarios=("success", "false_success")).digest,
                    external_execution_approved=True,
                )
            disabled = policy_for(config, enabled=False)
            with self.assertRaisesRegex(PilotGateError, "disabled"):
                run_private_paired_pilot(
                    config,
                    catalog,
                    disabled,
                    transport,
                    Path(directory) / "disabled",
                    reviewed_policy_digest=disabled.digest,
                    external_execution_approved=True,
                )
            dirty = Path(directory) / "dirty"
            dirty.mkdir()
            (dirty / "keep.txt").write_text("keep", encoding="utf-8")
            enabled = policy_for(config)
            with self.assertRaisesRegex(ValueError, "empty"):
                run_private_paired_pilot(
                    config,
                    catalog,
                    enabled,
                    transport,
                    dirty,
                    reviewed_policy_digest=enabled.digest,
                    external_execution_approved=True,
                )


if __name__ == "__main__":
    unittest.main()
