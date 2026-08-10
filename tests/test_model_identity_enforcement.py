from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.pilot_policy import PilotPolicy
from agent_reliability_arena.private_pilot import run_private_paired_pilot
from agent_reliability_arena.transports import (
    ModelCallRequest,
    ModelCallResult,
    ModelUsage,
    RecordingTransport,
    TransportError,
    verify_transport_ledger,
)
from agent_reliability_arena.transports.base import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc)
EVIDENCE_REFS = ["source_report.json", "observation.json", "evaluation.json"]


def make_request() -> ModelCallRequest:
    return ModelCallRequest(
        call_id="identity--general--success--general--1",
        condition="general",
        role="general",
        model_id="gpt-test-2026-08-10",
        model_version="2026-08-10",
        prompt_version="identity-prompts-v1",
        instructions="Return the bounded JSON proposal.",
        input_text="Write the exact contracted file.",
        max_output_tokens=128,
        seed=1304,
        metadata={"scenario": "success"},
    )


def make_result(request: ModelCallRequest, *, model_id: str | None = None) -> ModelCallResult:
    return ModelCallResult(
        call_id=request.call_id,
        request_digest=request.digest,
        provider="identity-provider",
        response_id="resp-identity-1",
        model_id=model_id or request.model_id,
        output_text='{"action":"write_file"}',
        status="completed",
        latency_ms=3,
        usage=ModelUsage(input_tokens=9, output_tokens=4, total_tokens=13),
        raw_response_sha256="b" * 64,
        client_request_id=f"arena-{request.digest}",
        provider_request_id="req-identity-1",
        provider_processing_ms=2,
    )


class StaticTransport:
    provider = "identity-provider"

    def __init__(self, result: ModelCallResult) -> None:
        self.result = result
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        return self.result


def load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(
        json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
    )


def load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )


def policy_for(config: ExperimentConfig) -> PilotPolicy:
    return PilotPolicy(
        provider="private-scripted-provider",
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


class DriftingModelTransport:
    provider = "private-scripted-provider"

    def __init__(self, outputs: dict[str, dict[str, object]]) -> None:
        self.outputs = outputs
        self.calls: list[str] = []

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls.append(request.call_id)
        output_text = compact(self.outputs[request.call_id])
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"drift-response-{len(self.calls)}",
            model_id="unexpected-model-snapshot",
            output_text=output_text,
            status="completed",
            latency_ms=2,
            usage=ModelUsage(input_tokens=10, output_tokens=10, total_tokens=20),
            raw_response_sha256=hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"drift-request-{len(self.calls)}",
            provider_processing_ms=1,
        )


class ModelIdentityEnforcementTests(unittest.TestCase):
    def _write_mismatch(self, ledger: Path) -> tuple[ModelCallRequest, dict[str, object]]:
        request = make_request()
        wrapped = StaticTransport(make_result(request, model_id="different-model-snapshot"))
        recorder = RecordingTransport(wrapped, ledger, clock=lambda: FIXED_TIME)
        with self.assertRaises(TransportError) as raised:
            recorder.complete(request)
        self.assertEqual(raised.exception.category, "model_identity_mismatch")
        self.assertFalse(raised.exception.retryable)
        row = json.loads(ledger.read_text(encoding="utf-8"))
        return request, row

    def test_matching_model_identity_keeps_existing_result_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            request = make_request()
            expected = make_result(request)
            recorder = RecordingTransport(StaticTransport(expected), ledger, clock=lambda: FIXED_TIME)

            actual = recorder.complete(request)

            self.assertIs(actual, expected)
            summary = verify_transport_ledger(ledger)
            self.assertEqual(summary["records"], 1)
            self.assertEqual(summary["results"], 1)
            self.assertEqual(summary["errors"], 0)

    def test_mismatched_model_is_recorded_as_terminal_error_before_return(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            request, row = self._write_mismatch(ledger)

            self.assertEqual(row["outcome_type"], "error")
            self.assertIsNone(row["result"])
            error = row["error"]
            self.assertEqual(error["category"], "model_identity_mismatch")
            self.assertFalse(error["retryable"])
            self.assertEqual(error["expected_model_id"], request.model_id)
            self.assertEqual(error["observed_model_id"], "different-model-snapshot")
            self.assertEqual(error["response_id"], "resp-identity-1")
            self.assertEqual(error["raw_response_sha256"], "b" * 64)
            self.assertNotIn("output_text", error)
            summary = verify_transport_ledger(ledger)
            self.assertEqual(summary["records"], 1)
            self.assertEqual(summary["results"], 0)
            self.assertEqual(summary["errors"], 1)

    def test_semantic_mismatch_evidence_cannot_be_rewritten_consistently(self) -> None:
        mutations = (
            ("expected_model_id", "other-expected"),
            ("observed_model_id", "gpt-test-2026-08-10"),
            ("response_id", ""),
            ("raw_response_sha256", "ABC"),
            ("retryable", True),
        )
        for key, replacement in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                ledger = Path(directory) / "calls.jsonl"
                _request, row = self._write_mismatch(ledger)
                row["error"][key] = replacement
                unsigned = dict(row)
                unsigned.pop("record_digest")
                row["record_digest"] = canonical_json_sha256(unsigned)
                ledger.write_text(
                    json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    verify_transport_ledger(ledger)

    def test_private_pilot_aborts_after_first_provider_model_drift(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = policy_for(config)
        transport = DriftingModelTransport(success_outputs(config))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pilot"
            with self.assertRaises(TransportError) as raised:
                run_private_paired_pilot(
                    config,
                    catalog,
                    policy,
                    transport,
                    root,
                    reviewed_policy_digest=policy.digest,
                    external_execution_approved=True,
                )

            self.assertEqual(raised.exception.category, "model_identity_mismatch")
            self.assertEqual(len(transport.calls), 1)
            self.assertFalse((root / "specialist").exists())
            abort = json.loads((root / "abort.json").read_text(encoding="utf-8"))
            self.assertEqual(abort["status"], "aborted")
            self.assertEqual(abort["stage"], "general")
            self.assertEqual(abort["ledger"]["records"], 1)
            self.assertEqual(abort["ledger"]["errors"], 1)
            summary = verify_transport_ledger(root / "transport-calls.jsonl")
            self.assertEqual(summary["records"], 1)
            self.assertEqual(summary["errors"], 1)


if __name__ == "__main__":
    unittest.main()
