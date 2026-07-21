from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from completion_verifier.models import Status
from agent_reliability_arena.orchestration.general import GeneralOrchestrator
from tests.helpers import config


EXPECTED = {
    "success": Status.VERIFIED_COMPLETE,
    "false_success": Status.FAILED,
    "partial_write": Status.FAILED,
    "timeout_before_write": Status.FAILED,
    "timeout_after_write": Status.VERIFIED_COMPLETE,
    "rollback": Status.FAILED,
    "path_traversal": Status.FAILED,
    "symlink_escape": Status.FAILED,
}


class GeneralOrchestratorTests(unittest.TestCase):
    def test_all_scenarios_preserve_verifier_truth(self) -> None:
        orchestrator = GeneralOrchestrator()
        for scenario, expected in EXPECTED.items():
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                result = orchestrator.run(config(), scenario, Path(directory))
                self.assertEqual(result.condition, "general")
                self.assertEqual(result.final_status, expected.value)
                self.assertEqual(result.logical_model_calls, 1)
                self.assertEqual(len(result.attempts), 1)
                self.assertFalse(result.recovered)
                self.assertEqual(result.completion_claimed, result.attempts[0].source_report["completion_claimed"])
                self.assertEqual(
                    result.attempts[0].evidence["trust_basis"],
                    "independent_local_state",
                )

    def test_false_success_partial_and_rollback_are_false_completions(self) -> None:
        orchestrator = GeneralOrchestrator()
        for scenario in ("false_success", "partial_write", "rollback"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                result = orchestrator.run(config(), scenario, Path(directory))
                self.assertTrue(result.completion_claimed)
                self.assertEqual(result.final_status, "FAILED")
                self.assertTrue(result.false_completion)

    def test_timeout_after_write_is_silent_verified_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = GeneralOrchestrator().run(config(), "timeout_after_write", Path(directory))
        self.assertEqual(result.final_status, "VERIFIED_COMPLETE")
        self.assertFalse(result.completion_claimed)
        self.assertTrue(result.silent_verified_completion)

    def test_non_empty_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "existing.txt").write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "empty"):
                GeneralOrchestrator().run(config(), "success", root)


if __name__ == "__main__":
    unittest.main()
