from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "ci" / "reliability_gate.py"


def load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reliability_gate_parity", GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReliabilityGateParityTests(unittest.TestCase):
    def test_path_bearing_command_outputs_normalize_only_output_field(self) -> None:
        gate = load_gate()
        with tempfile.TemporaryDirectory() as directory:
            outputs = Path(directory)
            (outputs / "editable-run.json").write_text(
                json.dumps(
                    {
                        "evidence_status": "deterministic_fixture",
                        "manifest_verified": True,
                        "output": "/tmp/editable-artifacts",
                        "paired_runs": 8,
                        "total_runs": 16,
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "wheel-run.json").write_text(
                json.dumps(
                    {
                        "evidence_status": "deterministic_fixture",
                        "manifest_verified": True,
                        "output": "/different/wheel-artifacts",
                        "paired_runs": 8,
                        "total_runs": 16,
                    }
                ),
                encoding="utf-8",
            )
            editable = gate._prefixed_manifest(outputs, "editable")
            wheel = gate._prefixed_manifest(outputs, "wheel")
            gate.compare_manifest(editable, wheel, label="semantic command parity")

    def test_non_path_semantic_drift_still_fails(self) -> None:
        gate = load_gate()
        with tempfile.TemporaryDirectory() as directory:
            outputs = Path(directory)
            (outputs / "editable-export-web-command.json").write_text(
                json.dumps(
                    {
                        "evidence_status": "deterministic_fixture",
                        "output": "/tmp/editable-public.json",
                        "scenarios": 8,
                    }
                ),
                encoding="utf-8",
            )
            (outputs / "wheel-export-web-command.json").write_text(
                json.dumps(
                    {
                        "evidence_status": "deterministic_fixture",
                        "output": "/tmp/wheel-public.json",
                        "scenarios": 9,
                    }
                ),
                encoding="utf-8",
            )
            editable = gate._prefixed_manifest(outputs, "editable")
            wheel = gate._prefixed_manifest(outputs, "wheel")
            with self.assertRaises(gate.GateFailure):
                gate.compare_manifest(editable, wheel, label="semantic command parity")


if __name__ == "__main__":
    unittest.main()
