from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.artifacts import verify_manifest, write_experiment_artifacts
from agent_reliability_arena.orchestration.general import GeneralOrchestrator
from agent_reliability_arena.orchestration.specialist import SpecialistOrchestrator
from tests.helpers import config


def runs(root: Path):
    cfg = config()
    items = []
    for condition, orchestrator in (
        ("general", GeneralOrchestrator()),
        ("specialist", SpecialistOrchestrator()),
    ):
        for scenario in cfg.scenarios:
            items.append(orchestrator.run(cfg, scenario, root / condition / scenario))
    return cfg, items


class ArtifactTests(unittest.TestCase):
    def test_artifact_layout_manifest_and_separation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cfg, items = runs(base / "sandbox")
            output = base / "artifacts"
            summary = write_experiment_artifacts(cfg, items, output)
            self.assertTrue(summary["manifest_verified"])
            self.assertTrue(verify_manifest(output))
            self.assertTrue((output / "runs" / "general" / "false_success.json").exists())
            self.assertTrue((output / "runs" / "specialist" / "false_success.json").exists())
            self.assertTrue((output / "paired_results.jsonl").exists())
            self.assertTrue((output / "aggregate_metrics.json").exists())
            self.assertTrue((output / "report.md").exists())
            general = json.loads((output / "runs" / "general" / "false_success.json").read_text())
            specialist = json.loads((output / "runs" / "specialist" / "false_success.json").read_text())
            self.assertIsNone(general["strategy"])
            self.assertIsNotNone(specialist["strategy"])
            self.assertEqual(general["attempts"][0]["evidence"]["trust_basis"], "independent_local_state")

    def test_writes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cfg, items = runs(base / "sandbox")
            one = base / "one"
            two = base / "two"
            write_experiment_artifacts(cfg, items, one)
            write_experiment_artifacts(cfg, items, two)
            one_files = sorted(path.relative_to(one) for path in one.rglob("*") if path.is_file())
            two_files = sorted(path.relative_to(two) for path in two.rglob("*") if path.is_file())
            self.assertEqual(one_files, two_files)
            for relative in one_files:
                self.assertEqual((one / relative).read_bytes(), (two / relative).read_bytes(), relative)

    def test_non_empty_output_tampering_and_unlisted_files_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cfg, items = runs(base / "sandbox")
            output = base / "artifacts"
            output.mkdir()
            (output / "keep.txt").write_text("keep")
            with self.assertRaisesRegex(FileExistsError, "empty"):
                write_experiment_artifacts(cfg, items, output)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cfg, items = runs(base / "sandbox")
            output = base / "artifacts"
            write_experiment_artifacts(cfg, items, output)
            (output / "aggregate_metrics.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "digest"):
                verify_manifest(output)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cfg, items = runs(base / "sandbox")
            output = base / "artifacts"
            write_experiment_artifacts(cfg, items, output)
            (output / "unlisted.txt").write_text("x")
            with self.assertRaisesRegex(ValueError, "unlisted"):
                verify_manifest(output)


if __name__ == "__main__":
    unittest.main()
