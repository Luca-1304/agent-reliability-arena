from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Mapping, Sequence


class ConcurrencyIsolationError(RuntimeError):
    """Raised when two supposedly isolated runs share mutable state."""


_SECRET_FRAGMENTS = ("API_KEY", "TOKEN", "PASSWORD", "SECRET")


def build_run_environment(*, base: Mapping[str, str], root: Path, hash_seed: int) -> dict[str, str]:
    if hash_seed < 0:
        raise ConcurrencyIsolationError("hash_seed must be non-negative")
    root = root.resolve()
    home = root / "home"
    temp = root / "tmp"
    pip_cache = root / "pip-cache"
    xdg_cache = root / "xdg-cache"
    for path in (home, temp, pip_cache, xdg_cache):
        path.mkdir(parents=True, exist_ok=True)
    env = {
        key: value
        for key, value in base.items()
        if not any(fragment in key.upper() for fragment in _SECRET_FRAGMENTS)
        and key not in {"PYTHONPATH", "VIRTUAL_ENV", "HOME", "TMPDIR", "TEMP", "TMP", "PIP_CACHE_DIR", "XDG_CACHE_HOME"}
    }
    env.update(
        {
            "HOME": str(home),
            "TMPDIR": str(temp),
            "TEMP": str(temp),
            "TMP": str(temp),
            "PIP_CACHE_DIR": str(pip_cache),
            "XDG_CACHE_HOME": str(xdg_cache),
            "PYTHONHASHSEED": str(hash_seed),
            "PYTHONDONTWRITEBYTECODE": "1",
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "ARENA_RELIABILITY_STABLE_OUTPUT": "1",
        }
    )
    return env


def _file_identity(path: Path) -> tuple[int, int] | None:
    try:
        result = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(result.st_mode):
        return None
    return (result.st_dev, result.st_ino)


def assert_disjoint_artifact_trees(left: Path, right: Path) -> None:
    left = left.resolve()
    right = right.resolve()
    if left == right:
        raise ConcurrencyIsolationError("run roots are identical")
    if left in right.parents or right in left.parents:
        raise ConcurrencyIsolationError("run roots are nested")

    identities: dict[tuple[int, int], Path] = {}
    for root, other in ((left, right), (right, left)):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_symlink():
                target = path.resolve(strict=False)
                if target == other or other in target.parents:
                    raise ConcurrencyIsolationError(
                        f"cross-run symlink detected: {path} -> {target}"
                    )
                continue
            identity = _file_identity(path)
            if identity is None:
                continue
            existing = identities.get(identity)
            if existing is not None and existing.resolve() != path.resolve():
                raise ConcurrencyIsolationError(
                    f"shared file identity detected: {existing} and {path}"
                )
            identities[identity] = path


def _run_one(*, executable: Path, config: Path, root: Path, hash_seed: int) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    output = root / "artifacts"
    env = build_run_environment(base=os.environ, root=root, hash_seed=hash_seed)
    completed = subprocess.run(
        [str(executable), "--config", str(config), "--output", str(output)],
        cwd=root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=300,
    )
    (root / "run.log").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise ConcurrencyIsolationError(
            f"concurrent run seed {hash_seed} failed with {completed.returncode}: {completed.stdout[-2000:]}"
        )
    payload = json.loads(completed.stdout)
    return {"seed": hash_seed, "output": output, "payload": payload}


def verify_concurrent_runs(*, executable: Path, config: Path, root: Path) -> dict[str, object]:
    root = root.resolve()
    run_a = root / "run-a"
    run_b = root / "run-b"
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(_run_one, executable=executable, config=config, root=run_a, hash_seed=3)
        future_b = executor.submit(_run_one, executable=executable, config=config, root=run_b, hash_seed=11)
        result_a = future_a.result()
        result_b = future_b.result()
    assert_disjoint_artifact_trees(run_a, run_b)
    if result_a["output"] == result_b["output"]:
        raise ConcurrencyIsolationError("concurrent runs reported the same output path")
    return {
        "status": "passed",
        "runs": [
            {"seed": result_a["seed"], "output": str(Path(result_a["output"]).relative_to(root))},
            {"seed": result_b["seed"], "output": str(Path(result_b["output"]).relative_to(root))},
        ],
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run two independent Arena executions concurrently and check isolation.")
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = verify_concurrent_runs(executable=args.executable, config=args.config, root=args.root)
    except Exception as exc:
        report = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
