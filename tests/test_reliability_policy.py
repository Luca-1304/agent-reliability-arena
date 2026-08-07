from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_policy import PolicyError, load_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "reliability-policy.json"
EXPECTED_WORKFLOW_ROLES = {
    "fast": ("reliability-fast.yml",),
    "deep": ("fifteen-pass-verification.yml",),
    "specialist": ("reliability-specialists.yml",),
    "scheduled": ("reliability-ecosystem.yml",),
}


class ReliabilityPolicyTests(unittest.TestCase):
    def test_repository_policy_has_required_contract(self) -> None:
        policy = load_policy(POLICY)
        self.assertEqual(policy.schema_version, "reliability-policy-v1")
        self.assertEqual(policy.supported_python, ("3.10", "3.11", "3.12", "3.13"))
        self.assertEqual(policy.deep_python, ("3.10", "3.13"))
        self.assertGreaterEqual(policy.stress_passes, 15)
        self.assertEqual(policy.max_permissions, {"contents": "read"})
        self.assertFalse(policy.persist_credentials)
        self.assertEqual(policy.workflow_roles, EXPECTED_WORKFLOW_ROLES)
        self.assertEqual(policy.determinism_classes, ("byte", "semantic", "bounded"))
        self.assertEqual(policy.cache_modes, ("warm", "cold"))
        self.assertIn(".github/workflows/**", policy.trigger_surfaces)
        self.assertIn("reliability-policy.json", policy.trigger_surfaces)
        self.assertEqual(policy.performance_mode, "observational")
        self.assertEqual(policy.performance_min_samples, 10)
        scanner = policy.raw["diagnostics"]["scanner"]
        self.assertTrue(scanner["forbid_absolute_workspace_paths"])
        self.assertEqual(scanner["max_text_file_bytes"], 5_000_000)
        self.assertTrue({"localhost", "127.0.0.1", "0.0.0.0"}.issubset(scanner["forbid_private_url_hosts"]))
        self.assertTrue({"api_key", "token", "password", "secret"}.issubset(scanner["secret_name_fragments"]))

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

    def test_workflow_role_reassignment_is_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["workflow_roles"]["fast"] = ["fifteen-pass-verification.yml"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "workflow_roles.fast"):
                load_policy(path)

    def test_unknown_workflow_role_is_rejected(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["workflow_roles"]["shadow"] = ["shadow.yml"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "unknown workflow_roles keys"):
                load_policy(path)

    def test_performance_mode_cannot_be_promoted_to_hard_threshold(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["performance"]["mode"] = "blocking"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "performance.mode"):
                load_policy(path)

    def test_performance_sample_floor_cannot_be_reduced_below_ten(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["performance"]["minimum_samples_before_threshold"] = 9
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "minimum_samples_before_threshold"):
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

    def test_diagnostic_workspace_scanning_cannot_be_disabled(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["diagnostics"]["scanner"]["forbid_absolute_workspace_paths"] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "forbid_absolute_workspace_paths"):
                load_policy(path)

    def test_required_secret_fragment_cannot_be_removed(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["diagnostics"]["scanner"]["secret_name_fragments"].remove("token")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "secret_name_fragments"):
                load_policy(path)

    def test_scanner_size_ceiling_cannot_be_raised(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["diagnostics"]["scanner"]["max_text_file_bytes"] = 5_000_001
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "max_text_file_bytes"):
                load_policy(path)


if __name__ == "__main__":
    unittest.main()
