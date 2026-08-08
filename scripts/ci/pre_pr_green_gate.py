from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = "pre-pr-green-gate-v1"
MAX_DIAGNOSTIC_CHARS = 8_000


class GateConfigurationError(RuntimeError):
    """Raised when the pre-PR check registry is malformed."""


class GateInternalError(RuntimeError):
    """Raised when the gate cannot execute its contract reliably."""


@dataclass(frozen=True)
class CheckSpec:
    identifier: str
    commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int = 900


@dataclass(frozen=True)
class CheckResult:
    identifier: str
    commands: tuple[tuple[str, ...], ...]
    returncode: int
    status: str
    diagnostic_excerpt: str


def validate_check_specs(specs: Sequence[CheckSpec]) -> None:
    if not specs:
        raise GateConfigurationError("at least one check is required")
    identifiers = [spec.identifier for spec in specs]
    if len(set(identifiers)) != len(identifiers):
        raise GateConfigurationError("check identifiers must be unique")
    for spec in specs:
        if not spec.identifier.strip():
            raise GateConfigurationError("check identifiers must be non-empty")
        if not spec.commands:
            raise GateConfigurationError(f"check {spec.identifier!r} has no commands")
        for command in spec.commands:
            if not command or any(not str(part) for part in command):
                raise GateConfigurationError(
                    f"check {spec.identifier!r} contains an incomplete command"
                )
        if spec.timeout_seconds <= 0:
            raise GateConfigurationError(
                f"check {spec.identifier!r} timeout_seconds must be positive"
            )


def _stable_environment(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.update(
        {
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "SOURCE_DATE_EPOCH": "315532800",
            "ARENA_RELIABILITY_STABLE_OUTPUT": "1",
        }
    )
    return env


def _normalize_text(text: str, replacements: Sequence[tuple[str, str]]) -> str:
    normalized = text
    for raw, replacement in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        if raw:
            normalized = normalized.replace(raw, replacement)
    return normalized


def _bounded_tail(text: str) -> str:
    if len(text) <= MAX_DIAGNOSTIC_CHARS:
        return text
    return text[-MAX_DIAGNOSTIC_CHARS:]


def run_check(
    spec: CheckSpec,
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    replacements: Sequence[tuple[str, str]] = (),
) -> CheckResult:
    first_nonzero = 0
    failed_outputs: list[str] = []
    for index, command in enumerate(spec.commands, start=1):
        try:
            completed = subprocess.run(
                list(command),
                cwd=cwd,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=spec.timeout_seconds,
                env=None if env is None else dict(env),
            )
        except FileNotFoundError as exc:
            raise GateInternalError(
                f"check {spec.identifier!r} cannot execute {command[0]!r}: executable not found"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GateInternalError(
                f"check {spec.identifier!r} exceeded {spec.timeout_seconds} seconds"
            ) from exc
        except OSError as exc:
            raise GateInternalError(
                f"check {spec.identifier!r} could not start: {exc}"
            ) from exc

        if completed.returncode != 0:
            if first_nonzero == 0:
                first_nonzero = completed.returncode
            output = completed.stdout or ""
            detail = output.strip() or f"command {index} exited {completed.returncode}"
            failed_outputs.append(f"command {index}: {detail}")

    diagnostic = "\n\n".join(failed_outputs)
    diagnostic = _normalize_text(diagnostic, replacements)
    diagnostic = _bounded_tail(diagnostic)
    return CheckResult(
        identifier=spec.identifier,
        commands=spec.commands,
        returncode=first_nonzero,
        status="pass" if first_nonzero == 0 else "fail",
        diagnostic_excerpt=diagnostic,
    )


def _report_command(
    command: Sequence[str], replacements: Sequence[tuple[str, str]]
) -> list[str]:
    return [_normalize_text(str(part), replacements) for part in command]


def build_report(
    results: Sequence[CheckResult],
    *,
    replacements: Sequence[tuple[str, str]] = (),
) -> dict[str, object]:
    failed = sum(result.status == "fail" for result in results)
    passed = len(results) - failed
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if failed == 0 else "fail",
        "checks_run": len(results),
        "checks_passed": passed,
        "checks_failed": failed,
        "pre_pr_failures": failed,
        "network_used": False,
        "mutation_supported": False,
        "merge_authority": False,
        "checks": [
            {
                "identifier": result.identifier,
                "commands": [
                    _report_command(command, replacements) for command in result.commands
                ],
                "returncode": result.returncode,
                "status": result.status,
                "diagnostic_excerpt": result.diagnostic_excerpt,
            }
            for result in results
        ],
    }


def run_gate(
    specs: Sequence[CheckSpec],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    replacements: Sequence[tuple[str, str]] = (),
) -> tuple[int, dict[str, object]]:
    validate_check_specs(specs)
    results: list[CheckResult] = []
    for spec in specs:
        try:
            result = run_check(
                spec,
                cwd=cwd,
                env=env,
                replacements=replacements,
            )
        except GateInternalError as exc:
            results.append(
                CheckResult(
                    identifier=spec.identifier,
                    commands=spec.commands,
                    returncode=2,
                    status="fail",
                    diagnostic_excerpt=_bounded_tail(
                        _normalize_text(str(exc), replacements)
                    ),
                )
            )
            return 2, build_report(results, replacements=replacements)
        results.append(result)
    report = build_report(results, replacements=replacements)
    return (0 if report["pre_pr_failures"] == 0 else 1), report


def render_report(report: Mapping[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def write_report_atomic(path: Path, report: Mapping[str, object]) -> None:
    target = path.resolve()
    temporary: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(render_report(report))
        temporary.replace(target)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise GateInternalError(f"could not write report {target}: {exc}") from exc


def _release_commands(python_executable: str) -> tuple[tuple[str, ...], ...]:
    scripts = (
        "scripts/verify_release.py",
        "scripts/verify_disclosure_release.py",
        "scripts/verify_repeated_release.py",
        "scripts/verify_showcase_release.py",
        "scripts/verify_launch_package.py",
        "scripts/verify_citation_package.py",
        "scripts/verify_supply_chain.py",
    )
    return tuple((python_executable, script) for script in scripts)


def _smoke_commands(
    *,
    temp_root: Path,
    executable_by_name: Mapping[str, str],
) -> tuple[tuple[str, ...], ...]:
    run_output = temp_root / "run"
    public_output = temp_root / "public.json"
    return (
        (
            executable_by_name["arena-run"],
            "--config",
            "examples/fixture_experiment.json",
            "--output",
            str(run_output),
        ),
        (executable_by_name["arena-replay"], "--input", str(run_output)),
        (
            executable_by_name["arena-export-web"],
            "--input",
            str(run_output),
            "--output",
            str(public_output),
        ),
        (executable_by_name["arena-verify-showcase"], "--root", "."),
        (executable_by_name["arena-verify-launch-package"], "--root", "."),
        (executable_by_name["arena-verify-citation-package"], "--root", "."),
        (executable_by_name["arena-verify-supply-chain"], "--root", "."),
    )


def _source_smoke_commands(temp_root: Path) -> tuple[tuple[str, ...], ...]:
    names = (
        "arena-run",
        "arena-replay",
        "arena-export-web",
        "arena-verify-showcase",
        "arena-verify-launch-package",
        "arena-verify-citation-package",
        "arena-verify-supply-chain",
    )
    return _smoke_commands(
        temp_root=temp_root,
        executable_by_name={name: name for name in names},
    )


def default_check_specs(
    *,
    python_executable: str = sys.executable,
    temp_root: Path,
) -> tuple[CheckSpec, ...]:
    temp_root = Path(temp_root)
    dist = temp_root / "dist"
    wheel_venv = temp_root / "wheel-venv"
    gate_script = "scripts/ci/pre_pr_green_gate.py"
    return (
        CheckSpec(
            "compile-source",
            ((python_executable, "-m", "compileall", "-q", "src", "tests", "scripts"),),
            300,
        ),
        CheckSpec(
            "source-tests",
            (
                (
                    python_executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_*.py",
                    "-v",
                ),
            ),
            1200,
        ),
        CheckSpec(
            "ci-policy",
            (
                (
                    python_executable,
                    "scripts/ci/verify_ci_policy.py",
                    "--policy",
                    "reliability-policy.json",
                ),
            ),
            300,
        ),
        CheckSpec(
            "git-operations-policy",
            (
                (
                    python_executable,
                    "scripts/ci/verify_git_operations.py",
                    "--policy",
                    "git-operations-policy.json",
                ),
            ),
            300,
        ),
        CheckSpec("release-verifiers", _release_commands(python_executable), 600),
        CheckSpec("installed-command-smoke", _source_smoke_commands(temp_root / "source-smoke"), 900),
        CheckSpec(
            "history-boundary-local",
            ((python_executable, "scripts/verify_history_boundary.py"),),
            300,
        ),
        CheckSpec(
            "build-wheel",
            (
                (
                    python_executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--disable-pip-version-check",
                    "--no-input",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(dist),
                    ".",
                ),
            ),
            900,
        ),
        CheckSpec(
            "verify-wheel-clean-environment",
            (
                (
                    python_executable,
                    gate_script,
                    "--internal-verify-wheel",
                    "--dist-dir",
                    str(dist),
                    "--workspace",
                    ".",
                    "--venv",
                    str(wheel_venv),
                ),
            ),
            1800,
        ),
        CheckSpec(
            "dependency-check",
            (
                (
                    python_executable,
                    gate_script,
                    "--internal-dependency-check",
                    "--venv",
                    str(wheel_venv),
                ),
            ),
            300,
        ),
    )


def validate_repository_root(root: Path) -> None:
    resolved = root.resolve()
    required = (
        resolved / "pyproject.toml",
        resolved / "scripts" / "verify_history_boundary.py",
        resolved / "scripts" / "ci" / "verify_ci_policy.py",
        resolved / "scripts" / "ci" / "verify_git_operations.py",
        resolved / "examples" / "fixture_experiment.json",
        resolved / "reference_runs" / "fixture-v1",
    )
    missing = [
        path.relative_to(resolved).as_posix()
        for path in required
        if not path.exists()
    ]
    if missing:
        raise GateInternalError(
            "repository root is missing required paths: " + ", ".join(missing)
        )
    try:
        completed = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--is-inside-work-tree"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise GateInternalError("git is required to verify the repository root") from exc
    if completed.returncode != 0 or completed.stdout.strip() != "true":
        raise GateInternalError(f"not a Git work tree: {resolved}")


def _venv_scripts(venv_root: Path) -> Path:
    return venv_root / ("Scripts" if os.name == "nt" else "bin")


def _venv_python(venv_root: Path) -> Path:
    if os.name == "nt":
        return _venv_scripts(venv_root) / "python.exe"
    return _venv_scripts(venv_root) / "python"


def _venv_environment(venv_root: Path) -> dict[str, str]:
    env = _stable_environment()
    scripts = str(_venv_scripts(venv_root.resolve()))
    existing = env.get("PATH", "")
    env["PATH"] = scripts if not existing else scripts + os.pathsep + existing
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _venv_command(venv_root: Path, name: str) -> Path:
    scripts = _venv_scripts(venv_root)
    suffix = ".exe" if os.name == "nt" else ""
    return scripts / f"{name}{suffix}"


def _run_internal(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int = 1200,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=_stable_environment(env),
            timeout=timeout_seconds,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return subprocess.CompletedProcess(list(command), 2, stdout=str(exc), stderr=None)


def _run_internal_batch(
    commands: Sequence[Sequence[str]],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> int:
    first_nonzero = 0
    for command in commands:
        completed = _run_internal(command, cwd=cwd, env=env)
        if completed.returncode != 0:
            if first_nonzero == 0:
                first_nonzero = completed.returncode
            if completed.stdout:
                print(completed.stdout, file=sys.stderr)
    return first_nonzero


def _internal_verify_wheel(dist_dir: Path, workspace: Path, venv_root: Path) -> int:
    dist_dir = dist_dir.resolve()
    workspace = workspace.resolve()
    venv_root = venv_root.resolve()
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        print(f"expected exactly one wheel in {dist_dir}, found {len(wheels)}", file=sys.stderr)
        return 1
    try:
        if venv_root.exists():
            shutil.rmtree(venv_root)
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_root)
    except OSError as exc:
        print(f"could not create clean wheel environment: {exc}", file=sys.stderr)
        return 1

    python_path = _venv_python(venv_root)
    clean_env = _venv_environment(venv_root)
    install = _run_internal(
        (
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--no-deps",
            str(wheels[0]),
        ),
        cwd=venv_root.parent,
        env=clean_env,
    )
    if install.returncode != 0:
        print(install.stdout, file=sys.stderr)
        return install.returncode

    probe = (
        "from pathlib import Path; import sys, agent_reliability_arena; "
        "workspace=Path(sys.argv[1]).resolve(); "
        "module=Path(agent_reliability_arena.__file__).resolve(); "
        "assert module != workspace and workspace not in module.parents, "
        "f'wheel import resolved into workspace: {module}'; print(module)"
    )
    imported = _run_internal(
        (str(python_path), "-c", probe, str(workspace)),
        cwd=venv_root.parent,
        env=clean_env,
    )
    if imported.returncode != 0:
        print(imported.stdout, file=sys.stderr)
        return imported.returncode

    source_tests = _run_internal(
        (
            str(python_path),
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ),
        cwd=workspace,
        timeout_seconds=1500,
        env=clean_env,
    )
    if source_tests.returncode != 0:
        print(source_tests.stdout, file=sys.stderr)
        return source_tests.returncode

    release_code = _run_internal_batch(
        _release_commands(str(python_path)),
        cwd=workspace,
        env=clean_env,
    )
    if release_code != 0:
        return release_code

    names = (
        "arena-run",
        "arena-replay",
        "arena-export-web",
        "arena-verify-showcase",
        "arena-verify-launch-package",
        "arena-verify-citation-package",
        "arena-verify-supply-chain",
    )
    executables: dict[str, str] = {}
    for name in names:
        executable = _venv_command(venv_root, name)
        if not executable.is_file():
            print(f"installed command missing: {executable}", file=sys.stderr)
            return 1
        executables[name] = str(executable)

    smoke_root = venv_root.parent / "wheel-smoke"
    if smoke_root.exists():
        print(f"temporary smoke output collision: {smoke_root}", file=sys.stderr)
        return 1
    smoke_root.mkdir(parents=True)
    smoke_code = _run_internal_batch(
        _smoke_commands(temp_root=smoke_root, executable_by_name=executables),
        cwd=workspace,
        env=clean_env,
    )
    if smoke_code != 0:
        return smoke_code

    return 0


def _internal_dependency_check(venv_root: Path) -> int:
    python_path = _venv_python(venv_root.resolve())
    if not python_path.is_file():
        print(f"clean wheel environment missing: {python_path}", file=sys.stderr)
        return 1
    checked = _run_internal(
        (str(python_path), "-m", "pip", "check"),
        cwd=venv_root.parent,
        env=_venv_environment(venv_root.resolve()),
    )
    if checked.returncode != 0:
        print(checked.stdout, file=sys.stderr)
    return checked.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic local checks before opening a pull request."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--internal-verify-wheel", action="store_true")
    parser.add_argument("--internal-dependency-check", action="store_true")
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--venv", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.internal_verify_wheel and args.internal_dependency_check:
        parser.error("internal helper modes are mutually exclusive")
    if args.internal_verify_wheel:
        if args.dist_dir is None or args.workspace is None or args.venv is None:
            parser.error("wheel verification requires --dist-dir, --workspace and --venv")
        return _internal_verify_wheel(args.dist_dir, args.workspace, args.venv)
    if args.internal_dependency_check:
        if args.venv is None:
            parser.error("dependency verification requires --venv")
        return _internal_dependency_check(args.venv)
    if args.report is None:
        parser.error("--report is required")

    try:
        root = args.root.resolve()
        validate_repository_root(root)
        with tempfile.TemporaryDirectory(prefix="arena-pre-pr-") as raw_temp:
            temp_root = Path(raw_temp).resolve()
            specs = default_check_specs(temp_root=temp_root)
            replacements = (
                (str(temp_root), "<TEMP>"),
                (str(root), "<ROOT>"),
            )
            code, report = run_gate(
                specs,
                cwd=root,
                env=_stable_environment(),
                replacements=replacements,
            )
            write_report_atomic(args.report, report)
    except (GateConfigurationError, GateInternalError) as exc:
        print(f"pre-PR gate internal error: {exc}", file=sys.stderr)
        return 2

    print(
        f"pre-PR gate: {report['status']} "
        f"({report['checks_passed']}/{report['checks_run']} checks passed, "
        f"failures={report['pre_pr_failures']})"
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
