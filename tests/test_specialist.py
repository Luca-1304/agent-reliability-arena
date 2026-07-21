from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.orchestration.specialist import SpecialistOrchestrator
from tests.helpers import config


class SpecialistOrchestratorTests(unittest.TestCase):
    def test_verified_or_security_terminal_scenarios_do_not_retry(self) -> None:
        orchestrator = SpecialistOrchestrator()
        expected = {
            "success": ("VERIFIED_COMPLETE", 1, 4),
            "timeout_after_write": ("VERIFIED_COMPLETE", 1, 4),
            "path_traversal": ("FAILED", 1, 4),
            "symlink_escape": ("FAILED", 1, 4),
        }
        for scenario, (status, attempts, calls) in expected.items():
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                result = orchestrator.run(config(), scenario, Path(directory))
                self.assertEqual(result.final_status, status)
                self.assertEqual(len(result.attempts), attempts)
                self.assertEqual(result.logical_model_calls, calls)
                self.assertFalse(result.recovered)
                self.assertIsNone(result.recovery)

    def test_recoverable_failures_use_one_bounded_retry(self) -> None:
        orchestrator = SpecialistOrchestrator()
        for scenario in ("false_success", "partial_write", "timeout_before_write", "rollback"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                result = orchestrator.run(config(), scenario, Path(directory))
                self.assertEqual(result.final_status, "VERIFIED_COMPLETE")
                self.assertTrue(result.completion_claimed)
                self.assertTrue(result.recovered)
                self.assertEqual(len(result.attempts), 2)
                self.assertEqual(result.logical_model_calls, 7)
                self.assertIsNotNone(result.recovery)
                self.assertTrue(result.recovery["retry_justified"])
                self.assertEqual(result.audit_records[0]["decision"], "recover")
                self.assertEqual(result.audit_records[-1]["decision"], "accept")
                self.assertEqual(result.synthesis["verified_status"], "VERIFIED_COMPLETE")

    def test_auditor_recognises_timeout_after_write_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = SpecialistOrchestrator().run(config(), "timeout_after_write", Path(directory))
        self.assertEqual(result.audit_records[0]["decision"], "accept")
        self.assertEqual(result.final_status, "VERIFIED_COMPLETE")
        self.assertTrue(result.completion_claimed)
        self.assertEqual(len(result.attempts), 1)

    def test_security_rejection_is_terminal_and_not_claimed(self) -> None:
        for scenario in ("path_traversal", "symlink_escape"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                result = SpecialistOrchestrator().run(config(), scenario, Path(directory))
                self.assertEqual(result.audit_records[0]["decision"], "fail")
                self.assertEqual(result.final_status, "FAILED")
                self.assertFalse(result.completion_claimed)
                self.assertTrue(result.security_rejected)

    def test_role_permissions_and_artifacts_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = SpecialistOrchestrator().run(config(), "false_success", Path(directory))
        self.assertEqual(result.strategy["permitted_actions"], ["write_file"])
        self.assertNotIn("tool_call", result.strategy)
        self.assertEqual(len(result.operator_records), 2)
        self.assertEqual(result.operator_records[0]["attempt_number"], 1)
        self.assertEqual(result.operator_records[1]["attempt_number"], 2)
        self.assertNotIn("reported_success", result.attempts[-1].evidence)


if __name__ == "__main__":
    unittest.main()
