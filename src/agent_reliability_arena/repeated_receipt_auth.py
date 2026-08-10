from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from pathlib import Path

from .repeated_receipt import verify_detached_witness_receipt


AUTH_SCHEMA = "arena-repeated-experiment-detached-receipt-auth-v1"
AUTH_ALGORITHM = "hmac-sha256"
AUTH_KEY_ENV = "ARENA_RECEIPT_AUTH_KEY_HEX"
_KEY_ID_DOMAIN = b"arena-repeated-receipt-auth-key-id-v1\x00"
_AUTH_DOMAIN = b"arena-repeated-receipt-auth-v1\x00"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ENV_KEY_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_AUTH_KEYS = {
    "schema_version",
    "algorithm",
    "receipt_digest",
    "key_id",
    "auth_tag",
}


def _key(value: object) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("Detached receipt authentication key must be exactly 32-byte bytes.")
    return value


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _experiment_root(path: Path) -> Path:
    root = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Repeated experiment root must be a regular non-symlink directory.")
    return root


def _auth_path(root: Path, auth_path: Path, *, require_exists: bool) -> Path:
    target = Path(auth_path)
    if target.is_symlink():
        raise ValueError("Detached receipt authentication path must not be a symlink.")

    parent = target.parent
    try:
        resolved_parent = parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("Detached receipt authentication parent must already exist.") from exc
    if not resolved_parent.is_dir():
        raise ValueError("Detached receipt authentication parent must resolve to a directory.")

    resolved_root = root.resolve(strict=True)
    if resolved_parent == resolved_root or resolved_root in resolved_parent.parents:
        raise ValueError(
            "Detached receipt authentication envelope must be stored outside the repeated experiment root."
        )

    if require_exists:
        if not target.is_file():
            raise ValueError(
                "Detached receipt authentication envelope must be an existing regular non-symlink file."
            )
        if target.stat().st_nlink != 1:
            raise ValueError("Detached receipt authentication envelope must have exactly one hard link.")
    elif target.exists():
        raise ValueError(
            "Detached receipt authentication output must be a new path and must not already exist."
        )
    return target


def _decode_object(text: str) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Detached receipt authentication envelope contains duplicate key {key!r}.")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError("Detached receipt authentication envelope is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("Detached receipt authentication envelope must contain a JSON object.")
    return value


def _read_auth(path: Path) -> dict[str, object]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ValueError(
            "Detached receipt authentication envelope must be a regular non-symlink file."
        )
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Detached receipt authentication envelope is not valid UTF-8.") from exc
    raw = _decode_object(text)
    if set(raw) != _AUTH_KEYS:
        raise ValueError("Detached receipt authentication envelope shape is invalid.")
    if raw.get("schema_version") != AUTH_SCHEMA:
        raise ValueError("Detached receipt authentication schema_version is invalid.")
    if raw.get("algorithm") != AUTH_ALGORITHM:
        raise ValueError("Detached receipt authentication algorithm is invalid.")
    _digest(raw.get("receipt_digest"), "Detached receipt authentication receipt_digest")
    _digest(raw.get("key_id"), "Detached receipt authentication key_id")
    _digest(raw.get("auth_tag"), "Detached receipt authentication auth_tag")
    return raw


def _key_id(key: bytes) -> str:
    return hashlib.sha256(_KEY_ID_DOMAIN + key).hexdigest()


def _auth_tag(key: bytes, receipt_digest: str) -> str:
    return hmac.new(
        key,
        _AUTH_DOMAIN + bytes.fromhex(receipt_digest),
        hashlib.sha256,
    ).hexdigest()


def _encoded_auth(envelope: dict[str, object]) -> bytes:
    return (
        json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_exclusive(path: Path, envelope: dict[str, object]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(_encoded_auth(envelope))
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        path.chmod(0o600)


def _verified_receipt(
    experiment_root: Path,
    receipt_path: Path,
) -> dict[str, object]:
    result = verify_detached_witness_receipt(experiment_root, receipt_path)
    receipt_digest = _digest(result.get("receipt_digest"), "Verified detached receipt digest")
    return {**result, "receipt_digest": receipt_digest}


def _verify_envelope(
    receipt_result: dict[str, object],
    envelope: dict[str, object],
    key: bytes,
) -> dict[str, object]:
    expected_key_id = _key_id(key)
    supplied_key_id = _digest(
        envelope.get("key_id"),
        "Detached receipt authentication key_id",
    )
    if not hmac.compare_digest(supplied_key_id, expected_key_id):
        raise ValueError("Detached receipt authentication key identifier does not match the supplied key.")

    verified_receipt_digest = _digest(
        receipt_result.get("receipt_digest"),
        "Verified detached receipt digest",
    )
    supplied_receipt_digest = _digest(
        envelope.get("receipt_digest"),
        "Detached receipt authentication receipt_digest",
    )
    if not hmac.compare_digest(supplied_receipt_digest, verified_receipt_digest):
        raise ValueError("Detached receipt authentication receipt digest does not match the verified receipt.")

    expected_tag = _auth_tag(key, verified_receipt_digest)
    supplied_tag = _digest(
        envelope.get("auth_tag"),
        "Detached receipt authentication auth_tag",
    )
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise ValueError("Detached receipt authentication tag does not match the supplied key and receipt.")

    return {
        "status": "verified",
        "algorithm": AUTH_ALGORITHM,
        "key_id": expected_key_id,
        "receipt_digest": verified_receipt_digest,
        "receipt_witness_records": receipt_result.get("receipt_witness_records"),
        "current_witness_records": receipt_result.get("current_witness_records"),
        "later_records_present": receipt_result.get("later_records_present"),
        "witness_head_digest": receipt_result.get("witness_head_digest"),
        "last_trial_id": receipt_result.get("last_trial_id"),
    }


def write_detached_receipt_auth(
    experiment_root: Path,
    receipt_path: Path,
    auth_path: Path,
    key: bytes,
) -> dict[str, object]:
    secret = _key(key)
    root = _experiment_root(Path(experiment_root))
    target = _auth_path(root, Path(auth_path), require_exists=False)
    receipt_result = _verified_receipt(root, Path(receipt_path))
    receipt_digest = _digest(
        receipt_result.get("receipt_digest"),
        "Verified detached receipt digest",
    )
    envelope: dict[str, object] = {
        "schema_version": AUTH_SCHEMA,
        "algorithm": AUTH_ALGORITHM,
        "receipt_digest": receipt_digest,
        "key_id": _key_id(secret),
        "auth_tag": _auth_tag(secret, receipt_digest),
    }
    _write_exclusive(target, envelope)
    _auth_path(root, target, require_exists=True)
    persisted = _read_auth(target)
    _verify_envelope(_verified_receipt(root, Path(receipt_path)), persisted, secret)
    return persisted


def verify_detached_receipt_auth(
    experiment_root: Path,
    receipt_path: Path,
    auth_path: Path,
    key: bytes,
) -> dict[str, object]:
    secret = _key(key)
    root = _experiment_root(Path(experiment_root))
    target = _auth_path(root, Path(auth_path), require_exists=True)
    envelope = _read_auth(target)
    receipt_result = _verified_receipt(root, Path(receipt_path))
    return _verify_envelope(receipt_result, envelope, secret)


def _environment_key() -> bytes:
    value = os.environ.get(AUTH_KEY_ENV)
    if value is None:
        raise ValueError(f"{AUTH_KEY_ENV} must be set to exactly 64 hexadecimal characters.")
    if not _ENV_KEY_HEX.fullmatch(value):
        raise ValueError(f"{AUTH_KEY_ENV} must contain exactly 64 hexadecimal characters.")
    key = bytes.fromhex(value)
    if len(key) != 32:
        raise ValueError(f"{AUTH_KEY_ENV} must decode to exactly 32 bytes.")
    return key


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent_reliability_arena.repeated_receipt_auth",
        description="Create or verify an HMAC-authenticated detached repeated-experiment receipt.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("--experiment-root", required=True, type=Path)
        child.add_argument("--receipt", required=True, type=Path)
        child.add_argument("--auth", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        key = _environment_key()
        if args.command == "create":
            result = write_detached_receipt_auth(
                args.experiment_root,
                args.receipt,
                args.auth,
                key,
            )
        else:
            result = verify_detached_receipt_auth(
                args.experiment_root,
                args.receipt,
                args.auth,
                key,
            )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
