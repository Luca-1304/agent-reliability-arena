from __future__ import annotations

from agent_reliability_arena.config import ExperimentConfig

RAW_CONFIG = {
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


def config() -> ExperimentConfig:
    return ExperimentConfig.from_dict(RAW_CONFIG)
