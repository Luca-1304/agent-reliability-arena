from __future__ import annotations

import unittest

from agent_reliability_arena.schemas import (
    AuditRecord,
    OperatorRecord,
    RecoveryRecord,
    StrategyPlan,
    SynthesisRecord,
)


class RoleSchemaTests(unittest.TestCase):
    def test_strategy_plan_is_bounded_and_non_mutating(self) -> None:
        plan = StrategyPlan(
            contract_summary="Write one exact UTF-8 file.",
            required_postcondition="Exact path, bytes and digest match.",
            permitted_actions=("write_file",),
            anticipated_failures=("false_success", "partial_write"),
            retryable_failures=("false_success", "partial_write"),
            terminal_failures=("security_rejection",),
            stop_conditions=("verified", "attempt_limit", "security_rejection"),
        )
        payload = plan.to_dict()
        self.assertEqual(payload["permitted_actions"], ["write_file"])
        self.assertNotIn("tool_call", payload)
        self.assertEqual(len(plan.digest), 64)

    def test_operator_requires_exact_approved_action_and_attempt(self) -> None:
        record = OperatorRecord(
            approved_action="write_file",
            attempted_path="output/result.txt",
            attempted_content_sha256="a" * 64,
            attempt_number=1,
            source_event_id="source-1",
        )
        self.assertEqual(record.attempt_number, 1)
        for action, attempt in (("shell", 1), ("write_file", 0), ("write_file", 3)):
            with self.subTest(action=action, attempt=attempt), self.assertRaises(ValueError):
                OperatorRecord(action, "output/result.txt", "a" * 64, attempt, "source-1")

    def test_auditor_decision_is_closed_enum_with_evidence(self) -> None:
        record = AuditRecord(
            decision="recover",
            source_assessment="Receipt conflicts with state.",
            observation_assessment="Expected file is absent.",
            conflicts=("reported_success_without_file",),
            evidence_refs=("observation.json", "source_report.json"),
        )
        self.assertEqual(record.decision, "recover")
        with self.assertRaisesRegex(ValueError, "decision"):
            AuditRecord("override", "x", "y", (), ("observation.json",))
        with self.assertRaisesRegex(ValueError, "evidence"):
            AuditRecord("accept", "x", "y", (), ())

    def test_recovery_requires_justification_and_remaining_attempt(self) -> None:
        record = RecoveryRecord(
            failure_class="partial_write",
            retry_justified=True,
            proposed_action="write_file",
            remaining_attempts=1,
            refusal_reason=None,
        )
        self.assertTrue(record.retry_justified)
        with self.assertRaisesRegex(ValueError, "remaining_attempts"):
            RecoveryRecord("partial_write", True, "write_file", 0, None)
        refused = RecoveryRecord("security_rejection", False, None, 0, "Terminal security failure.")
        self.assertFalse(refused.retry_justified)

    def test_synthesis_cannot_claim_unverified_completion(self) -> None:
        accepted = SynthesisRecord(
            completion_claimed=True,
            verified_status="VERIFIED_COMPLETE",
            summary="The independent verifier confirmed the file.",
            limitations=("Fixture policy, not model performance.",),
            evidence_refs=("evaluation.json",),
        )
        self.assertTrue(accepted.completion_claimed)
        with self.assertRaisesRegex(ValueError, "cannot claim"):
            SynthesisRecord(True, "FAILED", "Done", (), ("evaluation.json",))


if __name__ == "__main__":
    unittest.main()
