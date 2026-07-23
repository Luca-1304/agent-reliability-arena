from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.github_prerelease import (
    GithubPrereleaseError,
    build_github_prerelease_bundle,
    verify_github_prerelease_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class GithubPrereleaseTests(unittest.TestCase):
    def test_verified_contract_matches_rc2_and_public_evidence(self) -> None:
        summary = verify_github_prerelease_contract(ROOT)

        self.assertEqual(summary["version"], "0.2.0rc2")
        self.assertEqual(summary["tag"], "v0.2.0rc2")
        self.assertEqual(summary["release_title"], "Agent Reliability Arena v0.2.0rc2")
        self.assertTrue(summary["prerelease"])
        self.assertTrue(summary["provenance_attestation_required"])
        self.assertTrue(summary["sbom_attestation_required"])
        self.assertFalse(summary["provider_called"])
        self.assertFalse(summary["comparative_claim_permitted"])
        self.assertEqual(
            summary["showcase_manifest_digest"],
            "30061fec34ed199b6dcec650b78a7ee320166d11f08c74302871015fb4ca12e7",
        )
        self.assertEqual(
            summary["launch_manifest_digest"],
            "620c658240e4b05571de47dd66be13fbde72a6540ba06ba977d8056caf17427e",
        )

    def test_bundle_records_nine_primary_artifacts_commit_and_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            dist = temp / "dist"
            output = temp / "release"
            dist.mkdir()
            wheel = dist / "agent_reliability_arena-0.2.0rc2-py3-none-any.whl"
            source = dist / "agent_reliability_arena-0.2.0rc2.tar.gz"
            wheel.write_bytes(b"fixture wheel bytes")
            source.write_bytes(b"fixture source bytes")

            summary = build_github_prerelease_bundle(
                ROOT,
                dist,
                output,
                source_commit="a" * 40,
            )

            self.assertEqual(summary["source_commit"], "a" * 40)
            self.assertEqual(summary["primary_artifact_count"], 9)
            self.assertEqual(summary["checksum_entry_count"], 10)
            self.assertFalse(summary["provider_called"])
            self.assertFalse(summary["comparative_claim_permitted"])
            record = json.loads((output / "release-record.json").read_text(encoding="utf-8"))
            self.assertEqual(record["source_commit"], "a" * 40)
            self.assertTrue(record["provenance_attestation_required"])
            self.assertTrue(record["sbom_attestation_required"])
            self.assertEqual(record["artifacts"][wheel.name], hashlib.sha256(wheel.read_bytes()).hexdigest())
            self.assertEqual(record["artifacts"][source.name], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertIn("sbom.cdx.json", record["artifacts"])
            self.assertIn("supply-chain-manifest.json", record["artifacts"])
            self.assertIn("provenance.json", record["artifacts"])
            checksum_lines = (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(line.endswith("  release-record.json") for line in checksum_lines))
            self.assertEqual(len(checksum_lines), 10)

    def test_rc1_history_remains_and_rc2_notes_are_publication_safe(self) -> None:
        self.assertTrue((ROOT / "docs/RELEASE_NOTES_v0.2.0rc1.md").is_file())
        contract = json.loads((ROOT / "release/github-prerelease.json").read_text(encoding="utf-8"))
        notes = (ROOT / "docs/RELEASE_NOTES_v0.2.0rc2.md").read_text(encoding="utf-8")
        combined = json.dumps(contract, sort_keys=True) + "\n" + notes

        for marker in (
            "OPENAI_API_KEY",
            "private-evidence/",
            "provider_request_id",
            "INTERNAL_OPERATOR_NOTE",
            "external_execution_enabled=true",
            "transport-calls.jsonl",
            "C:\\Users\\",
            "/home/",
        ):
            self.assertNotIn(marker, combined)

        for required in (
            "deterministic fixture",
            "provider-free",
            "prerelease",
            "No real-provider benchmark",
            "not production readiness",
            "CycloneDX SBOM",
            "artifact attestation",
            "gh attestation verify",
        ):
            self.assertIn(required.lower(), combined.lower())

    def test_workflow_attests_only_on_main_and_publishes_after_attestation(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

        for marker in (
            "name: Publish attested v0.2.0rc2 prerelease",
            "pull_request:",
            "push:",
            "branches: [main]",
            "contents: read",
            "contents: write",
            "id-token: write",
            "attestations: write",
            "artifact-metadata: write",
            "python -m build",
            "python scripts/verify_github_prerelease.py",
            "release-record.json",
            "SHA256SUMS",
            "actions/attest@v4",
            "subject-checksums: release-bundle/SHA256SUMS",
            "sbom-path: release-bundle/sbom.cdx.json",
            "gh attestation verify",
            "--predicate-type https://cyclonedx.org/bom",
            "gh release create",
            "--prerelease",
            "--target \"$GITHUB_SHA\"",
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "needs: [build, attest]",
        ):
            self.assertIn(marker, workflow)

        global_permissions = workflow.split("jobs:", 1)[0]
        self.assertIn("contents: read", global_permissions)
        self.assertNotIn("contents: write", global_permissions)
        self.assertNotIn("id-token: write", global_permissions)
        self.assertNotIn("attestations: write", global_permissions)
        self.assertNotIn("artifact-metadata: write", global_permissions)

        attest_job = workflow.split("  attest:", 1)[1].split("  publish:", 1)[0]
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/main'", attest_job)
        self.assertNotIn("contents: write", attest_job)

    def test_verifier_rejects_unsupported_claim(self) -> None:
        notes_path = ROOT / "docs/RELEASE_NOTES_v0.2.0rc2.md"
        if not notes_path.exists():
            self.skipTest("rc2 release notes do not exist during the expected red phase")

        original = notes_path.read_text(encoding="utf-8")
        try:
            notes_path.write_text(original + "\nThis proves universal model superiority.\n", encoding="utf-8")
            with self.assertRaisesRegex(GithubPrereleaseError, "claim|superiority|prohibited"):
                verify_github_prerelease_contract(ROOT)
        finally:
            notes_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
