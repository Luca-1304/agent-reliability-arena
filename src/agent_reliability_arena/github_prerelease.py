from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .launch_package import verify_launch_package
from .showcase_release import verify_showcase_release
from .supply_chain import verify_supply_chain_package


_CONTRACT_PATH = Path("release/github-prerelease.json")
_SHOWCASE_MANIFEST_PATH = Path("showcase/publication-manifest.json")
_LAUNCH_MANIFEST_PATH = Path("showcase/launch-package-manifest.json")
_CITATION_PROVENANCE_PATH = Path("citation/provenance.json")
_SUPPLY_CHAIN_MANIFEST_PATH = Path("security/supply-chain-manifest.json")
_SBOM_PATH = Path("security/sbom.cdx.json")
_WORKFLOW_PATH = Path(".github/workflows/release.yml")
_VERSION_PATTERN = re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"\s*$', re.MULTILINE)
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_EXPECTED_CONTRACT_KEYS = {
    "attestation_action",
    "attestation_signer_workflow",
    "changelog_heading",
    "claims_boundary",
    "comparative_claim_permitted",
    "evidence_class",
    "prerelease",
    "primary_artifacts",
    "project",
    "provenance_attestation_required",
    "provider_called",
    "release_notes",
    "release_title",
    "sbom_attestation_required",
    "schema_version",
    "source_citation_provenance_sha256",
    "source_launch_manifest_digest",
    "source_repository",
    "source_sbom_sha256",
    "source_showcase_manifest_digest",
    "source_supply_chain_manifest_sha256",
    "tag",
    "target_branch",
    "version",
}
_FORBIDDEN_PUBLIC_MARKERS = (
    "OPENAI_API_KEY",
    "private-evidence/",
    "provider_request_id",
    "INTERNAL_OPERATOR_NOTE",
    "external_execution_enabled=true",
    "transport-calls.jsonl",
    "C:\\Users\\",
    "/home/",
)
_PROHIBITED_CLAIM_PATTERNS = (
    re.compile(r"(?:proves?|establish(?:es|ed)?|demonstrat(?:es|ed)?)\s+universal\s+model\s+superiority", re.IGNORECASE),
    re.compile(r"guarante(?:e|es|ed)\s+(?:complete\s+)?safety", re.IGNORECASE),
    re.compile(r"proves?\s+production\s+readiness", re.IGNORECASE),
    re.compile(r"(?:proves?|establish(?:es|ed)?|demonstrat(?:es|ed)?)\s+representative\s+real[- ]model\s+performance", re.IGNORECASE),
    re.compile(r"attestation\s+(?:proves|guarantees)\s+(?:the\s+)?software\s+is\s+secure", re.IGNORECASE),
)


class GithubPrereleaseError(ValueError):
    """Raised when the public prerelease contract or bundle is invalid."""


def _real_directory(path: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_dir() or candidate.is_symlink():
        raise GithubPrereleaseError(f"{label} must be an existing real directory: {candidate}")
    return candidate.resolve()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists() or not path.is_file() or path.is_symlink():
        raise GithubPrereleaseError(f"{label} is missing or not a real file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GithubPrereleaseError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise GithubPrereleaseError(f"{label} must contain a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(repository_root: Path) -> str:
    pyproject = repository_root / "pyproject.toml"
    if not pyproject.exists() or not pyproject.is_file() or pyproject.is_symlink():
        raise GithubPrereleaseError("pyproject.toml is missing or invalid.")
    match = _VERSION_PATTERN.search(pyproject.read_text(encoding="utf-8"))
    if match is None:
        raise GithubPrereleaseError("pyproject.toml does not contain a project version.")
    return match.group("version")


def _notes_path(version: str) -> Path:
    return Path(f"docs/RELEASE_NOTES_v{version}.md")


def _assert_publication_safe(text: str) -> None:
    for marker in _FORBIDDEN_PUBLIC_MARKERS:
        if marker in text:
            raise GithubPrereleaseError(f"Prerelease publication contains a prohibited private marker: {marker}")
    for pattern in _PROHIBITED_CLAIM_PATTERNS:
        if pattern.search(text):
            raise GithubPrereleaseError(
                f"Prerelease publication contains a prohibited unsupported claim: {pattern.pattern}"
            )


def _verify_workflow(workflow: str, version: str) -> None:
    required = (
        f"name: Publish attested v{version} prerelease",
        "python -m build",
        "python scripts/verify_github_prerelease.py",
        "actions/attest@v4",
        "subject-path: |",
        "release-bundle/*.whl",
        "release-bundle/*.tar.gz",
        "sbom-path: release-bundle/sbom.cdx.json",
        "gh attestation verify",
        "--predicate-type https://cyclonedx.org/bom",
        "gh release create",
        "--prerelease",
        '--target "$GITHUB_SHA"',
        "release-record.json",
        "SHA256SUMS",
        "needs: [build, attest]",
        "id-token: write",
        "attestations: write",
        "artifact-metadata: write",
    )
    for marker in required:
        if marker not in workflow:
            raise GithubPrereleaseError(f"Release workflow is missing required marker: {marker}")

    global_permissions = workflow.split("jobs:", 1)[0]
    for forbidden in (
        "contents: write",
        "id-token: write",
        "attestations: write",
        "artifact-metadata: write",
    ):
        if forbidden in global_permissions:
            raise GithubPrereleaseError(f"Release workflow grants global write permission: {forbidden}")
    if "contents: read" not in global_permissions:
        raise GithubPrereleaseError("Release workflow must be globally read-only.")

    if "  attest:" not in workflow or "  publish:" not in workflow:
        raise GithubPrereleaseError("Release workflow must contain separate attest and publish jobs.")
    attest_job = workflow.split("  attest:", 1)[1].split("  publish:", 1)[0]
    for required_permission in (
        "contents: read",
        "id-token: write",
        "attestations: write",
        "artifact-metadata: write",
    ):
        if required_permission not in attest_job:
            raise GithubPrereleaseError(
                f"Attestation job is missing scoped permission: {required_permission}"
            )
    if "contents: write" in attest_job:
        raise GithubPrereleaseError("Attestation job must not receive contents write permission.")
    if "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" not in attest_job:
        raise GithubPrereleaseError("Attestation job is not restricted to a main-branch push.")


def verify_github_prerelease_contract(root: Path) -> dict[str, Any]:
    """Verify the static public prerelease contract against repository evidence."""

    repository_root = _real_directory(Path(root), "Repository root")
    contract = _read_json(repository_root / _CONTRACT_PATH, "GitHub prerelease contract")
    if set(contract) != _EXPECTED_CONTRACT_KEYS:
        raise GithubPrereleaseError(
            "Prerelease contract schema is not exact: "
            f"missing={sorted(_EXPECTED_CONTRACT_KEYS - set(contract))}, "
            f"extra={sorted(set(contract) - _EXPECTED_CONTRACT_KEYS)}"
        )

    version = _package_version(repository_root)
    notes_path = _notes_path(version)
    workflow_path = repository_root / _WORKFLOW_PATH
    for path, label in (
        (repository_root / notes_path, "Release notes"),
        (workflow_path, "Release workflow"),
        (repository_root / _CITATION_PROVENANCE_PATH, "Citation provenance"),
        (repository_root / _SUPPLY_CHAIN_MANIFEST_PATH, "Supply-chain manifest"),
        (repository_root / _SBOM_PATH, "CycloneDX SBOM"),
    ):
        if not path.exists() or not path.is_file() or path.is_symlink():
            raise GithubPrereleaseError(f"{label} is missing or invalid: {path}")

    expected = {
        "schema_version": "arena-github-prerelease-v2",
        "project": "Agent Reliability Arena",
        "version": version,
        "tag": f"v{version}",
        "release_title": f"Agent Reliability Arena v{version}",
        "prerelease": True,
        "target_branch": "main",
        "release_notes": notes_path.as_posix(),
        "changelog_heading": f"## v{version}",
        "source_repository": "https://github.com/Luca-1304/agent-reliability-arena",
        "provenance_attestation_required": True,
        "sbom_attestation_required": True,
        "attestation_action": "actions/attest@v4",
        "attestation_signer_workflow": _WORKFLOW_PATH.as_posix(),
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
    for key, expected_value in expected.items():
        if contract.get(key) != expected_value:
            raise GithubPrereleaseError(
                f"Prerelease contract field {key!r} does not match expected value {expected_value!r}."
            )

    primary_artifacts = contract.get("primary_artifacts")
    if primary_artifacts != [
        "wheel",
        "source_distribution",
        "release_notes",
        "release_contract",
        "showcase_manifest",
        "launch_package_manifest",
        "citation_provenance",
        "supply_chain_manifest",
        "cyclonedx_sbom",
    ]:
        raise GithubPrereleaseError("Prerelease primary artifact allow-list is not exact.")

    changelog = (repository_root / "CHANGELOG.md").read_text(encoding="utf-8")
    if contract["changelog_heading"] not in changelog:
        raise GithubPrereleaseError("Changelog does not contain the prerelease version heading.")

    showcase = verify_showcase_release(repository_root)
    launch = verify_launch_package(repository_root)
    supply_chain = verify_supply_chain_package(repository_root)
    showcase_digest = str(showcase["manifest_digest"])
    launch_digest = str(launch["manifest_digest"])
    if contract.get("source_showcase_manifest_digest") != showcase_digest:
        raise GithubPrereleaseError("Prerelease showcase manifest digest does not match verified evidence.")
    if contract.get("source_launch_manifest_digest") != launch_digest:
        raise GithubPrereleaseError("Prerelease launch manifest digest does not match verified evidence.")
    if supply_chain.get("version") != version or supply_chain.get("release_tag") != f"v{version}":
        raise GithubPrereleaseError("Supply-chain package does not match the prerelease version.")

    source_hashes = {
        "source_citation_provenance_sha256": _sha256(repository_root / _CITATION_PROVENANCE_PATH),
        "source_supply_chain_manifest_sha256": _sha256(repository_root / _SUPPLY_CHAIN_MANIFEST_PATH),
        "source_sbom_sha256": _sha256(repository_root / _SBOM_PATH),
    }
    for key, expected_hash in source_hashes.items():
        if contract.get(key) != expected_hash:
            raise GithubPrereleaseError(f"Prerelease contract source hash mismatch: {key}")

    notes = (repository_root / notes_path).read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    required_note_markers = (
        "deterministic fixture",
        "provider-free",
        "prerelease",
        "No real-provider benchmark",
        "not production readiness",
        "CycloneDX SBOM",
        "artifact attestation",
        "gh attestation verify",
        "provider_called: false",
        "comparative_claim_permitted: false",
    )
    lowered_notes = notes.lower()
    for marker in required_note_markers:
        if marker.lower() not in lowered_notes:
            raise GithubPrereleaseError(f"Release notes are missing required boundary text: {marker}")
    _verify_workflow(workflow, version)

    public_text = json.dumps(contract, sort_keys=True) + "\n" + notes
    _assert_publication_safe(public_text)

    return {
        "version": version,
        "tag": contract["tag"],
        "release_title": contract["release_title"],
        "prerelease": True,
        "showcase_manifest_digest": showcase_digest,
        "launch_manifest_digest": launch_digest,
        "citation_provenance_sha256": source_hashes["source_citation_provenance_sha256"],
        "supply_chain_manifest_sha256": source_hashes["source_supply_chain_manifest_sha256"],
        "sbom_sha256": source_hashes["source_sbom_sha256"],
        "provenance_attestation_required": True,
        "sbom_attestation_required": True,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }


def build_github_prerelease_bundle(
    root: Path,
    dist_directory: Path,
    output_directory: Path,
    *,
    source_commit: str,
) -> dict[str, Any]:
    """Build the exact public prerelease asset bundle from verified inputs."""

    repository_root = _real_directory(Path(root), "Repository root")
    dist_root = _real_directory(Path(dist_directory), "Distribution directory")
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise GithubPrereleaseError(f"Release output directory must not already exist: {output}")
    if not _COMMIT_PATTERN.fullmatch(source_commit):
        raise GithubPrereleaseError("Source commit must be a lowercase 40-character hexadecimal SHA.")

    summary = verify_github_prerelease_contract(repository_root)
    version = summary["version"]
    wheels = sorted(dist_root.glob(f"agent_reliability_arena-{version}-*.whl"))
    sources = sorted(dist_root.glob(f"agent_reliability_arena-{version}.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise GithubPrereleaseError(
            "Distribution directory must contain exactly one matching wheel and one matching source archive."
        )
    for artifact in (*wheels, *sources):
        if artifact.is_symlink() or not artifact.is_file():
            raise GithubPrereleaseError(f"Distribution artifact must be a real file: {artifact}")

    source_paths = [
        (wheels[0], wheels[0].name),
        (sources[0], sources[0].name),
        (repository_root / _notes_path(version), _notes_path(version).name),
        (repository_root / _CONTRACT_PATH, _CONTRACT_PATH.name),
        (repository_root / _SHOWCASE_MANIFEST_PATH, _SHOWCASE_MANIFEST_PATH.name),
        (repository_root / _LAUNCH_MANIFEST_PATH, _LAUNCH_MANIFEST_PATH.name),
        (repository_root / _CITATION_PROVENANCE_PATH, "provenance.json"),
        (repository_root / _SUPPLY_CHAIN_MANIFEST_PATH, _SUPPLY_CHAIN_MANIFEST_PATH.name),
        (repository_root / _SBOM_PATH, _SBOM_PATH.name),
    ]
    output.mkdir(parents=True, exist_ok=False)
    copied: dict[str, Path] = {}
    for source_path, target_name in source_paths:
        if source_path.is_symlink() or not source_path.exists() or not source_path.is_file():
            raise GithubPrereleaseError(f"Release source must be a real file: {source_path}")
        target = output / target_name
        if target.name in copied:
            raise GithubPrereleaseError(f"Release bundle filename collision: {target.name}")
        shutil.copyfile(source_path, target)
        copied[target.name] = target

    artifact_hashes = {name: _sha256(path) for name, path in sorted(copied.items())}
    record = {
        "schema_version": "arena-github-prerelease-record-v2",
        "project": "Agent Reliability Arena",
        "version": version,
        "tag": summary["tag"],
        "release_title": summary["release_title"],
        "prerelease": True,
        "source_commit": source_commit,
        "showcase_manifest_digest": summary["showcase_manifest_digest"],
        "launch_manifest_digest": summary["launch_manifest_digest"],
        "provenance_attestation_required": True,
        "sbom_attestation_required": True,
        "attestation_signer_workflow": _WORKFLOW_PATH.as_posix(),
        "artifacts": artifact_hashes,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
    record_path = output / "release-record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checksum_targets = {**copied, record_path.name: record_path}
    checksum_lines = [
        f"{_sha256(path)}  {name}"
        for name, path in sorted(checksum_targets.items())
    ]
    (output / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    return {
        "version": version,
        "tag": summary["tag"],
        "source_commit": source_commit,
        "primary_artifact_count": len(copied),
        "checksum_entry_count": len(checksum_lines),
        "provenance_attestation_required": True,
        "sbom_attestation_required": True,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
