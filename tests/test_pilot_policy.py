from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import LiveRequestFactory, PromptCatalog
from agent_reliability_arena.pilot_policy import (
    PilotExecutionGate,
    PilotGateError,
    PilotPolicy,
    build_pilot_preflight,
)
from agent_reliability_arena.transports import ModelCallResult, ModelUsage
from agent_reliability_arena.transports.base import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "fixture_experiment.json"
CATALOG = ROOT / "examples" / "live_prompt_catalog.json"
POLICY = ROOT / "examples" / "pilot_policy.disabled.json"


def load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(json.loads(CONFIG.read_text(encoding="utf-8")))


def load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(json.loads(CATALOG.read_text(encoding="utf-8")))


def raw_policy(*, enabled: bool = False, max_calls: int = 8) -> dict[str, object]:
    return {
        "schema_version": "1",
        "provider": "openai-responses",
        "model_id": "fixture-model-v1",
        "model_version": "1",
        "prompt_version": "fixture-prompts-v1",
        "scenario_ids": ["success"],
        "max_calls": max_calls,
        "max_requested_output_tokens": 2068 if max_calls == 8 else 256,
        "reserved_total_tokens_per_call": 2048,
        "max_reserved_total_tokens": 16384 if max_calls == 8 else 2048,
        "currency": "GBP",
        "reserved_cost_per_call_minor_units": 12,
        "max_cost_minor_units": 100 if max_calls == 8 else 12,
        "external_execution_enabled": enabled,
    }


class FakeTransport:
    provider = "openai-responses"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return ModelCallResult(
            call_id=request.call_id,
            request_digest=request.digest,
            provider=self.provider,
            response_id=f"response-{self.calls}",
            model_id=request.model_id,
            output_text='{"ok":true}',
            status="completed",
            latency_ms=1,
            usage=ModelUsage(input_tokens=20, output_tokens=5, total_tokens=25),
            raw_response_sha256="a" * 64,
            client_request_id=f"arena-{request.digest}",
            provider_request_id=f"provider-{self.calls}",
            provider_processing_ms=1,
        )


class PilotPolicyTests(unittest.TestCase):
    def test_round_trip_digest_and_exact_schema(self) -> None:
        raw = raw_policy()
        policy = PilotPolicy.from_dict(raw)
        self.assertEqual(policy.to_dict(), raw)
        self.assertEqual(policy.digest, canonical_json_sha256(raw))
        self.assertEqual(len(policy.digest), 64)

        with_secret = dict(raw)
        with_secret["api_key"] = "must-never-be-stored"
        with self.assertRaisesRegex(ValueError, "exactly"):
            PilotPolicy.from_dict(with_secret)

    def test_preflight_is_disabled_provider_free_and_budget_complete(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = PilotPolicy.from_dict(json.loads(POLICY.read_text(encoding="utf-8")))
        manifest = build_pilot_preflight(config, catalog, policy)
        unsigned = dict(manifest)
        digest = unsigned.pop("manifest_digest")
        self.assertEqual(digest, canonical_json_sha256(unsigned))
        self.assertFalse(manifest["external_execution_enabled"])
        self.assertFalse(manifest["provider_called"])
        self.assertEqual(manifest["scenario_ids"], ["success"])
        self.assertEqual(manifest["planned_call_ceiling"], 8)
        self.assertEqual(manifest["planned_requested_output_tokens"], 2068)
        self.assertEqual(manifest["reserved_total_tokens"], 16384)
        self.assertEqual(manifest["reserved_cost_minor_units"], 96)
        self.assertEqual(manifest["currency"], "GBP")
        self.assertNotIn("api_key", json.dumps(manifest).lower())

    def test_preflight_rejects_drift_and_underfunded_limits(self) -> None:
        config = load_config()
        catalog = load_catalog()
        cases: list[tuple[dict[str, object], str]] = []

        model_drift = raw_policy()
        model_drift["model_id"] = "different-model"
        cases.append((model_drift, "model_id"))

        duplicate_scenario = raw_policy()
        duplicate_scenario["scenario_ids"] = ["success", "success"]
        cases.append((duplicate_scenario, "scenario_ids"))

        too_few_calls = raw_policy()
        too_few_calls["max_calls"] = 7
        cases.append((too_few_calls, "max_calls"))

        too_few_output_tokens = raw_policy()
        too_few_output_tokens["max_requested_output_tokens"] = 2067
        cases.append((too_few_output_tokens, "max_requested_output_tokens"))

        too_few_reserved_tokens = raw_policy()
        too_few_reserved_tokens["max_reserved_total_tokens"] = 16383
        cases.append((too_few_reserved_tokens, "max_reserved_total_tokens"))

        too_little_cost = raw_policy()
        too_little_cost["max_cost_minor_units"] = 95
        cases.append((too_little_cost, "max_cost_minor_units"))

        for raw, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                build_pilot_preflight(config, catalog, PilotPolicy.from_dict(raw))

    def test_execution_gate_requires_enablement_review_digest_and_explicit_approval(self) -> None:
        config = load_config()
        catalog = load_catalog()
        request = LiveRequestFactory(config, catalog).build(
            condition="general",
            role="general",
            scenario_id="success",
            attempt_number=1,
            role_payload={"observation": "none"},
        )

        disabled = PilotPolicy.from_dict(raw_policy(enabled=False, max_calls=1))
        gate = PilotExecutionGate(
            FakeTransport(),
            disabled,
            reviewed_policy_digest=disabled.digest,
            external_execution_approved=True,
        )
        with self.assertRaisesRegex(PilotGateError, "disabled"):
            gate.complete(request)

        enabled = PilotPolicy.from_dict(raw_policy(enabled=True, max_calls=1))
        with self.assertRaisesRegex(ValueError, "digest"):
            PilotExecutionGate(
                FakeTransport(),
                enabled,
                reviewed_policy_digest="0" * 64,
                external_execution_approved=True,
            )

        unapproved = PilotExecutionGate(
            FakeTransport(),
            enabled,
            reviewed_policy_digest=enabled.digest,
            external_execution_approved=False,
        )
        with self.assertRaisesRegex(PilotGateError, "approval"):
            unapproved.complete(request)

    def test_execution_gate_enforces_scope_and_cumulative_reservations(self) -> None:
        config = load_config()
        catalog = load_catalog()
        factory = LiveRequestFactory(config, catalog)
        request = factory.build(
            condition="general",
            role="general",
            scenario_id="success",
            attempt_number=1,
            role_payload={"observation": "none"},
        )
        policy = PilotPolicy.from_dict(raw_policy(enabled=True, max_calls=1))
        inner = FakeTransport()
        gate = PilotExecutionGate(
            inner,
            policy,
            reviewed_policy_digest=policy.digest,
            external_execution_approved=True,
        )
        result = gate.complete(request)
        self.assertEqual(result.status, "completed")
        self.assertEqual(inner.calls, 1)
        self.assertEqual(gate.snapshot()["calls_started"], 1)
        self.assertEqual(gate.snapshot()["requested_output_tokens_reserved"], 256)
        self.assertEqual(gate.snapshot()["total_tokens_reserved"], 2048)
        self.assertEqual(gate.snapshot()["cost_minor_units_reserved"], 12)
        self.assertEqual(gate.snapshot()["observed_total_tokens"], 25)

        with self.assertRaisesRegex(PilotGateError, "max_calls"):
            gate.complete(request)
        self.assertEqual(inner.calls, 1)

    def test_preflight_cli_is_provider_free_and_does_not_echo_environment_secret(self) -> None:
        environment = dict(os.environ)
        environment["OPENAI_API_KEY"] = "secret-value-that-must-not-appear"
        result = subprocess.run(
            [
                "arena-preflight-pilot",
                "--config",
                str(CONFIG),
                "--catalog",
                str(CATALOG),
                "--policy",
                str(POLICY),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["external_execution_enabled"])
        self.assertFalse(payload["provider_called"])
        self.assertNotIn(environment["OPENAI_API_KEY"], result.stdout)
        self.assertNotIn(environment["OPENAI_API_KEY"], result.stderr)


if __name__ == "__main__":
    unittest.main()
