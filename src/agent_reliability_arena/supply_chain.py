from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class SupplyChainError(RuntimeError):
    """Raised when the public supply-chain package fails closed."""


_MANIFEST_PATH = "security/supply-chain-manifest.json"
_SBOM_PATH = "security/sbom.cdx.json"
_EXPECTED_FILE_PATHS = (
    ".github/dependabot.yml",
    ".github/workflows/codeql.yml",
    "SECURITY.md",
    "docs/SUPPLY_CHAIN_SECURITY.md",
    _SBOM_PATH,
)
_EXPECTED_COMPONENT_NAMES = (
    "agent-reliability-arena",
    "agent-completion-verifier",
)
_PROHIBITED_MARKERS = (
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
    "fully secure",
    "vulnerability-free",
    "guaranteed secure",
    "proves there are no vulnerabilities",
    "production-ready security",
    "universal security",
)


def build_cyclonedx_sbom(root: Path) -> bytes:
    root = root.resolve()
    project = _read_project_metadata(root / "pyproject.toml")
    vendor = _read_json(root / "vendor_snapshot.json")

    project_name = str(project["name"])
    project_version = str(project["version"])
    vendor_name = "agent-completion-verifier"
    vendor_version = str(vendor["source_version"])
    vendor_commit = str(vendor["source_commit"])

    project_ref = f"pkg:pypi/{project_name}@{project_version}"
    vendor_ref = (
        f"pkg:github/Luca-1304/{vendor_name}@{vendor_version}"
        f"?vcs_url=git%2Bhttps%3A%2F%2Fgithub.com%2FLuca-1304%2F{vendor_name}.git%40{vendor_commit}"
    )

    project_component = {
        "bom-ref": project_ref,
        "description": str(project["description"]),
        "licenses": [{"license": {"id": str(project["license"])}}],
        "name": project_name,
        "purl": project_ref,
        "type": "application",
        "version": project_version,
    }
    vendor_component = {
        "bom-ref": vendor_ref,
        "externalReferences": [
            {
                "type": "vcs",
                "url": f"{vendor['source_repository']}/commit/{vendor_commit}",
            }
        ],
        "licenses": [{"license": {"id": "MIT"}}],
        "name": vendor_name,
        "properties": [
            {"name": "arena:vendored", "value": "true"},
            {"name": "arena:source-commit", "value": vendor_commit},
            {"name": "arena:file-count", "value": str(len(vendor["files"]))},
        ],
        "purl": vendor_ref,
        "type": "library",
        "version": vendor_version,
    }

    payload = {
        "bomFormat": "CycloneDX",
        "components": [project_component, vendor_component],
        "dependencies": [
            {"dependsOn": [vendor_ref], "ref": project_ref},
            {"dependsOn": [], "ref": vendor_ref},
        ],
        "metadata": {
            "component": project_component,
            "properties": [
                {
                    "name": "arena:declared-runtime-dependency-count",
                    "value": str(len(project["dependencies"])),
                },
                {
                    "name": "arena:build-requirements",
                    "value": json.dumps(project["build_requirements"], separators=(",", ":")),
                },
                {"name": "arena:deterministic", "value": "true"},
            ],
        },
        "specVersion": "1.6",
        "version": 1,
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def verify_supply_chain_package(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = _safe_path(root, _MANIFEST_PATH)
    manifest = _read_json(manifest_path)
    _require_exact_keys(
        manifest,
        {
            "build_requirements",
            "claims_boundary",
            "comparative_claim_permitted",
            "components",
            "exhaustive_security_scan_claimed",
            "files",
            "launch_manifest_digest",
            "project",
            "provider_called",
            "release_tag",
            "release_url",
            "runtime_dependency_count",
            "schema_version",
            "showcase_manifest_digest",
            "version",
        },
        "supply-chain manifest",
    )

    project = _read_project_metadata(root / "pyproject.toml")
    vendor = _read_json(root / "vendor_snapshot.json")
    showcase = _read_json(root / "showcase/publication-manifest.json")
    launch = _read_json(root / "showcase/launch-package-manifest.json")
    citation = _read_json(root / "citation/provenance.json")

    expected_scalars = {
        "schema_version": "arena-supply-chain-v1",
        "project": "Agent Reliability Arena",
        "version": project["version"],
        "release_tag": "v0.2.0rc1",
        "release_url": "https://github.com/Luca-1304/agent-reliability-arena/releases/tag/v0.2.0rc1",
        "runtime_dependency_count": len(project["dependencies"]),
        "build_requirements": project["build_requirements"],
        "provider_called": False,
        "comparative_claim_permitted": False,
        "exhaustive_security_scan_claimed": False,
        "showcase_manifest_digest": showcase["manifest_digest"],
        "launch_manifest_digest": launch["manifest_digest"],
    }
    for key, expected in expected_scalars.items():
        if manifest.get(key) != expected:
            raise SupplyChainError(f"supply-chain manifest {key} drift")

    if citation.get("release_tag") != manifest["release_tag"]:
        raise SupplyChainError("citation release tag drift")
    if citation.get("release_url") != manifest["release_url"]:
        raise SupplyChainError("citation release URL drift")

    expected_components = [
        {
            "name": project["name"],
            "source": "pyproject.toml",
            "type": "application",
            "version": project["version"],
        },
        {
            "name": "agent-completion-verifier",
            "source": vendor["source_repository"],
            "source_commit": vendor["source_commit"],
            "type": "vendored-library",
            "version": vendor["source_version"],
        },
    ]
    if manifest.get("components") != expected_components:
        raise SupplyChainError("supply-chain component inventory drift")

    files = manifest.get("files")
    if not isinstance(files, list):
        raise SupplyChainError("supply-chain manifest files must be a list")
    paths = [item.get("path") for item in files if isinstance(item, dict)]
    if tuple(paths) != _EXPECTED_FILE_PATHS:
        raise SupplyChainError("supply-chain file allow-list drift")

    public_text_parts: list[str] = []
    for item in files:
        _require_exact_keys(item, {"path", "sha256"}, "supply-chain file record")
        relative = item["path"]
        path = _safe_path(root, relative)
        if path.is_symlink() or not path.is_file():
            raise SupplyChainError(f"unsafe supply-chain file: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise SupplyChainError(f"supply-chain file hash drift: {relative}")
        if path.suffix in {".md", ".yml", ".yaml", ".json"}:
            public_text_parts.append(path.read_text(encoding="utf-8"))

    committed_sbom = _safe_path(root, _SBOM_PATH).read_bytes()
    regenerated_sbom = build_cyclonedx_sbom(root)
    if committed_sbom != regenerated_sbom:
        raise SupplyChainError("CycloneDX SBOM regeneration drift")

    sbom = json.loads(committed_sbom)
    _verify_sbom(sbom, project, vendor)
    _verify_security_policy(root / "SECURITY.md")
    _verify_automation(root)
    _scan_public_text("\n".join(public_text_parts))

    return {
        "build_requirements": project["build_requirements"],
        "comparative_claim_permitted": False,
        "component_count": len(sbom["components"]),
        "exhaustive_security_scan_claimed": False,
        "launch_manifest_digest": launch["manifest_digest"],
        "project": "Agent Reliability Arena",
        "provider_called": False,
        "release_tag": manifest["release_tag"],
        "runtime_dependency_count": len(project["dependencies"]),
        "showcase_manifest_digest": showcase["manifest_digest"],
        "version": project["version"],
    }


def _verify_sbom(sbom: dict[str, Any], project: dict[str, Any], vendor: dict[str, Any]) -> None:
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.6":
        raise SupplyChainError("invalid CycloneDX SBOM format")
    components = sbom.get("components")
    if not isinstance(components, list):
        raise SupplyChainError("SBOM components missing")
    names = tuple(component.get("name") for component in components if isinstance(component, dict))
    if names != _EXPECTED_COMPONENT_NAMES:
        raise SupplyChainError("SBOM component inventory drift")
    versions = {component["name"]: component.get("version") for component in components}
    if versions.get(project["name"]) != project["version"]:
        raise SupplyChainError("SBOM project version drift")
    if versions.get("agent-completion-verifier") != vendor["source_version"]:
        raise SupplyChainError("SBOM vendor version drift")


def _verify_security_policy(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    for marker in (
        "supported versions",
        "private vulnerability reporting",
        "github private vulnerability reporting",
        "do not include credentials",
        "no guarantee",
        "not an exhaustive security audit",
        "coordinated disclosure",
    ):
        if marker not in text:
            raise SupplyChainError(f"security policy missing marker: {marker}")


def _verify_automation(root: Path) -> None:
    codeql = (root / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
    dependabot = (root / ".github/dependabot.yml").read_text(encoding="utf-8")
    tests = (root / ".github/workflows/tests.yml").read_text(encoding="utf-8")

    for marker in (
        "security-events: write",
        "contents: read",
        "github/codeql-action/init@v4",
        "github/codeql-action/analyze@v4",
        "languages: [python]",
    ):
        if marker not in codeql:
            raise SupplyChainError(f"CodeQL workflow missing marker: {marker}")
    global_permissions = codeql.split("jobs:", 1)[0]
    if "security-events: write" in global_permissions:
        raise SupplyChainError("CodeQL security-events permission is not job-scoped")
    if "contents: write" in codeql:
        raise SupplyChainError("CodeQL workflow must not request contents write")

    for ecosystem in ('package-ecosystem: "pip"', 'package-ecosystem: "github-actions"'):
        if ecosystem not in dependabot:
            raise SupplyChainError(f"Dependabot missing ecosystem: {ecosystem}")

    for marker in (
        "python scripts/verify_supply_chain.py",
        "arena-verify-supply-chain --root .",
    ):
        if marker not in tests:
            raise SupplyChainError(f"test workflow missing supply-chain gate: {marker}")


def _scan_public_text(text: str) -> None:
    lowered = text.lower()
    for marker in _PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            raise SupplyChainError(f"prohibited private marker in supply-chain package: {marker}")
    for claim in _PROHIBITED_CLAIMS:
        if claim in lowered:
            raise SupplyChainError(f"prohibited security claim in supply-chain package: {claim}")


def _read_project_metadata(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - exercised on Python 3.10
        tomllib = None

    if tomllib is not None:
        payload = tomllib.loads(text)
        project = payload["project"]
        build = payload["build-system"]
        license_value = project.get("license", "MIT")
        if isinstance(license_value, dict):
            license_value = license_value.get("text") or license_value.get("file") or "MIT"
        return {
            "build_requirements": list(build.get("requires", [])),
            "dependencies": list(project.get("dependencies", [])),
            "description": project["description"],
            "license": license_value,
            "name": project["name"],
            "version": project["version"],
        }

    def _quoted(pattern: str) -> str:
        match = re.search(pattern, text, flags=re.MULTILINE)
        if not match:
            raise SupplyChainError(f"pyproject field missing: {pattern}")
        return match.group(1)

    def _array(section: str, key: str) -> list[str]:
        section_match = re.search(
            rf"^\[{re.escape(section)}\]\s*(.*?)(?=^\[|\Z)",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not section_match:
            raise SupplyChainError(f"pyproject section missing: {section}")
        match = re.search(rf"^{re.escape(key)}\s*=\s*\[(.*?)\]", section_match.group(1), flags=re.MULTILINE | re.DOTALL)
        if not match:
            return []
        return re.findall(r'"([^"]+)"', match.group(1))

    project_section = re.search(r"^\[project\]\s*(.*?)(?=^\[|\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not project_section:
        raise SupplyChainError("pyproject project section missing")
    project_text = project_section.group(1)
    return {
        "build_requirements": _array("build-system", "requires"),
        "dependencies": _array("project", "dependencies"),
        "description": _quoted(r'^description\s*=\s*"([^"]+)"'),
        "license": _quoted(r'^license\s*=\s*"([^"]+)"'),
        "name": _quoted(r'^name\s*=\s*"([^"]+)"'),
        "version": _quoted(r'^version\s*=\s*"([^"]+)"'),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SupplyChainError(f"cannot read JSON: {path.name}") from exc
    if not isinstance(payload, dict):
        raise SupplyChainError(f"JSON root must be an object: {path.name}")
    return payload


def _safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise SupplyChainError("unsafe supply-chain path")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SupplyChainError("supply-chain path escapes repository") from exc
    return candidate


def _require_exact_keys(payload: dict[str, Any], keys: set[str], label: str) -> None:
    actual = set(payload)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise SupplyChainError(f"{label} schema drift: missing={missing}, extra={extra}")
