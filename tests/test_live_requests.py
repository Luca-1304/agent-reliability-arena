from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import (
    LiveRequestFactory,
    PromptCatalog,
    build_live_request_preflight,
)
from agent_reliability_arena.transports.base import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
ROLE_NAMES = (
    "general",
    "strategist",
    "operator",
    "auditor",
    "recovery",
    "synthesiser",
)


def raw_catalog(prompt_version: str = "fixture-prompts-v1") -> dict[str, object]:
    return {
        "schema_version": "1",
        "prompt_version": prompt_version,
        "roles": {
            role: {
                "instructions": f"Perform the bounded {role} role and return structured JSON.",
                "max_output_tokens": 256 + index,
            }
            for index, role in enumerate(ROLE_NAMES)
        },
    }


def load_config() -> ExperimentConfig:
    raw = json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8"))
    return ExperimentConfig.from_dict(raw)


class PromptCatalogTests(unittest.TestCase):
    def test_round_trip_and_digest_are_deterministic(self) -> None:
        raw = raw_catalog()
        catalog = PromptCatalog.from_dict(raw)
        self.assertEqual(catalog.to_dict(), raw)
        self.assertEqual(catalog.digest, PromptCatalog.from_dict(dict(reversed(list(raw.items())))).digest)
        self.assertEqual(len(catalog.digest), 64)
        self.assertEqual(tuple(catalog.roles), ROLE_NAMES)
        self.assertEqual(catalog.roles["operator"].max_output_tokens, 258)

    def test_rejects_missing_unknown_or_invalid_roles(self) -> None:
        missing = raw_catalog()
        del missing["roles"]["auditor"]
        unknown = raw_catalog()
        unknown["roles"]["judge"] = {
            "instructions": "Judge the result.",
            "max_output_tokens": 128,
        }
        invalid = raw_catalog()
        invalid["roles"]["operator"]["max_output_tokens"] = 0
        for payload, message in (
            (missing, "roles"),
            (unknown, "roles"),
            (invalid, "max_output_tokens"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                PromptCatalog.from_dict(payload)


class LiveRequestFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.catalog = PromptCatalog.from_dict(raw_catalog())
        self.factory = LiveRequestFactory(self.config, self.catalog)

    def test_builds_exact_general_request_from_config_and_catalog(self) -> None:
        payload = {"observation": "no state has been inspected yet"}
        request = self.factory.build(
            condition="general",
            role="general",
            scenario_id="success",
            attempt_number=1,
            role_payload=payload,
        )
        expected_input = {
            "attempt_number": 1,
            "config_digest": self.config.digest,
            "contract": self.config.contract.to_dict(),
            "experiment_id": self.config.experiment_id,
            "role_payload": payload,
            "scenario_id": "success",
            "task": self.config.task,
        }
        self.assertEqual(request.call_id, "fixture-v1--general--success--general--1")
        self.assertEqual(request.condition, "general")
        self.assertEqual(request.role, "general")
        self.assertEqual(request.model_id, self.config.model_id)
        self.assertEqual(request.model_version, self.config.model_version)
        self.assertEqual(request.prompt_version, self.config.prompt_version)
        self.assertEqual(request.seed, self.config.seed)
        self.assertEqual(request.max_output_tokens, 256)
        self.assertEqual(
            request.input_text,
            json.dumps(expected_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        self.assertEqual(request.metadata["config_digest"], self.config.digest)
        self.assertEqual(request.metadata["contract_digest"], self.config.contract.digest)
        self.assertEqual(request.metadata["prompt_catalog_digest"], self.catalog.digest)
        self.assertEqual(request.metadata["scenario_id"], "success")

    def test_builds_second_specialist_operator_request_deterministically(self) -> None:
        first = self.factory.build(
            condition="specialist",
            role="operator",
            scenario_id="partial_write",
            attempt_number=2,
            role_payload={"approved_action": "write_file"},
        )
        second = self.factory.build(
            condition="specialist",
            role="operator",
            scenario_id="partial_write",
            attempt_number=2,
            role_payload={"approved_action": "write_file"},
        )
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.call_id, "fixture-v1--specialist--partial_write--operator--2")
        self.assertEqual(first.max_output_tokens, 258)

    def test_rejects_prompt_drift_and_invalid_request_grammar(self) -> None:
        with self.assertRaisesRegex(ValueError, "prompt_version"):
            LiveRequestFactory(self.config, PromptCatalog.from_dict(raw_catalog("other-prompts-v1")))

        invalid_cases = (
            {"condition": "general", "role": "operator", "scenario_id": "success", "attempt_number": 1, "role_payload": {}},
            {"condition": "specialist", "role": "general", "scenario_id": "success", "attempt_number": 1, "role_payload": {}},
            {"condition": "specialist", "role": "strategist", "scenario_id": "success", "attempt_number": 2, "role_payload": {}},
            {"condition": "specialist", "role": "operator", "scenario_id": "success", "attempt_number": 3, "role_payload": {}},
            {"condition": "specialist", "role": "auditor", "scenario_id": "unknown", "attempt_number": 1, "role_payload": {}},
            {"condition": "specialist", "role": "auditor", "scenario_id": "success", "attempt_number": 1, "role_payload": []},
            {"condition": "specialist", "role": "auditor", "scenario_id": "success", "attempt_number": 1, "role_payload": {"bad": {1, 2}}},
        )
        for case in invalid_cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.factory.build(**case)


class LiveRequestPreflightTests(unittest.TestCase):
    def test_manifest_enumerates_required_and_conditional_call_graph(self) -> None:
        config = load_config()
        catalog = PromptCatalog.from_dict(raw_catalog())
        manifest = build_live_request_preflight(config, catalog)
        unsigned = dict(manifest)
        digest = unsigned.pop("manifest_digest")
        self.assertEqual(digest, canonical_json_sha256(unsigned))
        self.assertEqual(manifest["config_digest"], config.digest)
        self.assertEqual(manifest["contract_digest"], config.contract.digest)
        self.assertEqual(manifest["prompt_catalog_digest"], catalog.digest)
        self.assertEqual(manifest["held_constant"], config.fairness_fingerprint("general"))
        self.assertEqual(len(manifest["scenarios"]), len(config.scenarios))

        first = manifest["scenarios"][0]
        self.assertEqual(first["scenario_id"], config.scenarios[0])
        self.assertEqual(len(first["calls"]), 8)
        general = [call for call in first["calls"] if call["condition"] == "general"]
        specialist = [call for call in first["calls"] if call["condition"] == "specialist"]
        self.assertEqual(len(general), 1)
        self.assertEqual(len(specialist), 7)
        conditional = {(call["role"], call["attempt_number"]) for call in specialist if not call["required"]}
        self.assertEqual(conditional, {("recovery", 1), ("operator", 2), ("auditor", 2)})
        self.assertTrue(all(call["model_id"] == config.model_id for call in first["calls"]))
        self.assertTrue(all(call["model_version"] == config.model_version for call in first["calls"]))
        self.assertTrue(all(call["prompt_version"] == config.prompt_version for call in first["calls"]))

    def test_manifest_is_deterministic_and_does_not_need_a_transport(self) -> None:
        config = load_config()
        catalog = PromptCatalog.from_dict(raw_catalog())
        first = build_live_request_preflight(config, catalog)
        second = build_live_request_preflight(config, catalog)
        self.assertEqual(first, second)
        self.assertEqual(
            sum(len(scenario["calls"]) for scenario in first["scenarios"]),
            len(config.scenarios) * 8,
        )


if __name__ == "__main__":
    unittest.main()
