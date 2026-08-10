from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.pilot_policy import PilotPolicy


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "stage7_candidate" / "experiment.json"
CATALOG = ROOT / "examples" / "live_prompt_catalog.json"
DISABLED_POLICY = ROOT / "examples" / "stage7_candidate" / "policy.disabled.json"
SCRIPT = ROOT / "scripts" / "run_private_pilot.py"
APPROVAL = "I_APPROVE_ONE_PRIVATE_PILOT"


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class Stage7PrivateScriptBoundaryTests(unittest.TestCase):
    def command(self, policy: Path, output: Path, digest: str) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--config",
            str(CONFIG),
            "--catalog",
            str(CATALOG),
            "--policy",
            str(policy),
            "--output",
            str(output),
            "--reviewed-policy-digest",
            digest,
            "--approve-external-execution",
            "--operator-confirmation",
            APPROVAL,
        ]

    def enabled_policy(self, directory: Path) -> tuple[Path, PilotPolicy]:
        raw = read_json(DISABLED_POLICY)
        raw["external_execution_enabled"] = True
        path = directory / "enabled-policy.json"
        write_json(path, raw)
        return path, PilotPolicy.from_dict(raw)

    def base_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment.pop("OPENAI_API_KEY", None)
        environment.pop("GITHUB_ACTIONS", None)
        return environment

    def test_committed_open_privacy_gate_blocks_before_key_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy_path, policy = self.enabled_policy(root)
            output = root / "pilot"
            result = subprocess.run(
                self.command(policy_path, output, policy.digest),
                cwd=ROOT,
                env=self.base_environment(),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("privacy", result.stderr.lower())
            self.assertNotIn("openai_api_key", result.stderr.lower())
            self.assertFalse(output.exists())

    def test_altered_enabled_policy_is_rejected_before_key_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = read_json(DISABLED_POLICY)
            raw["external_execution_enabled"] = True
            raw["max_cost_minor_units"] = 101
            policy = PilotPolicy.from_dict(raw)
            policy_path = root / "altered-policy.json"
            write_json(policy_path, raw)
            output = root / "pilot"
            result = subprocess.run(
                self.command(policy_path, output, policy.digest),
                cwd=ROOT,
                env=self.base_environment(),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            # The committed privacy hold may stop first today. Once that gate is closed,
            # the candidate-binding validator remains the next execution boundary.
            self.assertTrue(
                "privacy" in result.stderr.lower() or "candidate" in result.stderr.lower(),
                result.stderr,
            )
            self.assertNotIn("openai_api_key", result.stderr.lower())
            self.assertFalse(output.exists())

    def test_duplicate_key_private_policy_is_never_accepted_as_execution_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = read_json(DISABLED_POLICY)
            raw["external_execution_enabled"] = True
            clean = PilotPolicy.from_dict(raw)
            text = json.dumps(raw, sort_keys=True)
            duplicate = text[:-1] + ',"max_calls":9}'
            policy_path = root / "duplicate-policy.json"
            policy_path.write_text(duplicate + "\n", encoding="utf-8")
            output = root / "pilot"
            result = subprocess.run(
                self.command(policy_path, output, clean.digest),
                cwd=ROOT,
                env=self.base_environment(),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                "privacy" in result.stderr.lower() or "duplicate" in result.stderr.lower(),
                result.stderr,
            )
            self.assertFalse(output.exists())

    def test_symlinked_private_policy_is_never_accepted_as_execution_input(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real, policy = self.enabled_policy(root)
            link = root / "enabled-link.json"
            try:
                link.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            output = root / "pilot"
            result = subprocess.run(
                self.command(link, output, policy.digest),
                cwd=ROOT,
                env=self.base_environment(),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                "privacy" in result.stderr.lower() or "non-symlink" in result.stderr.lower(),
                result.stderr,
            )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
