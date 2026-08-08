from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ci.pre_pr_green_gate import (
    GateInternalError,
    _venv_environment,
    _venv_scripts,
    default_check_specs,
    validate_repository_root,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = (
    "compile-source",
    "source-tests",
    "ci-policy",
    "git-operations-policy",
    "release-verifiers",
    "installed-command-smoke",
    "history-boundary-local",
    "build-wheel",
    "verify-wheel-clean-environment",
    "dependency-check",
)


class PrePRGreenGateIntegrationTests(unittest.TestCase):
    def test_default_registry_has_exact_ordered_identifiers(self) -> None:
        specs = default_check_specs(python_executable="python", temp_root=Path("TEMP"))
        self.assertEqual(tuple(spec.identifier for spec in specs), EXPECTED_IDS)
        self.assertEqual(len({spec.identifier for spec in specs}), len(EXPECTED_IDS))

    def test_default_registry_reuses_canonical_existing_commands(self) -> None:
        specs = {spec.identifier: spec for spec in default_check_specs(python_executable="python", temp_root=Path("TEMP"))}
        self.assertEqual(specs["compile-source"].commands, (("python", "-m", "compileall", "-q", "src", "tests", "scripts"),))
        self.assertEqual(specs["source-tests"].commands, (("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"),))
        self.assertEqual(specs["ci-policy"].commands, (("python", "scripts/ci/verify_ci_policy.py", "--policy", "reliability-policy.json"),))
        self.assertEqual(specs["git-operations-policy"].commands, (("python", "scripts/ci/verify_git_operations.py", "--policy", "git-operations-policy.json"),))
        self.assertEqual(
            specs["release-verifiers"].commands,
            tuple(
                ("python", script)
                for script in (
                    "scripts/verify_release.py",
                    "scripts/verify_disclosure_release.py",
                    "scripts/verify_repeated_release.py",
                    "scripts/verify_showcase_release.py",
                    "scripts/verify_launch_package.py",
                    "scripts/verify_citation_package.py",
                    "scripts/verify_supply_chain.py",
                )
            ),
        )
        self.assertEqual(specs["history-boundary-local"].commands, (("python", "scripts/verify_history_boundary.py"),))

    def test_wheel_build_is_no_deps_no_isolation_and_outside_workspace(self) -> None:
        temp_root = Path("TEMP")
        specs = {spec.identifier: spec for spec in default_check_specs(python_executable="python", temp_root=temp_root)}
        command = specs["build-wheel"].commands[0]
        self.assertIn("--no-deps", command)
        self.assertIn("--no-build-isolation", command)
        self.assertEqual(command[command.index("--wheel-dir") + 1], str(temp_root / "dist"))
        helper = specs["verify-wheel-clean-environment"].commands[0]
        self.assertIn("--internal-verify-wheel", helper)
        self.assertIn(str(temp_root / "wheel-venv"), helper)
        dependency = specs["dependency-check"].commands[0]
        self.assertIn("--internal-dependency-check", dependency)

    def test_installed_command_smoke_uses_full_provider_free_fixture_surface(self) -> None:
        specs = {spec.identifier: spec for spec in default_check_specs(python_executable="python", temp_root=Path("TEMP"))}
        smoke = specs["installed-command-smoke"].commands
        self.assertEqual(len(smoke), 7)
        self.assertEqual(tuple(command[0] for command in smoke), (
            "arena-run",
            "arena-replay",
            "arena-export-web",
            "arena-verify-showcase",
            "arena-verify-launch-package",
            "arena-verify-citation-package",
            "arena-verify-supply-chain",
        ))
        self.assertIn("examples/fixture_experiment.json", smoke[0])
        self.assertTrue(any("TEMP" in part for command in smoke for part in command))

    def test_clean_wheel_environment_forces_venv_commands_onto_path(self) -> None:
        root = Path("VENV")
        env = _venv_environment(root)
        first = env["PATH"].split(__import__("os").pathsep, 1)[0]
        self.assertEqual(Path(first), _venv_scripts(root.resolve()))
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")

    def test_missing_repository_contract_files_fail_closed_before_real_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(GateInternalError):
                validate_repository_root(root)

    def test_non_git_workspace_fails_closed_after_contract_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "scripts" / "ci").mkdir(parents=True)
            (root / "examples").mkdir()
            (root / "reference_runs" / "fixture-v1").mkdir(parents=True)
            for relative in (
                "pyproject.toml",
                "scripts/verify_history_boundary.py",
                "scripts/ci/verify_ci_policy.py",
                "scripts/ci/verify_git_operations.py",
                "examples/fixture_experiment.json",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            with self.assertRaises(GateInternalError):
                validate_repository_root(root)


if __name__ == "__main__":
    unittest.main()
