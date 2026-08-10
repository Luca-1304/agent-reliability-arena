from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.repeated_runner import run_private_repeated_experiment
from agent_reliability_arena.repeated_witness import WITNESS_FILENAME
from agent_reliability_arena.transports import verify_transport_ledger
from test_private_pilot import ScriptedTransport, success_outputs
from test_repeated_runner import build_plan


class RepeatedRunnerWitnessTests(unittest.TestCase):
    def test_completed_run_witnesses_every_trial_in_order(self) -> None:
        config, catalog, template, plan = build_plan(4, starting_seed=1100)
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
            self.assertEqual(len(transport.calls), 20)
            rows = [
                json.loads(line)
                for line in (root / WITNESS_FILENAME).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([row["sequence"] for row in rows], [1, 2, 3, 4])
            self.assertEqual(
                [row["trial_id"] for row in rows],
                ["trial-0001", "trial-0002", "trial-0003", "trial-0004"],
            )
            self.assertIsNone(rows[0]["previous_witness_digest"])
            for previous, current in zip(rows, rows[1:]):
                self.assertEqual(current["previous_witness_digest"], previous["witness_digest"])

    def test_pause_resume_preserves_witness_prefix_without_replaying_calls(self) -> None:
        config, catalog, template, plan = build_plan(3, starting_seed=1200)
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
            self.assertEqual(len(first_transport.calls), 5)
            witness = root / WITNESS_FILENAME
            first_line = witness.read_bytes()

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
            self.assertEqual(len(second_transport.calls), 10)
            self.assertTrue(witness.read_bytes().startswith(first_line))
            self.assertEqual(len(witness.read_text(encoding="utf-8").splitlines()), 3)

    def test_resume_rejects_consistently_valid_summary_byte_rewrite_before_new_calls(self) -> None:
        config, catalog, template, plan = build_plan(3, starting_seed=1300)
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

            summary_path = root / "trial-0001" / "verification-summary.json"
            summary_path.write_bytes(summary_path.read_bytes() + b" ")
            fresh_transport = ScriptedTransport(success_outputs(config))
            with self.assertRaisesRegex(ValueError, "Witness verification summary digest mismatch"):
                run_private_repeated_experiment(
                    config,
                    catalog,
                    plan,
                    template,
                    fresh_transport,
                    root,
                    reviewed_plan_digest=plan.digest,
                    reviewed_policy_template_digest=template.digest,
                    external_execution_approved=True,
                )
            self.assertEqual(len(fresh_transport.calls), 0)

    def test_resume_rejects_valid_ledger_suffix_truncation_even_after_summary_rewrite(self) -> None:
        config, catalog, template, plan = build_plan(3, starting_seed=1400)
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

            trial_root = root / "trial-0001"
            ledger_path = trial_root / "transport-calls.jsonl"
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 5)
            ledger_path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            shorter_ledger = verify_transport_ledger(ledger_path)
            self.assertEqual(shorter_ledger["records"], 4)

            summary_path = trial_root / "verification-summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["ledger"] = shorter_ledger
            summary_path.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            fresh_transport = ScriptedTransport(success_outputs(config))
            with self.assertRaisesRegex(ValueError, "Witness ledger record count mismatch"):
                run_private_repeated_experiment(
                    config,
                    catalog,
                    plan,
                    template,
                    fresh_transport,
                    root,
                    reviewed_plan_digest=plan.digest,
                    reviewed_policy_template_digest=template.digest,
                    external_execution_approved=True,
                )
            self.assertEqual(len(fresh_transport.calls), 0)


if __name__ == "__main__":
    unittest.main()
