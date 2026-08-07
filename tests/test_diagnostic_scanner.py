from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_policy import load_policy
from scripts.ci.scan_diagnostics import scan_text, scan_tree


class DiagnosticScannerTests(unittest.TestCase):
    def test_detects_workspace_path(self) -> None:
        report = scan_text(
            "log",
            "cwd=/home/runner/work/repo/repo/src",
            workspace=Path("/home/runner/work/repo/repo"),
        )
        self.assertTrue(report.findings)
        self.assertEqual(report.findings[0].kind, "workspace-path")

    def test_detects_secret_assignment_without_echoing_value(self) -> None:
        report = scan_text(
            "log",
            "OPENAI_API_KEY=sk-example-not-real",
            workspace=Path("/repo"),
        )
        self.assertEqual(report.findings[0].kind, "secret-like-assignment")
        self.assertNotIn("sk-example", report.findings[0].rendered)
        self.assertIn("OPENAI_API_KEY", report.findings[0].rendered)

    def test_normal_command_argv_is_allowed(self) -> None:
        report = scan_text(
            "log",
            "python -m unittest discover -s tests",
            workspace=Path("/repo"),
        )
        self.assertEqual(report.findings, [])

    def test_detects_private_url_host_without_echoing_query(self) -> None:
        report = scan_text(
            "events.jsonl",
            "callback=http://localhost:8080/run?token=not-real",
            workspace=Path("/repo"),
        )
        self.assertTrue(any(item.kind == "private-url-host" for item in report.findings))
        rendered = "\n".join(item.rendered for item in report.findings)
        self.assertNotIn("not-real", rendered)

    def test_json_secret_key_is_detected_without_value(self) -> None:
        payload = json.dumps({"command": "run", "auth_token": "example-value-not-real"})
        report = scan_text("manifest.json", payload, workspace=Path("/repo"))
        secret_findings = [item for item in report.findings if item.kind == "secret-like-json-key"]
        self.assertEqual(len(secret_findings), 1)
        self.assertIn("auth_token", secret_findings[0].rendered)
        self.assertNotIn("example-value-not-real", secret_findings[0].rendered)

    def test_tree_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            evidence.mkdir()
            target = root / "outside.txt"
            target.write_text("safe", encoding="utf-8")
            try:
                (evidence / "linked.txt").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this platform")
            report = scan_tree(
                evidence,
                workspace=root / "workspace",
                policy=load_policy(Path("reliability-policy.json")),
            )
            self.assertTrue(any(item.kind == "symlink" for item in report.findings))

    def test_binary_file_only_flags_prohibited_workspace_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            evidence = root / "evidence"
            evidence.mkdir()
            binary = b"\x00\x01prefix:" + str(workspace).encode("utf-8") + b"\xff"
            (evidence / "payload.bin").write_bytes(binary)
            report = scan_tree(
                evidence,
                workspace=workspace,
                policy=load_policy(Path("reliability-policy.json")),
            )
            self.assertTrue(any(item.kind == "workspace-path-binary" for item in report.findings))


if __name__ == "__main__":
    unittest.main()
