from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ._ledger_lock import (
    _exclusive_ledger_lock,
    _validate_lock_timeout,
    validate_ledger_lock_path,
)
from .base import ModelCallRequest, ModelCallResult, ModelTransport, TransportError, canonical_json_sha256

LEGACY_SCHEMA_VERSION = "1"
SCHEMA_VERSION = "2"
_SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}
DEFAULT_LOCK_TIMEOUT_SECONDS = 30.0
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RECORD_KEYS_V1 = {
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
_RECORD_KEYS_V2 = _RECORD_KEYS_V1 | {"previous_record_digest"}
_MODEL_IDENTITY_MISMATCH_ERROR_KEYS = {
    "message",
    "category",
    "retryable",
    "status_code",
    "provider_error_code",
    "client_request_id",
    "provider_request_id",
    "expected_model_id",
    "observed_model_id",
    "response_id",
    "raw_response_sha256",
}


@dataclass(frozen=True)
class _LedgerState:
    schema_version: str
    records: int
    results: int
    errors: int
    ledger_sha256: str
    last_record_digest: str

    def to_summary(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "records": self.records,
            "results": self.results,
            "errors": self.errors,
            "ledger_sha256": self.ledger_sha256,
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


def _validate_model_identity_mismatch_error(
    error: dict[str, object],
    request: dict[str, object],
    line_number: int,
) -> None:
    if error.get("category") != "model_identity_mismatch":
        return
    if set(error) != _MODEL_IDENTITY_MISMATCH_ERROR_KEYS:
        raise ValueError(
            f"Ledger model identity mismatch error shape is invalid at line {line_number}."
        )
    if error.get("retryable") is not False:
        raise ValueError(
            f"Ledger model identity mismatch must be non-retryable at line {line_number}."
        )
    expected_model_id = _required_text(
        error.get("expected_model_id"),
        "error expected_model_id",
        line_number,
    )
    request_model_id = _required_text(request.get("model_id"), "request model_id", line_number)
    if expected_model_id != request_model_id:
        raise ValueError(
            f"Ledger model identity mismatch expected_model_id disagrees with request at line {line_number}."
        )
    observed_model_id = _required_text(
        error.get("observed_model_id"),
        "error observed_model_id",
        line_number,
    )
    if observed_model_id == expected_model_id:
        raise ValueError(
            f"Ledger model identity mismatch observed_model_id does not differ at line {line_number}."
        )
    _required_text(error.get("response_id"), "error response_id", line_number)
    raw_response_sha256 = _required_text(
        error.get("raw_response_sha256"),
        "error raw_response_sha256",
        line_number,
    )
    if not _HEX64.fullmatch(raw_response_sha256):
        raise ValueError(
            f"Ledger model identity mismatch raw_response_sha256 is invalid at line {line_number}."
        )


def _validate_record(
    row: object,
    line_number: int,
    *,
    schema_version: str,
    expected_previous_digest: str | None,
) -> tuple[str, str]:
    if not isinstance(row, dict):
        raise ValueError(f"Ledger line {line_number} must contain a JSON object.")
    if row.get("schema_version") != schema_version:
        raise ValueError(f"Ledger schema_version mismatch at line {line_number}.")

    expected_keys = _RECORD_KEYS_V2 if schema_version == SCHEMA_VERSION else _RECORD_KEYS_V1
    if set(row) != expected_keys:
        raise ValueError(f"Ledger record shape is invalid at line {line_number}.")

    record_digest = _required_text(row.get("record_digest"), "record_digest", line_number)
    unsigned = dict(row)
    unsigned.pop("record_digest")
    if canonical_json_sha256(unsigned) != record_digest:
        raise ValueError(f"Ledger record digest mismatch at line {line_number}.")

    sequence = row.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != line_number:
        raise ValueError(f"Ledger sequence mismatch at line {line_number}.")

    if schema_version == SCHEMA_VERSION:
        previous_record_digest = row.get("previous_record_digest")
        if line_number == 1:
            if previous_record_digest is not None:
                raise ValueError("Ledger schema-2 genesis previous_record_digest must be null at line 1.")
        else:
            previous_text = _required_text(
                previous_record_digest,
                "previous_record_digest",
                line_number,
            )
            if previous_text != expected_previous_digest:
                raise ValueError(f"Ledger previous_record_digest mismatch at line {line_number}.")

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
        return "result", record_digest
    if outcome_type == "error":
        if result is not None or not isinstance(error, dict):
            raise ValueError(f"Ledger result/error shape is invalid at line {line_number}.")
        _required_text(error.get("message"), "error message", line_number)
        _required_text(error.get("category"), "error category", line_number)
        if not isinstance(error.get("retryable"), bool):
            raise ValueError(f"Ledger error retryable flag is invalid at line {line_number}.")
        _validate_model_identity_mismatch_error(error, request, line_number)
        return "error", record_digest
    raise ValueError(f"Ledger outcome_type is invalid at line {line_number}.")


def _inspect_transport_ledger_unlocked(path: Path) -> _LedgerState:
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

    ledger_schema: str | None = None
    previous_record_digest: str | None = None
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ValueError(f"Ledger contains a blank line at line {line_number}.")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ledger contains invalid JSON at line {line_number}.") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Ledger line {line_number} must contain a JSON object.")

        row_schema = row.get("schema_version")
        if line_number == 1:
            if row_schema not in _SUPPORTED_SCHEMA_VERSIONS:
                raise ValueError(f"Unsupported ledger schema_version at line {line_number}.")
            ledger_schema = str(row_schema)
        elif row_schema != ledger_schema:
            raise ValueError(f"Ledger schema_version mismatch at line {line_number}.")

        assert ledger_schema is not None
        outcome_type, record_digest = _validate_record(
            row,
            line_number,
            schema_version=ledger_schema,
            expected_previous_digest=previous_record_digest,
        )
        if outcome_type == "result":
            results += 1
        else:
            errors += 1
        previous_record_digest = record_digest

    assert ledger_schema is not None
    assert previous_record_digest is not None
    return _LedgerState(
        schema_version=ledger_schema,
        records=len(lines),
        results=results,
        errors=errors,
        ledger_sha256=hashlib.sha256(raw).hexdigest(),
        last_record_digest=previous_record_digest,
    )


def _verify_transport_ledger_unlocked(path: Path) -> dict[str, object]:
    return _inspect_transport_ledger_unlocked(path).to_summary()


def verify_transport_ledger(
    path: Path,
    *,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> dict[str, object]:
    ledger_path = Path(path)
    timeout = _validate_lock_timeout(lock_timeout_seconds)
    # Preserve the old missing-ledger behavior without creating a sidecar lock file.
    _validate_path(ledger_path, require_exists=True)
    validate_ledger_lock_path(ledger_path)
    with _exclusive_ledger_lock(ledger_path, timeout_seconds=timeout):
        return _verify_transport_ledger_unlocked(ledger_path)


class RecordingTransport:
    def __init__(
        self,
        transport: ModelTransport,
        ledger_path: Path,
        *,
        clock: Callable[[], datetime] = _utc_now,
        lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
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
        self.lock_timeout_seconds = _validate_lock_timeout(lock_timeout_seconds)
        _validate_path(self.ledger_path, require_exists=False)
        validate_ledger_lock_path(self.ledger_path)
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            verify_transport_ledger(
                self.ledger_path,
                lock_timeout_seconds=self.lock_timeout_seconds,
            )

    def _record(
        self,
        request: ModelCallRequest,
        *,
        schema_version: str,
        sequence: int,
        previous_record_digest: str | None,
        outcome_type: str,
        result: dict[str, object] | None,
        error: dict[str, object] | None,
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "schema_version": schema_version,
            "sequence": sequence,
            "recorded_at": _timestamp(self.clock()),
            "provider": self.provider,
            "request": request.to_dict(),
            "request_digest": request.digest,
            "outcome_type": outcome_type,
            "result": result,
            "error": error,
        }
        if schema_version == SCHEMA_VERSION:
            record["previous_record_digest"] = previous_record_digest
        return record

    def _append_unlocked(self, record: dict[str, object]) -> None:
        _validate_path(self.ledger_path, require_exists=False)
        signed = dict(record)
        signed["record_digest"] = canonical_json_sha256(record)
        encoded = (
            json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.ledger_path, flags, 0o600)
        try:
            view = memoryview(encoded)
            offset = 0
            while offset < len(view):
                written = os.write(descriptor, view[offset:])
                if written <= 0:
                    raise OSError("Ledger append made no forward progress.")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _commit_record(
        self,
        request: ModelCallRequest,
        *,
        outcome_type: str,
        result: dict[str, object] | None,
        error: dict[str, object] | None,
    ) -> None:
        with _exclusive_ledger_lock(
            self.ledger_path,
            timeout_seconds=self.lock_timeout_seconds,
        ):
            _validate_path(self.ledger_path, require_exists=False)
            if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
                state = _inspect_transport_ledger_unlocked(self.ledger_path)
                schema_version = state.schema_version
                sequence = state.records + 1
                previous_record_digest = (
                    state.last_record_digest if schema_version == SCHEMA_VERSION else None
                )
            else:
                schema_version = SCHEMA_VERSION
                sequence = 1
                previous_record_digest = None
            self._append_unlocked(
                self._record(
                    request,
                    schema_version=schema_version,
                    sequence=sequence,
                    previous_record_digest=previous_record_digest,
                    outcome_type=outcome_type,
                    result=result,
                    error=error,
                )
            )

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        if not isinstance(request, ModelCallRequest):
            raise ValueError("'request' must be a ModelCallRequest instance.")
        try:
            result = self.transport.complete(request)
        except TransportError as error:
            self._commit_record(
                request,
                outcome_type="error",
                result=None,
                error=error.to_dict(),
            )
            raise
        if not isinstance(result, ModelCallResult):
            raise ValueError("Wrapped transport must return a ModelCallResult.")
        if result.call_id != request.call_id or result.request_digest != request.digest:
            raise ValueError("Wrapped transport result does not match the request.")
        if result.provider != self.provider:
            raise ValueError("Wrapped transport result provider does not match the transport provider.")
        if result.model_id != request.model_id:
            error = TransportError(
                "Provider-reported model_id does not match the requested model_id.",
                category="model_identity_mismatch",
                retryable=False,
                client_request_id=result.client_request_id,
                provider_request_id=result.provider_request_id,
            )
            mismatch_evidence = {
                **error.to_dict(),
                "expected_model_id": request.model_id,
                "observed_model_id": result.model_id,
                "response_id": result.response_id,
                "raw_response_sha256": result.raw_response_sha256,
            }
            self._commit_record(
                request,
                outcome_type="error",
                result=None,
                error=mismatch_evidence,
            )
            raise error
        self._commit_record(
            request,
            outcome_type="result",
            result=result.to_dict(),
            error=None,
        )
        return result
