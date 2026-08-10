from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import agent_reliability_arena.stage7_candidate as stage7


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "examples" / "stage7_candidate"
CONFIG = CANDIDATE / "experiment.json"
CATALOG = ROOT / "examples" / "live_prompt_catalog.json"
DISABLED_POLICY = CANDIDATE / "policy.disabled.json"
PRIVACY_GATE = CANDIDATE / "privacy-execution-gate.json"


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


class Stage7ExecutionBoundaryTests(unittest.TestCase):
    def require_callable(self, name: str):
        function = getattr(stage7, name, None)
        self.assertTrue(callable(function), f"stage7_candidate.{name} must exist")
        return function

    def enabled_policy(self, directory: Path) -> Path:
        raw = read_json(DISABLED_POLICY)
        raw["external_execution_enabled"] = True
        path = directory / "enabled-policy.json"
        write_json(path, raw)
        return path

    def test_committed_privacy_gate_is_valid_but_still_blocks_execution(self) -> None:
        verify = self.require_callable("verify_stage7_privacy_gate")
        self.assertTrue(PRIVACY_GATE.is_file())

        result = verify(PRIVACY_GATE)

        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["issue_number"], 14)
        self.assertEqual(result["incident_status"], "open")
        self.assertEqual(result["last_verified_date"], "2026-08-10")
        self.assertFalse(result["execution_permitted"])

    def test_privacy_gate_rejects_inconsistent_status_and_duplicate_keys(self) -> None:
        verify = self.require_callable("verify_stage7_privacy_gate")
        base = {
            "schema_version": "arena-stage7-privacy-execution-gate-v1",
            "issue_number": 14,
            "incident_status": "open",
            "last_verified_date": "2026-08-10",
            "execution_permitted": False,
            "rationale": "Historical provider removal is not independently verified.",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for status, permitted in (("open", True), ("closed", False)):
                with self.subTest(status=status, permitted=permitted):
                    payload = dict(base)
                    payload["incident_status"] = status
                    payload["execution_permitted"] = permitted
                    path = root / f"gate-{status}-{permitted}.json"
                    write_json(path, payload)
                    with self.assertRaises(ValueError):
                        verify(path)

            duplicate = root / "duplicate.json"
            duplicate.write_text(
                '{"schema_version":"arena-stage7-privacy-execution-gate-v1",'
                '"issue_number":14,"issue_number":15,"incident_status":"open",'
                '"last_verified_date":"2026-08-10","execution_permitted":false,'
                '"rationale":"x"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify(duplicate)

    def test_privacy_gate_rejects_symlink(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        verify = self.require_callable("verify_stage7_privacy_gate")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.json"
            write_json(
                real,
                {
                    "schema_version": "arena-stage7-privacy-execution-gate-v1",
                    "issue_number": 14,
                    "incident_status": "open",
                    "last_verified_date": "2026-08-10",
                    "execution_permitted": False,
                    "rationale": "Historical provider removal is not independently verified.",
                },
            )
            link = root / "gate.json"
            try:
                link.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                verify(link)

    def test_exact_enabled_policy_delta_is_verified(self) -> None:
        verify = self.require_callable("verify_stage7_execution_policy")
        with tempfile.TemporaryDirectory() as directory:
            enabled = self.enabled_policy(Path(directory))

            result = verify(CANDIDATE, CONFIG, CATALOG, enabled)

        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["external_execution_enabled"])
        self.assertEqual(result["model_id"], "gpt-5.5-2026-04-23")
        self.assertEqual(result["planned_call_ceiling"], 8)
        self.assertEqual(result["max_reserved_total_tokens"], 16384)
        self.assertEqual(result["reserved_cost_minor_units"], 96)
        self.assertEqual(result["max_cost_minor_units"], 100)
        self.assertEqual(len(result["policy_digest"]), 64)
        self.assertEqual(len(result["preflight_manifest_digest"]), 64)
        self.assertEqual(len(result["candidate_packet_digest"]), 64)

    def test_enabled_policy_rejects_every_material_delta(self) -> None:
        verify = self.require_callable("verify_stage7_execution_policy")
        mutations = (
            ("model_id", "other-model"),
            ("model_version", "other-version"),
            ("prompt_version", "other-prompts"),
            ("scenario_ids", ["success", "false_success"]),
            ("max_calls", 9),
            ("max_requested_output_tokens", 3000),
            ("reserved_total_tokens_per_call", 4096),
            ("max_reserved_total_tokens", 32768),
            ("currency", "GBP"),
            ("reserved_cost_per_call_minor_units", 13),
            ("max_cost_minor_units", 101),
        )
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                raw = read_json(DISABLED_POLICY)
                raw["external_execution_enabled"] = True
                raw[key] = value
                enabled = root / "enabled.json"
                write_json(enabled, raw)
                with self.assertRaisesRegex(ValueError, "candidate"):
                    verify(CANDIDATE, CONFIG, CATALOG, enabled)

    def test_enabled_policy_rejects_config_drift(self) -> None:
        verify = self.require_callable("verify_stage7_execution_policy")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            enabled = self.enabled_policy(root)
            config = read_json(CONFIG)
            config["seed"] = 9999
            drifted = root / "experiment.json"
            write_json(drifted, config)
            with self.assertRaisesRegex(ValueError, "config"):
                verify(CANDIDATE, drifted, CATALOG, enabled)

    def test_enabled_policy_rejects_duplicate_keys_and_symlink(self) -> None:
        verify = self.require_callable("verify_stage7_execution_policy")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = DISABLED_POLICY.read_text(encoding="utf-8")
            duplicate = root / "duplicate.json"
            duplicate.write_text(
                raw.rstrip()[:-1] + ',"external_execution_enabled":true}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify(CANDIDATE, CONFIG, CATALOG, duplicate)

            if hasattr(os, "symlink"):
                enabled = self.enabled_policy(root)
                link = root / "enabled-link.json"
                try:
                    link.symlink_to(enabled)
                except (OSError, NotImplementedError):
                    return
                with self.assertRaisesRegex(ValueError, "non-symlink"):
                    verify(CANDIDATE, CONFIG, CATALOG, link)


if __name__ == "__main__":
    unittest.main()
