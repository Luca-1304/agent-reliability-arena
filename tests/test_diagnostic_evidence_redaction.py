from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.ci import reliability_gate
from scripts.ci.redact_diagnostic_paths import DiagnosticRedactionError, redact_metadata_tree


class DiagnosticEvidenceRedactionTests(unittest.TestCase):
    def test_command_evidence_is_redacted_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            diagnostics = root / "diagnostics"
            pass_dir = diagnostics / "passes" / "01"
            workspace.mkdir(parents=True)
            pass_dir.mkdir(parents=True)
            environment = reliability_gate.build_pass_environment(
                {"PATH": os.environ.get("PATH", "")},
                pass_number=1,
                pass_root=root / "work" / "pass-01",
            )
            context = reliability_gate.CommandContext(
                workspace=workspace,
                diagnostics_dir=diagnostics,
                pass_dir=pass_dir,
                environment=environment,
                events_path=diagnostics / "events.jsonl",
                python_label="test",
                pass_number=1,
            )
            result = reliability_gate.run_command(
                reliability_gate.CommandSpec(
                    name="workspace-output",
                    phase="privacy-contract",
                    category="TEST",
                    argv=[
                        sys.executable,
                        "-c",
                        f"print({str(workspace)!r})",
                    ],
                ),
                context,
            )
            pass_json = pass_dir / "pass.json"
            pass_json.write_text(
                json.dumps(
                    {
                        "commands": [result.to_dict(context.diagnostics_dir)],
                        "workspace_hint": str(workspace),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            workspace_text = str(workspace)
            self.assertIn(workspace_text, result.log_path.read_text(encoding="utf-8"))
            self.assertIn(workspace_text, context.events_path.read_text(encoding="utf-8"))
            self.assertIn(workspace_text, pass_json.read_text(encoding="utf-8"))

            report = redact_metadata_tree(diagnostics, workspace=workspace)

            self.assertGreaterEqual(report.changed_files, 3)
            for path in (result.log_path, context.events_path, pass_json):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(workspace_text, text)
                self.assertIn("<workspace>", text)

    def test_redactor_does_not_mutate_hashed_output_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            diagnostics = root / "diagnostics"
            output = diagnostics / "passes" / "01" / "outputs" / "result.json"
            output.parent.mkdir(parents=True)
            output.write_text(json.dumps({"path": str(workspace)}) + "\n", encoding="utf-8")

            report = redact_metadata_tree(diagnostics, workspace=workspace)

            self.assertEqual(report.changed_files, 0)
            self.assertIn(str(workspace), output.read_text(encoding="utf-8"))

    def test_redactor_fails_closed_on_symlinked_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            diagnostics = root / "diagnostics"
            diagnostics.mkdir()
            target = root / "outside.log"
            target.write_text("safe\n", encoding="utf-8")
            try:
                (diagnostics / "bootstrap-tools.log").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this platform")

            with self.assertRaisesRegex(DiagnosticRedactionError, "symbolic links"):
                redact_metadata_tree(diagnostics, workspace=root / "workspace")


if __name__ == "__main__":
    unittest.main()
