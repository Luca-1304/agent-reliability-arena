from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ShowcaseCommandTests(unittest.TestCase):
    def _environment(self) -> tuple[dict[str, str], str]:
        secret = "test-secret-that-must-not-appear"
        environment = dict(os.environ)
        environment["OPENAI_API_KEY"] = secret
        return environment, secret

    def test_source_verifier_prints_provider_free_summary(self) -> None:
        environment, secret = self._environment()
        result = subprocess.run(
            [sys.executable, "scripts/verify_showcase_release.py"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["files_verified"], 7)
        self.assertEqual(payload["showcase_version"], "0.2.0rc1-public-showcase-1")
        self.assertEqual(payload["evidence_class"], "deterministic_and_provider_free_showcase")
        self.assertFalse(payload["provider_called"])
        self.assertFalse(payload["comparative_claim_permitted"])
        self.assertNotIn(secret, result.stdout)
        self.assertNotIn(secret, result.stderr)

    def test_installed_command_verifies_explicit_repository_root(self) -> None:
        environment, secret = self._environment()
        result = subprocess.run(
            ["arena-verify-showcase", "--root", str(ROOT)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["general_verified"], 2)
        self.assertEqual(payload["specialist_verified"], 6)
        self.assertEqual(payload["false_completion_reduction"], 3)
        self.assertEqual(payload["additional_logical_model_calls"], 36)
        self.assertFalse(payload["provider_called"])
        self.assertFalse(payload["comparative_claim_permitted"])
        self.assertNotIn(secret, result.stdout)
        self.assertNotIn(secret, result.stderr)

    def test_installed_command_refuses_missing_bundle(self) -> None:
        result = subprocess.run(
            ["arena-verify-showcase", "--root", str(ROOT / "missing-showcase-root")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("real directory", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
