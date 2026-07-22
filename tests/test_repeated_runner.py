from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.live_orchestration import LiveOrchestrationError
from agent_reliability_arena.repeated_plan import build_counterbalanced_plan
from agent_reliability_arena.repeated_runner import run_private_repeated_experiment
from test_private_pilot import (
    ScriptedTransport,
    load_catalog,
    load_config,
    policy_for,
    success_outputs,
)


def build_plan(repetitions: int = 4, *, starting_seed: int = 700):
    config = load_config()
    catalog = load_catalog()
    template = policy_for(config)
    plan = build_counterbalanced_plan(
        config,
        catalog,
        template,
        scenario_ids=("success",),
        repetitions_per_scenario=repetitions,
        starting_seed=starting_seed,
    )
    return config, catalog, template, plan


class RepeatedPrivateRunnerTests(unittest.TestCase):
    def test_four_counterbalanced_trials_complete_with_verified_private_evidence(self) -> None:
        config, catalog, template, plan = build_plan(4)
        transport = ScriptedTransport(success_outputs(config))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "experiment"
            summary = run_private_repeated_experiment(
                config,
                catalog,
                plan,
                template,
                transport,
                root,
                reviewed_plan_digest=plan.digest,
                reviewed_policy_template_digest=template.digest,
                external_execution_approved=True,
            )

            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["planned_trials"], 4)
            self.assertEqual(summary["completed_trials"], 4)
            self.assertEqual(summary["aborted_trials"], 0)
            self.assertFalse(summary["comparative_claim_permitted"])
            self.assertEqual(len(transport.calls), 20)
            self.assertTrue((root / "experiment-plan.json").is_file())
            self.assertTrue((root / "experiment-preflight.json").is_file())
            self.assertTrue((root / "experiment-start.json").is_file())
            self.assertTrue((root / "experiment-checkpoint.json").is_file())
            self.assertTrue((root / "experiment-summary.json").is_file())
            self.assertFalse((root / "experiment-abort.json").exists())

            orders = []
            for trial in plan.trials:
                trial_root = root / trial.trial_id
                trial_summary = json.loads(
                    (trial_root / "verification-summary.json").read_text(encoding="utf-8")
                )
                orders.append(trial_summary["condition_order"])
                self.assertEqual(trial_summary["scenario_id"], trial.scenario_id)
                self.assertTrue((trial_root / "transport-calls.jsonl").is_file())
            self.assertEqual(
                orders,
                [
                    ["general", "specialist"],
                    ["specialist", "general"],
                    ["general", "specialist"],
                    ["specialist", "general"],
                ],
            )

    def test_deliberate_pause_resumes_verified_prefix_without_replaying_calls(self) -> None:
        config, catalog, template, plan = build_plan(3, starting_seed=800)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "experiment"
            first_transport = ScriptedTransport(success_outputs(config))
            paused = run_private_repeated_experiment(
                config,
                catalog,
                plan,
                template,
                first_transport,
                root,
                reviewed_plan_digest=plan.digest,
                reviewed_policy_template_digest=template.digest,
                external_execution_approved=True,
                max_new_trials=1,
            )
            self.assertEqual(paused["status"], "paused")
            self.assertEqual(paused["completed_trials"], 1)
            self.assertEqual(len(first_transport.calls), 5)
            self.assertFalse((root / "experiment-summary.json").exists())
            self.assertFalse((root / "experiment-abort.json").exists())

            second_transport = ScriptedTransport(success_outputs(config))
            completed = run_private_repeated_experiment(
                config,
                catalog,
                plan,
                template,
                second_transport,
                root,
                reviewed_plan_digest=plan.digest,
                reviewed_policy_template_digest=template.digest,
                external_execution_approved=True,
            )
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["completed_trials"], 3)
            self.assertEqual(len(second_transport.calls), 10)
            checkpoint = json.loads(
                (root / "experiment-checkpoint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                checkpoint["completed_trial_ids"],
                ["trial-0001", "trial-0002", "trial-0003"],
            )

    def test_trial_abort_is_terminal_and_preserves_experiment_abort(self) -> None:
        config, catalog, template, plan = build_plan(2, starting_seed=900)
        outputs = success_outputs(config)
        general_id = f"{config.experiment_id}--general--success--general--1"
        outputs[general_id] = {"invalid": "general output"}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "experiment"
            with self.assertRaises(LiveOrchestrationError):
                run_private_repeated_experiment(
                    config,
                    catalog,
                    plan,
                    template,
                    ScriptedTransport(outputs),
                    root,
                    reviewed_plan_digest=plan.digest,
                    reviewed_policy_template_digest=template.digest,
                    external_execution_approved=True,
                )
            abort = json.loads((root / "experiment-abort.json").read_text(encoding="utf-8"))
            self.assertEqual(abort["status"], "aborted")
            self.assertEqual(abort["failed_trial_id"], "trial-0001")
            self.assertTrue((root / "trial-0001" / "abort.json").is_file())
            self.assertFalse((root / "experiment-summary.json").exists())

            with self.assertRaisesRegex(ValueError, "terminal"):
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

    def test_resume_rejects_extra_partial_and_drifted_evidence(self) -> None:
        config, catalog, template, plan = build_plan(3, starting_seed=1000)
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
                max_new_trials=1,
            )
            (root / "unexpected-trial").mkdir()
            with self.assertRaisesRegex(ValueError, "unexpected"):
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
                max_new_trials=1,
            )
            (root / "trial-0002").mkdir()
            with self.assertRaisesRegex(ValueError, "partial"):
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
                max_new_trials=1,
            )
            _, _, _, drifted_plan = build_plan(3, starting_seed=2000)
            with self.assertRaisesRegex(ValueError, "plan digest"):
                run_private_repeated_experiment(
                    config,
                    catalog,
                    drifted_plan,
                    template,
                    ScriptedTransport(success_outputs(config)),
                    root,
                    reviewed_plan_digest=drifted_plan.digest,
                    reviewed_policy_template_digest=template.digest,
                    external_execution_approved=True,
                )


if __name__ == "__main__":
    unittest.main()
