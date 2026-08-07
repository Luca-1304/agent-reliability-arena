from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class DiagnosticRedactionError(RuntimeError):
    """Raised when diagnostic metadata cannot be sanitised safely."""


@dataclass(frozen=True)
class RedactionReport:
    scanned_files: int
    changed_files: int
    replacements: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "schema_version": "diagnostic-redaction-v1",
            "status": "passed",
            "scanned_files": self.scanned_files,
            "changed_files": self.changed_files,
            "replacements": self.replacements,
        }


_ROOT_METADATA = {
    "bootstrap-environment.txt",
    "bootstrap-tools.log",
    "bootstrap-editable.log",
    "events.jsonl",
    "summary.json",
    "summary.md",
    "manifest.json",
    "dependencies.json",
    "toolchain.json",
}


def _workspace_markers(workspace: Path) -> tuple[str, ...]:
    raw = str(workspace)
    markers = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}
    try:
        resolved = str(workspace.resolve())
    except OSError:
        resolved = raw
    markers.update({resolved, resolved.replace("\\", "/"), resolved.replace("/", "\\")})
    return tuple(
        sorted(
            (marker for marker in markers if marker and marker not in {".", "/"}),
            key=len,
            reverse=True,
        )
    )


def _is_metadata_path(relative: Path) -> bool:
    if len(relative.parts) == 1 and relative.name in _ROOT_METADATA:
        return True
    parts = relative.parts
    if len(parts) == 4 and parts[0] == "passes" and parts[2] == "commands" and relative.suffix == ".log":
        return True
    if len(parts) == 3 and parts[0] == "passes" and parts[2] == "pass.json":
        return True
    return False


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.redact-{os.getpid()}")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def redact_metadata_tree(root: Path, *, workspace: Path) -> RedactionReport:
    root = root.resolve(strict=False)
    if not root.exists() or not root.is_dir():
        raise DiagnosticRedactionError("diagnostic root is missing or not a directory")
    markers = _workspace_markers(workspace)
    scanned_files = 0
    changed_files = 0
    replacements = 0

    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise DiagnosticRedactionError("symbolic links are prohibited in diagnostic evidence")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if not _is_metadata_path(relative):
            continue
        scanned_files += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise DiagnosticRedactionError(
                f"diagnostic metadata is not readable UTF-8: {relative.as_posix()}"
            ) from exc
        updated = text
        file_replacements = 0
        for marker in markers:
            count = updated.count(marker)
            if count:
                updated = updated.replace(marker, "<workspace>")
                file_replacements += count
        if file_replacements:
            _atomic_write_text(path, updated)
            changed_files += 1
            replacements += file_replacements

    return RedactionReport(
        scanned_files=scanned_files,
        changed_files=changed_files,
        replacements=replacements,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Redact absolute workspace paths from diagnostic metadata before scanning/publication."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = redact_metadata_tree(args.root, workspace=args.workspace)
        payload: dict[str, object] = report.to_dict()
        return_code = 0
    except Exception as exc:
        payload = {
            "schema_version": "diagnostic-redaction-v1",
            "status": "failed",
            "error": f"{type(exc).__name__}; detail=<redacted>",
        }
        return_code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
