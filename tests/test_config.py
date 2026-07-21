from __future__ import annotations

import unittest

from agent_reliability_arena.config import ExperimentConfig


RAW = {
    "experiment_id": "fixture-v1",
    "generated_at": "2026-07-21T00:00:00Z",
    "model_id": "fixture-model-v1",
    "model_version": "1",
    "prompt_version": "fixture-prompts-v1",
    "seed": 1304,
    "task": "Write the exact contracted content to the exact relative path.",
    "scenarios": [
        "success",
        "false_success",
        "partial_write",
        "timeout_before_write",
        "timeout_after_write",
        "rollback",
        "path_traversal",
        "symlink_escape",
    ],
    "conditions": ["general", "specialist"],
    "max_mutation_attempts": 2,
    "contract": {
        "contract_id": "arena-contract-v1",
        "path": "output/result.txt",
        "content": "Verified output from Agent Reliability Arena.\n",
    },
}


class ExperimentConfigTests(unittest.TestCase):
    def test_round_trip_and_digest_are_deterministic(self) -> None:
        config = ExperimentConfig.from_dict(RAW)
        self.assertEqual(config.to_dict(), RAW | {"schema_version": "1"})
        reordered = dict(reversed(list(RAW.items())))
        self.assertEqual(config.digest, ExperimentConfig.from_dict(reordered).digest)
        self.assertEqual(len(config.digest), 64)

    def test_fairness_fingerprint_excludes_condition_name(self) -> None:
        config = ExperimentConfig.from_dict(RAW)
        general = config.fairness_fingerprint("general")
        specialist = config.fairness_fingerprint("specialist")
        self.assertEqual(general, specialist)
        self.assertNotIn("condition", general)
        self.assertEqual(general["model_id"], "fixture-model-v1")
        self.assertEqual(general["max_mutation_attempts"], 2)

    def test_rejects_duplicate_or_unknown_scenarios(self) -> None:
        duplicate = dict(RAW)
        duplicate["scenarios"] = ["success", "success"]
        with self.assertRaisesRegex(ValueError, "Duplicate scenario"):
            ExperimentConfig.from_dict(duplicate)
        unknown = dict(RAW)
        unknown["scenarios"] = ["success", "magic"]
        with self.assertRaisesRegex(ValueError, "Unknown scenario"):
            ExperimentConfig.from_dict(unknown)

    def test_requires_both_conditions_in_fixed_order(self) -> None:
        for conditions in (["general"], ["specialist", "general"], ["general", "general"]):
            raw = dict(RAW)
            raw["conditions"] = conditions
            with self.subTest(conditions=conditions), self.assertRaisesRegex(ValueError, "conditions"):
                ExperimentConfig.from_dict(raw)

    def test_rejects_unbounded_mutation_attempts_and_invalid_seed(self) -> None:
        for field, value, message in (
            ("max_mutation_attempts", 0, "max_mutation_attempts"),
            ("max_mutation_attempts", 3, "max_mutation_attempts"),
            ("seed", True, "seed"),
        ):
            raw = dict(RAW)
            raw[field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, message):
                ExperimentConfig.from_dict(raw)


if __name__ == "__main__":
    unittest.main()
