from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from agent_reliability_arena.citation_package import (
    CitationPackageError,
    verify_citation_package,
)


ROOT = Path(__file__).resolve().parents[1]


class CitationPackageTests(unittest.TestCase):
    def test_verified_package_matches_public_release_and_evidence(self) -> None:
        summary = verify_citation_package(ROOT)

        self.assertEqual(summary["project"], "Agent Reliability Arena")
        self.assertEqual(summary["version"], "0.2.0rc2")
        self.assertEqual(summary["release_tag"], "v0.2.0rc2")
        self.assertEqual(summary["release_date"], "2026-07-23")
        self.assertEqual(
            summary["release_url"],
            "https://github.com/Luca-1304/agent-reliability-arena/releases/tag/v0.2.0rc2",
        )
        self.assertEqual(summary["files_verified"], 4)
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

    def test_public_documents_keep_evidence_classes_and_limitations_explicit(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "CITATION.cff",
                "docs/TECHNICAL_REPORT.md",
                "docs/REPRODUCIBILITY.md",
                "citation/provenance.json",
            )
        )
        required = (
            "deterministic fixture",
            "provider-free",
            "No real-provider benchmark",
            "not production readiness",
            "comparative_claim_permitted",
        )
        for marker in required:
            self.assertIn(marker.lower(), combined.lower())

        forbidden = (
            "OPENAI_API_KEY",
            "private-evidence/",
            "provider_request_id",
            "INTERNAL_OPERATOR_NOTE",
            "external_execution_enabled=true",
            "transport-calls.jsonl",
            "C:\\Users\\",
            "/home/",
        )
        for marker in forbidden:
            self.assertNotIn(marker, combined)

    def test_reproducibility_commands_are_provider_free(self) -> None:
        text = (ROOT / "docs/REPRODUCIBILITY.md").read_text(encoding="utf-8")
        for command in (
            "arena-run",
            "arena-replay",
            "arena-export-web",
            "arena-preflight-pilot",
            "arena-verify-showcase",
            "arena-verify-launch-package",
            "arena-verify-citation-package",
        ):
            self.assertIn(command, text)
        self.assertIn("provider_called: false", text)
        self.assertNotIn("run_private_pilot.py", text)

    def test_tampered_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "repository"
            copytree(ROOT, copied)
            report = copied / "docs/TECHNICAL_REPORT.md"
            report.write_text(
                report.read_text(encoding="utf-8") + "\nThis proves universal model superiority.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CitationPackageError, "digest|claim|superiority|prohibited"):
                verify_citation_package(copied)

    def test_provenance_schema_is_closed_and_hash_pinned(self) -> None:
        provenance = json.loads((ROOT / "citation/provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(provenance),
            {
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
            },
        )
        self.assertEqual(len(provenance["files"]), 3)
        for item in provenance["files"]:
            self.assertEqual(set(item), {"path", "sha256"})
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
