from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.ci.pre_pr_green_gate import (
    CheckSpec,
    GateConfigurationError,
    GateInternalError,
    build_report,
    render_report,
    run_check,
    run_gate,
    validate_check_specs,
    write_report_atomic,
)

ROOT = Path(__file__).resolve().parents[1]


class PrePRGreenGateTests(unittest.TestCase):
    def test_all_success_returns_zero_and_zero_failures(self) -> None:
        specs = (
            CheckSpec("a", ((sys.executable, "-c", "print('ok-a')"),), 10),
            CheckSpec("b", ((sys.executable, "-c", "print('ok-b')"),), 10),
        )
        code, report = run_gate(specs, cwd=ROOT)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["pre_pr_failures"], 0)
        self.assertEqual(report["checks_run"], 2)
        self.assertEqual(report["checks_passed"], 2)
        self.assertEqual(report["checks_failed"], 0)
        self.assertFalse(report["network_used"])
        self.assertFalse(report["mutation_supported"])
        self.assertFalse(report["merge_authority"])
        self.assertTrue(all(check["diagnostic_excerpt"] == "" for check in report["checks"]))

    def test_multiple_failures_are_aggregated_and_later_checks_run(self) -> None:
        specs = (
            CheckSpec("source-tests", ((sys.executable, "-c", "raise SystemExit(7)"),), 10),
            CheckSpec("later", ((sys.executable, "-c", "print('ran-later')"),), 10),
            CheckSpec("other-failure", ((sys.executable, "-c", "raise SystemExit(9)"),), 10),
        )
        code, report = run_gate(specs, cwd=ROOT)
        self.assertEqual(code, 1)
        self.assertEqual(report["pre_pr_failures"], 2)
        self.assertEqual(
            [check["identifier"] for check in report["checks"]],
            ["source-tests", "later", "other-failure"],
        )
        self.assertEqual(report["checks"][1]["status"], "pass")

    def test_multi_command_check_runs_all_children_and_reports_one_logical_failure(self) -> None:
        spec = CheckSpec(
            "batch",
            (
                (sys.executable, "-c", "raise SystemExit(3)"),
                (sys.executable, "-c", "raise SystemExit(4)"),
            ),
            10,
        )
        result = run_check(spec, cwd=ROOT)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.returncode, 3)
        self.assertIn("command 1", result.diagnostic_excerpt)
        self.assertIn("command 2", result.diagnostic_excerpt)

    def test_empty_and_duplicate_registries_are_rejected(self) -> None:
        with self.assertRaises(GateConfigurationError):
            validate_check_specs(())
        duplicate = (
            CheckSpec("same", ((sys.executable, "-c", "pass"),)),
            CheckSpec("same", ((sys.executable, "-c", "pass"),)),
        )
        with self.assertRaises(GateConfigurationError):
            validate_check_specs(duplicate)

    def test_incomplete_check_definition_is_rejected(self) -> None:
        with self.assertRaises(GateConfigurationError):
            validate_check_specs((CheckSpec("", ((sys.executable, "-c", "pass"),)),))
        with self.assertRaises(GateConfigurationError):
            validate_check_specs((CheckSpec("x", ()),))
        with self.assertRaises(GateConfigurationError):
            validate_check_specs((CheckSpec("x", ((sys.executable, ""),)),))
        with self.assertRaises(GateConfigurationError):
            validate_check_specs((CheckSpec("x", ((sys.executable, "-c", "pass"),), 0),))

    def test_missing_executable_and_timeout_fail_closed(self) -> None:
        with self.assertRaises(GateInternalError):
            run_check(
                CheckSpec("missing", (("definitely-not-a-real-executable",),), 10),
                cwd=ROOT,
            )
        code, report = run_gate(
            (
                CheckSpec("first", ((sys.executable, "-c", "pass"),), 10),
                CheckSpec("missing", (("definitely-not-a-real-executable",),), 10),
                CheckSpec("never", ((sys.executable, "-c", "pass"),), 10),
            ),
            cwd=ROOT,
        )
        self.assertEqual(code, 2)
        self.assertEqual(
            [item["identifier"] for item in report["checks"]],
            ["first", "missing"],
        )
        self.assertEqual(report["checks"][1]["returncode"], 2)
        with self.assertRaises(GateInternalError):
            run_check(
                CheckSpec(
                    "timeout",
                    ((sys.executable, "-c", "import time; time.sleep(1)"),),
                    0.01,
                ),
                cwd=ROOT,
            )

    def test_diagnostics_are_bounded_and_keep_tail(self) -> None:
        marker = "TAIL-MARKER"
        payload = "x" * 9000 + marker
        spec = CheckSpec(
            "noisy",
            ((sys.executable, "-c", f"print({payload!r}); raise SystemExit(1)"),),
            10,
        )
        result = run_check(spec, cwd=ROOT)
        self.assertLessEqual(len(result.diagnostic_excerpt), 8000)
        self.assertTrue(result.diagnostic_excerpt.endswith(marker))

    def test_report_rendering_is_deterministic_for_equivalent_results(self) -> None:
        specs = (CheckSpec("a", ((sys.executable, "-c", "pass"),), 10),)
        _, first = run_gate(specs, cwd=ROOT)
        _, second = run_gate(specs, cwd=ROOT)
        self.assertEqual(render_report(first), render_report(second))

    def test_temp_paths_are_normalized_in_commands_and_failure_diagnostics(self) -> None:
        raw = "/tmp/random-run-123"
        spec = CheckSpec(
            "x",
            ((sys.executable, "-c", f"print({raw!r}); raise SystemExit(1)", raw),),
            10,
        )
        _, report = run_gate((spec,), cwd=ROOT, replacements=((raw, "<TEMP>"),))
        payload = render_report(report)
        self.assertNotIn(raw, payload)
        self.assertIn("<TEMP>", payload)

    def test_report_claim_boundary_is_explicit(self) -> None:
        report = build_report(())
        payload = json.dumps(report)
        self.assertFalse(report["merge_authority"])
        self.assertFalse(report["network_used"])
        self.assertFalse(report["mutation_supported"])
        self.assertNotIn("safe_to_merge", payload)
        self.assertNotIn("all_ci_passed", payload)

    def test_report_write_is_atomic_and_invalid_destination_fails_closed(self) -> None:
        report = build_report(())
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "nested" / "report.json"
            write_report_atomic(target, report)
            self.assertEqual(target.read_text(encoding="utf-8"), render_report(report))
            with self.assertRaises(GateInternalError):
                write_report_atomic(root, report)

    def test_implementation_does_not_gain_destructive_or_shell_authority(self) -> None:
        source = (ROOT / "scripts" / "ci" / "pre_pr_green_gate.py").read_text(
            encoding="utf-8"
        )
        banned = (
            "shell=true",
            "git push",
            "git update-ref",
            "git tag",
            "gh api",
            "gh release",
            "repository_dispatch",
            "pages deploy",
            "vercel",
        )
        for token in banned:
            with self.subTest(token=token):
                self.assertNotIn(token, source.lower())


if __name__ == "__main__":
    unittest.main()
