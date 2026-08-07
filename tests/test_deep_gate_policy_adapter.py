from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci import run_deep_reliability as adapter
from scripts.ci.reliability_policy import load_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "reliability-policy.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"


class DeepGatePolicyAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy(POLICY_PATH)

    def _load_modified_policy(self, mutate) -> object:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        mutate(payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_policy(path)

    def test_current_policy_is_supported_by_v2_engine(self) -> None:
        adapter.validate_engine_compatibility(self.policy, python_label="3.10")
        adapter.validate_engine_compatibility(self.policy, python_label="3.13")

    def test_non_deep_python_label_fails_closed(self) -> None:
        with self.assertRaisesRegex(adapter.AdapterError, "deep-gate Python"):
            adapter.validate_engine_compatibility(self.policy, python_label="3.12")

    def test_policy_pass_count_cannot_outgrow_current_engine_silently(self) -> None:
        policy = self._load_modified_policy(
            lambda payload: (
                payload["deep_gate"].__setitem__("minimum_passes", 16),
                payload["deep_gate"]["hash_seeds"].append(15),
            )
        )
        with self.assertRaisesRegex(adapter.AdapterError, "pass count"):
            adapter.validate_engine_compatibility(policy, python_label="3.10")

    def test_policy_command_timeout_cannot_diverge_from_engine_silently(self) -> None:
        policy = self._load_modified_policy(
            lambda payload: payload["deep_gate"].__setitem__("command_timeout_seconds", 901)
        )
        with self.assertRaisesRegex(adapter.AdapterError, "command timeout"):
            adapter.validate_engine_compatibility(policy, python_label="3.10")

    def test_legacy_failure_categories_map_to_controlled_taxonomy(self) -> None:
        cases = {
            "compile": "BUILD",
            "editable-tests": "TEST",
            "repository-verifier": "TEST",
            "editable-cli": "TEST",
            "wheel-build": "BUILD",
            "wheel-install": "PACKAGE",
            "wheel-tests": "TEST",
            "wheel-verifier": "TEST",
            "wheel-cli": "TEST",
            "dependency-integrity": "DEPENDENCY",
            "package-parity": "PACKAGE",
            "cross-pass-determinism": "DETERMINISM",
            "internal-gate-error": "UNKNOWN",
        }
        for legacy, expected in cases.items():
            with self.subTest(legacy=legacy):
                self.assertEqual(adapter.classify_legacy_failure(legacy, message="failed"), expected)
        self.assertEqual(
            adapter.classify_legacy_failure("wheel-build", message="command timed out after 900s"),
            "TIMEOUT",
        )

    def _manifest(self, summary: dict[str, object], *, source: str = "a", tested: str = "b"):
        return adapter.build_common_manifest(
            policy=self.policy,
            summary=summary,
            repository="Luca-1304/agent-reliability-arena",
            commit_sha=source * 40,
            tested_commit_sha=tested * 40,
            workflow="deep-test",
            run_id="42",
            run_attempt="1",
            event="pull_request",
            ref="refs/pull/1/merge",
            runner_os="Linux",
            runner_arch="X64",
            python_version="3.10",
            dependency_fingerprint={"rows": ["pip==1"], "sha256": "d" * 64},
            toolchain={"python": "3.10", "pip": "1"},
        )

    def test_common_manifest_flattens_commands_preserves_determinism_and_provenance(self) -> None:
        summary = {
            "status": "passed",
            "duration_seconds": 2.5,
            "package_parity": True,
            "cross_pass_determinism": True,
            "failure": None,
            "passes": [
                {
                    "pass_number": 1,
                    "hash_seed": 0,
                    "duration_seconds": 1.2,
                    "deterministic_manifest_sha256": "a" * 64,
                    "commands": [
                        {
                            "name": "compile-source",
                            "argv": ["python", "-m", "compileall"],
                            "exit_code": 0,
                            "duration_seconds": 0.2,
                            "log_path": "passes/01/commands/01-compile-source.log",
                        }
                    ],
                },
                {
                    "pass_number": 2,
                    "hash_seed": 1,
                    "duration_seconds": 1.3,
                    "deterministic_manifest_sha256": "a" * 64,
                    "commands": [
                        {
                            "name": "compile-source",
                            "argv": ["python", "-m", "compileall"],
                            "exit_code": 0,
                            "duration_seconds": 0.3,
                            "log_path": "passes/02/commands/01-compile-source.log",
                        }
                    ],
                },
            ],
        }
        payload = self._manifest(summary).to_dict()
        self.assertEqual(payload["final_status"], "passed")
        self.assertEqual(payload["commit_sha"], "a" * 40)
        self.assertEqual(payload["tested_commit_sha"], "b" * 40)
        self.assertEqual([row["sequence"] for row in payload["commands"]], [1, 2])
        self.assertEqual([row["pass_number"] for row in payload["commands"]], [1, 2])
        self.assertEqual(payload["output_digests"]["pass_01"], "a" * 64)
        self.assertEqual(payload["output_digests"]["pass_02"], "a" * 64)
        self.assertTrue(payload["output_digests"]["package_parity"])
        self.assertTrue(payload["output_digests"]["cross_pass_determinism"])
        self.assertEqual(payload["failures"], [])

    def test_failed_summary_maps_failure_into_common_manifest(self) -> None:
        summary = {
            "status": "failed",
            "duration_seconds": 1.0,
            "package_parity": False,
            "cross_pass_determinism": False,
            "passes": [],
            "failure": {
                "category": "package-parity",
                "phase": "package-parity",
                "command_name": "compare-json-outputs",
                "argv": [],
                "pass_number": 1,
                "hash_seed": 0,
                "exit_code": 1,
                "duration_seconds": 0.0,
                "log_path": "",
                "message": "mismatch",
            },
        }
        failure = self._manifest(summary, source="c", tested="d").to_dict()["failures"][0]
        self.assertEqual(failure["category"], "PACKAGE")
        self.assertEqual(failure["phase"], "package-parity")
        self.assertEqual(failure["sequence"], 1)

    def test_workflow_uses_policy_adapter_without_duplicating_pass_count(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/ci/run_deep_reliability.py", workflow)
        self.assertIn("--policy reliability-policy.json", workflow)
        self.assertIn("--source-sha", workflow)
        self.assertIn("github.event.pull_request.head.sha", workflow)
        self.assertIn("--tested-sha", workflow)
        self.assertIn("$GITHUB_SHA", workflow)
        self.assertNotIn("--passes 15", workflow)
        self.assertIn("timeout-minutes: 180", workflow)
        self.assertIn("retention-days: 14", workflow)
        self.assertIn('      - "reliability-policy.json"', workflow)
        self.assertIn('      - "scripts/ci/reliability_evidence.py"', workflow)
        self.assertIn('      - "scripts/ci/run_deep_reliability.py"', workflow)


if __name__ == "__main__":
    unittest.main()
