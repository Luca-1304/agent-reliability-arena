from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence


class CleanRoomError(RuntimeError):
    """Raised when packaged execution is not isolated from the source workspace."""


_SECRET_FRAGMENTS = ("API_KEY", "TOKEN", "PASSWORD", "SECRET")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _filtered_path(value: str, workspace: Path) -> str:
    parts = []
    for item in value.split(os.pathsep):
        if not item:
            continue
        candidate = Path(item)
        if _inside(candidate, workspace):
            continue
        parts.append(item)
    return os.pathsep.join(parts)


def build_clean_room_environment(*, base: Mapping[str, str], workspace: Path, root: Path) -> dict[str, str]:
    workspace = workspace.resolve()
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    home = root / "home"
    temp = root / "tmp"
    pip_cache = root / "pip-cache"
    xdg_cache = root / "xdg-cache"
    for path in (home, temp, pip_cache, xdg_cache):
        path.mkdir(parents=True, exist_ok=True)

    env: dict[str, str] = {}
    path_value = base.get("PATH", os.defpath)
    env["PATH"] = _filtered_path(path_value, workspace)
    for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
        value = base.get(key)
        if value and str(workspace) not in value:
            env[key] = value
    env.update(
        {
            "HOME": str(home),
            "TMPDIR": str(temp),
            "TEMP": str(temp),
            "TMP": str(temp),
            "PIP_CACHE_DIR": str(pip_cache),
            "XDG_CACHE_HOME": str(xdg_cache),
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "SOURCE_DATE_EPOCH": base.get("SOURCE_DATE_EPOCH", "315532800"),
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "ARENA_RELIABILITY_STABLE_OUTPUT": "1",
        }
    )
    for key, value in env.items():
        if any(fragment in key.upper() for fragment in _SECRET_FRAGMENTS):
            raise CleanRoomError(f"secret-bearing variable leaked into clean room: {key}")
        if str(workspace) in value:
            raise CleanRoomError(f"workspace path leaked into clean-room environment variable {key}")
    return env


def assert_package_outside_workspace(module_file: Path, workspace: Path) -> None:
    resolved = module_file.resolve()
    workspace = workspace.resolve()
    if _inside(resolved, workspace):
        raise CleanRoomError(f"installed package resolved inside workspace: {resolved}")


def _run(argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: int = 300) -> str:
    completed = subprocess.run(
        [str(value) for value in argv],
        cwd=cwd,
        env=dict(env),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise CleanRoomError(
            f"command failed ({completed.returncode}): {' '.join(map(str, argv))}\n{completed.stdout[-4000:]}"
        )
    return completed.stdout


def verify_clean_room(*, wheel: Path, config: Path, workspace: Path, root: Path) -> dict[str, object]:
    wheel = wheel.resolve()
    config = config.resolve()
    workspace = workspace.resolve()
    root = root.resolve()
    if _inside(wheel, workspace):
        staged_wheel_dir = root / "input"
        staged_wheel_dir.mkdir(parents=True, exist_ok=True)
        staged_wheel = staged_wheel_dir / wheel.name
        shutil.copy2(wheel, staged_wheel)
        wheel = staged_wheel
    staged_config = root / "fixture.json"
    staged_config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config, staged_config)

    env = build_clean_room_environment(base=os.environ, workspace=workspace, root=root)
    venv = root / "venv"
    _run([sys.executable, "-m", "venv", str(venv)], cwd=root, env=env, timeout=300)
    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    python = bin_dir / ("python.exe" if os.name == "nt" else "python")
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    _run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], cwd=root, env=env, timeout=300)
    _run([str(python), "-m", "pip", "check"], cwd=root, env=env, timeout=120)

    module_path_text = _run(
        [str(python), "-c", "import agent_reliability_arena as p; print(p.__file__)"],
        cwd=root,
        env=env,
        timeout=60,
    ).strip().splitlines()[-1]
    module_path = Path(module_path_text)
    assert_package_outside_workspace(module_path, workspace)

    artifacts = root / "artifacts"
    replay_json = root / "replay.json"
    public_json = root / "public.json"
    _run([str(bin_dir / "arena-run"), "--config", str(staged_config), "--output", str(artifacts)], cwd=root, env=env)
    replay = _run([str(bin_dir / "arena-replay"), "--input", str(artifacts)], cwd=root, env=env)
    replay_json.write_text(replay, encoding="utf-8")
    export = _run(
        [str(bin_dir / "arena-export-web"), "--input", str(artifacts), "--output", str(public_json)],
        cwd=root,
        env=env,
    )
    if not public_json.is_file():
        raise CleanRoomError("arena-export-web did not create the requested public export")
    json.loads(replay_json.read_text(encoding="utf-8"))
    json.loads(public_json.read_text(encoding="utf-8"))
    return {
        "status": "passed",
        "module_path": str(module_path.relative_to(root) if _inside(module_path, root) else module_path),
        "artifacts": str(artifacts.relative_to(root)),
        "public_export": str(public_json.relative_to(root)),
        "export_command": json.loads(export),
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a wheel from a cold clean-room installation.")
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = verify_clean_room(wheel=args.wheel, config=args.config, workspace=args.workspace, root=args.root)
    except Exception as exc:
        report = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
