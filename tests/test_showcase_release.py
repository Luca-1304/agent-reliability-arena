from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.showcase_release import (
    ShowcaseReleaseError,
    canonical_manifest_digest,
    load_showcase_manifest,
    verify_showcase_release,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "showcase" / "publication-manifest.json"
EXPECTED_MANIFEST_KEYS = {
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
EXPECTED_FILES = {
    "web/index.html",
    "web/styles.css",
    "web/app.js",
    "web/data/fixture-v1.json",
    "docs/PUBLICATION_BOUNDARY.md",
    "docs/EMPLOYER_TECHNICAL_SUMMARY.md",
    "docs/SHOWCASE_DEMO_SCRIPT.md",
}


def copy_public_bundle(destination: Path) -> None:
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    target_manifest = destination / "showcase" / "publication-manifest.json"
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_manifest.write_bytes(MANIFEST.read_bytes())
    for row in raw["files"]:
        source = ROOT / row["path"]
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


class ShowcaseReleaseTests(unittest.TestCase):
    def test_manifest_has_exact_schema_digest_and_public_boundary(self) -> None:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(set(raw), EXPECTED_MANIFEST_KEYS)
        unsigned = dict(raw)
        supplied = unsigned.pop("manifest_digest")
        self.assertEqual(supplied, canonical_manifest_digest(unsigned))
        self.assertEqual(raw["schema_version"], "arena-showcase-publication-v1")
        self.assertEqual(raw["showcase_version"], "0.2.0rc1-public-showcase-1")
        self.assertEqual(raw["evidence_class"], "deterministic_and_provider_free_showcase")
        self.assertEqual(raw["project"], "Agent Reliability Arena")
        self.assertEqual(raw["author"], "Luca Panayiotou")
        self.assertFalse(raw["provider_called"])
        self.assertFalse(raw["comparative_claim_permitted"])
        self.assertEqual({row["path"] for row in raw["files"]}, EXPECTED_FILES)
        self.assertEqual(raw["files"], sorted(raw["files"], key=lambda row: row["path"]))

    def test_complete_public_bundle_verifies_against_reference_metrics(self) -> None:
        manifest = load_showcase_manifest(ROOT)
        summary = verify_showcase_release(ROOT)
        self.assertEqual(summary["showcase_version"], manifest["showcase_version"])
        self.assertEqual(summary["files_verified"], len(EXPECTED_FILES))
        self.assertEqual(summary["evidence_class"], "deterministic_and_provider_free_showcase")
        self.assertEqual(summary["general_verified"], 2)
        self.assertEqual(summary["specialist_verified"], 6)
        self.assertEqual(summary["false_completion_reduction"], 3)
        self.assertEqual(summary["additional_logical_model_calls"], 36)
        self.assertFalse(summary["provider_called"])
        self.assertFalse(summary["comparative_claim_permitted"])

    def test_landing_page_contains_proof_architecture_attribution_and_limits(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        for marker in (
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
        ):
            self.assertIn(marker, html)

    def test_public_documents_contain_required_sections(self) -> None:
        required = {
            "docs/PUBLICATION_BOUNDARY.md": (
                "# Publication boundary",
                "## Public showcase material",
                "## Private operational material",
                "## Claims boundary",
            ),
            "docs/EMPLOYER_TECHNICAL_SUMMARY.md": (
                "# Agent Reliability Arena — technical summary",
                "## Engineering question",
                "## What is verified",
                "## What is not claimed",
                "Luca Panayiotou",
            ),
            "docs/SHOWCASE_DEMO_SCRIPT.md": (
                "# 90-second showcase demo",
                "## Script",
                "## On-screen route",
                "## Claims to avoid",
            ),
        }
        for relative, markers in required.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, relative)

    def test_verifier_rejects_digest_drift_and_unlisted_or_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_public_bundle(root)
            target = root / "docs" / "EMPLOYER_TECHNICAL_SUMMARY.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
            with self.assertRaisesRegex(ShowcaseReleaseError, "digest"):
                verify_showcase_release(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_public_bundle(root)
            raw = json.loads((root / "showcase" / "publication-manifest.json").read_text(encoding="utf-8"))
            raw["files"].append({"path": "private-evidence/run-1.json", "sha256": "0" * 64})
            unsigned = dict(raw)
            unsigned.pop("manifest_digest")
            raw["manifest_digest"] = canonical_manifest_digest(unsigned)
            (root / "showcase" / "publication-manifest.json").write_text(
                json.dumps(raw, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ShowcaseReleaseError, "prohibited|private"):
                verify_showcase_release(root)

    def test_verifier_rejects_sensitive_markers_paths_and_unsupported_claims(self) -> None:
        cases = (
            ("credential", "sk-examplecredentialmaterial123456"),
            ("absolute path", "/home/operator/private-run"),
            ("private evidence", "private-evidence/run-001"),
            ("provider identifier", "provider_request_id=private-123"),
            ("internal note", "INTERNAL_OPERATOR_NOTE: retain this"),
            ("unsupported claim", "This proves representative model performance."),
        )
        for label, marker in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                copy_public_bundle(root)
                target = root / "docs" / "SHOWCASE_DEMO_SCRIPT.md"
                target.write_text(target.read_text(encoding="utf-8") + f"\n{marker}\n", encoding="utf-8")
                raw = json.loads((root / "showcase" / "publication-manifest.json").read_text(encoding="utf-8"))
                for row in raw["files"]:
                    if row["path"] == "docs/SHOWCASE_DEMO_SCRIPT.md":
                        import hashlib

                        row["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                unsigned = dict(raw)
                unsigned.pop("manifest_digest")
                raw["manifest_digest"] = canonical_manifest_digest(unsigned)
                (root / "showcase" / "publication-manifest.json").write_text(
                    json.dumps(raw, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ShowcaseReleaseError, "sensitive|unsupported|prohibited"):
                    verify_showcase_release(root)


if __name__ == "__main__":
    unittest.main()
