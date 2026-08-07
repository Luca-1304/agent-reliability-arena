from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

try:
    from scripts.ci import reliability_gate
    from scripts.ci.reliability_evidence import (
        EvidenceManifest,
        FailureRecord,
        dependency_fingerprint as build_dependency_fingerprint,
        write_json_atomic,
    )
    from scripts.ci.reliability_policy import ReliabilityPolicy, load_policy
except ModuleNotFoundError:  # Direct execution from scripts/ci.
    import reliability_gate  # type: ignore[no-redef]
    from reliability_evidence import (  # type: ignore[no-redef]
        EvidenceManifest,
        FailureRecord,
        dependency_fingerprint as build_dependency_fingerprint,
        write_json_atomic,
    )
    from reliability_policy import ReliabilityPolicy, load_policy  # type: ignore[no-redef]


ENGINE_PASS_COUNT = 15
ENGINE_HASH_SEEDS = tuple(range(ENGINE_PASS_COUNT))


class AdapterError(RuntimeError):
    """Raised when the policy cannot be represented safely by the v2 engine."""


_LEGACY_CATEGORY_MAP = {
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


def validate_engine_compatibility(policy: ReliabilityPolicy, *, python_label: str) -> None:
    if python_label not in policy.deep_python:
        raise AdapterError(
            f"{python_label} is not an authorised deep-gate Python version: {policy.deep_python}"
        )
    if policy.stress_passes != ENGINE_PASS_COUNT:
        raise AdapterError(
            f"policy pass count {policy.stress_passes} is not supported by v2 engine; "
            f"expected exactly {ENGINE_PASS_COUNT}"
        )
    deep_gate = policy.raw["deep_gate"]
    if not isinstance(deep_gate, Mapping):
        raise AdapterError("validated policy deep_gate is not an object")
    hash_seeds = tuple(int(value) for value in deep_gate["hash_seeds"])
    if hash_seeds != ENGINE_HASH_SEEDS:
        raise AdapterError(
            f"policy hash seeds {hash_seeds} are not supported by v2 engine; "
            f"expected {ENGINE_HASH_SEEDS}"
        )
    command_timeout = int(deep_gate["command_timeout_seconds"])
    if command_timeout != reliability_gate.DEFAULT_TIMEOUT_SECONDS:
        raise AdapterError(
            f"policy command timeout {command_timeout}s diverges from v2 engine "
            f"timeout {reliability_gate.DEFAULT_TIMEOUT_SECONDS}s"
        )
    if str(deep_gate["timezone"]) != "UTC" or str(deep_gate["locale"]) != "C.UTF-8":
        raise AdapterError("v2 engine currently requires UTC and C.UTF-8")


def classify_legacy_failure(category: str, *, message: str) -> str:
    if "timed out" in message.lower() or "timeout" in category.lower():
        return "TIMEOUT"
    return _LEGACY_CATEGORY_MAP.get(category, "UNKNOWN")


def _run_text(argv: Sequence[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        [str(value) for value in argv],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise AdapterError(f"unable to capture toolchain evidence for {argv[0]}: {detail}")
    return completed.stdout.strip()


def capture_toolchain(*, workspace: Path) -> dict[str, str]:
    return {
        "git": _run_text(["git", "--version"], cwd=workspace),
        "pip": _run_text([sys.executable, "-m", "pip", "--version"], cwd=workspace),
        "python": platform.python_version(),
    }


def capture_dependency_fingerprint(*, workspace: Path) -> dict[str, object]:
    raw = _run_text([sys.executable, "-m", "pip", "freeze", "--all"], cwd=workspace)
    rows: list[str] = []
    for row in raw.splitlines():
        stripped = row.strip()
        lowered = stripped.lower()
        if not stripped or stripped.startswith("-e "):
            continue
        if " @ file:" in lowered or lowered.startswith("agent-reliability-arena @"):
            continue
        rows.append(stripped)
    return build_dependency_fingerprint(rows)


def _flatten_commands(summary: Mapping[str, object]) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    sequence = 0
    passes = summary.get("passes", [])
    if not isinstance(passes, list):
        return flattened
    for pass_row in passes:
        if not isinstance(pass_row, Mapping):
            continue
        pass_number = int(pass_row.get("pass_number", len(flattened) + 1))
        hash_seed = int(pass_row.get("hash_seed", pass_number - 1))
        commands = pass_row.get("commands", [])
        if not isinstance(commands, list):
            continue
        for command in commands:
            if not isinstance(command, Mapping):
                continue
            sequence += 1
            row = dict(command)
            row["sequence"] = sequence
            row["pass_number"] = pass_number
            row["hash_seed"] = hash_seed
            flattened.append(row)
    return flattened


def _timings(summary: Mapping[str, object]) -> dict[str, float]:
    pass_durations: list[float] = []
    passes = summary.get("passes", [])
    if isinstance(passes, list):
        for pass_row in passes:
            if isinstance(pass_row, Mapping):
                value = pass_row.get("duration_seconds")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    pass_durations.append(float(value))
    result = {"total_seconds": float(summary.get("duration_seconds", 0.0) or 0.0)}
    if pass_durations:
        result["median_pass_seconds"] = float(statistics.median(pass_durations))
        result["max_pass_seconds"] = max(pass_durations)
    return result


def _output_digests(summary: Mapping[str, object]) -> dict[str, object]:
    output: dict[str, object] = {
        "package_parity": bool(summary.get("package_parity", False)),
        "cross_pass_determinism": bool(summary.get("cross_pass_determinism", False)),
    }
    passes = summary.get("passes", [])
    if isinstance(passes, list):
        for pass_row in passes:
            if not isinstance(pass_row, Mapping):
                continue
            pass_number = int(pass_row.get("pass_number", 0) or 0)
            digest = pass_row.get("deterministic_manifest_sha256")
            if pass_number > 0 and isinstance(digest, str):
                output[f"pass_{pass_number:02d}"] = digest
    return output


def _failure_from_summary(
    summary: Mapping[str, object],
    *,
    command_count: int,
) -> FailureRecord | None:
    raw = summary.get("failure")
    if not isinstance(raw, Mapping):
        return None
    legacy_category = str(raw.get("category", "internal-gate-error"))
    message = str(raw.get("message", "deep reliability gate failed"))
    argv_raw = raw.get("argv", [])
    argv = tuple(str(value) for value in argv_raw) if isinstance(argv_raw, list) else ()
    pass_number_raw = raw.get("pass_number")
    hash_seed_raw = raw.get("hash_seed")
    exit_code_raw = raw.get("exit_code")
    duration_raw = raw.get("duration_seconds", 0.0)
    return FailureRecord(
        category=classify_legacy_failure(legacy_category, message=message),
        phase=str(raw.get("phase", legacy_category)),
        command_name=str(raw.get("command_name", "reliability-gate")),
        argv=argv,
        sequence=max(1, command_count + 1),
        pass_number=int(pass_number_raw) if isinstance(pass_number_raw, int) else None,
        hash_seed=int(hash_seed_raw) if isinstance(hash_seed_raw, int) else None,
        exit_code=int(exit_code_raw) if isinstance(exit_code_raw, int) else None,
        duration_seconds=float(duration_raw) if isinstance(duration_raw, (int, float)) else 0.0,
        log_path=str(raw.get("log_path", "")),
        message=message,
    )


def build_common_manifest(
    *,
    policy: ReliabilityPolicy,
    summary: Mapping[str, object],
    repository: str,
    commit_sha: str,
    tested_commit_sha: str,
    workflow: str,
    run_id: str,
    run_attempt: str,
    event: str,
    ref: str,
    runner_os: str,
    runner_arch: str,
    python_version: str,
    dependency_fingerprint: dict[str, object],
    toolchain: dict[str, str],
) -> EvidenceManifest:
    commands = _flatten_commands(summary)
    raw_status = str(summary.get("status", "unknown"))
    final_status = raw_status if raw_status in {"passed", "failed", "blocked", "unknown"} else "unknown"
    manifest = EvidenceManifest(
        repository=repository,
        commit_sha=commit_sha,
        tested_commit_sha=tested_commit_sha,
        workflow=workflow,
        run_id=run_id,
        run_attempt=run_attempt,
        event=event,
        ref=ref,
        runner_os=runner_os,
        runner_arch=runner_arch,
        python_version=python_version,
        timezone=str(policy.raw["deep_gate"]["timezone"]),
        locale=str(policy.raw["deep_gate"]["locale"]),
        hash_seed=None,
        install_mode="editable+wheel",
        cache_mode="warm",
        toolchain=dict(toolchain),
        dependency_fingerprint=dict(dependency_fingerprint),
        commands=commands,
        timings=_timings(summary),
        output_digests=_output_digests(summary),
        final_status=final_status,
    )
    failure = _failure_from_summary(summary, command_count=len(commands))
    if failure is not None:
        manifest.failures.append(failure)
        manifest.final_status = "failed"
    return manifest


def _policy_violations(
    policy: ReliabilityPolicy,
    summary: Mapping[str, object],
    *,
    command_count: int,
) -> list[FailureRecord]:
    violations: list[FailureRecord] = []
    if str(summary.get("status", "unknown")) != "passed":
        return violations
    passes = summary.get("passes", [])
    if not isinstance(passes, list):
        passes = []
    expected_seeds = tuple(int(value) for value in policy.raw["deep_gate"]["hash_seeds"])
    actual_seeds = tuple(
        int(row.get("hash_seed", -1)) for row in passes if isinstance(row, Mapping)
    )
    completed = int(summary.get("completed_passes", len(passes)) or 0)
    if completed != policy.stress_passes or len(passes) != policy.stress_passes:
        violations.append(
            FailureRecord(
                category="POLICY",
                phase="policy-enforcement",
                command_name="validate-pass-count",
                argv=(),
                sequence=max(1, command_count + len(violations) + 1),
                pass_number=None,
                hash_seed=None,
                exit_code=1,
                duration_seconds=0.0,
                log_path="",
                message=(
                    f"deep gate completed {completed}/{policy.stress_passes} passes "
                    f"with {len(passes)} pass records"
                ),
            )
        )
    if actual_seeds != expected_seeds[: len(actual_seeds)] or len(actual_seeds) != policy.stress_passes:
        violations.append(
            FailureRecord(
                category="POLICY",
                phase="policy-enforcement",
                command_name="validate-hash-seeds",
                argv=(),
                sequence=max(1, command_count + len(violations) + 1),
                pass_number=None,
                hash_seed=None,
                exit_code=1,
                duration_seconds=0.0,
                log_path="",
                message=f"deep gate seeds {actual_seeds} do not match policy {expected_seeds}",
            )
        )
    pass_timeout = float(policy.raw["deep_gate"]["pass_timeout_seconds"])
    command_timeout = float(policy.raw["deep_gate"]["command_timeout_seconds"])
    for pass_row in passes:
        if not isinstance(pass_row, Mapping):
            continue
        pass_number = int(pass_row.get("pass_number", 0) or 0)
        hash_seed = int(pass_row.get("hash_seed", 0) or 0)
        duration = float(pass_row.get("duration_seconds", 0.0) or 0.0)
        if duration > pass_timeout:
            violations.append(
                FailureRecord(
                    category="TIMEOUT",
                    phase="policy-enforcement",
                    command_name="validate-pass-timeout",
                    argv=(),
                    sequence=max(1, command_count + len(violations) + 1),
                    pass_number=pass_number or None,
                    hash_seed=hash_seed,
                    exit_code=124,
                    duration_seconds=duration,
                    log_path="",
                    message=f"pass duration {duration:.3f}s exceeded policy {pass_timeout:.3f}s",
                )
            )
        commands = pass_row.get("commands", [])
        if isinstance(commands, list):
            for command in commands:
                if not isinstance(command, Mapping):
                    continue
                command_duration = float(command.get("duration_seconds", 0.0) or 0.0)
                if command_duration > command_timeout:
                    violations.append(
                        FailureRecord(
                            category="TIMEOUT",
                            phase="policy-enforcement",
                            command_name=str(command.get("name", "unknown-command")),
                            argv=tuple(str(value) for value in command.get("argv", []))
                            if isinstance(command.get("argv", []), list)
                            else (),
                            sequence=max(1, command_count + len(violations) + 1),
                            pass_number=pass_number or None,
                            hash_seed=hash_seed,
                            exit_code=124,
                            duration_seconds=command_duration,
                            log_path=str(command.get("log_path", "")),
                            message=(
                                f"command duration {command_duration:.3f}s exceeded "
                                f"policy {command_timeout:.3f}s"
                            ),
                        )
                    )
    return violations


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the policy-governed deep reliability gate.")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--python-label", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--tested-sha", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--diagnostics-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    workspace = args.workspace.resolve()
    diagnostics_dir = args.diagnostics_dir.resolve()
    policy = load_policy(args.policy.resolve())
    validate_engine_compatibility(policy, python_label=args.python_label)
    toolchain = capture_toolchain(workspace=workspace)
    dependencies = capture_dependency_fingerprint(workspace=workspace)

    config = reliability_gate.GateConfig(
        passes=policy.stress_passes,
        python_label=args.python_label,
        workspace=workspace,
        work_root=args.work_root.resolve(),
        diagnostics_dir=diagnostics_dir,
    )
    engine_return_code = reliability_gate.execute(config)
    summary_path = diagnostics_dir / "summary.json"
    if not summary_path.is_file():
        raise AdapterError("deep engine did not produce summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, Mapping):
        raise AdapterError("deep engine summary.json must contain an object")

    manifest = build_common_manifest(
        policy=policy,
        summary=summary,
        repository=os.environ.get("GITHUB_REPOSITORY", "Luca-1304/agent-reliability-arena"),
        commit_sha=args.source_sha.strip().lower(),
        tested_commit_sha=args.tested_sha.strip().lower(),
        workflow=os.environ.get("GITHUB_WORKFLOW", "local-deep-reliability"),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        event=os.environ.get("GITHUB_EVENT_NAME", "local"),
        ref=os.environ.get("GITHUB_REF", "local"),
        runner_os=os.environ.get("RUNNER_OS", platform.system()),
        runner_arch=os.environ.get("RUNNER_ARCH", platform.machine()),
        python_version=args.python_label,
        dependency_fingerprint=dependencies,
        toolchain=toolchain,
    )
    violations = _policy_violations(policy, summary, command_count=len(manifest.commands))
    if violations:
        manifest.failures.extend(violations)
        manifest.final_status = "failed"
    write_json_atomic(diagnostics_dir / "manifest.json", manifest.to_dict())
    write_json_atomic(diagnostics_dir / "dependencies.json", dependencies)
    write_json_atomic(diagnostics_dir / "toolchain.json", toolchain)
    if engine_return_code != 0 or manifest.final_status != "passed" or manifest.failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
