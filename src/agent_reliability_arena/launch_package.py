from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_PATH = Path("showcase/launch-package-manifest.json")
SCHEMA_VERSION = "arena-launch-package-v1"
PACKAGE_VERSION = "0.2.0rc1-launch-package-1"
SHOWCASE_VERSION = "0.2.0rc1-public-showcase-1"
SHOWCASE_MANIFEST_DIGEST = "30061fec34ed199b6dcec650b78a7ee320166d11f08c74302871015fb4ca12e7"

_EXPECTED_KEYS = {
    "schema_version",
    "package_version",
    "project",
    "author",
    "source_showcase_manifest_digest",
    "source_showcase_version",
    "files",
    "distribution_register",
    "claims_boundary",
    "provider_called",
    "comparative_claim_permitted",
    "manifest_digest",
}
_FILE_KEYS = {"path", "sha256"}
_REGISTER_KEYS = {
    "schema_version",
    "project",
    "author",
    "source_showcase_version",
    "source_showcase_manifest_digest",
    "claims_boundary",
    "entries",
}
_ENTRY_KEYS = {
    "target_id",
    "audience",
    "surface",
    "state",
    "copy_source",
    "public_url",
    "published_date",
    "notes",
}
_ALLOWED_STATES = {
    "published_repository",
    "prepared",
    "submitted",
    "declined",
    "blocked",
}
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SENSITIVE_PATTERNS = (
    ("credential-shaped material", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("credential-shaped material", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("credential-shaped material", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("credential-shaped material", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}\b", re.IGNORECASE)),
    ("local absolute path", re.compile(r"(?:[A-Za-z]:\\|/(?:home|Users|tmp|var|private)/)")),
    ("private evidence path", re.compile(r"\bprivate-evidence(?:/|\\)", re.IGNORECASE)),
    ("raw provider identifier", re.compile(r"\bprovider_request_id\b", re.IGNORECASE)),
    ("internal note marker", re.compile(r"\bINTERNAL_OPERATOR_NOTE\b")),
    ("enabled live policy", re.compile(r"external_execution_enabled\s*[=:]\s*true", re.IGNORECASE)),
    ("private transport ledger", re.compile(r"\btransport-calls\.jsonl\b", re.IGNORECASE)),
)
_UNSUPPORTED_CLAIMS = (
    re.compile(r"\bproves representative model performance\b", re.IGNORECASE),
    re.compile(r"\brepresentative external-model performance\b", re.IGNORECASE),
    re.compile(r"\buniversally superior\b", re.IGNORECASE),
    re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    re.compile(r"\bsafe for arbitrary tools\b", re.IGNORECASE),
    re.compile(r"\bmeasured (?:real-world )?cost efficiency\b", re.IGNORECASE),
)
_REQUIRED_DOCUMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "LAUNCH.md": (
        "# Agent Reliability Arena — launch package",
        "## Verified public evidence",
        "## Use this package",
        "Luca Panayiotou",
        "AI-assisted implementation",
    ),
    "docs/CV_PROJECT_ENTRY.md": (
        "# CV project entry",
        "## Concise version",
        "## Expanded version",
        "deterministic fixture",
    ),
    "docs/PORTFOLIO_PROJECT_ENTRY.md": (
        "# Portfolio project entry",
        "## Problem",
        "## Engineering contribution",
        "## Evidence boundary",
    ),
    "docs/RECRUITER_OUTREACH.md": (
        "# Recruiter outreach",
        "## Initial message",
        "## Follow-up",
        "No message has been sent automatically",
    ),
    "docs/LAUNCH_POSTS.md": (
        "# Public launch posts",
        "## LinkedIn",
        "## Short-form",
        "deterministic fixture",
    ),
    "docs/COMMUNITY_SUBMISSIONS.md": (
        "# Technical-community submission copy",
        "## Technical submission",
        "## Discussion prompt",
        "not a real-model leaderboard",
    ),
    "docs/HOSTED_DEPLOYMENT.md": (
        "# Hosted deployment readiness",
        "## Verified source",
        "## Current state",
        "No hosted deployment is claimed live",
    ),
}


class LaunchPackageError(ValueError):
    """Raised when the public launch package is unsafe or inconsistent."""


def canonical_launch_manifest_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LaunchPackageError(f"Required {label} is missing: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchPackageError(f"Required {label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise LaunchPackageError(f"Required {label} must be a JSON object: {path}")
    return raw


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LaunchPackageError(f"Launch-package field {name!r} must be a non-empty string.")
    return value.strip()


def _optional_text_or_none(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


def _safe_relative_path(value: object) -> PurePosixPath:
    text = _required_text(value, "files[].path")
    if "\\" in text:
        raise LaunchPackageError(f"Launch-package path is prohibited or non-portable: {text}")
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise LaunchPackageError(f"Launch-package path is prohibited or unsafe: {text}")
    if any("private" in part.lower() for part in path.parts):
        raise LaunchPackageError(f"Launch-package path is prohibited because it is private: {text}")
    return path


def _scan_public_text(relative: str, text: str) -> None:
    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            raise LaunchPackageError(f"Sensitive or prohibited {label} found in {relative}.")
    for pattern in _UNSUPPORTED_CLAIMS:
        if pattern.search(text):
            raise LaunchPackageError(f"Unsupported public claim found in {relative}.")


def load_launch_manifest(root: Path) -> dict[str, Any]:
    repository_root = Path(root)
    manifest_path = repository_root / MANIFEST_PATH
    if manifest_path.is_symlink():
        raise LaunchPackageError("Launch-package manifest must not be a symlink.")
    raw = _read_object(manifest_path, "launch-package manifest")
    if set(raw) != _EXPECTED_KEYS:
        raise LaunchPackageError("Launch-package manifest does not match the exact schema.")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise LaunchPackageError("Unsupported launch-package schema_version.")
    if raw.get("package_version") != PACKAGE_VERSION:
        raise LaunchPackageError("Unexpected launch-package version.")
    if raw.get("project") != "Agent Reliability Arena":
        raise LaunchPackageError("Unexpected project name in launch-package manifest.")
    if raw.get("author") != "Luca Panayiotou":
        raise LaunchPackageError("Unexpected author in launch-package manifest.")
    if raw.get("source_showcase_version") != SHOWCASE_VERSION:
        raise LaunchPackageError("Launch package is not linked to the expected showcase version.")
    if raw.get("source_showcase_manifest_digest") != SHOWCASE_MANIFEST_DIGEST:
        raise LaunchPackageError("Launch package is not linked to the expected showcase digest.")
    if raw.get("distribution_register") != "showcase/distribution-register.json":
        raise LaunchPackageError("Unexpected distribution-register path.")
    if raw.get("provider_called") is not False:
        raise LaunchPackageError("The provider_called launch-package flag must remain false.")
    if raw.get("comparative_claim_permitted") is not False:
        raise LaunchPackageError("The comparative_claim_permitted launch-package flag must remain false.")
    _required_text(raw.get("claims_boundary"), "claims_boundary")

    supplied_digest = raw.get("manifest_digest")
    unsigned = dict(raw)
    unsigned.pop("manifest_digest")
    if not isinstance(supplied_digest, str) or not _DIGEST.fullmatch(supplied_digest):
        raise LaunchPackageError("Launch-package manifest digest is invalid.")
    if canonical_launch_manifest_digest(unsigned) != supplied_digest:
        raise LaunchPackageError("Launch-package manifest digest mismatch.")

    files = raw.get("files")
    if not isinstance(files, list) or not files:
        raise LaunchPackageError("Launch-package files must be a non-empty list.")
    seen: set[str] = set()
    normalised: list[str] = []
    for row in files:
        if not isinstance(row, dict) or set(row) != _FILE_KEYS:
            raise LaunchPackageError("Launch-package file row does not match the exact schema.")
        relative = _safe_relative_path(row.get("path")).as_posix()
        digest = row.get("sha256")
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise LaunchPackageError(f"Launch-package file digest is invalid for {relative}.")
        if relative in seen:
            raise LaunchPackageError(f"Duplicate launch-package path: {relative}")
        seen.add(relative)
        normalised.append(relative)
    if normalised != sorted(normalised):
        raise LaunchPackageError("Launch-package files must be sorted by path.")
    return raw


def _validate_distribution_register(path: Path) -> dict[str, int]:
    raw = _read_object(path, "distribution register")
    if set(raw) != _REGISTER_KEYS:
        raise LaunchPackageError("Distribution register does not match the exact schema.")
    if raw.get("schema_version") != "arena-distribution-register-v1":
        raise LaunchPackageError("Unsupported distribution-register schema_version.")
    if raw.get("project") != "Agent Reliability Arena":
        raise LaunchPackageError("Unexpected project in distribution register.")
    if raw.get("author") != "Luca Panayiotou":
        raise LaunchPackageError("Unexpected author in distribution register.")
    if raw.get("source_showcase_version") != SHOWCASE_VERSION:
        raise LaunchPackageError("Distribution register is linked to the wrong showcase version.")
    if raw.get("source_showcase_manifest_digest") != SHOWCASE_MANIFEST_DIGEST:
        raise LaunchPackageError("Distribution register is linked to the wrong showcase digest.")
    _required_text(raw.get("claims_boundary"), "distribution_register.claims_boundary")

    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise LaunchPackageError("Distribution register entries must be a non-empty list.")
    seen_ids: set[str] = set()
    counts = {state: 0 for state in _ALLOWED_STATES}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
            raise LaunchPackageError("Distribution entry does not match the exact schema.")
        target_id = _required_text(entry.get("target_id"), "entries[].target_id")
        if target_id in seen_ids:
            raise LaunchPackageError(f"Duplicate distribution target_id: {target_id}")
        seen_ids.add(target_id)
        _required_text(entry.get("audience"), "entries[].audience")
        _required_text(entry.get("surface"), "entries[].surface")
        copy_source = _safe_relative_path(entry.get("copy_source")).as_posix()
        if copy_source.startswith("showcase/") and copy_source != "showcase/distribution-register.json":
            raise LaunchPackageError("Distribution copy_source must point to a public audience document.")
        _required_text(entry.get("notes"), "entries[].notes")

        state = entry.get("state")
        if state not in _ALLOWED_STATES:
            raise LaunchPackageError(f"Unsupported distribution state for {target_id}: {state}")
        counts[state] += 1
        public_url = _optional_text_or_none(entry.get("public_url"), "entries[].public_url")
        published_date = _optional_text_or_none(entry.get("published_date"), "entries[].published_date")

        if state in {"published_repository", "submitted"}:
            if public_url is None or published_date is None:
                raise LaunchPackageError(
                    f"Distribution entry {target_id} is {state} but has no public URL and date evidence."
                )
            if not public_url.startswith("https://"):
                raise LaunchPackageError(f"Distribution URL for {target_id} must use HTTPS.")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_date):
                raise LaunchPackageError(f"Distribution date for {target_id} must use YYYY-MM-DD.")
        else:
            if public_url is not None or published_date is not None:
                raise LaunchPackageError(
                    f"Distribution entry {target_id} has URL/date evidence without a published state."
                )

    if counts["published_repository"] != 1:
        raise LaunchPackageError("Distribution register must contain exactly one repository publication entry.")
    return counts


def verify_launch_package(root: Path) -> dict[str, object]:
    repository_root = Path(root)
    if not repository_root.exists() or not repository_root.is_dir() or repository_root.is_symlink():
        raise LaunchPackageError("Launch-package repository root must be a real directory.")
    root_resolved = repository_root.resolve()
    manifest = load_launch_manifest(repository_root)

    listed_paths: set[str] = set()
    for row in manifest["files"]:
        relative = _safe_relative_path(row["path"]).as_posix()
        listed_paths.add(relative)
        target = repository_root / relative
        if target.is_symlink():
            raise LaunchPackageError(f"Launch-package file must not be a symlink: {relative}")
        if not target.exists() or not target.is_file():
            raise LaunchPackageError(f"Required launch-package file is missing: {relative}")
        try:
            resolved = target.resolve(strict=True)
        except OSError as exc:
            raise LaunchPackageError(f"Unable to resolve launch-package file: {relative}") from exc
        if resolved != root_resolved and root_resolved not in resolved.parents:
            raise LaunchPackageError(f"Launch-package file escapes repository root: {relative}")
        raw = target.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != row["sha256"]:
            raise LaunchPackageError(f"Launch-package file digest mismatch: {relative}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LaunchPackageError(f"Launch-package file is not UTF-8 text: {relative}") from exc
        _scan_public_text(relative, text)

    if set(_REQUIRED_DOCUMENT_MARKERS) - listed_paths:
        raise LaunchPackageError("Launch-package manifest omits required audience documents.")
    for relative, markers in _REQUIRED_DOCUMENT_MARKERS.items():
        text = (repository_root / relative).read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise LaunchPackageError(f"Launch-package document is missing required markers: {relative}")

    register_relative = manifest["distribution_register"]
    if register_relative not in listed_paths:
        raise LaunchPackageError("Distribution register is not pinned in the launch-package manifest.")
    counts = _validate_distribution_register(repository_root / register_relative)

    return {
        "schema_version": SCHEMA_VERSION,
        "package_version": manifest["package_version"],
        "source_showcase_version": manifest["source_showcase_version"],
        "source_showcase_manifest_digest": manifest["source_showcase_manifest_digest"],
        "files_verified": len(manifest["files"]),
        "repository_publications": counts["published_repository"],
        "prepared_external_actions": counts["prepared"],
        "submitted_external_actions": counts["submitted"],
        "blocked_external_actions": counts["blocked"],
        "provider_called": manifest["provider_called"],
        "comparative_claim_permitted": manifest["comparative_claim_permitted"],
        "manifest_digest": manifest["manifest_digest"],
    }
