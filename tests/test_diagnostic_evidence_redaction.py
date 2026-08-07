from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.ci import reliability_gate


class DiagnosticEvidenceRedactionTests(unittest.TestCase):
    def test_command_evidence_never_persists_absolute_workspace_path(self) -> None:
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

            workspace_text = str(workspace)
            log_text = result.log_path.read_text(encoding="utf-8")
            events_text = context.events_path.read_text(encoding="utf-8")
            serialized_result = json.dumps(
                result.to_dict(context.diagnostics_dir, workspace=context.workspace),
                sort_keys=True,
            )
            self.assertNotIn(workspace_text, log_text)
            self.assertNotIn(workspace_text, events_text)
            self.assertNotIn(workspace_text, serialized_result)
            self.assertIn("<workspace>", log_text)
            self.assertIn("<workspace>", events_text)
            self.assertIn("<workspace>", serialized_result)


if __name__ == "__main__":
    unittest.main()
