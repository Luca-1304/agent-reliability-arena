from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


SCHEMA_VERSION = "reliability-evidence-v1"
FAILURE_CATEGORIES = frozenset(
    {
        "TEST",
        "BUILD",
        "PACKAGE",
        "REPLAY",
        "DETERMINISM",
        "SECURITY",
        "DEPENDENCY",
        "ENVIRONMENT",
        "TIMEOUT",
        "CONCURRENCY",
        "POLICY",
        "UNKNOWN",
    }
)
_FINAL_STATUSES = frozenset({"pending", "passed", "failed", "blocked", "unknown"})
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(payload: object, *, pretty: bool) -> bytes:
    if pretty:
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    else:
        text = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ) + "\n"
    return text.encode("utf-8")


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_json_bytes(payload, pretty=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = _canonical_json_bytes(payload, pretty=False)
    with path.open("ab") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def dependency_fingerprint(rows: Sequence[str]) -> dict[str, object]:
    normalized = sorted({row.strip() for row in rows if row.strip()})
    payload = ("\n".join(normalized) + ("\n" if normalized else "")).encode("utf-8")
    return {
        "rows": normalized,
        "sha256": sha256_bytes(payload),
    }


def _validate_sha(value: str, *, field: str) -> None:
    if not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field} must be a lower-case 40-character hexadecimal SHA")


@dataclass(frozen=True)
class FailureRecord:
    category: str
    phase: str
    command_name: str
    argv: tuple[str, ...]
    sequence: int
    pass_number: int | None
    hash_seed: int | None
    exit_code: int | None
    duration_seconds: float
    log_path: str
    message: str

    def __post_init__(self) -> None:
        if self.category not in FAILURE_CATEGORIES:
            raise ValueError(f"unsupported failure category: {self.category}")
        if self.sequence < 1:
            raise ValueError("failure sequence must be positive")
        if self.pass_number is not None and self.pass_number < 1:
            raise ValueError("failure pass_number must be positive when present")
        if self.hash_seed is not None and self.hash_seed < 0:
            raise ValueError("failure hash_seed must be non-negative when present")
        if self.duration_seconds < 0:
            raise ValueError("failure duration_seconds must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "category": self.category,
            "command_name": self.command_name,
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "hash_seed": self.hash_seed,
            "log_path": self.log_path,
            "message": self.message,
            "pass_number": self.pass_number,
            "phase": self.phase,
            "sequence": self.sequence,
        }


@dataclass
class EvidenceManifest:
    repository: str
    commit_sha: str
    tested_commit_sha: str
    workflow: str
    run_id: str
    run_attempt: str
    event: str
    ref: str
    runner_os: str
    runner_arch: str
    python_version: str
    timezone: str
    locale: str
    hash_seed: int | None
    install_mode: str
    cache_mode: str
    toolchain: dict[str, str] = field(default_factory=dict)
    dependency_fingerprint: dict[str, object] = field(default_factory=dict)
    commands: list[dict[str, object]] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    output_digests: dict[str, object] = field(default_factory=dict)
    failures: list[FailureRecord] = field(default_factory=list)
    final_status: str = "pending"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported evidence schema version: {self.schema_version}")
        _validate_sha(self.commit_sha, field="commit_sha")
        _validate_sha(self.tested_commit_sha, field="tested_commit_sha")
        if self.hash_seed is not None and self.hash_seed < 0:
            raise ValueError("hash_seed must be non-negative when present")
        if self.final_status not in _FINAL_STATUSES:
            raise ValueError(f"unsupported final status: {self.final_status}")

    @classmethod
    def minimum_for_test(cls, *, commit_sha: str) -> "EvidenceManifest":
        return cls(
            repository="Luca-1304/agent-reliability-arena",
            commit_sha=commit_sha,
            tested_commit_sha=commit_sha,
            workflow="test",
            run_id="test-run",
            run_attempt="1",
            event="test",
            ref="refs/heads/test",
            runner_os="test-os",
            runner_arch="test-arch",
            python_version="3.10",
            timezone="UTC",
            locale="C.UTF-8",
            hash_seed=None,
            install_mode="test",
            cache_mode="cold",
        )

    def to_dict(self) -> dict[str, object]:
        if self.final_status not in _FINAL_STATUSES:
            raise ValueError(f"unsupported final status: {self.final_status}")
        command_rows = sorted(
            (dict(row) for row in self.commands),
            key=lambda row: int(row.get("sequence", 0)),
        )
        failure_rows = sorted(
            (record.to_dict() for record in self.failures),
            key=lambda row: int(row["sequence"]),
        )
        return {
            "cache_mode": self.cache_mode,
            "commands": command_rows,
            "commit_sha": self.commit_sha,
            "dependency_fingerprint": dict(self.dependency_fingerprint),
            "event": self.event,
            "failures": failure_rows,
            "final_status": self.final_status,
            "hash_seed": self.hash_seed,
            "install_mode": self.install_mode,
            "locale": self.locale,
            "output_digests": dict(self.output_digests),
            "python_version": self.python_version,
            "ref": self.ref,
            "repository": self.repository,
            "run_attempt": self.run_attempt,
            "run_id": self.run_id,
            "runner_arch": self.runner_arch,
            "runner_os": self.runner_os,
            "schema_version": self.schema_version,
            "tested_commit_sha": self.tested_commit_sha,
            "timings": dict(self.timings),
            "timezone": self.timezone,
            "toolchain": dict(self.toolchain),
            "workflow": self.workflow,
        }
