from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_policy import PolicyError, load_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "reliability-policy.json"


class ReliabilityPolicyTests(unittest.TestCase):
    def test_repository_policy_has_required_contract(self) -> None:
        policy = load_policy(POLICY)
        self.assertEqual(policy.schema_version, "reliability-policy-v1")
        self.assertEqual(policy.supported_python, ("3.10", "3.11", "3.12", "3.13"))
        self.assertEqual(policy.deep_python, ("3.10", "3.13"))
        self.assertGreaterEqual(policy.stress_passes, 15)
        self.assertEqual(policy.max_permissions, {"contents": "read"})
        self.assertFalse(policy.persist_credentials)
        self.assertEqual(policy.determinism_classes, ("byte", "semantic", "bounded"))
        self.assertEqual(policy.cache_modes, ("warm", "cold"))
        self.assertIn(".github/workflows/**", policy.trigger_surfaces)
        self.assertIn("reliability-policy.json", policy.trigger_surfaces)

    def test_unknown_top_level_key_fails_closed(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["surprise"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "unknown policy keys"):
                load_policy(path)

    def test_weakened_stress_count_is_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["deep_gate"]["minimum_passes"] = 14
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "minimum_passes"):
                load_policy(path)

    def test_write_permission_is_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["permissions"]["maximum"] = {"contents": "write"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "permissions"):
                load_policy(path)

    def test_persisted_checkout_credentials_are_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["permissions"]["persist_credentials"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "persist_credentials"):
                load_policy(path)

    def test_duplicate_hash_seed_is_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["deep_gate"]["hash_seeds"][-1] = 13
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "hash_seeds"):
                load_policy(path)

    def test_retention_outside_policy_bound_is_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["diagnostics"]["retention_days"] = 31
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "retention_days"):
                load_policy(path)


if __name__ == "__main__":
    unittest.main()
