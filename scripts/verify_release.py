from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agent_reliability_arena.artifacts import verify_manifest
from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.experiment import execute_fixture_experiment
from agent_reliability_arena.live_requests import PromptCatalog, build_live_request_preflight
from agent_reliability_arena.public_export import build_public_export
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


class _ReleaseFixtureTransport:
    provider = "release-fixture-provider"

    def __init__(self, result: ModelCallResult) -> None:
        self.result = result
        self.calls = 0

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.calls += 1
        return self.result


def count_tests() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    return suite.countTestCases()


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


def main() -> None:
    config = ExperimentConfig.from_dict(json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8")))
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
    total = count_tests()
    assert total >= MINIMUM_DISCOVERED_TESTS, total
    print(json.dumps({
        "tests_expected_minimum": MINIMUM_DISCOVERED_TESTS,
        "tests_discovered": total,
        "reference_manifest_verified": True,
        "general_verified": 2,
        "specialist_verified": 6,
        "false_completion_reduction": 3,
        "additional_logical_model_calls": 36,
        "transport_ledger_records_verified": ledger_summary["records"],
        "transport_ledger_digest_verified": True,
        "live_request_templates_verified": live_preflight["templates"],
        "live_request_preflight_digest_verified": True,
        "evidence_status": "deterministic_fixture",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
