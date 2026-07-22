from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.repeated_analysis import (
    analyse_repeated_experiment,
    analyse_trial_records,
    exact_sign_test_p_value,
    paired_normal_interval,
    wilson_interval,
)
from agent_reliability_arena.repeated_plan import build_counterbalanced_plan
from agent_reliability_arena.repeated_runner import run_private_repeated_experiment
from test_private_pilot import (
    ScriptedTransport,
    load_catalog,
    load_config,
    policy_for,
    success_outputs,
)


def record(
    trial_id: str,
    general: bool,
    specialist: bool,
    *,
    calls: int = 5,
    input_tokens: int = 10,
    output_tokens: int = 5,
    total_tokens: int = 15,
    latency_ms: int = 2,
    processing_ms: int = 1,
) -> dict[str, object]:
    return {
        "trial_id": trial_id,
        "general_verified_complete": general,
        "specialist_verified_complete": specialist,
        "logical_model_calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
        "wall_clock_latency_ms": latency_ms,
        "provider_processing_ms": processing_ms,
        "provider_processing_reported_calls": calls,
        "error_records": 0,
    }


class RepeatedExperimentAnalysisTests(unittest.TestCase):
    def test_trial_records_preserve_absolute_paired_outcomes_and_measurements(self) -> None:
        analysis = analyse_trial_records(
            [
                record("trial-0001", True, True),
                record("trial-0002", False, False),
                record("trial-0003", False, True),
                record("trial-0004", True, False),
            ],
            planned_trials=4,
            aborted_trials=0,
        )

        self.assertEqual(analysis["trials"]["planned"], 4)
        self.assertEqual(analysis["trials"]["completed"], 4)
        self.assertEqual(analysis["trials"]["aborted"], 0)
        self.assertEqual(
            analysis["outcomes"],
            {
                "general_verified_complete": 2,
                "specialist_verified_complete": 2,
                "both_complete": 1,
                "neither_complete": 1,
                "specialist_only": 1,
                "general_only": 1,
                "discordant_pairs": 2,
            },
        )
        self.assertEqual(analysis["proportions"]["general"], 0.5)
        self.assertEqual(analysis["proportions"]["specialist"], 0.5)
        self.assertEqual(analysis["paired_difference"], 0.0)
        self.assertEqual(analysis["uncertainty"]["discordant_sign_test"]["p_value"], 1.0)
        self.assertEqual(analysis["measurements"]["logical_model_calls"], 20)
        self.assertEqual(analysis["measurements"]["input_tokens"], 40)
        self.assertEqual(analysis["measurements"]["output_tokens"], 20)
        self.assertEqual(analysis["measurements"]["total_tokens"], 60)
        self.assertEqual(analysis["measurements"]["wall_clock_latency_ms"], 8)
        self.assertFalse(analysis["comparative_claim_permitted"])

    def test_uncertainty_methods_are_bounded_and_explicit(self) -> None:
        general = wilson_interval(2, 4)
        self.assertEqual(general["method"], "wilson-score-95-percent")
        self.assertGreaterEqual(general["lower"], 0.0)
        self.assertLessEqual(general["upper"], 1.0)

        paired = paired_normal_interval([0, 0, 1, -1])
        self.assertEqual(paired["method"], "paired-normal-approximation-95-percent")
        self.assertGreaterEqual(paired["lower"], -1.0)
        self.assertLessEqual(paired["upper"], 1.0)
        self.assertEqual(paired["estimate"], 0.0)

        self.assertEqual(exact_sign_test_p_value(1, 1), 1.0)
        self.assertIsNone(exact_sign_test_p_value(0, 0))

    def test_zero_discordance_is_reported_without_an_invented_p_value(self) -> None:
        analysis = analyse_trial_records(
            [record("trial-0001", True, True), record("trial-0002", False, False)],
            planned_trials=2,
            aborted_trials=0,
        )
        self.assertEqual(analysis["outcomes"]["discordant_pairs"], 0)
        self.assertIsNone(analysis["uncertainty"]["discordant_sign_test"]["p_value"])
        self.assertIn("no discordant", analysis["uncertainty"]["discordant_sign_test"]["limitation"])

    def test_private_root_analysis_reverifies_ledgers_and_sums_measured_usage(self) -> None:
        config = load_config()
        catalog = load_catalog()
        template = policy_for(config)
        plan = build_counterbalanced_plan(
            config,
            catalog,
            template,
            scenario_ids=("success",),
            repetitions_per_scenario=2,
            starting_seed=1200,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "experiment"
            run_private_repeated_experiment(
                config,
                catalog,
                plan,
                template,
                ScriptedTransport(success_outputs(config)),
                root,
                reviewed_plan_digest=plan.digest,
                reviewed_policy_template_digest=template.digest,
                external_execution_approved=True,
            )
            analysis = analyse_repeated_experiment(root, plan, catalog)

        self.assertEqual(analysis["trials"], {"planned": 2, "completed": 2, "aborted": 0})
        self.assertEqual(analysis["outcomes"]["both_complete"], 2)
        self.assertEqual(analysis["measurements"]["logical_model_calls"], 10)
        self.assertEqual(analysis["measurements"]["input_tokens"], 100)
        self.assertEqual(analysis["measurements"]["output_tokens"], 100)
        self.assertEqual(analysis["measurements"]["total_tokens"], 200)
        self.assertEqual(analysis["measurements"]["wall_clock_latency_ms"], 20)
        self.assertEqual(analysis["measurements"]["provider_processing_ms"], 10)
        self.assertEqual(analysis["measurements"]["provider_processing_reported_calls"], 10)


if __name__ == "__main__":
    unittest.main()
