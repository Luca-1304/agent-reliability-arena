from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


_PROVENANCE_PATH = Path("citation/provenance.json")
_EXPECTED_SCHEMA = "arena-citation-package-v1"
_EXPECTED_PROJECT = "Agent Reliability Arena"
_EXPECTED_VERSION = "0.2.0rc2"
_EXPECTED_TAG = "v0.2.0rc2"
_EXPECTED_DATE = "2026-07-23"
_EXPECTED_RELEASE_URL = (
    "https://github.com/Luca-1304/agent-reliability-arena/releases/tag/v0.2.0rc2"
)
_EXPECTED_SHOWCASE_DIGEST = (
    "30061fec34ed199b6dcec650b78a7ee320166d11f08c74302871015fb4ca12e7"
)
_EXPECTED_LAUNCH_DIGEST = (
    "620c658240e4b05571de47dd66be13fbde72a6540ba06ba977d8056caf17427e"
)
_EXPECTED_FILES = {
    "CITATION.cff",
    "docs/REPRODUCIBILITY.md",
    "docs/TECHNICAL_REPORT.md",
}
_EXPECTED_KEYS = {
    "author",
    "claims_boundary",
    "comparative_claim_permitted",
    "files",
    "launch_manifest_digest",
    "project",
    "provider_called",
    "release_date",
    "release_tag",
    "release_url",
    "schema_version",
    "showcase_manifest_digest",
    "version",
}
_FORBIDDEN_MARKERS = (
    "OPENAI_API_KEY",
    "private-evidence/",
    "provider_request_id",
    "INTERNAL_OPERATOR_NOTE",
    "external_execution_enabled=true",
    "transport-calls.jsonl",
    "C:\\Users\\",
    "/home/",
)
_PROHIBITED_CLAIMS = (
    re.compile(r"\bproves?\s+universal\s+model\s+superiority\b", re.IGNORECASE),
    re.compile(r"\bproves?\s+production\s+readiness\b", re.IGNORECASE),
    re.compile(r"\bguarantees?\s+(?:agent|model|tool)\s+safety\b", re.IGNORECASE),
    re.compile(r"\brepresentative\s+real[- ]model\s+benchmark\b", re.IGNORECASE),
)
_REQUIRED_PUBLIC_MARKERS = (
    "deterministic fixture",
    "provider-free",
    "no real-provider benchmark",
    "not production readiness",
    "comparative_claim_permitted",
)


class CitationPackageError(ValueError):
    """Raised when the public citation package fails closed verification."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _real_root(root: Path) -> Path:
    candidate = Path(root)
    if not candidate.exists() or not candidate.is_dir() or candidate.is_symlink():
        raise CitationPackageError(f"Repository root must be an existing real directory: {candidate}")
    return candidate.resolve()


def _confined_file(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_symlink():
        raise CitationPackageError(f"Citation package file must not be a symlink: {relative}")
    if not path.exists() or not path.is_file():
        raise CitationPackageError(f"Citation package file is missing: {relative}")
    resolved = path.resolve(strict=True)
    if root != resolved and root not in resolved.parents:
        raise CitationPackageError(f"Citation package path escapes repository root: {relative}")
    return path


def _single_quoted_scalar(text: str, field: str) -> str:
    match = re.search(
        rf"(?m)^{re.escape(field)}:\s*[\"'](?P<value>[^\"']+)[\"']\s*$",
        text,
    )
    if match is None:
        raise CitationPackageError(f"CITATION.cff is missing quoted field: {field}")
    return match.group("value")


def _single_plain_scalar(text: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*(?P<value>[^\s#]+)\s*$", text)
    if match is None:
        raise CitationPackageError(f"CITATION.cff is missing scalar field: {field}")
    return match.group("value").strip('"\'')


def _package_version(root: Path) -> str:
    pyproject = _confined_file(root, "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"(?P<version>[^"]+)"\s*$', pyproject)
    if match is None:
        raise CitationPackageError("pyproject.toml does not declare a project version.")
    return match.group("version")


def _load_provenance(root: Path) -> tuple[dict[str, Any], Path]:
    path = _confined_file(root, _PROVENANCE_PATH.as_posix())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CitationPackageError("Citation provenance is not valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise CitationPackageError("Citation provenance must be a JSON object.")
    if set(payload) != _EXPECTED_KEYS:
        raise CitationPackageError(
            "Citation provenance schema mismatch: "
            f"expected {sorted(_EXPECTED_KEYS)}, received {sorted(payload)}"
        )
    return payload, path


def _verify_provenance_values(payload: dict[str, Any]) -> None:
    expected = {
        "author": "Luca Panayiotou",
        "project": _EXPECTED_PROJECT,
        "version": _EXPECTED_VERSION,
        "release_tag": _EXPECTED_TAG,
        "release_date": _EXPECTED_DATE,
        "release_url": _EXPECTED_RELEASE_URL,
        "schema_version": _EXPECTED_SCHEMA,
        "showcase_manifest_digest": _EXPECTED_SHOWCASE_DIGEST,
        "launch_manifest_digest": _EXPECTED_LAUNCH_DIGEST,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise CitationPackageError(
                f"Citation provenance field {key!r} must equal {value!r}."
            )
    claims = payload.get("claims_boundary")
    if not isinstance(claims, str) or "No real-provider benchmark" not in claims:
        raise CitationPackageError("Citation provenance must preserve the real-provider claims boundary.")


def _verify_file_inventory(root: Path, payload: dict[str, Any]) -> list[Path]:
    files = payload.get("files")
    if not isinstance(files, list) or len(files) != len(_EXPECTED_FILES):
        raise CitationPackageError("Citation provenance must list exactly three source files.")
    seen: set[str] = set()
    paths: list[Path] = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise CitationPackageError("Each citation provenance file entry must contain path and sha256 only.")
        relative = item.get("path")
        digest = item.get("sha256")
        if not isinstance(relative, str) or relative in seen:
            raise CitationPackageError("Citation provenance contains an invalid or duplicate file path.")
        if relative not in _EXPECTED_FILES:
            raise CitationPackageError(f"Citation provenance contains an unapproved file: {relative}")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise CitationPackageError(f"Citation provenance contains an invalid SHA-256 for {relative}.")
        path = _confined_file(root, relative)
        actual = _sha256_bytes(path.read_bytes())
        if actual != digest:
            raise CitationPackageError(
                f"Citation file digest mismatch for {relative}: expected {digest}, received {actual}."
            )
        seen.add(relative)
        paths.append(path)
    if seen != _EXPECTED_FILES:
        raise CitationPackageError(
            f"Citation file inventory mismatch: expected {sorted(_EXPECTED_FILES)}, received {sorted(seen)}"
        )
    return paths


def _verify_citation_metadata(root: Path, text: str) -> None:
    if _single_plain_scalar(text, "cff-version") != "1.2.0":
        raise CitationPackageError("CITATION.cff must use CFF 1.2.0.")
    if _single_quoted_scalar(text, "title") != _EXPECTED_PROJECT:
        raise CitationPackageError("CITATION.cff title does not match the project.")
    if _single_quoted_scalar(text, "version") != _EXPECTED_VERSION:
        raise CitationPackageError("CITATION.cff version does not match the release.")
    if _single_quoted_scalar(text, "date-released") != _EXPECTED_DATE:
        raise CitationPackageError("CITATION.cff release date does not match the public release.")
    if _single_quoted_scalar(text, "url") != _EXPECTED_RELEASE_URL:
        raise CitationPackageError("CITATION.cff URL does not match the public release.")
    if 'family-names: "Panayiotou"' not in text or 'given-names: "Luca"' not in text:
        raise CitationPackageError("CITATION.cff author metadata is incomplete.")
    if _package_version(root) != _EXPECTED_VERSION:
        raise CitationPackageError("Package version does not match the citation release version.")


def _verify_public_text(text: str) -> None:
    for marker in _FORBIDDEN_MARKERS:
        if marker in text:
            raise CitationPackageError(f"Citation package contains prohibited private marker: {marker}")
    for pattern in _PROHIBITED_CLAIMS:
        if pattern.search(text):
            raise CitationPackageError(
                f"Citation package contains a prohibited unsupported claim: {pattern.pattern}"
            )
    lowered = text.lower()
    for marker in _REQUIRED_PUBLIC_MARKERS:
        if marker not in lowered:
            raise CitationPackageError(f"Citation package is missing required limitation marker: {marker}")


def verify_citation_package(root: Path) -> dict[str, object]:
    """Verify the citation-ready public report package without external access."""

    repository_root = _real_root(Path(root))
    payload, provenance_path = _load_provenance(repository_root)
    _verify_provenance_values(payload)
    source_paths = _verify_file_inventory(repository_root, payload)

    citation_text = _confined_file(repository_root, "CITATION.cff").read_text(encoding="utf-8")
    _verify_citation_metadata(repository_root, citation_text)

    combined = "\n".join(
        [
            citation_text,
            *[path.read_text(encoding="utf-8") for path in source_paths if path.name != "CITATION.cff"],
            json.dumps(payload, sort_keys=True),
        ]
    )
    _verify_public_text(combined)

    return {
        "project": _EXPECTED_PROJECT,
        "version": _EXPECTED_VERSION,
        "release_tag": _EXPECTED_TAG,
        "release_date": _EXPECTED_DATE,
        "release_url": _EXPECTED_RELEASE_URL,
        "files_verified": len(source_paths) + 1,
        "provenance_digest": _sha256_bytes(provenance_path.read_bytes()),
        "showcase_manifest_digest": _EXPECTED_SHOWCASE_DIGEST,
        "launch_manifest_digest": _EXPECTED_LAUNCH_DIGEST,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
