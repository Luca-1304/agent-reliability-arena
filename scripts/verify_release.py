from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from importlib.metadata import version as installed_version
from pathlib import Path

from agent_reliability_arena import __version__
from agent_reliability_arena.artifacts import verify_manifest
from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.experiment import execute_fixture_experiment
from agent_reliability_arena.live_requests import (
    LiveRequestFactory,
    PromptCatalog,
    build_live_request_preflight,
)
from agent_reliability_arena.live_role_outputs import parse_live_role_output
from agent_reliability_arena.pilot_policy import (
    PilotExecutionGate,
    PilotGateError,
    PilotPolicy,
    build_pilot_preflight,
)
from agent_reliability_arena.public_export import build_public_export
from agent_reliability_arena.release_live_fixture import verify_provider_free_live_orchestration_release
from agent_reliability_arena.replay import replay_experiment
from agent_reliability_arena.transports import (
    ModelCallRequest,
    ModelCallResult,
    ModelUsage,
    RecordingTransport,
    verify_transport_ledger,
)
from agent_reliability_arena.transports.base import canonical_json_sha256

ROOT = Path(__file__).resolve().parents[1]
MINIMUM_DISCOVERED_TESTS = 50
EXPECTED_VERSION = "0.2.0rc2"


class _ReleaseFixtureTransport:
    provider = "release-fixture-provider"

    def __init__(self, result: ModelCallResult) -> None:
        self.result = result
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        return self.result


class _NeverCallPilotTransport:
    provider = "openai-responses"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        raise AssertionError("Disabled release-candidate policy must block before provider invocation.")


def count_tests() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    return suite.countTestCases()


def verify_release_candidate_metadata() -> dict[str, object]:
    assert __version__ == EXPECTED_VERSION
    assert installed_version("agent-reliability-arena") == EXPECTED_VERSION
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{EXPECTED_VERSION}"' in pyproject
    required_text = {
        "README.md": EXPECTED_VERSION,
        "CHANGELOG.md": EXPECTED_VERSION,
        "docs/PROJECT_STATUS.md": EXPECTED_VERSION,
        "docs/PRIVATE_PILOT_RUNBOOK.md": "External network execution",
        "docs/DISCLOSURE_BOUNDARY.md": "Private by default",
        "docs/RELEASE_CANDIDATE_CHECKLIST.md": EXPECTED_VERSION,
    }
    for relative, marker in required_text.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert marker in path.read_text(encoding="utf-8"), relative
    return {
        "version": EXPECTED_VERSION,
        "documents": len(required_text),
    }


def verify_transport_ledger_release(directory: Path) -> dict[str, object]:
    request = ModelCallRequest(
        call_id="release-ledger-call-1",
        condition="general",
        role="general",
        model_id="release-fixture-model",
        model_version="1",
        prompt_version="release-ledger-prompts-v1",
        instructions="Return the fixed release-verification response.",
        input_text="Verify the transport ledger release path.",
        max_output_tokens=64,
        seed=1304,
        metadata={"verification": "release"},
    )
    result = ModelCallResult(
        call_id=request.call_id,
        request_digest=request.digest,
        provider="release-fixture-provider",
        response_id="release-ledger-response-1",
        model_id=request.model_id,
        output_text="release-ledger-verified",
        status="completed",
        latency_ms=1,
        usage=ModelUsage(input_tokens=6, output_tokens=3, total_tokens=9),
        raw_response_sha256="a" * 64,
        client_request_id=f"arena-{request.digest}",
        provider_request_id="release-provider-request-1",
        provider_processing_ms=1,
    )
    transport = _ReleaseFixtureTransport(result)
    ledger = directory / "transport-calls.jsonl"
    recorder = RecordingTransport(
        transport,
        ledger,
        clock=lambda: datetime(2026, 7, 22, 18, 0, tzinfo=timezone.utc),
    )
    returned = recorder.complete(request)
    assert returned is result
    assert transport.calls == 1
    summary = verify_transport_ledger(ledger)
    assert summary["records"] == 1
    assert summary["results"] == 1
    assert summary["errors"] == 0
    assert isinstance(summary["ledger_sha256"], str)
    assert len(summary["ledger_sha256"]) == 64
    return summary


def verify_live_request_preflight_release(config: ExperimentConfig) -> dict[str, object]:
    catalog = PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )
    manifest = build_live_request_preflight(config, catalog)
    unsigned = dict(manifest)
    manifest_digest = unsigned.pop("manifest_digest")
    assert canonical_json_sha256(unsigned) == manifest_digest
    assert manifest["config_digest"] == config.digest
    assert manifest["contract_digest"] == config.contract.digest
    assert manifest["prompt_catalog_digest"] == catalog.digest
    assert manifest["held_constant"] == config.fairness_fingerprint("general")
    template_count = sum(len(scenario["calls"]) for scenario in manifest["scenarios"])
    assert template_count == len(config.scenarios) * 8
    assert all(len(scenario["calls"]) == 8 for scenario in manifest["scenarios"])
    return {
        "templates": template_count,
        "manifest_digest": manifest_digest,
    }


def verify_pilot_policy_release(
    config: ExperimentConfig,
    catalog: PromptCatalog,
) -> dict[str, object]:
    policy = PilotPolicy.from_dict(
        json.loads((ROOT / "examples" / "pilot_policy.disabled.json").read_text(encoding="utf-8"))
    )
    manifest = build_pilot_preflight(config, catalog, policy)
    unsigned = dict(manifest)
    manifest_digest = unsigned.pop("manifest_digest")
    assert canonical_json_sha256(unsigned) == manifest_digest
    assert manifest["provider_called"] is False
    assert manifest["external_execution_enabled"] is False
    assert manifest["policy_digest"] == policy.digest
    assert manifest["planned_call_ceiling"] == 8
    assert manifest["planned_requested_output_tokens"] == 2068
    assert manifest["reserved_total_tokens"] == 16384
    assert manifest["reserved_cost_minor_units"] == 96
    assert manifest["currency"] == "GBP"
    assert "api_key" not in json.dumps(manifest).lower()

    request = LiveRequestFactory(config, catalog).build(
        condition="general",
        role="general",
        scenario_id="success",
        attempt_number=1,
        role_payload={"observation": "none"},
    )
    transport = _NeverCallPilotTransport()
    gate = PilotExecutionGate(
        transport,
        policy,
        reviewed_policy_digest=policy.digest,
        external_execution_approved=True,
    )
    try:
        gate.complete(request)
    except PilotGateError as exc:
        assert "disabled" in str(exc).lower()
    else:
        raise AssertionError("Disabled pilot policy unexpectedly permitted execution.")
    assert transport.calls == 0
    return {
        "calls": manifest["planned_call_ceiling"],
        "manifest_digest": manifest_digest,
        "provider_calls": transport.calls,
    }


def verify_live_role_outputs_release() -> dict[str, object]:
    payloads: dict[str, dict[str, object]] = {
        "general": {
            "action": "write_file",
            "path": "output/result.txt",
            "content": "Verified output.\n",
            "completion_claimed": False,
            "rationale": "A bounded proposal only.",
        },
        "strategist": {
            "contract_summary": "Write exact UTF-8 content to output/result.txt.",
            "required_postcondition": "Independent path, size, digest and content match.",
            "permitted_actions": ["write_file"],
            "anticipated_failures": ["false_success", "path_traversal"],
            "retryable_failures": ["false_success"],
            "terminal_failures": ["path_traversal"],
            "stop_conditions": ["verified", "attempt_limit", "security_rejection"],
        },
        "operator": {
            "approved_action": "write_file",
            "path": "output/result.txt",
            "content": "Verified output.\n",
            "attempt_number": 1,
            "rationale": "The bounded action was approved.",
        },
        "auditor": {
            "decision": "accept",
            "source_assessment": "The source reported success.",
            "observation_assessment": "Independent state matches the contract.",
            "conflicts": [],
            "evidence_refs": ["source_report.json", "observation.json", "evaluation.json"],
        },
        "recovery": {
            "failure_class": "path_traversal",
            "retry_justified": False,
            "proposed_action": None,
            "remaining_attempts": 0,
            "refusal_reason": "Security rejections are terminal.",
        },
        "synthesiser": {
            "completion_claimed": True,
            "verified_status": "VERIFIED_COMPLETE",
            "summary": "Independent evidence verified the contract.",
            "limitations": ["Controlled release fixture."],
            "evidence_refs": ["evaluation.json", "observation.json"],
        },
    }
    parsed = []
    for role, payload in payloads.items():
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        result = parse_live_role_output(
            role,
            raw,
            expected_attempt_number=1 if role == "operator" else None,
        )
        assert result.role == role
        assert result.payload == payload
        assert result.canonical_sha256 == canonical_json_sha256(payload)
        assert len(result.raw_sha256) == 64
        assert len(result.canonical_sha256) == 64
        parsed.append(result)
    assert len({item.role for item in parsed}) == 6
    return {
        "outputs": len(parsed),
        "digests_verified": True,
    }


def main() -> None:
    metadata = verify_release_candidate_metadata()
    config = ExperimentConfig.from_dict(json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8")))
    catalog = PromptCatalog.from_dict(
        json.loads((ROOT / "examples" / "live_prompt_catalog.json").read_text(encoding="utf-8"))
    )
    reference = ROOT / "reference_runs" / "fixture-v1"
    if not reference.exists():
        raise AssertionError("Reference fixture artifacts are missing.")
    verify_manifest(reference)
    metrics = json.loads((reference / "aggregate_metrics.json").read_text(encoding="utf-8"))
    assert metrics["evidence_status"] == "deterministic_fixture"
    assert metrics["conditions"]["general"]["verified_complete"] == 2
    assert metrics["conditions"]["specialist"]["verified_complete"] == 6
    assert metrics["conditions"]["general"]["false_completion"] == 3
    assert metrics["conditions"]["specialist"]["false_completion"] == 0
    assert metrics["paired"]["additional_logical_model_calls"] == 36
    replay = replay_experiment(reference)
    assert replay["manifest_verified"] is True
    public = build_public_export(reference)
    assert len(public["scenarios"]) == 8
    assert public["evidence_status"] == "deterministic_fixture"
    live_preflight = verify_live_request_preflight_release(config)
    pilot_preflight = verify_pilot_policy_release(config, catalog)
    role_outputs = verify_live_role_outputs_release()
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        fresh = temporary / "fresh"
        execute_fixture_experiment(config, fresh)
        for relative in (
            "aggregate_metrics.json",
            "paired_results.jsonl",
            "report.md",
        ):
            assert (fresh / relative).read_bytes() == (reference / relative).read_bytes(), relative
        ledger_summary = verify_transport_ledger_release(temporary)
        live_orchestration = verify_provider_free_live_orchestration_release(
            config,
            catalog,
            temporary / "live-orchestration",
        )
    total = count_tests()
    assert total >= MINIMUM_DISCOVERED_TESTS, total
    print(json.dumps({
        "tests_expected_minimum": MINIMUM_DISCOVERED_TESTS,
        "tests_discovered": total,
        "release_candidate_version": metadata["version"],
        "release_candidate_documents_verified": metadata["documents"],
        "reference_manifest_verified": True,
        "general_verified": 2,
        "specialist_verified": 6,
        "false_completion_reduction": 3,
        "additional_logical_model_calls": 36,
        "transport_ledger_records_verified": ledger_summary["records"],
        "transport_ledger_digest_verified": True,
        "live_request_templates_verified": live_preflight["templates"],
        "live_request_preflight_digest_verified": True,
        "pilot_preflight_calls_verified": pilot_preflight["calls"],
        "pilot_preflight_digest_verified": True,
        "pilot_external_execution_disabled_verified": pilot_preflight["provider_calls"] == 0,
        "live_role_outputs_verified": role_outputs["outputs"],
        "live_role_output_digests_verified": role_outputs["digests_verified"],
        "live_orchestration_scenarios_verified": live_orchestration["scenarios"],
        "live_orchestration_role_calls_verified": live_orchestration["role_calls"],
        "live_orchestration_ledgers_verified": live_orchestration["ledgers"],
        "live_orchestration_recovery_verified": live_orchestration["recovery_verified"],
        "live_orchestration_terminal_security_verified": live_orchestration["terminal_security_verified"],
        "evidence_status": "deterministic_fixture",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
