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
CONFIG = ROOT / "examples" / "fixture_experiment.json"
CATALOG = ROOT / "examples" / "live_prompt_catalog.json"
DISABLED_POLICY = ROOT / "examples" / "pilot_policy.disabled.json"
SCRIPT = ROOT / "scripts" / "run_private_pilot.py"
APPROVAL = "I_APPROVE_ONE_PRIVATE_PILOT"


class PrivatePilotScriptTests(unittest.TestCase):
    def command(self, policy: Path, output: Path, digest: str, *extra: str) -> list[str]:
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
            *extra,
        ]

    def test_help_requires_no_key(self) -> None:
        environment = dict(os.environ)
        environment.pop("OPENAI_API_KEY", None)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local private paired pilot", result.stdout.lower())
        self.assertNotIn("api-key", result.stdout.lower())

    def test_missing_operator_approval_stops_before_secret_or_output(self) -> None:
        policy = PilotPolicy.from_dict(json.loads(DISABLED_POLICY.read_text(encoding="utf-8")))
        environment = dict(os.environ)
        secret = "sk-script-test-secret"
        environment["OPENAI_API_KEY"] = secret
        environment.pop("GITHUB_ACTIONS", None)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pilot"
            result = subprocess.run(
                self.command(DISABLED_POLICY, output, policy.digest),
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approval", result.stderr.lower())
            self.assertFalse(output.exists())
            self.assertNotIn(secret, result.stdout + result.stderr)

    def test_github_actions_is_always_refused_even_with_approvals(self) -> None:
        policy = PilotPolicy.from_dict(json.loads(DISABLED_POLICY.read_text(encoding="utf-8")))
        environment = dict(os.environ)
        environment["OPENAI_API_KEY"] = "sk-ci-secret"
        environment["GITHUB_ACTIONS"] = "true"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pilot"
            result = subprocess.run(
                self.command(
                    DISABLED_POLICY,
                    output,
                    policy.digest,
                    "--approve-external-execution",
                    "--operator-confirmation",
                    APPROVAL,
                ),
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("github actions", result.stderr.lower())
            self.assertFalse(output.exists())
            self.assertNotIn(environment["OPENAI_API_KEY"], result.stdout + result.stderr)

    def test_enabled_policy_without_environment_key_stops_before_output(self) -> None:
        raw = json.loads(DISABLED_POLICY.read_text(encoding="utf-8"))
        raw["external_execution_enabled"] = True
        policy = PilotPolicy.from_dict(raw)
        environment = dict(os.environ)
        environment.pop("OPENAI_API_KEY", None)
        environment.pop("GITHUB_ACTIONS", None)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            policy_path = base / "enabled-policy.json"
            policy_path.write_text(json.dumps(raw), encoding="utf-8")
            output = base / "pilot"
            result = subprocess.run(
                self.command(
                    policy_path,
                    output,
                    policy.digest,
                    "--approve-external-execution",
                    "--operator-confirmation",
                    APPROVAL,
                ),
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("openai_api_key", result.stderr.lower())
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
