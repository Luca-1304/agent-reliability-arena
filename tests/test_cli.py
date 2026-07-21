from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "fixture_experiment.json"


class CliTests(unittest.TestCase):
    def test_run_replay_and_export_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output = base / "run"
            run = subprocess.run(
                ["arena-run", "--config", str(CONFIG), "--output", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            summary = json.loads(run.stdout)
            self.assertEqual(summary["total_runs"], 16)
            self.assertEqual(summary["paired_runs"], 8)
            self.assertTrue(summary["manifest_verified"])
            replay = subprocess.run(
                ["arena-replay", "--input", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(replay.returncode, 0, replay.stderr)
            replay_payload = json.loads(replay.stdout)
            self.assertEqual(replay_payload["specialist_verified"], 6)
            public = base / "public.json"
            export = subprocess.run(
                ["arena-export-web", "--input", str(output), "--output", str(public)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(export.returncode, 0, export.stderr)
            export_payload = json.loads(export.stdout)
            self.assertEqual(export_payload["evidence_status"], "deterministic_fixture")
            data = json.loads(public.read_text(encoding="utf-8"))
            self.assertEqual(len(data["scenarios"]), 8)
            self.assertNotIn("raw_provider_response", json.dumps(data))

    def test_run_rejects_non_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            output.mkdir()
            (output / "keep.txt").write_text("keep")
            result = subprocess.run(
                ["arena-run", "--config", str(CONFIG), "--output", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("empty", result.stderr)

    def test_module_cli_matches_installed_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = subprocess.run(
                [sys.executable, "-m", "agent_reliability_arena.cli", "run", "--config", str(CONFIG), "--output", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["total_runs"], 16)


if __name__ == "__main__":
    unittest.main()
