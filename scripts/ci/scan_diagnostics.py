from __future__ import annotations

import argparse
import codecs
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlsplit

try:
    from scripts.ci.reliability_policy import ReliabilityPolicy, load_policy
except ModuleNotFoundError:  # Direct execution from scripts/ci.
    from reliability_policy import ReliabilityPolicy, load_policy  # type: ignore[no-redef]


_DEFAULT_PRIVATE_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0")
_DEFAULT_SECRET_FRAGMENTS = ("api_key", "token", "password", "secret")
_TOKEN_METRIC_SUFFIXES = {
    "usage",
    "count",
    "counts",
    "total",
    "totals",
    "budget",
    "budgets",
    "limit",
    "limits",
    "estimate",
    "estimates",
}
_URL_RE = re.compile(r"https?://[^\s<>'\"`]+", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)\s*(?:=|:)\s*(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
_SCAN_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class ScanFinding:
    source: str
    line: int
    kind: str
    context: str

    @property
    def rendered(self) -> str:
        return f"{self.source}:{self.line}: {self.kind}: {self.context}"

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "line": self.line,
            "kind": self.kind,
            "context": self.context,
        }


@dataclass
class ScanReport:
    findings: list[ScanFinding] = field(default_factory=list)
    scanned_files: int = 0
    skipped_binary_files: int = 0

    @property
    def status(self) -> str:
        return "passed" if not self.findings else "blocked"

    def extend(self, other: "ScanReport") -> None:
        self.findings.extend(other.findings)
        self.scanned_files += other.scanned_files
        self.skipped_binary_files += other.skipped_binary_files

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "diagnostic-scan-v1",
            "status": self.status,
            "finding_count": len(self.findings),
            "scanned_files": self.scanned_files,
            "skipped_binary_files": self.skipped_binary_files,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _normalise_key(value: str) -> str:
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _contains_parts(parts: tuple[str, ...], fragment_parts: tuple[str, ...]) -> bool:
    if not fragment_parts or len(fragment_parts) > len(parts):
        return False
    width = len(fragment_parts)
    return any(parts[index : index + width] == fragment_parts for index in range(len(parts) - width + 1))


def _is_secret_key(key: str, fragments: Iterable[str]) -> bool:
    normalized = _normalise_key(key)
    parts = tuple(part for part in normalized.split("_") if part)
    for fragment in fragments:
        normalized_fragment = _normalise_key(fragment)
        fragment_parts = tuple(part for part in normalized_fragment.split("_") if part)
        if not fragment_parts:
            continue
        if fragment_parts == ("token",):
            for index, part in enumerate(parts):
                if part != "token":
                    continue
                following = parts[index + 1] if index + 1 < len(parts) else None
                if following in _TOKEN_METRIC_SUFFIXES:
                    continue
                return True
            continue
        if _contains_parts(parts, fragment_parts):
            return True
    return False


def _workspace_markers(workspace: Path) -> tuple[str, ...]:
    raw = str(workspace)
    markers = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}
    try:
        resolved = str(workspace.resolve())
    except OSError:
        resolved = raw
    markers.update({resolved, resolved.replace("\\", "/"), resolved.replace("/", "\\")})
    return tuple(
        sorted((item for item in markers if item and item not in {".", "/"}), key=len, reverse=True)
    )


def _json_secret_findings(
    source: str,
    payload: object,
    *,
    secret_name_fragments: tuple[str, ...],
) -> list[ScanFinding]:
    findings: list[ScanFinding] = []

    def visit(value: object, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}/{key_text}" if path else f"/{key_text}"
                if _is_secret_key(key_text, secret_name_fragments):
                    findings.append(
                        ScanFinding(
                            source=source,
                            line=1,
                            kind="secret-like-json-key",
                            context=f"key={key_text}; path_depth={child_path.count('/')}; value=<redacted>",
                        )
                    )
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}/{index}")

    visit(payload, "")
    return findings


def scan_text(
    source: str,
    text: str,
    *,
    workspace: Path,
    private_url_hosts: Sequence[str] = _DEFAULT_PRIVATE_HOSTS,
    secret_name_fragments: Sequence[str] = _DEFAULT_SECRET_FRAGMENTS,
) -> ScanReport:
    report = ScanReport(scanned_files=1)
    private_hosts = {host.lower().rstrip(".") for host in private_url_hosts}
    fragments = tuple(_normalise_key(value) for value in secret_name_fragments)
    workspace_markers = _workspace_markers(workspace)

    for line_number, line in enumerate(text.splitlines() or [text], start=1):
        if any(marker in line for marker in workspace_markers):
            report.findings.append(
                ScanFinding(
                    source=source,
                    line=line_number,
                    kind="workspace-path",
                    context="absolute workspace path detected; value=<redacted>",
                )
            )

        for match in _ASSIGNMENT_RE.finditer(line):
            key = match.group("key")
            if _is_secret_key(key, fragments):
                report.findings.append(
                    ScanFinding(
                        source=source,
                        line=line_number,
                        kind="secret-like-assignment",
                        context=f"key={key}; value=<redacted>",
                    )
                )

        for match in _URL_RE.finditer(line):
            raw_url = match.group(0).rstrip(".,);]}")
            try:
                parsed = urlsplit(raw_url)
            except ValueError:
                continue
            host = (parsed.hostname or "").lower().rstrip(".")
            if host in private_hosts:
                report.findings.append(
                    ScanFinding(
                        source=source,
                        line=line_number,
                        kind="private-url-host",
                        context=f"scheme={parsed.scheme.lower()}; host=<redacted>; url=<redacted>",
                    )
                )
            if parsed.username is not None or parsed.password is not None:
                report.findings.append(
                    ScanFinding(
                        source=source,
                        line=line_number,
                        kind="credentialed-url",
                        context=f"scheme={parsed.scheme.lower()}; host=<redacted>; url=<redacted>",
                    )
                )

    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("[") or source.lower().endswith((".json", ".jsonl")):
        if source.lower().endswith(".jsonl"):
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                report.findings.extend(
                    _json_secret_findings(source, payload, secret_name_fragments=fragments)
                )
        else:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                pass
            else:
                report.findings.extend(
                    _json_secret_findings(source, payload, secret_name_fragments=fragments)
                )
    return report


def _scanner_policy(policy: ReliabilityPolicy) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    diagnostics = policy.raw.get("diagnostics")
    if not isinstance(diagnostics, Mapping):
        raise ValueError("policy diagnostics must be an object")
    scanner = diagnostics.get("scanner")
    if not isinstance(scanner, Mapping):
        raise ValueError("policy diagnostics.scanner must be an object")
    forbid_workspace = scanner.get("forbid_absolute_workspace_paths")
    private_hosts = scanner.get("forbid_private_url_hosts")
    secret_fragments = scanner.get("secret_name_fragments")
    max_bytes = scanner.get("max_text_file_bytes")
    if forbid_workspace is not True:
        raise ValueError("diagnostics.scanner.forbid_absolute_workspace_paths must be true")
    if not isinstance(private_hosts, list) or not all(isinstance(value, str) and value for value in private_hosts):
        raise ValueError("diagnostics.scanner.forbid_private_url_hosts must be a non-empty string array")
    if not isinstance(secret_fragments, list) or not all(
        isinstance(value, str) and value for value in secret_fragments
    ):
        raise ValueError("diagnostics.scanner.secret_name_fragments must be a non-empty string array")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("diagnostics.scanner.max_text_file_bytes must be positive")
    return tuple(private_hosts), tuple(secret_fragments), max_bytes


def _inspect_stream(path: Path, workspace_bytes: tuple[bytes, ...]) -> tuple[bool, bool, int]:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    binary = False
    workspace_found = False
    total_bytes = 0
    max_marker = max((len(marker) for marker in workspace_bytes), default=1)
    tail = b""
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_SCAN_CHUNK_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                combined = tail + chunk
                if not workspace_found and any(marker in combined for marker in workspace_bytes):
                    workspace_found = True
                if b"\x00" in chunk:
                    binary = True
                if not binary:
                    try:
                        decoder.decode(chunk, final=False)
                    except UnicodeDecodeError:
                        binary = True
                tail = combined[-(max_marker - 1) :] if max_marker > 1 else b""
            if not binary:
                try:
                    decoder.decode(b"", final=True)
                except UnicodeDecodeError:
                    binary = True
    except OSError as exc:
        raise RuntimeError("evidence file could not be streamed") from exc
    return binary, workspace_found, total_bytes


def scan_tree(root: Path, *, workspace: Path, policy: ReliabilityPolicy) -> ScanReport:
    report = ScanReport()
    private_hosts, secret_fragments, max_text_file_bytes = _scanner_policy(policy)
    root = root.resolve(strict=False)
    workspace_markers = _workspace_markers(workspace)
    workspace_bytes = tuple(marker.encode("utf-8", errors="strict") for marker in workspace_markers)

    if not root.exists() or not root.is_dir():
        report.findings.append(
            ScanFinding(
                source=str(root),
                line=0,
                kind="missing-evidence-root",
                context="diagnostic evidence root is missing or not a directory",
            )
        )
        return report

    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            report.findings.append(
                ScanFinding(source=relative, line=0, kind="symlink", context="symbolic link is prohibited")
            )
            continue
        if not path.is_file():
            continue
        report.scanned_files += 1
        try:
            binary, workspace_found, total_bytes = _inspect_stream(path, workspace_bytes)
        except RuntimeError:
            report.findings.append(
                ScanFinding(source=relative, line=0, kind="unreadable-file", context="file could not be read")
            )
            continue

        if binary:
            report.skipped_binary_files += 1
            if workspace_found:
                report.findings.append(
                    ScanFinding(
                        source=relative,
                        line=0,
                        kind="workspace-path-binary",
                        context="absolute workspace path bytes detected; value=<redacted>",
                    )
                )
            continue

        if total_bytes > max_text_file_bytes:
            if workspace_found:
                report.findings.append(
                    ScanFinding(
                        source=relative,
                        line=0,
                        kind="workspace-path-large-text",
                        context="absolute workspace path detected in oversized text; value=<redacted>",
                    )
                )
            report.findings.append(
                ScanFinding(
                    source=relative,
                    line=0,
                    kind="oversized-text-file",
                    context=f"text evidence exceeds configured {max_text_file_bytes}-byte scan ceiling",
                )
            )
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            report.findings.append(
                ScanFinding(source=relative, line=0, kind="unreadable-file", context="file could not be read as UTF-8")
            )
            continue
        child = scan_text(
            relative,
            text,
            workspace=workspace,
            private_url_hosts=private_hosts,
            secret_name_fragments=secret_fragments,
        )
        report.findings.extend(child.findings)

    return report


def _write_report(path: Path, report: ScanReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan diagnostic evidence before any artifact publication.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        policy = load_policy(args.policy)
        report = scan_tree(args.root, workspace=args.workspace, policy=policy)
    except Exception as exc:
        report = ScanReport(
            findings=[
                ScanFinding(
                    source="scanner",
                    line=0,
                    kind="scanner-error",
                    context=f"{type(exc).__name__}; detail=<redacted>",
                )
            ]
        )
    _write_report(args.output, report)
    print(
        json.dumps(
            {
                "status": report.status,
                "finding_count": len(report.findings),
                "scanned_files": report.scanned_files,
                "skipped_binary_files": report.skipped_binary_files,
            },
            sort_keys=True,
        )
    )
    return 0 if not report.findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
