from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def load_script_module():
    spec = importlib.util.spec_from_file_location("stage7_private_pilot_script_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load private pilot script for provider-free boundary test.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def args(self, policy: Path, output: Path, digest: str) -> argparse.Namespace:
        return argparse.Namespace(
            config=CONFIG,
            catalog=CATALOG,
            policy=policy,
            output=output,
            reviewed_policy_digest=digest,
            approve_external_execution=True,
            operator_confirmation=APPROVAL,
        )

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
            environment = self.base_environment()
            secret = "sk-stage7-privacy-boundary-test-secret"
            environment["OPENAI_API_KEY"] = secret
            result = subprocess.run(
                self.command(policy_path, output, policy.digest),
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("privacy", result.stderr.lower())
            self.assertNotIn("openai_api_key", result.stderr.lower())
            self.assertNotIn(secret, result.stdout + result.stderr)
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

    def test_prepared_output_validation_runs_before_key_lookup_after_closed_gate(self) -> None:
        module = load_script_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy_path, policy = self.enabled_policy(root)
            output = root / "not-created-yet"
            environment = self.base_environment()
            with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(
                module,
                "verify_stage7_privacy_gate",
                return_value={
                    "status": "verified",
                    "issue_number": 14,
                    "incident_status": "closed",
                    "last_verified_date": "2026-08-10",
                    "execution_permitted": True,
                    "rationale": "test-only injected closure state",
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "already exist") as raised:
                    module._run(self.args(policy_path, output, policy.digest))
            self.assertNotIn("openai_api_key", str(raised.exception).lower())
            self.assertFalse(output.exists())

    def test_valid_prepared_output_reaches_key_gate_only_after_path_check(self) -> None:
        module = load_script_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy_path, policy = self.enabled_policy(root)
            output = root / "pilot"
            output.mkdir(mode=0o700)
            if os.name != "nt":
                output.chmod(0o700)
            environment = self.base_environment()
            with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(
                module,
                "verify_stage7_privacy_gate",
                return_value={
                    "status": "verified",
                    "issue_number": 14,
                    "incident_status": "closed",
                    "last_verified_date": "2026-08-10",
                    "execution_permitted": True,
                    "rationale": "test-only injected closure state",
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                    module._run(self.args(policy_path, output, policy.digest))
            self.assertTrue(output.is_dir())
            self.assertFalse(any(output.iterdir()))

    def test_prepared_output_rejects_dirty_and_overbroad_directory(self) -> None:
        module = load_script_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dirty = root / "dirty"
            dirty.mkdir(mode=0o700)
            (dirty / "existing.txt").write_text("evidence", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "empty"):
                module._verify_prepared_private_output(dirty)

            if os.name != "nt":
                broad = root / "broad"
                broad.mkdir(mode=0o755)
                broad.chmod(0o755)
                with self.assertRaisesRegex(RuntimeError, "0700"):
                    module._verify_prepared_private_output(broad)


if __name__ == "__main__":
    unittest.main()
