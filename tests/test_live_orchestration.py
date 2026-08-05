from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_orchestration import (
    LiveGeneralOrchestrator,
    LiveOrchestrationError,
    LiveScenarioExecution,
    LiveSpecialistOrchestrator,
)
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.transports import (
    ModelCallRequest,
    ModelCallResult,
    ModelUsage,
    RecordingTransport,
    verify_transport_ledger,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_REFS = ["source_report.json", "observation.json", "evaluation.json"]


def compact(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(
        json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
    )


def load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )


def general_output(config: ExperimentConfig, *, completion_claimed: bool = True) -> dict[str, object]:
    return {
        "action": "write_file",
        "path": config.contract.path,
        "content": config.contract.content,
        "completion_claimed": completion_claimed,
        "rationale": "The bounded contract action is explicit.",
    }


def strategy_output(config: ExperimentConfig) -> dict[str, object]:
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


def operator_output(config: ExperimentConfig, attempt_number: int, *, path: str | None = None) -> dict[str, object]:
    return {
        "approved_action": "write_file",
        "path": path if path is not None else config.contract.path,
        "content": config.contract.content,
        "attempt_number": attempt_number,
        "rationale": "Execute only the approved exact contract action.",
    }


def audit_output(decision: str, conflicts: list[str]) -> dict[str, object]:
    return {
        "decision": decision,
        "source_assessment": "Assessment derived from the supplied source report.",
        "observation_assessment": "Assessment derived from independent state evidence.",
        "conflicts": conflicts,
        "evidence_refs": EVIDENCE_REFS,
    }


def recovery_output(scenario_id: str) -> dict[str, object]:
    return {
        "failure_class": scenario_id,
        "retry_justified": True,
        "proposed_action": "write_file",
        "remaining_attempts": 1,
        "refusal_reason": None,
    }


def synthesis_output(status: str, completion_claimed: bool) -> dict[str, object]:
    return {
        "completion_claimed": completion_claimed,
        "verified_status": status,
        "summary": "Summary limited to supplied independent evidence.",
        "limitations": ["Controlled provider-free integration fixture."],
        "evidence_refs": ["evaluation.json", "observation.json"],
    }


class ScriptedTransport:
    provider = "scripted-role-provider"

    def __init__(self, outputs: dict[str, dict[str, object]]) -> None:
        self.outputs = outputs
        self.calls: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if request.call_id not in self.outputs:
            raise AssertionError(f"Unexpected role call: {request.call_id}")
        self.calls.append(request.call_id)
        output_text = compact(self.outputs[request.call_id])
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"response-{len(self.calls)}",
            model_id=request.model_id,
            output_text=output_text,
            status="completed",
            latency_ms=1,
            usage=ModelUsage(input_tokens=10, output_tokens=10, total_tokens=20),
            raw_response_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"scripted-{len(self.calls)}",
            provider_processing_ms=1,
        )


class LiveOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.catalog = load_catalog()

    def test_general_success_runs_one_call_and_one_verified_attempt(self) -> None:
        call_id = "fixture-v1--general--success--general--1"
        scripted = ScriptedTransport({call_id: general_output(self.config, completion_claimed=True)})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "calls.jsonl"
            transport = RecordingTransport(scripted, ledger)
            execution = LiveGeneralOrchestrator(transport).run(
                self.config,
                self.catalog,
                "success",
                root / "sandbox",
            )

            self.assertIsInstance(execution, LiveScenarioExecution)
            self.assertEqual(execution.condition, "general")
            self.assertEqual(execution.final_status, "VERIFIED_COMPLETE")
            self.assertTrue(execution.completion_claimed)
            self.assertTrue(execution.verified_complete)
            self.assertFalse(execution.false_completion)
            self.assertEqual(len(execution.role_calls), 1)
            self.assertEqual(len(execution.attempts), 1)
            self.assertEqual(scripted.calls, [call_id])
            self.assertEqual(verify_transport_ledger(ledger)["records"], 1)

    def test_general_false_success_claim_remains_false_completion(self) -> None:
        call_id = "fixture-v1--general--false_success--general--1"
        scripted = ScriptedTransport({call_id: general_output(self.config, completion_claimed=True)})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            execution = LiveGeneralOrchestrator(scripted).run(
                self.config,
                self.catalog,
                "false_success",
                root / "sandbox",
            )
            self.assertNotEqual(execution.final_status, "VERIFIED_COMPLETE")
            self.assertTrue(execution.completion_claimed)
            self.assertTrue(execution.false_completion)
            self.assertFalse(execution.verified_complete)

    def test_specialist_false_success_recovers_with_seven_calls(self) -> None:
        scenario = "false_success"
        prefix = f"fixture-v1--specialist--{scenario}--"
        outputs = {
            prefix + "strategist--1": strategy_output(self.config),
            prefix + "operator--1": operator_output(self.config, 1),
            prefix + "auditor--1": audit_output("recover", ["reported_success_without_matching_state"]),
            prefix + "recovery--1": recovery_output(scenario),
            prefix + "operator--2": operator_output(self.config, 2),
            prefix + "auditor--2": audit_output("accept", []),
            prefix + "synthesiser--1": synthesis_output("VERIFIED_COMPLETE", True),
        }
        scripted = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "calls.jsonl"
            execution = LiveSpecialistOrchestrator(RecordingTransport(scripted, ledger)).run(
                self.config,
                self.catalog,
                scenario,
                root / "sandbox",
            )
            self.assertEqual(execution.final_status, "VERIFIED_COMPLETE")
            self.assertTrue(execution.completion_claimed)
            self.assertTrue(execution.recovered)
            self.assertEqual(len(execution.attempts), 2)
            self.assertEqual(len(execution.role_calls), 7)
            self.assertEqual(len(scripted.calls), 7)
            self.assertEqual(verify_transport_ledger(ledger)["records"], 7)

    def test_specialist_timeout_after_write_accepts_without_retry(self) -> None:
        scenario = "timeout_after_write"
        prefix = f"fixture-v1--specialist--{scenario}--"
        outputs = {
            prefix + "strategist--1": strategy_output(self.config),
            prefix + "operator--1": operator_output(self.config, 1),
            prefix + "auditor--1": audit_output("accept", ["source_failure_but_postcondition_verified"]),
            prefix + "synthesiser--1": synthesis_output("VERIFIED_COMPLETE", True),
        }
        scripted = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            execution = LiveSpecialistOrchestrator(scripted).run(
                self.config,
                self.catalog,
                scenario,
                Path(directory) / "sandbox",
            )
            self.assertTrue(execution.verified_complete)
            self.assertFalse(execution.recovered)
            self.assertEqual(len(execution.attempts), 1)
            self.assertEqual(len(execution.role_calls), 4)

    def test_specialist_security_rejection_is_terminal(self) -> None:
        scenario = "path_traversal"
        prefix = f"fixture-v1--specialist--{scenario}--"
        outputs = {
            prefix + "strategist--1": strategy_output(self.config),
            prefix + "operator--1": operator_output(self.config, 1),
            prefix + "auditor--1": audit_output("fail", []),
            prefix + "synthesiser--1": synthesis_output("FAILED", False),
        }
        scripted = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            execution = LiveSpecialistOrchestrator(scripted).run(
                self.config,
                self.catalog,
                scenario,
                Path(directory) / "sandbox",
            )
            self.assertFalse(execution.verified_complete)
            self.assertFalse(execution.completion_claimed)
            self.assertTrue(execution.security_rejected)
            self.assertFalse(execution.recovered)
            self.assertEqual(len(execution.role_calls), 4)
            self.assertFalse(any("recovery" in call_id for call_id in scripted.calls))

    def test_wrong_operator_contract_fails_before_sandbox_execution(self) -> None:
        scenario = "success"
        prefix = f"fixture-v1--specialist--{scenario}--"
        outputs = {
            prefix + "strategist--1": strategy_output(self.config),
            prefix + "operator--1": operator_output(self.config, 1, path="output/other.txt"),
        }
        scripted = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory) / "sandbox"
            with self.assertRaisesRegex(LiveOrchestrationError, "contract"):
                LiveSpecialistOrchestrator(scripted).run(
                    self.config,
                    self.catalog,
                    scenario,
                    sandbox,
                )
            self.assertTrue(sandbox.exists())
            self.assertFalse(any(sandbox.iterdir()))
            self.assertEqual(len(scripted.calls), 2)

    def test_auditor_cannot_accept_unmatched_state(self) -> None:
        scenario = "false_success"
        prefix = f"fixture-v1--specialist--{scenario}--"
        outputs = {
            prefix + "strategist--1": strategy_output(self.config),
            prefix + "operator--1": operator_output(self.config, 1),
            prefix + "auditor--1": audit_output("accept", []),
        }
        scripted = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(LiveOrchestrationError, "Auditor decision"):
                LiveSpecialistOrchestrator(scripted).run(
                    self.config,
                    self.catalog,
                    scenario,
                    Path(directory) / "sandbox",
                )
            self.assertEqual(len(scripted.calls), 3)

    def test_synthesis_cannot_override_final_verifier_status(self) -> None:
        scenario = "path_traversal"
        prefix = f"fixture-v1--specialist--{scenario}--"
        outputs = {
            prefix + "strategist--1": strategy_output(self.config),
            prefix + "operator--1": operator_output(self.config, 1),
            prefix + "auditor--1": audit_output("fail", []),
            prefix + "synthesiser--1": synthesis_output("VERIFIED_COMPLETE", True),
        }
        scripted = ScriptedTransport(outputs)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(LiveOrchestrationError, "Synthesis"):
                LiveSpecialistOrchestrator(scripted).run(
                    self.config,
                    self.catalog,
                    scenario,
                    Path(directory) / "sandbox",
                )


if __name__ == "__main__":
    unittest.main()
