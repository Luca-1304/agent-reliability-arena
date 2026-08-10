from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from .repeated_witness import WITNESS_FILENAME, inspect_completed_trial_witnesses
from .transports.base import canonical_json_sha256


RECEIPT_SCHEMA = "arena-repeated-experiment-detached-witness-receipt-v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TRIAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_RECEIPT_KEYS = {
    "schema_version",
    "plan_digest",
    "preflight_manifest_digest",
    "witness_records",
    "witness_prefix_bytes",
    "witness_prefix_sha256",
    "witness_head_digest",
    "last_trial_id",
    "receipt_digest",
}


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _positive_integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _trial_id(value: object) -> str:
    if not isinstance(value, str) or not _TRIAL_ID.fullmatch(value) or value in {".", ".."}:
        raise ValueError("Detached receipt last_trial_id is invalid.")
    return value


def _experiment_root(path: Path) -> Path:
    root = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Repeated experiment root must be a regular non-symlink directory.")
    return root


def _decode_object(text: str, name: str) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{name} contains duplicate key {key!r}.")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain a JSON object.")
    return value


def _read_object(path: Path, name: str) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"{name} must be a regular non-symlink file.")
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not valid UTF-8.") from exc
    return _decode_object(text, name)


def _context(root: Path) -> tuple[str, str]:
    plan = _read_object(root / "experiment-plan.json", "experiment plan")
    preflight = _read_object(root / "experiment-preflight.json", "experiment preflight")
    return (
        _digest(plan.get("plan_digest"), "experiment plan_digest"),
        _digest(preflight.get("manifest_digest"), "experiment preflight manifest_digest"),
    )


def _detached_receipt_path(root: Path, receipt_path: Path, *, require_exists: bool) -> Path:
    target = Path(receipt_path)
    if target.is_symlink():
        raise ValueError("Detached receipt path must not be a symlink.")

    parent = target.parent
    try:
        resolved_parent = parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("Detached receipt parent must already exist.") from exc
    if not resolved_parent.is_dir():
        raise ValueError("Detached receipt parent must resolve to a directory.")

    resolved_root = root.resolve(strict=True)
    if resolved_parent == resolved_root or resolved_root in resolved_parent.parents:
        raise ValueError("Detached receipt must be stored outside the repeated experiment root.")

    if require_exists:
        if not target.is_file():
            raise ValueError("Detached receipt must be an existing regular non-symlink file.")
    elif target.exists():
        raise ValueError("Detached receipt output must be a new path and must not already exist.")
    return target


def _validate_receipt(raw: dict[str, object]) -> dict[str, object]:
    if set(raw) != _RECEIPT_KEYS:
        raise ValueError("Detached receipt shape is invalid.")
    if raw.get("schema_version") != RECEIPT_SCHEMA:
        raise ValueError("Detached receipt schema_version is invalid.")

    _digest(raw.get("plan_digest"), "Detached receipt plan_digest")
    _digest(
        raw.get("preflight_manifest_digest"),
        "Detached receipt preflight_manifest_digest",
    )
    _positive_integer(raw.get("witness_records"), "Detached receipt witness_records")
    _positive_integer(raw.get("witness_prefix_bytes"), "Detached receipt witness_prefix_bytes")
    _digest(raw.get("witness_prefix_sha256"), "Detached receipt witness_prefix_sha256")
    _digest(raw.get("witness_head_digest"), "Detached receipt witness_head_digest")
    _trial_id(raw.get("last_trial_id"))
    supplied = _digest(raw.get("receipt_digest"), "Detached receipt receipt_digest")
    unsigned = dict(raw)
    unsigned.pop("receipt_digest")
    if canonical_json_sha256(unsigned) != supplied:
        raise ValueError("Detached receipt receipt_digest mismatch.")
    return raw


def _read_receipt(path: Path) -> dict[str, object]:
    return _validate_receipt(_read_object(path, "detached receipt"))


def _current_witness_state(root: Path) -> tuple[str, str, list[dict[str, object]], bytes]:
    plan_digest, preflight_digest = _context(root)
    rows = inspect_completed_trial_witnesses(root, plan_digest, preflight_digest)
    witness_path = root / WITNESS_FILENAME
    if witness_path.is_symlink() or not witness_path.is_file():
        raise ValueError("Experiment evidence witness must be a regular non-symlink file.")
    witness_bytes = witness_path.read_bytes()
    if len(witness_bytes.splitlines()) != len(rows):
        raise ValueError("Experiment evidence witness changed during receipt inspection.")
    return plan_digest, preflight_digest, rows, witness_bytes


def _encoded_receipt(receipt: dict[str, object]) -> bytes:
    return (
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_exclusive(path: Path, payload: dict[str, object]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(_encoded_receipt(payload))
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        path.chmod(0o600)


def _verify_receipt_against_current(
    root: Path,
    receipt: dict[str, object],
) -> dict[str, object]:
    plan_digest, preflight_digest, rows, witness_bytes = _current_witness_state(root)
    if receipt["plan_digest"] != plan_digest:
        raise ValueError("Detached receipt plan_digest does not match the current experiment plan.")
    if receipt["preflight_manifest_digest"] != preflight_digest:
        raise ValueError(
            "Detached receipt preflight_manifest_digest does not match the current experiment preflight."
        )

    receipt_records = _positive_integer(
        receipt["witness_records"],
        "Detached receipt witness_records",
    )
    prefix_bytes = _positive_integer(
        receipt["witness_prefix_bytes"],
        "Detached receipt witness_prefix_bytes",
    )
    if len(rows) < receipt_records:
        raise ValueError("Current witness is shorter than the detached receipt record checkpoint.")
    if len(witness_bytes) < prefix_bytes:
        raise ValueError("Current witness is shorter than the detached receipt byte prefix.")

    line_bytes = witness_bytes.splitlines(keepends=True)
    if len(line_bytes) < receipt_records:
        raise ValueError("Current witness is shorter than the detached receipt record checkpoint.")
    expected_prefix_bytes = sum(len(line) for line in line_bytes[:receipt_records])
    if prefix_bytes != expected_prefix_bytes:
        raise ValueError("Detached receipt byte prefix does not end at the recorded witness boundary.")

    prefix = witness_bytes[:prefix_bytes]
    if hashlib.sha256(prefix).hexdigest() != receipt["witness_prefix_sha256"]:
        raise ValueError("Detached receipt witness prefix digest mismatch.")

    checkpoint_row = rows[receipt_records - 1]
    if checkpoint_row.get("witness_digest") != receipt["witness_head_digest"]:
        raise ValueError("Detached receipt witness head digest mismatch.")
    if checkpoint_row.get("trial_id") != receipt["last_trial_id"]:
        raise ValueError("Detached receipt last trial ID mismatch.")

    return {
        "status": "verified",
        "receipt_digest": receipt["receipt_digest"],
        "receipt_witness_records": receipt_records,
        "current_witness_records": len(rows),
        "later_records_present": len(rows) > receipt_records,
        "witness_head_digest": receipt["witness_head_digest"],
        "last_trial_id": receipt["last_trial_id"],
    }


def write_detached_witness_receipt(
    experiment_root: Path,
    receipt_path: Path,
) -> dict[str, object]:
    root = _experiment_root(Path(experiment_root))
    target = _detached_receipt_path(root, Path(receipt_path), require_exists=False)
    plan_digest, preflight_digest, rows, witness_bytes = _current_witness_state(root)
    unsigned: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA,
        "plan_digest": plan_digest,
        "preflight_manifest_digest": preflight_digest,
        "witness_records": len(rows),
        "witness_prefix_bytes": len(witness_bytes),
        "witness_prefix_sha256": hashlib.sha256(witness_bytes).hexdigest(),
        "witness_head_digest": rows[-1]["witness_digest"],
        "last_trial_id": rows[-1]["trial_id"],
    }
    receipt = {**unsigned, "receipt_digest": canonical_json_sha256(unsigned)}
    _write_exclusive(target, receipt)
    persisted = _read_receipt(target)
    _verify_receipt_against_current(root, persisted)
    return persisted


def verify_detached_witness_receipt(
    experiment_root: Path,
    receipt_path: Path,
) -> dict[str, object]:
    root = _experiment_root(Path(experiment_root))
    target = _detached_receipt_path(root, Path(receipt_path), require_exists=True)
    receipt = _read_receipt(target)
    return _verify_receipt_against_current(root, receipt)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent_reliability_arena.repeated_receipt",
        description="Create or verify a detached repeated-experiment witness receipt.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("--experiment-root", required=True, type=Path)
        child.add_argument("--receipt", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = write_detached_witness_receipt(args.experiment_root, args.receipt)
        else:
            result = verify_detached_witness_receipt(args.experiment_root, args.receipt)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
