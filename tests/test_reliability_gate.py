from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "ci" / "reliability_gate.py"


def load_gate() -> ModuleType | None:
    if not GATE_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("reliability_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReliabilityGatePrimitiveTests(unittest.TestCase):
    def require_gate(self) -> ModuleType:
        gate = load_gate()
        self.assertIsNotNone(gate, f"missing reliability gate runner: {GATE_PATH}")
        return gate  # type: ignore[return-value]

    def make_context(self, gate: ModuleType, root: Path):
        workspace = root / "workspace"
        diagnostics = root / "diagnostics"
        pass_dir = diagnostics / "passes" / "01"
        workspace.mkdir(parents=True)
        pass_dir.mkdir(parents=True)
        environment = gate.build_pass_environment(
            {"PATH": os.environ.get("PATH", "")},
            pass_number=1,
            pass_root=root / "work" / "pass-01",
        )
        return gate.CommandContext(
            workspace=workspace,
            diagnostics_dir=diagnostics,
            pass_dir=pass_dir,
            environment=environment,
            events_path=diagnostics / "events.jsonl",
            python_label="test",
            pass_number=1,
        )

    def test_canonical_json_digest_ignores_formatting_but_detects_semantic_drift(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compact = root / "compact.json"
            formatted = root / "formatted.json"
            changed = root / "changed.json"
            compact.write_text('{"b":[2,1],"a":{"x":true}}', encoding="utf-8")
            formatted.write_text(
                json.dumps({"a": {"x": True}, "b": [2, 1]}, indent=4),
                encoding="utf-8",
            )
            changed.write_text(
                json.dumps({"a": {"x": False}, "b": [2, 1]}),
                encoding="utf-8",
            )

            first = gate.canonical_digest(compact)
            second = gate.canonical_digest(formatted)
            drifted = gate.canonical_digest(changed)

            self.assertEqual(first["kind"], "json")
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertNotEqual(first["sha256"], drifted["sha256"])

    def test_tree_manifest_is_path_sorted_and_detects_file_changes(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / "nested" / "z.json").write_text('{"value":1}', encoding="utf-8")
            (root / "a.txt").write_text("stable\n", encoding="utf-8")

            first = gate.tree_manifest(root)
            self.assertEqual(list(first), ["a.txt", "nested/z.json"])

            (root / "nested" / "z.json").write_text('{"value":2}', encoding="utf-8")
            second = gate.tree_manifest(root)
            self.assertNotEqual(first["nested/z.json"]["sha256"], second["nested/z.json"]["sha256"])

    def test_tree_manifest_rejects_symbolic_links(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.txt"
            link = root / "link.txt"
            target.write_text("evidence\n", encoding="utf-8")
            try:
                link.symlink_to(target)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            with self.assertRaisesRegex(gate.GateFailure, "symbolic links"):
                gate.tree_manifest(root)

    def test_manifest_comparison_reports_missing_unexpected_and_changed_paths(self) -> None:
        gate = self.require_gate()
        expected = {
            "same.json": {"kind": "json", "sha256": "a", "size": 1},
            "changed.json": {"kind": "json", "sha256": "b", "size": 1},
            "missing.json": {"kind": "json", "sha256": "c", "size": 1},
        }
        actual = {
            "same.json": {"kind": "json", "sha256": "a", "size": 1},
            "changed.json": {"kind": "json", "sha256": "d", "size": 1},
            "unexpected.json": {"kind": "json", "sha256": "e", "size": 1},
        }

        with self.assertRaises(gate.GateFailure) as context:
            gate.compare_manifest(expected, actual, label="fixture parity")

        message = str(context.exception)
        self.assertIn("fixture parity", message)
        self.assertIn("missing.json", message)
        self.assertIn("unexpected.json", message)
        self.assertIn("changed.json", message)

    def test_pass_environment_is_deterministic_isolated_and_secret_free(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            pass_root = Path(directory) / "pass-04"
            environment = gate.build_pass_environment(
                {
                    "PATH": os.environ.get("PATH", ""),
                    "OPENAI_API_KEY": "must-not-survive",
                    "GITHUB_TOKEN": "must-not-survive",
                    "SAFE_VALUE": "preserved",
                },
                pass_number=4,
                pass_root=pass_root,
            )

            self.assertEqual(environment["PYTHONHASHSEED"], "3")
            self.assertEqual(environment["TZ"], "UTC")
            self.assertEqual(environment["LC_ALL"], "C.UTF-8")
            self.assertEqual(environment["LANG"], "C.UTF-8")
            self.assertEqual(environment["SOURCE_DATE_EPOCH"], "315532800")
            self.assertEqual(environment["PYTHONUNBUFFERED"], "1")
            self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
            self.assertEqual(environment["PIP_DISABLE_PIP_VERSION_CHECK"], "1")
            self.assertEqual(environment["SAFE_VALUE"], "preserved")
            self.assertNotIn("OPENAI_API_KEY", environment)
            self.assertNotIn("GITHUB_TOKEN", environment)
            self.assertEqual(Path(environment["HOME"]), pass_root / "home")
            self.assertEqual(Path(environment["TMPDIR"]), pass_root / "tmp")
            self.assertEqual(Path(environment["XDG_CACHE_HOME"]), pass_root / "cache")
            self.assertEqual(Path(environment["PIP_CACHE_DIR"]), pass_root / "cache" / "pip")

    def test_failure_record_is_complete_and_json_serializable(self) -> None:
        gate = self.require_gate()
        record = gate.FailureRecord(
            category="wheel-cli",
            phase="wheel-cli",
            command_name="wheel-replay",
            argv=["arena-replay", "--input", "fixture"],
            pass_number=7,
            hash_seed=6,
            exit_code=2,
            duration_seconds=1.25,
            log_path="passes/07/commands/21-wheel-replay.log",
            message="command failed",
        )

        payload = record.to_dict()
        json.dumps(payload, sort_keys=True)
        self.assertEqual(
            set(payload),
            {
                "argv",
                "category",
                "command_name",
                "duration_seconds",
                "exit_code",
                "hash_seed",
                "log_path",
                "message",
                "pass_number",
                "phase",
            },
        )
        self.assertEqual(payload["category"], "wheel-cli")
        self.assertEqual(payload["pass_number"], 7)
        self.assertEqual(payload["hash_seed"], 6)

    def test_atomic_json_writer_sorts_keys_and_terminates_with_newline(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "evidence.json"
            gate.write_json(path, {"z": 1, "a": 2})
            self.assertEqual(path.read_text(encoding="utf-8"), '{\n  "a": 2,\n  "z": 1\n}\n')

    def test_command_runner_records_events_log_and_validated_json(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = self.make_context(gate, root)
            output = context.pass_dir / "outputs" / "command.json"
            result = gate.run_command(
                gate.CommandSpec(
                    name="json-success",
                    phase="unit-contract",
                    category="editable-cli",
                    argv=[
                        sys.executable,
                        "-c",
                        "import json; print(json.dumps({'verified': True}, sort_keys=True))",
                    ],
                    stdout_json_path=output,
                ),
                context,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"verified": True})
            self.assertIn("json-success", result.log_path.read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in context.events_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["event"] for event in events], ["command-started", "command-finished"])
            self.assertEqual(events[-1]["status"], "passed")

    def test_command_runner_preserves_exact_nonzero_failure_evidence(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            context = self.make_context(gate, Path(directory))
            with self.assertRaises(gate.GateFailure) as raised:
                gate.run_command(
                    gate.CommandSpec(
                        name="known-failure",
                        phase="wheel-test-contract",
                        category="wheel-tests",
                        argv=[sys.executable, "-c", "import sys; sys.stderr.write('broken\\n'); sys.exit(7)"],
                    ),
                    context,
                )

            record = raised.exception.record
            self.assertIsNotNone(record)
            self.assertEqual(record.exit_code, 7)
            self.assertEqual(record.category, "wheel-tests")
            self.assertEqual(record.pass_number, 1)
            self.assertEqual(record.hash_seed, 0)
            self.assertIn("broken", (context.diagnostics_dir / record.log_path).read_text(encoding="utf-8"))

    def test_command_runner_rejects_malformed_json_after_zero_exit(self) -> None:
        gate = self.require_gate()
        with tempfile.TemporaryDirectory() as directory:
            context = self.make_context(gate, Path(directory))
            with self.assertRaisesRegex(gate.GateFailure, "malformed JSON") as raised:
                gate.run_command(
                    gate.CommandSpec(
                        name="invalid-json",
                        phase="editable-cli-contract",
                        category="editable-cli",
                        argv=[sys.executable, "-c", "print('not-json')"],
                        stdout_json_path=context.pass_dir / "outputs" / "invalid.json",
                    ),
                    context,
                )
            self.assertEqual(raised.exception.record.exit_code, 0)
            self.assertEqual(raised.exception.record.category, "editable-cli")


if __name__ == "__main__":
    unittest.main()
