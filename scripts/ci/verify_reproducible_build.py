from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


class ReproducibilityError(ValueError):
    """Raised when a wheel cannot be treated as a safe reproducibility input."""


@dataclass(frozen=True)
class WheelComparison:
    equal: bool
    left_digest: str
    right_digest: str
    diff: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member_name(name: str) -> str:
    if not name or "\\" in name:
        raise ReproducibilityError(f"unsafe wheel member: {name!r}")
    pure = PurePosixPath(name)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ReproducibilityError(f"unsafe wheel member: {name!r}")
    return pure.as_posix()


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    if info.create_system != 3:
        return False
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _normalized_record_rows(data: bytes, *, member: str) -> list[list[str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReproducibilityError(f"RECORD is not UTF-8: {member}") from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    rows: list[list[str]] = []
    for row in reader:
        if len(row) != 3:
            raise ReproducibilityError(f"invalid RECORD row in {member}: {row!r}")
        rows.append([str(value) for value in row])
    rows.sort(key=lambda row: tuple(row))
    return rows


def normalized_wheel_manifest(path: Path) -> dict[str, dict[str, object]]:
    if not path.is_file():
        raise ReproducibilityError(f"wheel does not exist: {path}")
    manifest: dict[str, dict[str, object]] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name = _safe_member_name(info.filename)
                if name in manifest:
                    raise ReproducibilityError(f"duplicate wheel member: {name}")
                if info.is_dir():
                    manifest[name] = {"kind": "directory"}
                    continue
                if _is_symlink(info):
                    raise ReproducibilityError(f"symlink wheel member is not allowed: {name}")
                data = archive.read(info)
                if name.endswith(".dist-info/RECORD"):
                    rows = _normalized_record_rows(data, member=name)
                    manifest[name] = {
                        "kind": "record",
                        "rows": rows,
                        "sha256": _sha256(
                            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
                        ),
                    }
                else:
                    manifest[name] = {
                        "kind": "file",
                        "size": len(data),
                        "sha256": _sha256(data),
                    }
    except zipfile.BadZipFile as exc:
        raise ReproducibilityError(f"invalid wheel ZIP: {path}: {exc}") from exc
    return dict(sorted(manifest.items()))


def _manifest_digest(manifest: Mapping[str, Mapping[str, object]]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256(payload)


def compare_wheels(left: Path, right: Path) -> WheelComparison:
    left_manifest = normalized_wheel_manifest(left)
    right_manifest = normalized_wheel_manifest(right)
    left_digest = _manifest_digest(left_manifest)
    right_digest = _manifest_digest(right_manifest)
    if left_manifest == right_manifest:
        return WheelComparison(True, left_digest, right_digest, "")
    paths = sorted(set(left_manifest) | set(right_manifest))
    differences: list[str] = []
    for name in paths:
        if name not in left_manifest:
            differences.append(f"+ {name}: only in right wheel")
        elif name not in right_manifest:
            differences.append(f"- {name}: only in left wheel")
        elif left_manifest[name] != right_manifest[name]:
            differences.append(
                f"~ {name}: left={json.dumps(left_manifest[name], sort_keys=True)} "
                f"right={json.dumps(right_manifest[name], sort_keys=True)}"
            )
    return WheelComparison(False, left_digest, right_digest, "\n".join(differences))


def _controlled_build_environment(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        upper = key.upper()
        if any(fragment in upper for fragment in ("API_KEY", "TOKEN", "PASSWORD", "SECRET")):
            env.pop(key, None)
    home = root / "home"
    temp = root / "tmp"
    cache = root / "cache"
    for path in (home, temp, cache):
        path.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "HOME": str(home),
            "TMPDIR": str(temp),
            "TEMP": str(temp),
            "TMP": str(temp),
            "PIP_CACHE_DIR": str(cache),
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": env.get("SOURCE_DATE_EPOCH", "315532800"),
            "TZ": "UTC",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        }
    )
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    return env


def _build_once(*, workspace: Path, root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    wheel_dir = root / "dist"
    wheel_dir.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        cwd=workspace,
        env=_controlled_build_environment(root),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=900,
    )
    (root / "build.log").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise ReproducibilityError(
            f"wheel build failed with exit code {completed.returncode}; see {root / 'build.log'}"
        )
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise ReproducibilityError(f"expected exactly one wheel in {wheel_dir}, found {len(wheels)}")
    return wheels[0]


def build_and_compare(*, workspace: Path, work_root: Path) -> dict[str, object]:
    workspace = workspace.resolve()
    work_root = work_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    first = _build_once(workspace=workspace, root=work_root / "build-a")
    second = _build_once(workspace=workspace, root=work_root / "build-b")
    result = compare_wheels(first, second)
    return {
        "status": "passed" if result.equal else "failed",
        "left_wheel": first.name,
        "right_wheel": second.name,
        "left_digest": result.left_digest,
        "right_digest": result.right_digest,
        "diff": result.diff,
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the project twice and compare normalized wheel contents.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_and_compare(workspace=args.workspace, work_root=args.work_root)
    except Exception as exc:
        report = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
