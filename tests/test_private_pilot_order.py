from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.private_pilot import run_private_paired_pilot
from test_private_pilot import (
    ScriptedTransport,
    load_catalog,
    load_config,
    policy_for,
    success_outputs,
)


class PrivatePilotConditionOrderTests(unittest.TestCase):
    def test_specialist_first_executes_in_order_and_preserves_named_artifacts(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = policy_for(config)
        transport = ScriptedTransport(success_outputs(config))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "specialist-first"
            summary = run_private_paired_pilot(
                config,
                catalog,
                policy,
                transport,
                root,
                reviewed_policy_digest=policy.digest,
                external_execution_approved=True,
                condition_order=("specialist", "general"),
            )

            self.assertEqual(summary["condition_order"], ["specialist", "general"])
            start = json.loads((root / "run-start.json").read_text(encoding="utf-8"))
            self.assertEqual(start["condition_order"], ["specialist", "general"])
            self.assertIn("--specialist--", transport.calls[0])
            self.assertIn("--general--", transport.calls[-1])
            self.assertTrue((root / "general" / "result.json").is_file())
            self.assertTrue((root / "specialist" / "result.json").is_file())
            self.assertTrue(summary["conditions"]["general"]["verified_complete"])
            self.assertTrue(summary["conditions"]["specialist"]["verified_complete"])

    def test_invalid_condition_order_is_rejected_before_evidence_creation(self) -> None:
        config = load_config()
        catalog = load_catalog()
        policy = policy_for(config)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "invalid-order"
            with self.assertRaisesRegex(ValueError, "condition_order"):
                run_private_paired_pilot(
                    config,
                    catalog,
                    policy,
                    ScriptedTransport(success_outputs(config)),
                    root,
                    reviewed_policy_digest=policy.digest,
                    external_execution_approved=True,
                    condition_order=("general", "general"),
                )
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
