from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_PATH = Path("showcase/publication-manifest.json")
SCHEMA_VERSION = "arena-showcase-publication-v1"
EXPECTED_SHOWCASE_VERSION = "0.2.0rc1-public-showcase-1"
EXPECTED_EVIDENCE_CLASS = "deterministic_and_provider_free_showcase"
_EXPECTED_KEYS = {
    "schema_version",
    "showcase_version",
    "evidence_class",
    "project",
    "author",
    "source_repository",
    "files",
    "public_metrics",
    "prohibited_categories",
    "claims_boundary",
    "provider_called",
    "comparative_claim_permitted",
    "manifest_digest",
}
_FILE_KEYS = {"path", "sha256"}
_METRIC_KEYS = {
    "evidence_status",
    "general_verified",
    "specialist_verified",
    "false_completion_reduction",
    "additional_logical_model_calls",
    "source_file",
}
_REQUIRED_PROHIBITED_CATEGORIES = {
    "credentials_and_authentication",
    "private_prompts_and_raw_outputs",
    "provider_request_metadata",
    "private_ledgers_logs_and_notes",
    "local_machine_paths_and_identifiers",
    "enabled_live_policies_and_private_budgets",
    "unsupported_performance_or_safety_claims",
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
    re.compile(r"\buniversally superior\b", re.IGNORECASE),
    re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    re.compile(r"\bsafe for arbitrary tools\b", re.IGNORECASE),
    re.compile(r"\bmeasured cost efficiency\b", re.IGNORECASE),
)
_REQUIRED_HTML_MARKERS = (
    'id="proof"',
    'id="architecture"',
    'id="verified-build"',
    'id="about"',
    "No real-provider benchmark request or provider spend has been executed.",
    "Luca Panayiotou",
    "AI-assisted implementation",
    "comparative_claim_permitted: false",
    "docs/EMPLOYER_TECHNICAL_SUMMARY.md",
    "docs/PUBLICATION_BOUNDARY.md",
)


class ShowcaseReleaseError(ValueError):
    """Raised when the compact public showcase package is unsafe or inconsistent."""


def canonical_manifest_digest(payload: object) -> str:
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
        raise ShowcaseReleaseError(f"Required {label} is missing: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ShowcaseReleaseError(f"Required {label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise ShowcaseReleaseError(f"Required {label} must be a JSON object: {path}")
    return raw


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShowcaseReleaseError(f"Manifest field {name!r} must be a non-empty string.")
    return value.strip()


def _safe_relative_path(value: object) -> PurePosixPath:
    text = _required_text(value, "files[].path")
    if "\\" in text:
        raise ShowcaseReleaseError(f"Publication path is prohibited or non-portable: {text}")
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ShowcaseReleaseError(f"Publication path is prohibited or unsafe: {text}")
    if any("private" in part.lower() for part in path.parts):
        raise ShowcaseReleaseError(f"Publication path is prohibited because it is private: {text}")
    return path


def load_showcase_manifest(root: Path) -> dict[str, Any]:
    repository_root = Path(root)
    manifest_path = repository_root / MANIFEST_PATH
    if manifest_path.is_symlink():
        raise ShowcaseReleaseError("Publication manifest must not be a symlink.")
    raw = _read_object(manifest_path, "publication manifest")
    if set(raw) != _EXPECTED_KEYS:
        raise ShowcaseReleaseError("Publication manifest does not match the exact schema.")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ShowcaseReleaseError("Unsupported publication manifest schema_version.")
    if raw.get("showcase_version") != EXPECTED_SHOWCASE_VERSION:
        raise ShowcaseReleaseError("Unexpected showcase_version in publication manifest.")
    if raw.get("evidence_class") != EXPECTED_EVIDENCE_CLASS:
        raise ShowcaseReleaseError("Unexpected evidence_class in publication manifest.")
    if raw.get("project") != "Agent Reliability Arena":
        raise ShowcaseReleaseError("Unexpected project name in publication manifest.")
    if raw.get("author") != "Luca Panayiotou":
        raise ShowcaseReleaseError("Unexpected author in publication manifest.")
    if raw.get("source_repository") != "https://github.com/Luca-1304/agent-reliability-arena":
        raise ShowcaseReleaseError("Unexpected source repository in publication manifest.")
    if raw.get("provider_called") is not False:
        raise ShowcaseReleaseError("The provider_called publication flag must remain false.")
    if raw.get("comparative_claim_permitted") is not False:
        raise ShowcaseReleaseError("The comparative_claim_permitted publication flag must remain false.")

    supplied_digest = raw.get("manifest_digest")
    unsigned = dict(raw)
    unsigned.pop("manifest_digest")
    if not isinstance(supplied_digest, str) or not _DIGEST.fullmatch(supplied_digest):
        raise ShowcaseReleaseError("Publication manifest digest is invalid.")
    if canonical_manifest_digest(unsigned) != supplied_digest:
        raise ShowcaseReleaseError("Publication manifest digest mismatch.")

    files = raw.get("files")
    if not isinstance(files, list) or not files:
        raise ShowcaseReleaseError("Publication manifest files must be a non-empty list.")
    seen: set[str] = set()
    normalised: list[str] = []
    for row in files:
        if not isinstance(row, dict) or set(row) != _FILE_KEYS:
            raise ShowcaseReleaseError("Publication file row does not match the exact schema.")
        relative = _safe_relative_path(row.get("path")).as_posix()
        digest = row.get("sha256")
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise ShowcaseReleaseError(f"Publication file digest is invalid for {relative}.")
        if relative in seen:
            raise ShowcaseReleaseError(f"Duplicate publication path: {relative}")
        seen.add(relative)
        normalised.append(relative)
    if normalised != sorted(normalised):
        raise ShowcaseReleaseError("Publication files must be sorted by path.")

    metrics = raw.get("public_metrics")
    if not isinstance(metrics, dict) or set(metrics) != _METRIC_KEYS:
        raise ShowcaseReleaseError("Publication public_metrics do not match the exact schema.")
    categories = raw.get("prohibited_categories")
    if not isinstance(categories, list) or set(categories) != _REQUIRED_PROHIBITED_CATEGORIES:
        raise ShowcaseReleaseError("Publication prohibited_categories are incomplete or invalid.")
    _required_text(raw.get("claims_boundary"), "claims_boundary")
    return raw


def _scan_public_text(relative: str, text: str) -> None:
    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            raise ShowcaseReleaseError(f"Sensitive or prohibited {label} found in {relative}.")
    for pattern in _UNSUPPORTED_CLAIMS:
        if pattern.search(text):
            raise ShowcaseReleaseError(f"Unsupported public claim found in {relative}.")


def _fixture_metrics(root: Path) -> dict[str, object]:
    fixture = _read_object(root / "web/data/fixture-v1.json", "public fixture data")
    metrics = fixture.get("metrics")
    if not isinstance(metrics, dict):
        raise ShowcaseReleaseError("Public fixture metrics are invalid.")
    conditions = metrics.get("conditions")
    paired = metrics.get("paired")
    if not isinstance(conditions, dict) or not isinstance(paired, dict):
        raise ShowcaseReleaseError("Public fixture metric groups are invalid.")
    general = conditions.get("general")
    specialist = conditions.get("specialist")
    if not isinstance(general, dict) or not isinstance(specialist, dict):
        raise ShowcaseReleaseError("Public fixture condition metrics are invalid.")
    reconstructed = {
        "evidence_status": fixture.get("evidence_status"),
        "general_verified": general.get("verified_complete"),
        "specialist_verified": specialist.get("verified_complete"),
        "false_completion_reduction": paired.get("false_completion_reduction"),
        "additional_logical_model_calls": paired.get("additional_logical_model_calls"),
        "source_file": "web/data/fixture-v1.json",
    }
    expected = {
        "evidence_status": "deterministic_fixture",
        "general_verified": 2,
        "specialist_verified": 6,
        "false_completion_reduction": 3,
        "additional_logical_model_calls": 36,
        "source_file": "web/data/fixture-v1.json",
    }
    if reconstructed != expected:
        raise ShowcaseReleaseError("Public fixture metrics differ from the locked deterministic reference.")
    return reconstructed


def verify_showcase_release(root: Path) -> dict[str, object]:
    repository_root = Path(root)
    if not repository_root.exists() or not repository_root.is_dir() or repository_root.is_symlink():
        raise ShowcaseReleaseError("Showcase repository root must be a real directory.")
    root_resolved = repository_root.resolve()
    manifest = load_showcase_manifest(repository_root)

    for row in manifest["files"]:
        relative = _safe_relative_path(row["path"]).as_posix()
        target = repository_root / relative
        if target.is_symlink():
            raise ShowcaseReleaseError(f"Publication file must not be a symlink: {relative}")
        if not target.exists() or not target.is_file():
            raise ShowcaseReleaseError(f"Required publication file is missing: {relative}")
        try:
            resolved = target.resolve(strict=True)
        except OSError as exc:
            raise ShowcaseReleaseError(f"Unable to resolve publication file: {relative}") from exc
        if resolved != root_resolved and root_resolved not in resolved.parents:
            raise ShowcaseReleaseError(f"Publication file escapes repository root: {relative}")
        raw = target.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != row["sha256"]:
            raise ShowcaseReleaseError(f"Publication file digest mismatch: {relative}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ShowcaseReleaseError(f"Publication file is not UTF-8 text: {relative}") from exc
        _scan_public_text(relative, text)

    metrics = _fixture_metrics(repository_root)
    if manifest["public_metrics"] != metrics:
        raise ShowcaseReleaseError("Manifest public metrics do not match verified fixture metrics.")

    html = (repository_root / "web/index.html").read_text(encoding="utf-8")
    missing = [marker for marker in _REQUIRED_HTML_MARKERS if marker not in html]
    if missing:
        raise ShowcaseReleaseError("Landing page is missing required proof, attribution or limitation markers.")

    return {
        "schema_version": SCHEMA_VERSION,
        "showcase_version": manifest["showcase_version"],
        "evidence_class": manifest["evidence_class"],
        "files_verified": len(manifest["files"]),
        "general_verified": metrics["general_verified"],
        "specialist_verified": metrics["specialist_verified"],
        "false_completion_reduction": metrics["false_completion_reduction"],
        "additional_logical_model_calls": metrics["additional_logical_model_calls"],
        "provider_called": manifest["provider_called"],
        "comparative_claim_permitted": manifest["comparative_claim_permitted"],
        "manifest_digest": manifest["manifest_digest"],
    }
