from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_reliability_arena.assurance_router import classify_paths
from agent_reliability_arena.cli_assurance import _git_paths, main


class AssuranceRouterPathFidelityTests(unittest.TestCase):
    def test_leading_whitespace_path_is_not_reclassified_as_runtime(self) -> None:
        report = classify_paths([" src/a.py"], ["src/**"])
        self.assertEqual(report.changed_paths, (" src/a.py",))
        self.assertEqual(report.touched_surfaces, ())
        self.assertEqual(report.unknown_paths, (" src/a.py",))
        self.assertEqual(
            report.outside_reliability_trigger_surface,
            (" src/a.py",),
        )
        self.assertTrue(report.attention_required)

    def test_paths_file_preserves_leading_whitespace_path_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / "policy.json"
            paths = root / "paths.txt"
            policy.write_text(
                json.dumps({"trigger_surfaces": ["src/**"]}) + "\n",
                encoding="utf-8",
            )
            paths.write_text(" src/a.py\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "--paths-file",
                        str(paths),
                        "--policy",
                        str(policy),
                        "--json",
                    ]
                )
        self.assertEqual(code, 0, stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["changed_paths"], [" src/a.py"])
        self.assertEqual(payload["unknown_paths"], [" src/a.py"])
        self.assertTrue(payload["attention_required"])

    def test_git_adapter_preserves_leading_whitespace_path_identity(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout=" src/a.py\n",
            stderr="",
        )
        with patch(
            "agent_reliability_arena.cli_assurance.shutil.which",
            return_value="/usr/bin/git",
        ), patch(
            "agent_reliability_arena.cli_assurance.subprocess.run",
            return_value=completed,
        ):
            paths = _git_paths("BASE", "HEAD")
        self.assertEqual(paths, (" src/a.py",))


if __name__ == "__main__":
    unittest.main()
