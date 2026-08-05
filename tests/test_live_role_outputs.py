from __future__ import annotations

import hashlib
import json
import unittest

from agent_reliability_arena.live_role_outputs import (
    GeneralProposal,
    OperatorProposal,
    ParsedRoleOutput,
    parse_live_role_output,
)
from agent_reliability_arena.schemas import AuditRecord, RecoveryRecord, StrategyPlan, SynthesisRecord
from agent_reliability_arena.transports.base import canonical_json_sha256


def compact(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class LiveRoleOutputTests(unittest.TestCase):
    def test_parses_general_proposal_and_records_both_digests(self) -> None:
        payload = {
            "action": "write_file",
            "path": "output/result.txt",
            "content": "Verified output.\n",
            "completion_claimed": True,
            "rationale": "The requested action is explicit.",
        }
        raw = json.dumps(payload, ensure_ascii=False, indent=2)

        parsed = parse_live_role_output("general", raw)

        self.assertIsInstance(parsed, ParsedRoleOutput)
        self.assertIsInstance(parsed.value, GeneralProposal)
        self.assertEqual(parsed.role, "general")
        self.assertEqual(parsed.value.path, "output/result.txt")
        self.assertTrue(parsed.value.completion_claimed)
        self.assertEqual(parsed.payload, payload)
        self.assertEqual(parsed.raw_sha256, hashlib.sha256(raw.encode("utf-8")).hexdigest())
        self.assertEqual(parsed.canonical_sha256, canonical_json_sha256(payload))
        self.assertNotEqual(parsed.raw_sha256, parsed.canonical_sha256)

    def test_general_none_requires_null_path_and_content(self) -> None:
        valid = {
            "action": "none",
            "path": None,
            "content": None,
            "completion_claimed": False,
            "rationale": "No bounded action is justified.",
        }
        parsed = parse_live_role_output("general", compact(valid))
        self.assertEqual(parsed.value.to_dict(), valid)

        invalid = dict(valid)
        invalid["path"] = "output/result.txt"
        with self.assertRaisesRegex(ValueError, "null"):
            parse_live_role_output("general", compact(invalid))

    def test_parses_operator_and_enforces_expected_attempt(self) -> None:
        payload = {
            "approved_action": "write_file",
            "path": "output/result.txt",
            "content": "Verified output.\n",
            "attempt_number": 2,
            "rationale": "One bounded retry was approved.",
        }
        parsed = parse_live_role_output("operator", compact(payload), expected_attempt_number=2)
        self.assertIsInstance(parsed.value, OperatorProposal)
        self.assertEqual(parsed.value.to_dict(), payload)
        with self.assertRaisesRegex(ValueError, "expected_attempt_number"):
            parse_live_role_output("operator", compact(payload), expected_attempt_number=1)

    def test_parses_existing_strategy_audit_recovery_and_synthesis_schemas(self) -> None:
        strategy = {
            "contract_summary": "Write exact UTF-8 content to output/result.txt.",
            "required_postcondition": "Independent path, size, digest and content match.",
            "permitted_actions": ["write_file"],
            "anticipated_failures": ["false_success", "path_traversal"],
            "retryable_failures": ["false_success"],
            "terminal_failures": ["path_traversal"],
            "stop_conditions": ["verified", "attempt_limit", "security_rejection"],
        }
        audit = {
            "decision": "recover",
            "source_assessment": "The source reported success.",
            "observation_assessment": "Independent state does not match the contract.",
            "conflicts": ["reported_success_without_matching_state"],
            "evidence_refs": ["source_report.json", "observation.json", "evaluation.json"],
        }
        recovery = {
            "failure_class": "false_success",
            "retry_justified": True,
            "proposed_action": "write_file",
            "remaining_attempts": 1,
            "refusal_reason": None,
        }
        synthesis = {
            "completion_claimed": True,
            "verified_status": "VERIFIED_COMPLETE",
            "summary": "Independent evidence verified the contract.",
            "limitations": ["One controlled scenario."],
            "evidence_refs": ["evaluation.json", "observation.json"],
        }

        parsed_strategy = parse_live_role_output("strategist", compact(strategy))
        parsed_audit = parse_live_role_output("auditor", compact(audit))
        parsed_recovery = parse_live_role_output("recovery", compact(recovery))
        parsed_synthesis = parse_live_role_output("synthesiser", compact(synthesis))

        self.assertIsInstance(parsed_strategy.value, StrategyPlan)
        self.assertIsInstance(parsed_audit.value, AuditRecord)
        self.assertIsInstance(parsed_recovery.value, RecoveryRecord)
        self.assertIsInstance(parsed_synthesis.value, SynthesisRecord)
        self.assertEqual(parsed_strategy.value.to_dict(), strategy)
        self.assertEqual(parsed_audit.value.to_dict(), audit)
        self.assertEqual(parsed_recovery.value.to_dict(), recovery)
        self.assertEqual(parsed_synthesis.value.to_dict(), synthesis)

    def test_rejects_markdown_trailing_values_non_objects_and_unknown_roles(self) -> None:
        valid = {
            "action": "none",
            "path": None,
            "content": None,
            "completion_claimed": False,
            "rationale": "No action.",
        }
        cases = (
            ("general", "```json\n" + compact(valid) + "\n```"),
            ("general", compact(valid) + " trailing"),
            ("general", "[]"),
            ("general", '"text"'),
            ("judge", compact(valid)),
        )
        for role, raw in cases:
            with self.subTest(role=role, raw=raw), self.assertRaises(ValueError):
                parse_live_role_output(role, raw)

    def test_rejects_duplicate_keys_at_any_level_and_non_finite_numbers(self) -> None:
        duplicate_top = (
            '{"action":"none","action":"write_file","path":null,"content":null,'
            '"completion_claimed":false,"rationale":"No action."}'
        )
        duplicate_nested = (
            '{"contract_summary":"x","required_postcondition":"y",'
            '"permitted_actions":["write_file"],"anticipated_failures":["a"],'
            '"retryable_failures":["a"],"terminal_failures":["b"],'
            '"stop_conditions":["verified"],"extra":{"x":1,"x":2}}'
        )
        non_finite = (
            '{"action":"none","path":null,"content":null,'
            '"completion_claimed":false,"rationale":NaN}'
        )
        for role, raw in (("general", duplicate_top), ("strategist", duplicate_nested), ("general", non_finite)):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_live_role_output(role, raw)

    def test_rejects_oversized_output_unknown_or_missing_fields(self) -> None:
        oversized = {
            "action": "none",
            "path": None,
            "content": None,
            "completion_claimed": False,
            "rationale": "x" * 65536,
        }
        with self.assertRaisesRegex(ValueError, "65,536"):
            parse_live_role_output("general", compact(oversized))

        unknown = {
            "action": "none",
            "path": None,
            "content": None,
            "completion_claimed": False,
            "rationale": "No action.",
            "extra": True,
        }
        missing = dict(unknown)
        missing.pop("extra")
        missing.pop("rationale")
        for payload in (unknown, missing):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "fields"):
                parse_live_role_output("general", compact(payload))

    def test_rejects_unsafe_relative_paths(self) -> None:
        base = {
            "approved_action": "write_file",
            "path": "output/result.txt",
            "content": "x",
            "attempt_number": 1,
            "rationale": "Bounded proposal.",
        }
        unsafe = (
            "/tmp/result.txt",
            "../result.txt",
            "output/../result.txt",
            "output\\result.txt",
            "output//result.txt",
            "./output/result.txt",
            "C:/result.txt",
            "output/result.txt/",
            "output/\u0000result.txt",
        )
        for path in unsafe:
            payload = dict(base)
            payload["path"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "path"):
                parse_live_role_output("operator", compact(payload))

    def test_existing_role_invariants_still_fail_closed(self) -> None:
        bad_strategy = {
            "contract_summary": "x",
            "required_postcondition": "y",
            "permitted_actions": ["shell"],
            "anticipated_failures": ["a"],
            "retryable_failures": ["a"],
            "terminal_failures": ["b"],
            "stop_conditions": ["verified"],
        }
        bad_recovery = {
            "failure_class": "false_success",
            "retry_justified": False,
            "proposed_action": "write_file",
            "remaining_attempts": 0,
            "refusal_reason": "Retry refused.",
        }
        false_synthesis = {
            "completion_claimed": True,
            "verified_status": "FAILED",
            "summary": "Claimed anyway.",
            "limitations": [],
            "evidence_refs": ["evaluation.json"],
        }
        for role, payload in (
            ("strategist", bad_strategy),
            ("recovery", bad_recovery),
            ("synthesiser", false_synthesis),
        ):
            with self.subTest(role=role), self.assertRaises(ValueError):
                parse_live_role_output(role, compact(payload))


if __name__ == "__main__":
    unittest.main()
