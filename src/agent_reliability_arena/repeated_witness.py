from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .transports import verify_transport_ledger
from .transports.base import canonical_json_sha256


WITNESS_FILENAME = "experiment-evidence-witness.jsonl"
WITNESS_SCHEMA = "arena-repeated-experiment-evidence-witness-v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TRIAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WITNESS_KEYS = {
    "schema_version",
    "sequence",
    "trial_id",
    "plan_digest",
    "preflight_manifest_digest",
    "ledger_schema_version",
    "ledger_records",
    "ledger_sha256",
    "verification_summary_sha256",
    "previous_witness_digest",
    "witness_digest",
}


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _trial_id(value: object) -> str:
    if not isinstance(value, str) or not _TRIAL_ID.fullmatch(value) or value in {".", ".."}:
        raise ValueError("Witness trial_id is invalid.")
    return value


def _root(path: Path) -> Path:
    root = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Repeated experiment root must be a regular non-symlink directory.")
    return root


def _decode_row(line: str, line_number: int) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Witness line {line_number} contains duplicate key {key!r}.")
            result[key] = value
        return result

    try:
        row = json.loads(line, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Witness line {line_number} is not valid JSON.") from exc
    if not isinstance(row, dict):
        raise ValueError(f"Witness line {line_number} must contain a JSON object.")
    return row


def _validate_row(
    row: dict[str, object],
    line_number: int,
    *,
    plan_digest: str,
    preflight_manifest_digest: str,
    expected_previous_digest: str | None,
) -> str:
    if set(row) != _WITNESS_KEYS:
        raise ValueError(f"Witness record shape is invalid at line {line_number}.")
    if row.get("schema_version") != WITNESS_SCHEMA:
        raise ValueError(f"Witness schema_version is invalid at line {line_number}.")
    if row.get("sequence") != line_number:
        raise ValueError(f"Witness sequence mismatch at line {line_number}.")
    _trial_id(row.get("trial_id"))
    if row.get("plan_digest") != plan_digest:
        raise ValueError(f"Witness plan_digest mismatch at line {line_number}.")
    if row.get("preflight_manifest_digest") != preflight_manifest_digest:
        raise ValueError(f"Witness preflight_manifest_digest mismatch at line {line_number}.")

    ledger_schema = row.get("ledger_schema_version")
    if not isinstance(ledger_schema, str) or not ledger_schema:
        raise ValueError(f"Witness ledger_schema_version is invalid at line {line_number}.")
    ledger_records = row.get("ledger_records")
    if not isinstance(ledger_records, int) or isinstance(ledger_records, bool) or ledger_records <= 0:
        raise ValueError(f"Witness ledger_records is invalid at line {line_number}.")
    _digest(row.get("ledger_sha256"), "Witness ledger_sha256")
    _digest(row.get("verification_summary_sha256"), "Witness verification_summary_sha256")

    previous = row.get("previous_witness_digest")
    if line_number == 1:
        if previous is not None:
            raise ValueError("Witness genesis previous_witness_digest must be null.")
    else:
        if _digest(previous, "Witness previous_witness_digest") != expected_previous_digest:
            raise ValueError(f"Witness previous_witness_digest mismatch at line {line_number}.")

    supplied = _digest(row.get("witness_digest"), "Witness witness_digest")
    unsigned = dict(row)
    unsigned.pop("witness_digest")
    if canonical_json_sha256(unsigned) != supplied:
        raise ValueError(f"Witness digest mismatch at line {line_number}.")
    return supplied


def _read_witness_rows(
    path: Path,
    *,
    plan_digest: str,
    preflight_manifest_digest: str,
) -> list[dict[str, object]]:
    if path.is_symlink():
        raise ValueError("Experiment evidence witness must be a regular non-symlink file.")
    if not path.exists():
        return []
    if not path.is_file():
        raise ValueError("Experiment evidence witness must be a regular non-symlink file.")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Experiment evidence witness is not valid UTF-8.") from exc
    if not text:
        raise ValueError("Experiment evidence witness exists but is empty.")
    lines = text.splitlines()
    if not lines:
        raise ValueError("Experiment evidence witness exists but is empty.")

    rows: list[dict[str, object]] = []
    previous: str | None = None
    seen_trials: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ValueError(f"Experiment evidence witness contains a blank line at line {line_number}.")
        row = _decode_row(line, line_number)
        digest = _validate_row(
            row,
            line_number,
            plan_digest=plan_digest,
            preflight_manifest_digest=preflight_manifest_digest,
            expected_previous_digest=previous,
        )
        trial_id = _trial_id(row["trial_id"])
        if trial_id in seen_trials:
            raise ValueError(f"Experiment evidence witness contains duplicate trial_id {trial_id!r}.")
        seen_trials.add(trial_id)
        rows.append(row)
        previous = digest
    return rows


def _summary_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Witness verification summary must be a regular non-symlink file.")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trial_commitment(root: Path, trial_id: str) -> dict[str, object]:
    name = _trial_id(trial_id)
    trial_root = root / name
    if trial_root.is_symlink() or not trial_root.is_dir():
        raise ValueError(f"Witness trial evidence must be a regular directory: {name}")
    ledger = verify_transport_ledger(trial_root / "transport-calls.jsonl")
    schema_version = ledger.get("schema_version")
    records = ledger.get("records")
    ledger_sha256 = ledger.get("ledger_sha256")
    if not isinstance(schema_version, str) or not schema_version:
        raise ValueError(f"Witness trial {name!r} ledger schema is invalid.")
    if not isinstance(records, int) or isinstance(records, bool) or records <= 0:
        raise ValueError(f"Witness trial {name!r} ledger record count is invalid.")
    return {
        "ledger_schema_version": schema_version,
        "ledger_records": records,
        "ledger_sha256": _digest(ledger_sha256, "ledger_sha256"),
        "verification_summary_sha256": _summary_sha256(trial_root / "verification-summary.json"),
    }


def _reconcile(
    root: Path,
    rows: list[dict[str, object]],
    completed_trial_ids: list[str],
) -> None:
    if len(rows) < len(completed_trial_ids):
        if not rows:
            raise ValueError("Experiment evidence witness is missing for completed trial evidence.")
        raise ValueError("Experiment evidence witness is shorter than the verified completed prefix.")
    if len(rows) > len(completed_trial_ids):
        raise ValueError("Experiment evidence witness is ahead of the verified completed prefix.")

    expected_ids = [_trial_id(value) for value in completed_trial_ids]
    actual_ids = [_trial_id(row.get("trial_id")) for row in rows]
    if actual_ids != expected_ids:
        raise ValueError("Experiment evidence witness trial prefix does not match verified completed trials.")

    for row, trial_id in zip(rows, expected_ids):
        current = _trial_commitment(root, trial_id)
        if row.get("ledger_schema_version") != current["ledger_schema_version"]:
            raise ValueError(f"Witness ledger schema mismatch for trial {trial_id!r}.")
        if row.get("ledger_records") != current["ledger_records"]:
            raise ValueError(f"Witness ledger record count mismatch for trial {trial_id!r}.")
        if row.get("ledger_sha256") != current["ledger_sha256"]:
            raise ValueError(f"Witness ledger digest mismatch for trial {trial_id!r}.")
        if row.get("verification_summary_sha256") != current["verification_summary_sha256"]:
            raise ValueError(f"Witness verification summary digest mismatch for trial {trial_id!r}.")


def inspect_completed_trial_witnesses(
    experiment_root: Path,
    plan_digest: str,
    preflight_manifest_digest: str,
) -> list[dict[str, object]]:
    root = _root(Path(experiment_root))
    plan = _digest(plan_digest, "plan_digest")
    preflight = _digest(preflight_manifest_digest, "preflight_manifest_digest")
    rows = _read_witness_rows(
        root / WITNESS_FILENAME,
        plan_digest=plan,
        preflight_manifest_digest=preflight,
    )
    if not rows:
        raise ValueError("Experiment evidence witness contains no completed trial records.")
    trial_ids = [_trial_id(row.get("trial_id")) for row in rows]
    _reconcile(root, rows, trial_ids)
    return rows


def verify_completed_trial_witnesses(
    experiment_root: Path,
    completed_trial_ids: list[str],
    plan_digest: str,
    preflight_manifest_digest: str,
) -> list[dict[str, object]]:
    root = _root(Path(experiment_root))
    plan = _digest(plan_digest, "plan_digest")
    preflight = _digest(preflight_manifest_digest, "preflight_manifest_digest")
    path = root / WITNESS_FILENAME
    rows = _read_witness_rows(
        path,
        plan_digest=plan,
        preflight_manifest_digest=preflight,
    )
    if not completed_trial_ids:
        if rows:
            raise ValueError("Experiment evidence witness is ahead of the verified completed prefix.")
        return []
    _reconcile(root, rows, completed_trial_ids)
    return rows


def append_completed_trial_witness(
    experiment_root: Path,
    trial_id: str,
    plan_digest: str,
    preflight_manifest_digest: str,
) -> dict[str, object]:
    root = _root(Path(experiment_root))
    name = _trial_id(trial_id)
    plan = _digest(plan_digest, "plan_digest")
    preflight = _digest(preflight_manifest_digest, "preflight_manifest_digest")
    path = root / WITNESS_FILENAME
    rows = _read_witness_rows(
        path,
        plan_digest=plan,
        preflight_manifest_digest=preflight,
    )
    existing_ids = [_trial_id(row.get("trial_id")) for row in rows]
    _reconcile(root, rows, existing_ids)
    if name in existing_ids:
        raise ValueError(f"Experiment evidence witness already contains trial {name!r}.")

    commitment = _trial_commitment(root, name)
    unsigned: dict[str, object] = {
        "schema_version": WITNESS_SCHEMA,
        "sequence": len(rows) + 1,
        "trial_id": name,
        "plan_digest": plan,
        "preflight_manifest_digest": preflight,
        **commitment,
        "previous_witness_digest": rows[-1]["witness_digest"] if rows else None,
    }
    record = {**unsigned, "witness_digest": canonical_json_sha256(unsigned)}
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )

    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Experiment evidence witness must be a regular non-symlink file.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        path.chmod(0o600)

    verified = _read_witness_rows(
        path,
        plan_digest=plan,
        preflight_manifest_digest=preflight,
    )
    _reconcile(root, verified, [*existing_ids, name])
    return verified[-1]
