from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_reliability_arena.portfolio_demo import (
    PortfolioDemoError,
    canonicalise_events,
    evaluate_portfolio_suite,
)


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "portfolio" / "ai-operations-assurance"


def load_json(name: str) -> dict[str, object]:
    raw = json.loads((PORTFOLIO / name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


class PortfolioDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_json("acceptance_contract.json")
        self.suite = load_json("scenarios.json")

    def test_public_suite_matches_preregistered_expected_statuses(self) -> None:
        report = evaluate_portfolio_suite(self.contract, self.suite)
        self.assertTrue(report["all_expected"])
        self.assertEqual(report["scenario_count"], 6)
        self.assertEqual(report["verified_complete"], 2)
        self.assertEqual(report["false_completions"], 4)
        statuses = {
            result["scenario_id"]: result["evaluation"]["status"]
            for result in report["results"]
        }
        self.assertEqual(statuses["verified_draft"], "VERIFIED_COMPLETE")
        self.assertEqual(statuses["false_success_without_observation"], "PARTIAL")
        self.assertEqual(statuses["stale_approval_content_changed"], "FAILED")
        self.assertEqual(statuses["duplicate_retry"], "FAILED")
        self.assertEqual(statuses["rollback_after_creation"], "FAILED")
        self.assertEqual(statuses["verified_without_claim"], "VERIFIED_COMPLETE")

    def test_stale_approval_turns_source_success_into_canonical_failure(self) -> None:
        scenario = next(
            value
            for value in self.suite["scenarios"]
            if value["scenario_id"] == "stale_approval_content_changed"
        )
        events = canonicalise_events(self.contract, scenario["events"])
        created = next(event for event in events if event["action"] == "create_email_draft")
        self.assertFalse(created["success"])
        self.assertIn(
            "created content does not match approved content",
            created["evidence"]["contract_mismatches"],
        )

    def test_duplicate_idempotency_key_fails_latest_mutation(self) -> None:
        scenario = next(
            value
            for value in self.suite["scenarios"]
            if value["scenario_id"] == "duplicate_retry"
        )
        events = canonicalise_events(self.contract, scenario["events"])
        created = [event for event in events if event["action"] == "create_email_draft"]
        self.assertEqual(len(created), 2)
        self.assertTrue(created[0]["success"])
        self.assertFalse(created[1]["success"])
        self.assertIn(
            "duplicate successful mutation for idempotency key "
            "SYN-PROT-001-income-confirmation-v1",
            created[1]["evidence"]["contract_mismatches"],
        )

    def test_verified_without_claim_is_recorded_as_silent_completion(self) -> None:
        report = evaluate_portfolio_suite(self.contract, self.suite)
        result = next(
            value
            for value in report["results"]
            if value["scenario_id"] == "verified_without_claim"
        )
        self.assertTrue(result["silent_verified_completion"])
        self.assertFalse(result["false_completion"])

    def test_expected_value_mismatch_is_failed_closed(self) -> None:
        events = [
            {
                "action": "confirm_email_not_sent",
                "success": True,
                "evidence": {
                    "draft_id": "draft-synthetic-001",
                    "send_status": "sent",
                    "observed_at": "2026-07-28T18:00:00Z",
                },
            }
        ]
        canonical = canonicalise_events(self.contract, events)
        self.assertFalse(canonical[0]["success"])
        self.assertIn("expected send_status='not_sent'", canonical[0]["evidence"]["contract_mismatches"][0])

    def test_empty_contract_is_rejected(self) -> None:
        with self.assertRaises(PortfolioDemoError):
            evaluate_portfolio_suite({"requirements": []}, self.suite)


if __name__ == "__main__":
    unittest.main()
