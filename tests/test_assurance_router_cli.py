from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _cli():
    try:
        return importlib.import_module("agent_reliability_arena.cli_assurance")
    except ModuleNotFoundError as exc:
        raise AssertionError("assurance router CLI is intentionally missing") from exc


def _invoke(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = _cli().main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class AssuranceRouterCliTests(unittest.TestCase):
    def test_json_path_mode_emits_valid_advisory_report(self) -> None:
        code, stdout, stderr = _invoke(["--path", "src/a.py", "--json"])
        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["schema_version"], "assurance-router-v1")
        self.assertEqual(payload["changed_paths"], ["src/a.py"])
        self.assertIs(payload["authoritative"], False)
        self.assertEqual(stderr, "")

    def test_paths_file_mode_reads_one_path_per_non_empty_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path_file = Path(directory) / "paths.txt"
            path_file.write_text("README.md\n\nsrc/a.py\n", encoding="utf-8")
            code, stdout, stderr = _invoke(["--paths-file", str(path_file), "--json"])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            json.loads(stdout)["changed_paths"],
            ["README.md", "src/a.py"],
        )

    def test_mixed_input_modes_are_rejected_without_success_report(self) -> None:
        code, stdout, stderr = _invoke(
            ["--path", "README.md", "--paths-file", "paths.txt", "--json"]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("input mode", stderr.casefold())

    def test_base_without_head_is_rejected(self) -> None:
        code, stdout, stderr = _invoke(["--base", "HEAD~1", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("base", stderr.casefold())
        self.assertIn("head", stderr.casefold())

    def test_unreadable_paths_file_is_rejected(self) -> None:
        code, stdout, stderr = _invoke(
            ["--paths-file", "definitely-missing-paths-file.txt", "--json"]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("paths file", stderr.casefold())

    def test_malformed_policy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.json"
            policy.write_text('{"trigger_surfaces":"src/**"}\n', encoding="utf-8")
            code, stdout, stderr = _invoke(
                ["--path", "src/a.py", "--policy", str(policy), "--json"]
            )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("trigger_surfaces", stderr)

    def test_git_mode_reads_changed_paths_from_real_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Assurance Test"], cwd=repo, check=True)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            (repo / "src").mkdir()
            (repo / "src" / "new.py").write_text("value = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "src/new.py"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "head"], cwd=repo, check=True)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            previous = Path.cwd()
            try:
                os.chdir(repo)
                code, stdout, stderr = _invoke(["--base", base, "--head", head, "--json"])
            finally:
                os.chdir(previous)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["changed_paths"], ["src/new.py"])

    def test_git_diff_failure_returns_two_without_success_report(self) -> None:
        code, stdout, stderr = _invoke(
            ["--base", "definitely-missing-ref", "--head", "HEAD", "--json"]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("git diff", stderr.casefold())

    def test_missing_git_executable_returns_two(self) -> None:
        previous_path = os.environ.get("PATH")
        try:
            os.environ["PATH"] = ""
            code, stdout, stderr = _invoke(["--base", "A", "--head", "B", "--json"])
        finally:
            if previous_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = previous_path
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("git", stderr.casefold())
        self.assertIn("unavailable", stderr.casefold())

    def test_human_mode_names_attention_and_evidence_without_claiming_authority(self) -> None:
        code, stdout, stderr = _invoke(["--path", ".github/workflows/pages.yml"])
        self.assertEqual(code, 0, stderr)
        folded = stdout.casefold()
        self.assertIn("attention required", folded)
        self.assertIn("evidence", folded)
        self.assertIn("non-authoritative", folded)
        self.assertNotIn("safe to merge", folded)


if __name__ == "__main__":
    unittest.main()
