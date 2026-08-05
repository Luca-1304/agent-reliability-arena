from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.live_requests import PromptCatalog
from agent_reliability_arena.pilot_policy import PilotPolicy
from agent_reliability_arena.repeated_plan import (
    RepeatedExperimentPlan,
    TrialPlan,
    build_counterbalanced_plan,
    build_repeated_experiment_preflight,
)
from agent_reliability_arena.transports.base import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "examples" / "fixture_experiment.json"
CATALOG_PATH = ROOT / "examples" / "live_prompt_catalog.json"


def load_config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def load_catalog() -> PromptCatalog:
    return PromptCatalog.from_dict(json.loads(CATALOG_PATH.read_text(encoding="utf-8")))


def policy_template(*, enabled: bool = False) -> PilotPolicy:
    return PilotPolicy(
        provider="openai-responses",
        model_id="fixture-model-v1",
        model_version="1",
        prompt_version="fixture-prompts-v1",
        scenario_ids=("success",),
        max_calls=8,
        max_requested_output_tokens=2068,
        reserved_total_tokens_per_call=2048,
        max_reserved_total_tokens=16384,
        currency="GBP",
        reserved_cost_per_call_minor_units=12,
        max_cost_minor_units=100,
        external_execution_enabled=enabled,
    )


class RepeatedExperimentPlanTests(unittest.TestCase):
    def test_counterbalanced_plan_is_deterministic_round_robin_and_digest_stable(self) -> None:
        config = load_config()
        catalog = load_catalog()
        template = policy_template()

        plan = build_counterbalanced_plan(
            config,
            catalog,
            template,
            scenario_ids=("success", "false_success"),
            repetitions_per_scenario=3,
            starting_seed=100,
        )

        self.assertEqual(
            [trial.to_dict() for trial in plan.trials],
            [
                {
                    "trial_id": "trial-0001",
                    "scenario_id": "success",
                    "seed": 100,
                    "condition_order": ["general", "specialist"],
                },
                {
                    "trial_id": "trial-0002",
                    "scenario_id": "false_success",
                    "seed": 101,
                    "condition_order": ["general", "specialist"],
                },
                {
                    "trial_id": "trial-0003",
                    "scenario_id": "success",
                    "seed": 102,
                    "condition_order": ["specialist", "general"],
                },
                {
                    "trial_id": "trial-0004",
                    "scenario_id": "false_success",
                    "seed": 103,
                    "condition_order": ["specialist", "general"],
                },
                {
                    "trial_id": "trial-0005",
                    "scenario_id": "success",
                    "seed": 104,
                    "condition_order": ["general", "specialist"],
                },
                {
                    "trial_id": "trial-0006",
                    "scenario_id": "false_success",
                    "seed": 105,
                    "condition_order": ["general", "specialist"],
                },
            ],
        )
        self.assertEqual(plan.digest, canonical_json_sha256(plan.to_dict()))
        self.assertEqual(RepeatedExperimentPlan.from_dict(plan.to_dict()), plan)
        self.assertEqual(plan.order_counts["success"], {"general_first": 2, "specialist_first": 1})
        self.assertEqual(
            plan.order_counts["false_success"],
            {"general_first": 2, "specialist_first": 1},
        )

    def test_plan_rejects_duplicate_ids_seeds_and_unbalanced_order(self) -> None:
        config = load_config()
        catalog = load_catalog()
        template = policy_template()
        valid = build_counterbalanced_plan(
            config,
            catalog,
            template,
            scenario_ids=("success",),
            repetitions_per_scenario=2,
            starting_seed=7,
        )
        first, second = valid.trials

        with self.assertRaisesRegex(ValueError, "trial_id"):
            RepeatedExperimentPlan(
                provider=valid.provider,
                model_id=valid.model_id,
                model_version=valid.model_version,
                prompt_version=valid.prompt_version,
                base_config_digest=valid.base_config_digest,
                contract_digest=valid.contract_digest,
                prompt_catalog_digest=valid.prompt_catalog_digest,
                pilot_policy_template_digest=valid.pilot_policy_template_digest,
                trials=(first, TrialPlan(first.trial_id, second.scenario_id, second.seed, second.condition_order)),
            )

        with self.assertRaisesRegex(ValueError, "seed"):
            RepeatedExperimentPlan(
                provider=valid.provider,
                model_id=valid.model_id,
                model_version=valid.model_version,
                prompt_version=valid.prompt_version,
                base_config_digest=valid.base_config_digest,
                contract_digest=valid.contract_digest,
                prompt_catalog_digest=valid.prompt_catalog_digest,
                pilot_policy_template_digest=valid.pilot_policy_template_digest,
                trials=(first, TrialPlan(second.trial_id, second.scenario_id, first.seed, second.condition_order)),
            )

        with self.assertRaisesRegex(ValueError, "imbalance"):
            RepeatedExperimentPlan(
                provider=valid.provider,
                model_id=valid.model_id,
                model_version=valid.model_version,
                prompt_version=valid.prompt_version,
                base_config_digest=valid.base_config_digest,
                contract_digest=valid.contract_digest,
                prompt_catalog_digest=valid.prompt_catalog_digest,
                pilot_policy_template_digest=valid.pilot_policy_template_digest,
                trials=(
                    first,
                    TrialPlan(second.trial_id, second.scenario_id, second.seed, ("general", "specialist")),
                ),
            )

    def test_builder_and_preflight_reject_source_drift_and_unknown_scenarios(self) -> None:
        config = load_config()
        catalog = load_catalog()
        template = policy_template()

        with self.assertRaisesRegex(ValueError, "scenario"):
            build_counterbalanced_plan(
                config,
                catalog,
                template,
                scenario_ids=("not-a-scenario",),
                repetitions_per_scenario=2,
                starting_seed=1,
            )

        plan = build_counterbalanced_plan(
            config,
            catalog,
            template,
            scenario_ids=("success",),
            repetitions_per_scenario=2,
            starting_seed=1,
        )
        drifted = PilotPolicy(
            provider=template.provider,
            model_id=template.model_id,
            model_version=template.model_version,
            prompt_version=template.prompt_version,
            scenario_ids=template.scenario_ids,
            max_calls=template.max_calls,
            max_requested_output_tokens=template.max_requested_output_tokens,
            reserved_total_tokens_per_call=template.reserved_total_tokens_per_call,
            max_reserved_total_tokens=template.max_reserved_total_tokens,
            currency=template.currency,
            reserved_cost_per_call_minor_units=13,
            max_cost_minor_units=104,
            external_execution_enabled=template.external_execution_enabled,
        )
        with self.assertRaisesRegex(ValueError, "template digest"):
            build_repeated_experiment_preflight(config, catalog, plan, drifted)

    def test_preflight_sums_exact_trial_reservations_without_provider_call(self) -> None:
        config = load_config()
        catalog = load_catalog()
        template = policy_template()
        plan = build_counterbalanced_plan(
            config,
            catalog,
            template,
            scenario_ids=("success", "false_success"),
            repetitions_per_scenario=2,
            starting_seed=500,
        )

        manifest = build_repeated_experiment_preflight(config, catalog, plan, template)
        unsigned = dict(manifest)
        digest = unsigned.pop("manifest_digest")
        self.assertEqual(digest, canonical_json_sha256(unsigned))
        self.assertFalse(manifest["provider_called"])
        self.assertFalse(manifest["external_execution_enabled"])
        self.assertEqual(manifest["plan_digest"], plan.digest)
        self.assertEqual(manifest["planned_trials"], 4)
        self.assertEqual(manifest["planned_call_ceiling"], 32)
        self.assertEqual(manifest["planned_requested_output_tokens"], 8272)
        self.assertEqual(manifest["reserved_total_tokens"], 65536)
        self.assertEqual(manifest["max_reserved_total_tokens"], 65536)
        self.assertEqual(manifest["reserved_cost_minor_units"], 384)
        self.assertEqual(manifest["max_cost_minor_units"], 400)
        self.assertEqual(manifest["currency"], "GBP")
        self.assertEqual(len(manifest["trials"]), 4)
        self.assertEqual(
            [trial["seed"] for trial in manifest["trials"]],
            [500, 501, 502, 503],
        )
        self.assertEqual(
            [trial["condition_order"] for trial in manifest["trials"]],
            [
                ["general", "specialist"],
                ["general", "specialist"],
                ["specialist", "general"],
                ["specialist", "general"],
            ],
        )
        self.assertEqual(len({trial["config_digest"] for trial in manifest["trials"]}), 4)
        self.assertNotIn("api_key", json.dumps(manifest).lower())


if __name__ == "__main__":
    unittest.main()
