from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


class PublishedReleaseError(RuntimeError):
    """Raised when a downloaded public release fails closed verification."""


_CONTRACT_PATH = Path("release/github-prerelease.json")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CONTRACT_SCHEMA_PATTERN = re.compile(r"^arena-github-prerelease-v([1-9][0-9]*)$")


def verify_downloaded_release(
    root: Path,
    release_dir: Path,
    metadata_path: Path,
) -> dict[str, object]:
    """Verify an already-downloaded GitHub prerelease without trusting local build output."""

    repository_root = _real_directory(root, "Repository root")
    downloaded = _real_directory(release_dir, "Downloaded release directory")
    metadata_file = _real_file(metadata_path, "Release metadata")

    contract_path = _real_file(repository_root / _CONTRACT_PATH, "Release contract")
    contract = _read_json(contract_path, "Release contract")
    version = _required_string(contract, "version", "Release contract")
    tag = _required_string(contract, "tag", "Release contract")
    title = _required_string(contract, "release_title", "Release contract")
    source_repository = _required_string(contract, "source_repository", "Release contract")
    signer_workflow = _required_string(contract, "attestation_signer_workflow", "Release contract")
    expected_record_schema = _record_schema_from_contract(contract)

    if tag != f"v{version}":
        raise PublishedReleaseError("release contract tag/version drift")
    if contract.get("prerelease") is not True:
        raise PublishedReleaseError("release contract must remain a prerelease")
    if contract.get("provider_called") is not False:
        raise PublishedReleaseError("release contract provider boundary drift")
    if contract.get("comparative_claim_permitted") is not False:
        raise PublishedReleaseError("release contract comparative-claim boundary drift")

    primary_names = _primary_asset_names(version)
    expected_names = primary_names | {"release-record.json", "SHA256SUMS"}
    downloaded_names = _directory_file_names(downloaded)
    if downloaded_names != expected_names:
        raise PublishedReleaseError(
            f"release asset inventory drift: expected {sorted(expected_names)!r}, "
            f"got {sorted(downloaded_names)!r}"
        )

    metadata = _read_json(metadata_file, "Release metadata")
    metadata_assets = metadata.get("assets")
    if not isinstance(metadata_assets, list):
        raise PublishedReleaseError("release metadata assets must be a list")
    metadata_names: list[str] = []
    for item in metadata_assets:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PublishedReleaseError("release metadata contains an invalid asset record")
        metadata_names.append(item["name"])
    if len(metadata_names) != len(set(metadata_names)) or set(metadata_names) != expected_names:
        raise PublishedReleaseError("release metadata asset inventory drift")

    record = _read_json(_safe_file(downloaded, "release-record.json"), "Release record")
    if record.get("schema_version") != expected_record_schema:
        raise PublishedReleaseError(
            f"release record schema drift: expected {expected_record_schema!r}, "
            f"got {record.get('schema_version')!r}"
        )
    expected_record_scalars = {
        "project": contract.get("project"),
        "version": version,
        "tag": tag,
        "release_title": title,
        "prerelease": True,
        "provenance_attestation_required": True,
        "sbom_attestation_required": True,
        "attestation_signer_workflow": signer_workflow,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
    for key, expected in expected_record_scalars.items():
        if record.get(key) != expected:
            raise PublishedReleaseError(f"release record {key} drift")

    source_commit = record.get("source_commit")
    if not isinstance(source_commit, str) or not _COMMIT_PATTERN.fullmatch(source_commit):
        raise PublishedReleaseError("release record source commit is invalid")

    expected_metadata = {
        "tagName": tag,
        "name": title,
        "isPrerelease": True,
        "targetCommitish": source_commit,
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            raise PublishedReleaseError(f"release metadata {key} drift")
    if not isinstance(metadata.get("publishedAt"), str) or not metadata["publishedAt"]:
        raise PublishedReleaseError("release metadata publishedAt missing")
    if not isinstance(metadata.get("url"), str) or not metadata["url"]:
        raise PublishedReleaseError("release metadata URL missing")

    downloaded_contract = _safe_file(downloaded, "github-prerelease.json").read_bytes()
    if downloaded_contract != contract_path.read_bytes():
        raise PublishedReleaseError("downloaded release contract differs from verifier contract")

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != primary_names:
        raise PublishedReleaseError("release record artifact inventory drift")
    for name in sorted(primary_names):
        expected_digest = artifacts.get(name)
        if not isinstance(expected_digest, str) or not _SHA256_PATTERN.fullmatch(expected_digest):
            raise PublishedReleaseError(f"release record digest is invalid: {name}")
        actual_digest = _sha256(_safe_file(downloaded, name))
        if actual_digest != expected_digest:
            raise PublishedReleaseError(f"release record digest mismatch: {name}")

    checksums = _read_checksum_inventory(_safe_file(downloaded, "SHA256SUMS"))
    expected_checksum_names = primary_names | {"release-record.json"}
    if set(checksums) != expected_checksum_names:
        raise PublishedReleaseError("SHA256 checksum inventory drift")
    for name in sorted(expected_checksum_names):
        actual_digest = _sha256(_safe_file(downloaded, name))
        if checksums[name] != actual_digest:
            raise PublishedReleaseError(f"SHA256 checksum mismatch: {name}")

    sbom = _read_json(_safe_file(downloaded, "sbom.cdx.json"), "CycloneDX SBOM")
    expected_serial = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'{source_repository}@{version}')}"
    if (
        sbom.get("bomFormat") != "CycloneDX"
        or sbom.get("specVersion") != "1.6"
        or sbom.get("serialNumber") != expected_serial
    ):
        raise PublishedReleaseError("CycloneDX identity drift")

    return {
        "schema_version": "arena-published-release-download-v1",
        "project": contract.get("project"),
        "version": version,
        "tag": tag,
        "release_title": title,
        "release_url": metadata["url"],
        "published_at": metadata["publishedAt"],
        "source_commit": source_commit,
        "source_repository": source_repository,
        "attestation_signer_workflow": signer_workflow,
        "asset_count": len(expected_names),
        "checksum_entry_count": len(expected_checksum_names),
        "cyclonedx_serial_number": expected_serial,
        "provider_called": False,
        "comparative_claim_permitted": False,
        "security_certification_claimed": False,
    }


def _record_schema_from_contract(contract: dict[str, Any]) -> str:
    schema = contract.get("schema_version")
    if not isinstance(schema, str):
        raise PublishedReleaseError("release contract schema is missing")
    match = _CONTRACT_SCHEMA_PATTERN.fullmatch(schema)
    if not match:
        raise PublishedReleaseError("release contract schema is unsupported")
    return f"arena-github-prerelease-record-v{match.group(1)}"


def _primary_asset_names(version: str) -> set[str]:
    return {
        f"agent_reliability_arena-{version}-py3-none-any.whl",
        f"agent_reliability_arena-{version}.tar.gz",
        f"RELEASE_NOTES_v{version}.md",
        "github-prerelease.json",
        "publication-manifest.json",
        "launch-package-manifest.json",
        "provenance.json",
        "supply-chain-manifest.json",
        "sbom.cdx.json",
    }


def _read_checksum_inventory(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        digest, separator, name = line.partition("  ")
        if separator != "  " or not _SHA256_PATTERN.fullmatch(digest):
            raise PublishedReleaseError(f"invalid SHA256 checksum line {line_number}")
        if not name or Path(name).name != name or name in {".", ".."}:
            raise PublishedReleaseError(f"unsafe SHA256 checksum path on line {line_number}")
        if name in rows:
            raise PublishedReleaseError(f"duplicate SHA256 checksum entry: {name}")
        rows[name] = digest
    return rows


def _directory_file_names(directory: Path) -> set[str]:
    names: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise PublishedReleaseError(f"release directory contains unsafe entry: {path.name}")
        names.add(path.name)
    return names


def _safe_file(directory: Path, name: str) -> Path:
    if Path(name).name != name or name in {".", ".."}:
        raise PublishedReleaseError(f"unsafe release filename: {name}")
    path = directory / name
    return _real_file(path, f"Release asset {name}")


def _real_directory(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.exists() or not path.is_dir():
        raise PublishedReleaseError(f"{label} must be a real directory: {path}")
    return path.resolve()


def _real_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.exists() or not path.is_file():
        raise PublishedReleaseError(f"{label} must be a real file: {path}")
    return path.resolve()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublishedReleaseError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise PublishedReleaseError(f"{label} must be a JSON object")
    return payload


def _required_string(payload: dict[str, Any], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PublishedReleaseError(f"{label} {key} is missing")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
