from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.supply_chain import (
    SupplyChainError,
    build_cyclonedx_sbom,
    verify_supply_chain_package,
)


ROOT = Path(__file__).resolve().parents[1]


class SupplyChainSecurityTests(unittest.TestCase):
    def test_verified_package_matches_public_project_state(self) -> None:
        summary = verify_supply_chain_package(ROOT)

        self.assertEqual(summary["project"], "Agent Reliability Arena")
        self.assertEqual(summary["version"], "0.2.0rc1")
        self.assertEqual(summary["release_tag"], "v0.2.0rc1")
        self.assertEqual(summary["component_count"], 2)
        self.assertEqual(summary["runtime_dependency_count"], 0)
        self.assertEqual(summary["build_requirements"], ["setuptools>=68"])
        self.assertFalse(summary["provider_called"])
        self.assertFalse(summary["comparative_claim_permitted"])
        self.assertFalse(summary["exhaustive_security_scan_claimed"])
        self.assertEqual(
            summary["showcase_manifest_digest"],
            "30061fec34ed199b6dcec650b78a7ee320166d11f08c74302871015fb4ca12e7",
        )
        self.assertEqual(
            summary["launch_manifest_digest"],
            "620c658240e4b05571de47dd66be13fbde72a6540ba06ba977d8056caf17427e",
        )

    def test_committed_sbom_regenerates_byte_for_byte(self) -> None:
        expected = (ROOT / "security/sbom.cdx.json").read_bytes()
        self.assertEqual(build_cyclonedx_sbom(ROOT), expected)

        parsed = json.loads(expected)
        self.assertEqual(parsed["bomFormat"], "CycloneDX")
        self.assertEqual(parsed["specVersion"], "1.6")
        self.assertEqual(parsed["metadata"]["component"]["name"], "agent-reliability-arena")
        self.assertEqual(
            [component["name"] for component in parsed["components"]],
            ["agent-reliability-arena", "agent-completion-verifier"],
        )

    def test_public_security_policy_is_clear_and_non_exaggerated(self) -> None:
        policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
        for required in (
            "supported versions",
            "private vulnerability reporting",
            "github private vulnerability reporting",
            "do not include credentials",
            "no guarantee",
            "not an exhaustive security audit",
            "coordinated disclosure",
        ):
            self.assertIn(required, policy)

    def test_codeql_and_dependabot_are_least_privilege_and_reviewable(self) -> None:
        codeql = (ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
        dependabot = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")

        for marker in (
            "name: CodeQL",
            "pull_request:",
            "push:",
            "branches: [main]",
            "schedule:",
            "security-events: write",
            "contents: read",
            "languages: [python]",
        ):
            self.assertIn(marker, codeql)

        global_permissions = codeql.split("jobs:", 1)[0]
        self.assertIn("contents: read", global_permissions)
        self.assertNotIn("security-events: write", global_permissions)

        for marker in (
            'package-ecosystem: "pip"',
            'package-ecosystem: "github-actions"',
            'target-branch: "main"',
            "open-pull-requests-limit:",
        ):
            self.assertIn(marker, dependabot)

    def test_verifier_rejects_tampering_and_unsupported_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy_root = Path(directory) / "repo"
            _copy_public_security_package(ROOT, copy_root)

            security_path = copy_root / "SECURITY.md"
            security_path.write_text(
                security_path.read_text(encoding="utf-8")
                + "\nThis repository is fully secure and vulnerability-free.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SupplyChainError, "claim|secure|prohibited|hash"):
                verify_supply_chain_package(copy_root)

        with tempfile.TemporaryDirectory() as directory:
            copy_root = Path(directory) / "repo"
            _copy_public_security_package(ROOT, copy_root)
            sbom_path = copy_root / "security/sbom.cdx.json"
            payload = json.loads(sbom_path.read_text(encoding="utf-8"))
            payload["components"].append({"type": "library", "name": "hidden-component", "version": "1"})
            sbom_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SupplyChainError, "sbom|component|hash|drift"):
                verify_supply_chain_package(copy_root)


def _copy_public_security_package(source: Path, destination: Path) -> None:
    paths = (
        "pyproject.toml",
        "vendor_snapshot.json",
        "SECURITY.md",
        "docs/SUPPLY_CHAIN_SECURITY.md",
        "security/sbom.cdx.json",
        "security/supply-chain-manifest.json",
        "showcase/publication-manifest.json",
        "showcase/launch-package-manifest.json",
        "citation/provenance.json",
        ".github/workflows/tests.yml",
        ".github/workflows/codeql.yml",
        ".github/dependabot.yml",
    )
    for relative in paths:
        source_path = source / relative
        destination_path = destination / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_bytes(source_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
