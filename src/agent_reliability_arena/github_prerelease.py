from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .launch_package import verify_launch_package
from .showcase_release import verify_showcase_release


_CONTRACT_PATH = Path("release/github-prerelease.json")
_NOTES_PATH = Path("docs/RELEASE_NOTES_v0.2.0rc1.md")
_SHOWCASE_MANIFEST_PATH = Path("showcase/publication-manifest.json")
_LAUNCH_MANIFEST_PATH = Path("showcase/launch-package-manifest.json")
_WORKFLOW_PATH = Path(".github/workflows/release.yml")
_VERSION_PATTERN = re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"\s*$', re.MULTILINE)
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
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
    re.compile(r"universal\s+model\s+superiority", re.IGNORECASE),
    re.compile(r"guarante(?:e|es|ed)\s+(?:complete\s+)?safety", re.IGNORECASE),
    re.compile(r"proves?\s+production\s+readiness", re.IGNORECASE),
    re.compile(r"representative\s+real[- ]model\s+performance", re.IGNORECASE),
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


def _assert_publication_safe(text: str) -> None:
    for marker in _FORBIDDEN_PUBLIC_MARKERS:
        if marker in text:
            raise GithubPrereleaseError(f"Prerelease publication contains a prohibited private marker: {marker}")
    for pattern in _PROHIBITED_CLAIM_PATTERNS:
        if pattern.search(text):
            raise GithubPrereleaseError(
                f"Prerelease publication contains a prohibited unsupported claim: {pattern.pattern}"
            )


def verify_github_prerelease_contract(root: Path) -> dict[str, Any]:
    """Verify the static public prerelease contract against repository evidence."""

    repository_root = _real_directory(Path(root), "Repository root")
    contract = _read_json(repository_root / _CONTRACT_PATH, "GitHub prerelease contract")
    notes_path = repository_root / _NOTES_PATH
    workflow_path = repository_root / _WORKFLOW_PATH
    if not notes_path.exists() or not notes_path.is_file() or notes_path.is_symlink():
        raise GithubPrereleaseError(f"Release notes are missing or invalid: {_NOTES_PATH}")
    if not workflow_path.exists() or not workflow_path.is_file() or workflow_path.is_symlink():
        raise GithubPrereleaseError(f"Release workflow is missing or invalid: {_WORKFLOW_PATH}")

    version = _package_version(repository_root)
    expected = {
        "schema_version": "arena-github-prerelease-v1",
        "project": "Agent Reliability Arena",
        "version": version,
        "tag": f"v{version}",
        "release_title": f"Agent Reliability Arena v{version}",
        "prerelease": True,
        "target_branch": "main",
        "release_notes": _NOTES_PATH.as_posix(),
        "changelog_heading": f"## v{version}",
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
    ]:
        raise GithubPrereleaseError("Prerelease primary artifact allow-list is not exact.")

    changelog = (repository_root / "CHANGELOG.md").read_text(encoding="utf-8")
    if contract["changelog_heading"] not in changelog:
        raise GithubPrereleaseError("Changelog does not contain the prerelease version heading.")

    showcase = verify_showcase_release(repository_root)
    launch = verify_launch_package(repository_root)
    showcase_digest = str(showcase["manifest_digest"])
    launch_digest = str(launch["manifest_digest"])
    if contract.get("source_showcase_manifest_digest") != showcase_digest:
        raise GithubPrereleaseError("Prerelease showcase manifest digest does not match verified evidence.")
    if contract.get("source_launch_manifest_digest") != launch_digest:
        raise GithubPrereleaseError("Prerelease launch manifest digest does not match verified evidence.")

    notes = notes_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    required_note_markers = (
        "deterministic fixture",
        "provider-free",
        "prerelease",
        "No real-provider benchmark",
        "not production readiness",
        "provider_called: false",
        "comparative_claim_permitted: false",
    )
    lowered_notes = notes.lower()
    for marker in required_note_markers:
        if marker.lower() not in lowered_notes:
            raise GithubPrereleaseError(f"Release notes are missing required boundary text: {marker}")

    required_workflow_markers = (
        "name: Publish verified v0.2.0rc1 prerelease",
        "python -m build",
        "python scripts/verify_github_prerelease.py",
        "gh release create",
        "--prerelease",
        "--target \"$GITHUB_SHA\"",
        "release-record.json",
        "SHA256SUMS",
    )
    for marker in required_workflow_markers:
        if marker not in workflow:
            raise GithubPrereleaseError(f"Release workflow is missing required marker: {marker}")

    public_text = json.dumps(contract, sort_keys=True) + "\n" + notes
    _assert_publication_safe(public_text)

    return {
        "version": version,
        "tag": contract["tag"],
        "release_title": contract["release_title"],
        "prerelease": True,
        "showcase_manifest_digest": showcase_digest,
        "launch_manifest_digest": launch_digest,
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
        wheels[0],
        sources[0],
        repository_root / _NOTES_PATH,
        repository_root / _CONTRACT_PATH,
        repository_root / _SHOWCASE_MANIFEST_PATH,
        repository_root / _LAUNCH_MANIFEST_PATH,
    ]
    output.mkdir(parents=True, exist_ok=False)
    copied: dict[str, Path] = {}
    for source_path in source_paths:
        if source_path.is_symlink() or not source_path.exists() or not source_path.is_file():
            raise GithubPrereleaseError(f"Release source must be a real file: {source_path}")
        target = output / source_path.name
        if target.name in copied:
            raise GithubPrereleaseError(f"Release bundle filename collision: {target.name}")
        shutil.copyfile(source_path, target)
        copied[target.name] = target

    artifact_hashes = {name: _sha256(path) for name, path in sorted(copied.items())}
    record = {
        "schema_version": "arena-github-prerelease-record-v1",
        "project": "Agent Reliability Arena",
        "version": version,
        "tag": summary["tag"],
        "release_title": summary["release_title"],
        "prerelease": True,
        "source_commit": source_commit,
        "showcase_manifest_digest": summary["showcase_manifest_digest"],
        "launch_manifest_digest": summary["launch_manifest_digest"],
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
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
