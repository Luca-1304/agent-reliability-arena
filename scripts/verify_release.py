from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.artifacts import verify_manifest
from agent_reliability_arena.config import ExperimentConfig
from agent_reliability_arena.experiment import execute_fixture_experiment
from agent_reliability_arena.public_export import build_public_export
from agent_reliability_arena.replay import replay_experiment

ROOT = Path(__file__).resolve().parents[1]


def count_tests() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    return suite.countTestCases()


def main() -> None:
    config = ExperimentConfig.from_dict(json.loads((ROOT / "examples" / "fixture_experiment.json").read_text(encoding="utf-8")))
    reference = ROOT / "reference_runs" / "fixture-v1"
    if not reference.exists():
        raise AssertionError("Reference fixture artifacts are missing.")
    verify_manifest(reference)
    metrics = json.loads((reference / "aggregate_metrics.json").read_text(encoding="utf-8"))
    assert metrics["evidence_status"] == "deterministic_fixture"
    assert metrics["conditions"]["general"]["verified_complete"] == 2
    assert metrics["conditions"]["specialist"]["verified_complete"] == 6
    assert metrics["conditions"]["general"]["false_completion"] == 3
    assert metrics["conditions"]["specialist"]["false_completion"] == 0
    assert metrics["paired"]["additional_logical_model_calls"] == 36
    replay = replay_experiment(reference)
    assert replay["manifest_verified"] is True
    public = build_public_export(reference)
    assert len(public["scenarios"]) == 8
    assert public["evidence_status"] == "deterministic_fixture"
    with tempfile.TemporaryDirectory() as directory:
        fresh = Path(directory) / "fresh"
        execute_fixture_experiment(config, fresh)
        for relative in (
            "aggregate_metrics.json",
            "paired_results.jsonl",
            "report.md",
        ):
            assert (fresh / relative).read_bytes() == (reference / relative).read_bytes(), relative
    total = count_tests()
    assert total >= 30, total
    print(json.dumps({
        "tests_expected_minimum": 30,
        "tests_discovered": total,
        "reference_manifest_verified": True,
        "general_verified": 2,
        "specialist_verified": 6,
        "false_completion_reduction": 3,
        "additional_logical_model_calls": 36,
        "evidence_status": "deterministic_fixture",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
