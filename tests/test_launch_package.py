from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.launch_package import (
    LaunchPackageError,
    canonical_launch_manifest_digest,
    load_launch_manifest,
    verify_launch_package,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "showcase" / "launch-package-manifest.json"
EXPECTED_FILES = {
    "LAUNCH.md",
    "docs/COMMUNITY_SUBMISSIONS.md",
    "docs/CV_PROJECT_ENTRY.md",
    "docs/HOSTED_DEPLOYMENT.md",
    "docs/LAUNCH_POSTS.md",
    "docs/PORTFOLIO_PROJECT_ENTRY.md",
    "docs/RECRUITER_OUTREACH.md",
    "showcase/distribution-register.json",
}
EXPECTED_MANIFEST_KEYS = {
    "schema_version",
    "package_version",
    "project",
    "author",
    "source_showcase_manifest_digest",
    "source_showcase_version",
    "files",
    "distribution_register",
    "claims_boundary",
    "provider_called",
    "comparative_claim_permitted",
    "manifest_digest",
}


def copy_launch_package(destination: Path) -> None:
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    target_manifest = destination / "showcase" / "launch-package-manifest.json"
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_manifest.write_bytes(MANIFEST.read_bytes())
    for row in raw["files"]:
        source = ROOT / row["path"]
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


class LaunchPackageTests(unittest.TestCase):
    def test_manifest_has_exact_schema_digest_and_showcase_link(self) -> None:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(set(raw), EXPECTED_MANIFEST_KEYS)
        unsigned = dict(raw)
        supplied = unsigned.pop("manifest_digest")
        self.assertEqual(supplied, canonical_launch_manifest_digest(unsigned))
        self.assertEqual(raw["schema_version"], "arena-launch-package-v1")
        self.assertEqual(raw["package_version"], "0.2.0rc1-launch-package-1")
        self.assertEqual(raw["project"], "Agent Reliability Arena")
        self.assertEqual(raw["author"], "Luca Panayiotou")
        self.assertEqual(raw["source_showcase_version"], "0.2.0rc1-public-showcase-1")
        self.assertEqual(
            raw["source_showcase_manifest_digest"],
            "30061fec34ed199b6dcec650b78a7ee320166d11f08c74302871015fb4ca12e7",
        )
        self.assertFalse(raw["provider_called"])
        self.assertFalse(raw["comparative_claim_permitted"])
        self.assertEqual({row["path"] for row in raw["files"]}, EXPECTED_FILES)
        self.assertEqual(raw["files"], sorted(raw["files"], key=lambda row: row["path"]))
        self.assertEqual(raw["distribution_register"], "showcase/distribution-register.json")

    def test_complete_launch_package_verifies(self) -> None:
        manifest = load_launch_manifest(ROOT)
        summary = verify_launch_package(ROOT)
        self.assertEqual(summary["package_version"], manifest["package_version"])
        self.assertEqual(summary["files_verified"], len(EXPECTED_FILES))
        self.assertEqual(summary["repository_publications"], 1)
        self.assertGreaterEqual(summary["prepared_external_actions"], 4)
        self.assertEqual(summary["submitted_external_actions"], 0)
        self.assertFalse(summary["provider_called"])
        self.assertFalse(summary["comparative_claim_permitted"])

    def test_public_documents_contain_audience_and_claim_markers(self) -> None:
        required = {
            "LAUNCH.md": (
                "# Agent Reliability Arena — launch package",
                "## Verified public evidence",
                "## Use this package",
                "Luca Panayiotou",
                "AI-assisted implementation",
            ),
            "docs/CV_PROJECT_ENTRY.md": (
                "# CV project entry",
                "## Concise version",
                "## Expanded version",
                "deterministic fixture",
            ),
            "docs/PORTFOLIO_PROJECT_ENTRY.md": (
                "# Portfolio project entry",
                "## Problem",
                "## Engineering contribution",
                "## Evidence boundary",
            ),
            "docs/RECRUITER_OUTREACH.md": (
                "# Recruiter outreach",
                "## Initial message",
                "## Follow-up",
                "No message has been sent automatically",
            ),
            "docs/LAUNCH_POSTS.md": (
                "# Public launch posts",
                "## LinkedIn",
                "## Short-form",
                "deterministic fixture",
            ),
            "docs/COMMUNITY_SUBMISSIONS.md": (
                "# Technical-community submission copy",
                "## Technical submission",
                "## Discussion prompt",
                "not a real-model leaderboard",
            ),
            "docs/HOSTED_DEPLOYMENT.md": (
                "# Hosted deployment readiness",
                "## Verified source",
                "## Current state",
                "No hosted deployment is claimed live",
            ),
        }
        for relative, markers in required.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, relative)

    def test_distribution_register_uses_evidence_backed_states(self) -> None:
        raw = json.loads((ROOT / "showcase" / "distribution-register.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], "arena-distribution-register-v1")
        self.assertEqual(raw["project"], "Agent Reliability Arena")
        self.assertEqual(raw["author"], "Luca Panayiotou")
        entries = raw["entries"]
        self.assertIsInstance(entries, list)
        self.assertGreaterEqual(len(entries), 5)
        repository = [item for item in entries if item["state"] == "published_repository"]
        submitted = [item for item in entries if item["state"] == "submitted"]
        prepared = [item for item in entries if item["state"] == "prepared"]
        self.assertEqual(len(repository), 1)
        self.assertEqual(submitted, [])
        self.assertGreaterEqual(len(prepared), 4)
        self.assertTrue(repository[0]["public_url"])
        self.assertTrue(repository[0]["published_date"])
        for item in prepared:
            self.assertIsNone(item["public_url"])
            self.assertIsNone(item["published_date"])

    def test_verifier_rejects_digest_drift_and_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_launch_package(root)
            target = root / "docs" / "CV_PROJECT_ENTRY.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
            with self.assertRaisesRegex(LaunchPackageError, "digest"):
                verify_launch_package(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_launch_package(root)
            raw = json.loads((root / "showcase" / "launch-package-manifest.json").read_text(encoding="utf-8"))
            raw["files"].append({"path": "private-evidence/outreach.json", "sha256": "0" * 64})
            unsigned = dict(raw)
            unsigned.pop("manifest_digest")
            raw["manifest_digest"] = canonical_launch_manifest_digest(unsigned)
            (root / "showcase" / "launch-package-manifest.json").write_text(
                json.dumps(raw, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LaunchPackageError, "private|prohibited"):
                verify_launch_package(root)

    def test_verifier_rejects_sensitive_and_unsupported_copy(self) -> None:
        cases = (
            ("credential", "sk-examplecredentialmaterial123456"),
            ("absolute path", "/home/operator/private-run"),
            ("private evidence", "private-evidence/run-001"),
            ("provider identifier", "provider_request_id=private-123"),
            ("internal note", "INTERNAL_OPERATOR_NOTE: retain this"),
            ("enabled policy", "external_execution_enabled=true"),
            ("representative claim", "This proves representative model performance."),
            ("universal claim", "The orchestration is universally superior."),
            ("production claim", "This system is production-ready."),
        )
        for label, marker in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                copy_launch_package(root)
                target = root / "docs" / "LAUNCH_POSTS.md"
                target.write_text(target.read_text(encoding="utf-8") + f"\n{marker}\n", encoding="utf-8")
                raw = json.loads((root / "showcase" / "launch-package-manifest.json").read_text(encoding="utf-8"))
                for row in raw["files"]:
                    if row["path"] == "docs/LAUNCH_POSTS.md":
                        row["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                unsigned = dict(raw)
                unsigned.pop("manifest_digest")
                raw["manifest_digest"] = canonical_launch_manifest_digest(unsigned)
                (root / "showcase" / "launch-package-manifest.json").write_text(
                    json.dumps(raw, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(LaunchPackageError, "(?i)sensitive|unsupported|prohibited"):
                    verify_launch_package(root)

    def test_verifier_rejects_false_external_submission_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_launch_package(root)
            register = root / "showcase" / "distribution-register.json"
            raw_register = json.loads(register.read_text(encoding="utf-8"))
            external = next(item for item in raw_register["entries"] if item["state"] == "prepared")
            external["state"] = "submitted"
            register.write_text(json.dumps(raw_register, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            raw_manifest = json.loads((root / "showcase" / "launch-package-manifest.json").read_text(encoding="utf-8"))
            for row in raw_manifest["files"]:
                if row["path"] == "showcase/distribution-register.json":
                    row["sha256"] = hashlib.sha256(register.read_bytes()).hexdigest()
            unsigned = dict(raw_manifest)
            unsigned.pop("manifest_digest")
            raw_manifest["manifest_digest"] = canonical_launch_manifest_digest(unsigned)
            (root / "showcase" / "launch-package-manifest.json").write_text(
                json.dumps(raw_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LaunchPackageError, "submitted|URL|date"):
                verify_launch_package(root)


if __name__ == "__main__":
    unittest.main()
