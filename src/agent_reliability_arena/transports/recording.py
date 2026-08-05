from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .base import ModelCallRequest, ModelCallResult, ModelTransport, TransportError, canonical_json_sha256

SCHEMA_VERSION = "1"
_RECORD_KEYS = {
    "schema_version",
    "sequence",
    "recorded_at",
    "provider",
    "request",
    "request_digest",
    "outcome_type",
    "result",
    "error",
    "record_digest",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Ledger clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _required_text(value: object, name: str, line_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Ledger {name} is invalid at line {line_number}.")
    return value


def _validate_timestamp(value: object, line_number: int) -> None:
    text = _required_text(value, "recorded_at", line_number)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Ledger recorded_at is invalid at line {line_number}.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"Ledger recorded_at must include a timezone at line {line_number}.")


def _validate_path(path: Path, *, require_exists: bool) -> None:
    parent = path.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError(f"Ledger parent directory does not exist or is not a directory: {parent}")
    if path.is_symlink():
        raise ValueError(f"Ledger path must not be a symlink: {path}")
    if path.exists():
        if not path.is_file():
            raise ValueError(f"Ledger path must be a regular file: {path}")
    elif require_exists:
        raise ValueError(f"Ledger does not exist: {path}")


def _validate_record(row: object, line_number: int) -> str:
    if not isinstance(row, dict):
        raise ValueError(f"Ledger line {line_number} must contain a JSON object.")
    if set(row) != _RECORD_KEYS:
        raise ValueError(f"Ledger record shape is invalid at line {line_number}.")

    record_digest = _required_text(row.get("record_digest"), "record_digest", line_number)
    unsigned = dict(row)
    unsigned.pop("record_digest")
    if canonical_json_sha256(unsigned) != record_digest:
        raise ValueError(f"Ledger record digest mismatch at line {line_number}.")

    if row.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported ledger schema_version at line {line_number}.")
    sequence = row.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != line_number:
        raise ValueError(f"Ledger sequence mismatch at line {line_number}.")
    _validate_timestamp(row.get("recorded_at"), line_number)
    provider = _required_text(row.get("provider"), "provider", line_number)

    request = row.get("request")
    if not isinstance(request, dict):
        raise ValueError(f"Ledger request is invalid at line {line_number}.")
    request_digest = _required_text(row.get("request_digest"), "request_digest", line_number)
    if canonical_json_sha256(request) != request_digest:
        raise ValueError(f"Ledger request digest mismatch at line {line_number}.")
    request_call_id = _required_text(request.get("call_id"), "request call_id", line_number)

    outcome_type = row.get("outcome_type")
    result = row.get("result")
    error = row.get("error")
    if outcome_type == "result":
        if not isinstance(result, dict) or error is not None:
            raise ValueError(f"Ledger result/error shape is invalid at line {line_number}.")
        if result.get("request_digest") != request_digest:
            raise ValueError(f"Ledger result request_digest mismatch at line {line_number}.")
        if result.get("call_id") != request_call_id:
            raise ValueError(f"Ledger result call_id mismatch at line {line_number}.")
        if result.get("provider") != provider:
            raise ValueError(f"Ledger result provider mismatch at line {line_number}.")
        return "result"
    if outcome_type == "error":
        if result is not None or not isinstance(error, dict):
            raise ValueError(f"Ledger result/error shape is invalid at line {line_number}.")
        _required_text(error.get("message"), "error message", line_number)
        _required_text(error.get("category"), "error category", line_number)
        if not isinstance(error.get("retryable"), bool):
            raise ValueError(f"Ledger error retryable flag is invalid at line {line_number}.")
        return "error"
    raise ValueError(f"Ledger outcome_type is invalid at line {line_number}.")


def verify_transport_ledger(path: Path) -> dict[str, object]:
    ledger_path = Path(path)
    _validate_path(ledger_path, require_exists=True)
    raw = ledger_path.read_bytes()
    if not raw:
        raise ValueError(f"Ledger is empty: {ledger_path}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Ledger is not valid UTF-8: {ledger_path}") from exc

    results = 0
    errors = 0
    lines = text.splitlines()
    if not lines:
        raise ValueError(f"Ledger is empty: {ledger_path}")
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ValueError(f"Ledger contains a blank line at line {line_number}.")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ledger contains invalid JSON at line {line_number}.") from exc
        outcome_type = _validate_record(row, line_number)
        if outcome_type == "result":
            results += 1
        else:
            errors += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "records": len(lines),
        "results": results,
        "errors": errors,
        "ledger_sha256": hashlib.sha256(raw).hexdigest(),
    }


class RecordingTransport:
    def __init__(
        self,
        transport: ModelTransport,
        ledger_path: Path,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        provider = getattr(transport, "provider", None)
        if not isinstance(provider, str) or not provider.strip() or not callable(getattr(transport, "complete", None)):
            raise ValueError("'transport' must implement ModelTransport.")
        if not callable(clock):
            raise ValueError("'clock' must be callable.")
        self.transport = transport
        self.provider = provider.strip()
        self.ledger_path = Path(ledger_path)
        self.clock = clock
        _validate_path(self.ledger_path, require_exists=False)
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            summary = verify_transport_ledger(self.ledger_path)
            self._next_sequence = int(summary["records"]) + 1
        else:
            self._next_sequence = 1

    def _record(
        self,
        request: ModelCallRequest,
        *,
        outcome_type: str,
        result: dict[str, object] | None,
        error: dict[str, object] | None,
    ) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "sequence": self._next_sequence,
            "recorded_at": _timestamp(self.clock()),
            "provider": self.provider,
            "request": request.to_dict(),
            "request_digest": request.digest,
            "outcome_type": outcome_type,
            "result": result,
            "error": error,
        }

    def _append(self, record: dict[str, object]) -> None:
        _validate_path(self.ledger_path, require_exists=False)
        signed = dict(record)
        signed["record_digest"] = canonical_json_sha256(record)
        encoded = json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.ledger_path, flags, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if not isinstance(request, ModelCallRequest):
            raise ValueError("'request' must be a ModelCallRequest instance.")
        try:
            result = self.transport.complete(request)
        except TransportError as error:
            self._append(
                self._record(
                    request,
                    outcome_type="error",
                    result=None,
                    error=error.to_dict(),
                )
            )
            self._next_sequence += 1
            raise
        if not isinstance(result, ModelCallResult):
            raise ValueError("Wrapped transport must return a ModelCallResult.")
        if result.call_id != request.call_id or result.request_digest != request.digest:
            raise ValueError("Wrapped transport result does not match the request.")
        if result.provider != self.provider:
            raise ValueError("Wrapped transport result provider does not match the transport provider.")
        self._append(
            self._record(
                request,
                outcome_type="result",
                result=result.to_dict(),
                error=None,
            )
        )
        self._next_sequence += 1
        return result
