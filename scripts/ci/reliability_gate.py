from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "reliability-gate-v2"
SOURCE_DATE_EPOCH = "315532800"
DEFAULT_TIMEOUT_SECONDS = 900
VERIFIER_SCRIPTS = (
    "verify_release.py",
    "verify_disclosure_release.py",
    "verify_repeated_release.py",
    "verify_showcase_release.py",
    "verify_launch_package.py",
    "verify_citation_package.py",
    "verify_supply_chain.py",
)
SENSITIVE_ENV_SUFFIXES = ("_API_KEY", "_SECRET", "_TOKEN", "_PASSWORD")
SENSITIVE_ENV_NAMES = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GITHUB_TOKEN",
    "GH_TOKEN",
}


class FailureRecord:
    def __init__(
        self,
        *,
        category: str,
        phase: str,
        command_name: str,
        argv: Sequence[str],
        pass_number: int,
        hash_seed: int,
        exit_code: int,
        duration_seconds: float,
        log_path: str,
        message: str,
    ) -> None:
        self.category = category
        self.phase = phase
        self.command_name = command_name
        self.argv = list(argv)
        self.pass_number = pass_number
        self.hash_seed = hash_seed
        self.exit_code = exit_code
        self.duration_seconds = duration_seconds
        self.log_path = log_path
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "category": self.category,
            "command_name": self.command_name,
            "duration_seconds": round(float(self.duration_seconds), 6),
            "exit_code": int(self.exit_code),
            "hash_seed": int(self.hash_seed),
            "log_path": self.log_path,
            "message": self.message,
            "pass_number": int(self.pass_number),
            "phase": self.phase,
        }


class GateFailure(RuntimeError):
    def __init__(self, message: str, record: FailureRecord | None = None) -> None:
        super().__init__(message)
        self.record = record


class CommandSpec:
    def __init__(
        self,
        *,
        name: str,
        phase: str,
        category: str,
        argv: Sequence[str],
        stdout_json_path: Path | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.name = name
        self.phase = phase
        self.category = category
        self.argv = [str(value) for value in argv]
        self.stdout_json_path = stdout_json_path
        self.timeout_seconds = timeout_seconds


class CommandResult:
    def __init__(
        self,
        *,
        name: str,
        argv: Sequence[str],
        exit_code: int,
        duration_seconds: float,
        log_path: Path,
    ) -> None:
        self.name = name
        self.argv = list(argv)
        self.exit_code = exit_code
        self.duration_seconds = duration_seconds
        self.log_path = log_path

    def to_dict(self, diagnostics_dir: Path) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "duration_seconds": round(self.duration_seconds, 6),
            "exit_code": self.exit_code,
            "log_path": self.log_path.relative_to(diagnostics_dir).as_posix(),
            "name": self.name,
        }


class CommandContext:
    def __init__(
        self,
        *,
        workspace: Path,
        diagnostics_dir: Path,
        pass_dir: Path,
        environment: Mapping[str, str],
        events_path: Path,
        python_label: str,
        pass_number: int,
    ) -> None:
        self.workspace = workspace
        self.diagnostics_dir = diagnostics_dir
        self.pass_dir = pass_dir
        self.environment = dict(environment)
        self.events_path = events_path
        self.python_label = python_label
        self.pass_number = pass_number
        self.hash_seed = pass_number - 1
        self.command_index = 0
        self.command_results: list[CommandResult] = []


class GateConfig:
    def __init__(
        self,
        *,
        passes: int,
        python_label: str,
        workspace: Path,
        work_root: Path,
        diagnostics_dir: Path,
    ) -> None:
        self.passes = passes
        self.python_label = python_label
        self.workspace = workspace
        self.work_root = work_root
        self.diagnostics_dir = diagnostics_dir


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_bytes(payload: object, *, pretty: bool) -> bytes:
    if pretty:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    else:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
    return (text + "\n").encode("utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(_json_bytes(payload, pretty=True))
    os.replace(temporary, path)


def append_event(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_json_bytes(dict(payload), pretty=False).decode("utf-8"))


def canonical_digest(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise GateFailure(f"refusing to digest symbolic link: {path}")
    if not path.is_file():
        raise GateFailure(f"missing file required for digest: {path}")
    raw = path.read_bytes()
    kind = "bytes"
    canonical = raw
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw.decode("utf-8"))
            canonical = _json_bytes(payload, pretty=False)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise GateFailure(f"malformed JSON evidence {path}: {exc}") from exc
        kind = "json"
    return {
        "kind": kind,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "size": len(canonical),
    }


def tree_manifest(root: Path) -> dict[str, dict[str, object]]:
    if not root.is_dir():
        raise GateFailure(f"missing directory required for manifest: {root}")
    entries: dict[str, dict[str, object]] = {}
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        if path.is_symlink():
            raise GateFailure(f"symbolic links are not permitted in evidence trees: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            entries[relative] = canonical_digest(path)
    return entries


def compare_manifest(
    expected: Mapping[str, Mapping[str, object]],
    actual: Mapping[str, Mapping[str, object]],
    *,
    label: str,
) -> None:
    expected_keys = set(expected)
    actual_keys = set(actual)
    missing = sorted(expected_keys - actual_keys)
    unexpected = sorted(actual_keys - expected_keys)
    changed = sorted(
        key for key in expected_keys & actual_keys if dict(expected[key]) != dict(actual[key])
    )
    if missing or unexpected or changed:
        details = [f"{label} mismatch"]
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        if changed:
            details.append(f"changed={changed}")
        raise GateFailure("; ".join(details))


def build_pass_environment(
    base: Mapping[str, str],
    *,
    pass_number: int,
    pass_root: Path,
) -> dict[str, str]:
    if pass_number < 1:
        raise ValueError("pass_number must be at least 1")
    environment = {str(key): str(value) for key, value in base.items()}
    for key in list(environment):
        upper = key.upper()
        if upper in SENSITIVE_ENV_NAMES or upper.endswith(SENSITIVE_ENV_SUFFIXES):
            environment.pop(key, None)

    home = pass_root / "home"
    temporary = pass_root / "tmp"
    cache = pass_root / "cache"
    pip_cache = cache / "pip"
    for directory in (home, temporary, cache, pip_cache):
        directory.mkdir(parents=True, exist_ok=True)

    environment.update(
        {
            "CI": "1",
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NO_COLOR": "1",
            "PIP_CACHE_DIR": str(pip_cache),
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": str(pass_number - 1),
            "PYTHONUNBUFFERED": "1",
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
            "TEMP": str(temporary),
            "TZ": "UTC",
            "XDG_CACHE_HOME": str(cache),
        }
    )
    return environment


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _write_command_log(
    path: Path,
    *,
    spec: CommandSpec,
    cwd: Path,
    stdout: str,
    stderr: str,
    exit_code: int,
    duration_seconds: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "argv": spec.argv,
        "command_name": spec.name,
        "cwd": str(cwd),
        "duration_seconds": round(duration_seconds, 6),
        "exit_code": exit_code,
        "phase": spec.phase,
    }
    text = [
        "=== metadata ===",
        json.dumps(payload, indent=2, sort_keys=True),
        "",
        "=== stdout ===",
        stdout,
        "",
        "=== stderr ===",
        stderr,
        "",
    ]
    path.write_text("\n".join(text), encoding="utf-8", newline="\n")


def _failure_from_command(
    *,
    context: CommandContext,
    spec: CommandSpec,
    exit_code: int,
    duration_seconds: float,
    log_path: Path,
    message: str,
) -> GateFailure:
    record = FailureRecord(
        category=spec.category,
        phase=spec.phase,
        command_name=spec.name,
        argv=spec.argv,
        pass_number=context.pass_number,
        hash_seed=context.hash_seed,
        exit_code=exit_code,
        duration_seconds=duration_seconds,
        log_path=_relative(log_path, context.diagnostics_dir),
        message=message,
    )
    return GateFailure(message, record)


def run_command(spec: CommandSpec, context: CommandContext) -> CommandResult:
    context.command_index += 1
    safe_name = "".join(character if character.isalnum() or character in "-_" else "-" for character in spec.name)
    log_path = context.pass_dir / "commands" / f"{context.command_index:02d}-{safe_name}.log"
    started = time.perf_counter()
    append_event(
        context.events_path,
        {
            "argv": spec.argv,
            "command_name": spec.name,
            "event": "command-started",
            "hash_seed": context.hash_seed,
            "pass_number": context.pass_number,
            "phase": spec.phase,
            "python_label": context.python_label,
            "status": "running",
            "timestamp": utc_timestamp(),
        },
    )
    try:
        completed = subprocess.run(
            spec.argv,
            cwd=context.workspace,
            env=context.environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=spec.timeout_seconds,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")
        duration = time.perf_counter() - started
        _write_command_log(
            log_path,
            spec=spec,
            cwd=context.workspace,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_seconds=duration,
        )
        append_event(
            context.events_path,
            {
                "command_name": spec.name,
                "duration_seconds": round(duration, 6),
                "event": "command-finished",
                "exit_code": exit_code,
                "hash_seed": context.hash_seed,
                "log_path": _relative(log_path, context.diagnostics_dir),
                "pass_number": context.pass_number,
                "phase": spec.phase,
                "python_label": context.python_label,
                "status": "timeout",
                "timestamp": utc_timestamp(),
            },
        )
        raise _failure_from_command(
            context=context,
            spec=spec,
            exit_code=exit_code,
            duration_seconds=duration,
            log_path=log_path,
            message=f"command timed out after {spec.timeout_seconds}s: {spec.name}",
        )
    except OSError as exc:
        exit_code = 127
        duration = time.perf_counter() - started
        stdout = ""
        stderr = str(exc)
        _write_command_log(
            log_path,
            spec=spec,
            cwd=context.workspace,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_seconds=duration,
        )
        raise _failure_from_command(
            context=context,
            spec=spec,
            exit_code=exit_code,
            duration_seconds=duration,
            log_path=log_path,
            message=f"unable to execute {spec.name}: {exc}",
        ) from exc

    duration = time.perf_counter() - started
    _write_command_log(
        log_path,
        spec=spec,
        cwd=context.workspace,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_seconds=duration,
    )
    status = "passed" if exit_code == 0 else "failed"
    append_event(
        context.events_path,
        {
            "command_name": spec.name,
            "duration_seconds": round(duration, 6),
            "event": "command-finished",
            "exit_code": exit_code,
            "hash_seed": context.hash_seed,
            "log_path": _relative(log_path, context.diagnostics_dir),
            "pass_number": context.pass_number,
            "phase": spec.phase,
            "python_label": context.python_label,
            "status": status,
            "timestamp": utc_timestamp(),
        },
    )
    if exit_code != 0:
        raise _failure_from_command(
            context=context,
            spec=spec,
            exit_code=exit_code,
            duration_seconds=duration,
            log_path=log_path,
            message=f"command failed with exit code {exit_code}: {spec.name}",
        )

    if spec.stdout_json_path is not None:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise _failure_from_command(
                context=context,
                spec=spec,
                exit_code=0,
                duration_seconds=duration,
                log_path=log_path,
                message=f"command produced malformed JSON: {spec.name}: {exc}",
            ) from exc
        write_json(spec.stdout_json_path, payload)

    result = CommandResult(
        name=spec.name,
        argv=spec.argv,
        exit_code=exit_code,
        duration_seconds=duration,
        log_path=log_path,
    )
    context.command_results.append(result)
    return result


def _git_value(workspace: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=workspace,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _safe_reset_directory(path: Path, *, workspace: Path) -> None:
    resolved = path.resolve()
    workspace_resolved = workspace.resolve()
    if resolved == Path(resolved.anchor) or resolved == workspace_resolved:
        raise GateFailure(f"refusing unsafe disposable directory: {resolved}")
    if resolved in workspace_resolved.parents:
        raise GateFailure(f"refusing to remove workspace ancestor: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _venv_paths(venv_root: Path) -> tuple[Path, Path]:
    bin_directory = venv_root / ("Scripts" if os.name == "nt" else "bin")
    python_name = "python.exe" if os.name == "nt" else "python"
    return bin_directory, bin_directory / python_name


def _comparison_failure(
    *,
    context: CommandContext,
    category: str,
    phase: str,
    name: str,
    message: str,
) -> GateFailure:
    record = FailureRecord(
        category=category,
        phase=phase,
        command_name=name,
        argv=[],
        pass_number=context.pass_number,
        hash_seed=context.hash_seed,
        exit_code=1,
        duration_seconds=0.0,
        log_path="",
        message=message,
    )
    return GateFailure(message, record)


def _run_json_command(
    context: CommandContext,
    *,
    name: str,
    phase: str,
    category: str,
    argv: Sequence[str],
    output_path: Path,
) -> None:
    run_command(
        CommandSpec(
            name=name,
            phase=phase,
            category=category,
            argv=argv,
            stdout_json_path=output_path,
        ),
        context,
    )


def _copy_json(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise GateFailure(f"expected JSON output was not created: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateFailure(f"generated output is not valid JSON: {source}: {exc}") from exc
    write_json(destination, payload)


def _run_verifiers(
    context: CommandContext,
    *,
    python: Path,
    prefix: str,
    phase: str,
    category: str,
    outputs_dir: Path,
) -> None:
    for script in VERIFIER_SCRIPTS:
        stem = Path(script).stem
        _run_json_command(
            context,
            name=f"{prefix}-{stem}",
            phase=phase,
            category=category,
            argv=[str(python), str(context.workspace / "scripts" / script)],
            output_path=outputs_dir / f"{prefix}-{stem}.json",
        )


def _run_cli_contract(
    context: CommandContext,
    *,
    bin_directory: Path | None,
    prefix: str,
    phase: str,
    category: str,
    artifact_root: Path,
    outputs_dir: Path,
) -> None:
    def executable(name: str) -> str:
        if bin_directory is None:
            resolved = shutil.which(name, path=context.environment.get("PATH"))
            if resolved is None:
                return name
            return resolved
        suffix = ".exe" if os.name == "nt" else ""
        return str(bin_directory / f"{name}{suffix}")

    fixture = context.workspace / "examples" / "fixture_experiment.json"
    public_output = artifact_root.parent / f"{prefix}-public.json"
    _run_json_command(
        context,
        name=f"{prefix}-run",
        phase=phase,
        category=category,
        argv=[executable("arena-run"), "--config", str(fixture), "--output", str(artifact_root)],
        output_path=outputs_dir / f"{prefix}-run.json",
    )
    _run_json_command(
        context,
        name=f"{prefix}-replay",
        phase=phase,
        category=category,
        argv=[executable("arena-replay"), "--input", str(artifact_root)],
        output_path=outputs_dir / f"{prefix}-replay.json",
    )
    _run_json_command(
        context,
        name=f"{prefix}-export-web",
        phase=phase,
        category=category,
        argv=[
            executable("arena-export-web"),
            "--input",
            str(artifact_root),
            "--output",
            str(public_output),
        ],
        output_path=outputs_dir / f"{prefix}-export-web-command.json",
    )
    _copy_json(public_output, outputs_dir / f"{prefix}-public.json")
    for executable_name, output_name in (
        ("arena-verify-showcase", "showcase"),
        ("arena-verify-launch-package", "launch"),
        ("arena-verify-citation-package", "citation"),
        ("arena-verify-supply-chain", "supply-chain"),
    ):
        _run_json_command(
            context,
            name=f"{prefix}-{output_name}",
            phase=phase,
            category=category,
            argv=[executable(executable_name), "--root", str(context.workspace)],
            output_path=outputs_dir / f"{prefix}-{output_name}.json",
        )


def _prefixed_manifest(outputs_dir: Path, prefix: str) -> dict[str, dict[str, object]]:
    manifest: dict[str, dict[str, object]] = {}
    marker = f"{prefix}-"
    for path in sorted(outputs_dir.glob(f"{prefix}-*.json")):
        logical_name = path.name[len(marker) :]
        manifest[logical_name] = canonical_digest(path)
    return manifest


def _aggregate_digest(manifest: Mapping[str, Mapping[str, object]]) -> str:
    canonical = _json_bytes(dict(manifest), pretty=False)
    return hashlib.sha256(canonical).hexdigest()


def run_pass(
    config: GateConfig,
    *,
    pass_number: int,
    events_path: Path,
    baseline_manifest: Mapping[str, Mapping[str, object]] | None,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    pass_started = time.perf_counter()
    pass_name = f"{pass_number:02d}"
    pass_work = config.work_root / "passes" / pass_name
    pass_dir = config.diagnostics_dir / "passes" / pass_name
    _safe_reset_directory(pass_work, workspace=config.workspace)
    _safe_reset_directory(pass_dir, workspace=config.workspace)
    outputs_dir = pass_dir / "outputs"
    manifests_dir = pass_dir / "manifests"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    environment = build_pass_environment(os.environ, pass_number=pass_number, pass_root=pass_work)
    context = CommandContext(
        workspace=config.workspace,
        diagnostics_dir=config.diagnostics_dir,
        pass_dir=pass_dir,
        environment=environment,
        events_path=events_path,
        python_label=config.python_label,
        pass_number=pass_number,
    )
    append_event(
        events_path,
        {
            "event": "pass-started",
            "hash_seed": context.hash_seed,
            "pass_number": pass_number,
            "python_label": config.python_label,
            "status": "running",
            "timestamp": utc_timestamp(),
        },
    )

    editable_artifacts = pass_work / "editable-artifacts"
    wheel_artifacts = pass_work / "wheel-artifacts"
    wheel_env = pass_work / "wheel-environment"
    dist_dir = pass_work / "dist"

    run_command(
        CommandSpec(
            name="compile-source",
            phase="source-integrity",
            category="compile",
            argv=[sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts"],
        ),
        context,
    )
    run_command(
        CommandSpec(
            name="editable-tests",
            phase="source-integrity",
            category="editable-tests",
            argv=[sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        ),
        context,
    )
    _run_verifiers(
        context,
        python=Path(sys.executable),
        prefix="editable",
        phase="repository-verifiers",
        category="repository-verifier",
        outputs_dir=outputs_dir,
    )
    _run_cli_contract(
        context,
        bin_directory=None,
        prefix="editable",
        phase="editable-cli-contract",
        category="editable-cli",
        artifact_root=editable_artifacts,
        outputs_dir=outputs_dir,
    )

    dist_dir.mkdir(parents=True, exist_ok=True)
    run_command(
        CommandSpec(
            name="build-wheel",
            phase="wheel-build",
            category="wheel-build",
            argv=[
                sys.executable,
                "-m",
                "pip",
                "wheel",
                str(config.workspace),
                "--disable-pip-version-check",
                "--no-input",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(dist_dir),
            ],
        ),
        context,
    )
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise _comparison_failure(
            context=context,
            category="wheel-build",
            phase="wheel-build",
            name="locate-wheel",
            message=f"expected exactly one wheel, found {len(wheels)}: {[path.name for path in wheels]}",
        )
    wheel_path = wheels[0]
    wheel_digest = canonical_digest(wheel_path)
    write_json(manifests_dir / "wheel.json", {"filename": wheel_path.name, **wheel_digest})

    run_command(
        CommandSpec(
            name="create-wheel-environment",
            phase="wheel-install",
            category="wheel-install",
            argv=[sys.executable, "-m", "venv", str(wheel_env)],
        ),
        context,
    )
    wheel_bin, wheel_python = _venv_paths(wheel_env)
    wheel_environment = dict(environment)
    wheel_environment["PATH"] = str(wheel_bin) + os.pathsep + wheel_environment.get("PATH", "")
    context.environment = wheel_environment
    run_command(
        CommandSpec(
            name="install-wheel",
            phase="wheel-install",
            category="wheel-install",
            argv=[
                str(wheel_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--no-deps",
                str(wheel_path),
            ],
        ),
        context,
    )
    run_command(
        CommandSpec(
            name="wheel-tests",
            phase="wheel-test-contract",
            category="wheel-tests",
            argv=[str(wheel_python), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        ),
        context,
    )
    _run_verifiers(
        context,
        python=wheel_python,
        prefix="wheel",
        phase="wheel-verifiers",
        category="wheel-verifier",
        outputs_dir=outputs_dir,
    )
    _run_cli_contract(
        context,
        bin_directory=wheel_bin,
        prefix="wheel",
        phase="wheel-cli-contract",
        category="wheel-cli",
        artifact_root=wheel_artifacts,
        outputs_dir=outputs_dir,
    )
    run_command(
        CommandSpec(
            name="wheel-pip-check",
            phase="dependency-integrity",
            category="dependency-integrity",
            argv=[str(wheel_python), "-m", "pip", "check"],
        ),
        context,
    )
    context.environment = environment
    run_command(
        CommandSpec(
            name="editable-pip-check",
            phase="dependency-integrity",
            category="dependency-integrity",
            argv=[sys.executable, "-m", "pip", "check"],
        ),
        context,
    )

    editable_outputs = _prefixed_manifest(outputs_dir, "editable")
    wheel_outputs = _prefixed_manifest(outputs_dir, "wheel")
    try:
        compare_manifest(editable_outputs, wheel_outputs, label="editable/wheel JSON output parity")
    except GateFailure as exc:
        raise _comparison_failure(
            context=context,
            category="package-parity",
            phase="package-parity",
            name="compare-json-outputs",
            message=str(exc),
        ) from exc
    write_json(manifests_dir / "editable-outputs.json", editable_outputs)
    write_json(manifests_dir / "wheel-outputs.json", wheel_outputs)

    editable_tree = tree_manifest(editable_artifacts)
    wheel_tree = tree_manifest(wheel_artifacts)
    try:
        compare_manifest(editable_tree, wheel_tree, label="editable/wheel artifact-tree parity")
    except GateFailure as exc:
        raise _comparison_failure(
            context=context,
            category="package-parity",
            phase="package-parity",
            name="compare-artifact-trees",
            message=str(exc),
        ) from exc
    write_json(manifests_dir / "editable-artifacts.json", editable_tree)
    write_json(manifests_dir / "wheel-artifacts.json", wheel_tree)

    deterministic_manifest: dict[str, dict[str, object]] = {}
    for name, digest in editable_outputs.items():
        deterministic_manifest[f"outputs/{name}"] = dict(digest)
    for name, digest in editable_tree.items():
        deterministic_manifest[f"artifacts/{name}"] = dict(digest)
    deterministic_manifest["distribution/wheel"] = dict(wheel_digest)
    write_json(manifests_dir / "deterministic-baseline.json", deterministic_manifest)

    if baseline_manifest is not None:
        try:
            compare_manifest(
                baseline_manifest,
                deterministic_manifest,
                label=f"pass 01/pass {pass_name} determinism",
            )
        except GateFailure as exc:
            raise _comparison_failure(
                context=context,
                category="cross-pass-determinism",
                phase="cross-pass-determinism",
                name="compare-pass-baseline",
                message=str(exc),
            ) from exc

    duration = time.perf_counter() - pass_started
    pass_payload = {
        "artifact_files": len(editable_tree),
        "command_count": len(context.command_results),
        "commands": [result.to_dict(config.diagnostics_dir) for result in context.command_results],
        "deterministic_manifest_sha256": _aggregate_digest(deterministic_manifest),
        "duration_seconds": round(duration, 6),
        "hash_seed": context.hash_seed,
        "package_parity": True,
        "pass_number": pass_number,
        "python_label": config.python_label,
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "wheel_sha256": wheel_digest["sha256"],
    }
    write_json(pass_dir / "pass.json", pass_payload)
    append_event(
        events_path,
        {
            "duration_seconds": round(duration, 6),
            "event": "pass-finished",
            "hash_seed": context.hash_seed,
            "pass_number": pass_number,
            "python_label": config.python_label,
            "status": "passed",
            "timestamp": utc_timestamp(),
        },
    )
    shutil.rmtree(wheel_env, ignore_errors=True)
    shutil.rmtree(editable_artifacts, ignore_errors=True)
    shutil.rmtree(wheel_artifacts, ignore_errors=True)
    shutil.rmtree(dist_dir, ignore_errors=True)
    return deterministic_manifest, pass_payload


def _write_summary_markdown(
    path: Path,
    *,
    config: GateConfig,
    status: str,
    completed: Sequence[Mapping[str, object]],
    duration_seconds: float,
    failure: FailureRecord | None,
) -> None:
    lines = [
        f"## Reliability Gate v2 — Python {config.python_label}",
        "",
        f"**Status:** `{status.upper()}`",
        f"**Passes:** `{len(completed)}/{config.passes}`",
        f"**Duration:** `{duration_seconds:.2f}s`",
        "",
        "| Pass | Hash seed | Commands | Parity | Deterministic manifest | Duration |",
        "|---:|---:|---:|:---:|---|---:|",
    ]
    for payload in completed:
        lines.append(
            "| {pass_number} | {hash_seed} | {command_count} | yes | `{digest}` | {duration:.2f}s |".format(
                pass_number=payload["pass_number"],
                hash_seed=payload["hash_seed"],
                command_count=payload["command_count"],
                digest=str(payload["deterministic_manifest_sha256"])[:16],
                duration=float(payload["duration_seconds"]),
            )
        )
    if failure is not None:
        lines.extend(
            [
                "",
                "### Failure",
                "",
                f"- Category: `{failure.category}`",
                f"- Phase: `{failure.phase}`",
                f"- Pass / seed: `{failure.pass_number}` / `{failure.hash_seed}`",
                f"- Command: `{failure.command_name}`",
                f"- Exit code: `{failure.exit_code}`",
                f"- Evidence: `{failure.log_path or 'failure.json'}`",
                f"- Message: {failure.message}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "All requested passes completed with editable/wheel semantic parity and pass-one digest equality.",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def execute(config: GateConfig) -> int:
    started = time.perf_counter()
    _safe_reset_directory(config.diagnostics_dir, workspace=config.workspace)
    _safe_reset_directory(config.work_root, workspace=config.workspace)
    events_path = config.diagnostics_dir / "events.jsonl"
    run_payload = {
        "hash_seeds": list(range(config.passes)),
        "passes_requested": config.passes,
        "policy": {
            "cross_pass_determinism": True,
            "editable_wheel_parity": True,
            "external_network_required": False,
            "provider_execution_permitted": False,
        },
        "python_label": config.python_label,
        "schema_version": SCHEMA_VERSION,
        "started_at": utc_timestamp(),
    }
    write_json(config.diagnostics_dir / "run.json", run_payload)
    environment_payload = {
        "ci": os.environ.get("CI", ""),
        "event_name": os.environ.get("GITHUB_EVENT_NAME", ""),
        "git_commit": _git_value(config.workspace, "rev-parse", "HEAD"),
        "git_status": _git_value(config.workspace, "status", "--porcelain"),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "python_executable": Path(sys.executable).name,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "runner_arch": os.environ.get("RUNNER_ARCH", ""),
        "runner_os": os.environ.get("RUNNER_OS", ""),
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "timezone": "UTC",
    }
    write_json(config.diagnostics_dir / "environment.json", environment_payload)
    append_event(
        events_path,
        {
            "event": "gate-started",
            "passes_requested": config.passes,
            "python_label": config.python_label,
            "status": "running",
            "timestamp": utc_timestamp(),
        },
    )

    completed: list[dict[str, object]] = []
    baseline: dict[str, dict[str, object]] | None = None
    failure_record: FailureRecord | None = None
    status = "failed"
    try:
        for pass_number in range(1, config.passes + 1):
            manifest, pass_payload = run_pass(
                config,
                pass_number=pass_number,
                events_path=events_path,
                baseline_manifest=baseline,
            )
            if baseline is None:
                baseline = manifest
                write_json(config.diagnostics_dir / "baseline.json", baseline)
            completed.append(pass_payload)
        status = "passed"
        return_code = 0
    except GateFailure as exc:
        failure_record = exc.record or FailureRecord(
            category="internal-gate-error",
            phase="internal-gate-error",
            command_name="reliability-gate",
            argv=[],
            pass_number=len(completed) + 1,
            hash_seed=len(completed),
            exit_code=1,
            duration_seconds=0.0,
            log_path="",
            message=str(exc),
        )
        write_json(config.diagnostics_dir / "failure.json", failure_record.to_dict())
        append_event(
            events_path,
            {
                "category": failure_record.category,
                "event": "gate-failed",
                "hash_seed": failure_record.hash_seed,
                "message": failure_record.message,
                "pass_number": failure_record.pass_number,
                "phase": failure_record.phase,
                "python_label": config.python_label,
                "status": "failed",
                "timestamp": utc_timestamp(),
            },
        )
        return_code = 1
    except Exception as exc:  # defensive boundary: preserve unexpected evidence
        internal_log = config.diagnostics_dir / "internal-error.log"
        internal_log.write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        failure_record = FailureRecord(
            category="internal-gate-error",
            phase="internal-gate-error",
            command_name="reliability-gate",
            argv=[],
            pass_number=len(completed) + 1,
            hash_seed=len(completed),
            exit_code=1,
            duration_seconds=0.0,
            log_path=internal_log.relative_to(config.diagnostics_dir).as_posix(),
            message=f"unexpected gate error: {type(exc).__name__}: {exc}",
        )
        write_json(config.diagnostics_dir / "failure.json", failure_record.to_dict())
        return_code = 1

    duration = time.perf_counter() - started
    summary_payload = {
        "completed_passes": len(completed),
        "cross_pass_determinism": status == "passed",
        "duration_seconds": round(duration, 6),
        "failure": failure_record.to_dict() if failure_record else None,
        "package_parity": status == "passed",
        "passes": completed,
        "passes_requested": config.passes,
        "python_label": config.python_label,
        "schema_version": SCHEMA_VERSION,
        "status": status,
    }
    write_json(config.diagnostics_dir / "summary.json", summary_payload)
    _write_summary_markdown(
        config.diagnostics_dir / "summary.md",
        config=config,
        status=status,
        completed=completed,
        duration_seconds=duration,
        failure=failure_record,
    )
    append_event(
        events_path,
        {
            "completed_passes": len(completed),
            "duration_seconds": round(duration, 6),
            "event": "gate-finished",
            "python_label": config.python_label,
            "status": status,
            "timestamp": utc_timestamp(),
        },
    )
    return return_code


def parse_args(argv: Sequence[str] | None = None) -> GateConfig:
    parser = argparse.ArgumentParser(
        description="Run the auditable Agent Reliability Arena repeated verification gate."
    )
    parser.add_argument("--passes", type=int, required=True)
    parser.add_argument("--python-label", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--diagnostics-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.passes <= 100:
        parser.error("--passes must be between 1 and 100")
    workspace = args.workspace.resolve()
    if not (workspace / "pyproject.toml").is_file():
        parser.error("--workspace must contain pyproject.toml")
    work_root = args.work_root.resolve()
    diagnostics_dir = args.diagnostics_dir.resolve()
    if work_root == diagnostics_dir:
        parser.error("--work-root and --diagnostics-dir must be different")
    return GateConfig(
        passes=args.passes,
        python_label=args.python_label,
        workspace=workspace,
        work_root=work_root,
        diagnostics_dir=diagnostics_dir,
    )


def main(argv: Sequence[str] | None = None) -> int:
    return execute(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
