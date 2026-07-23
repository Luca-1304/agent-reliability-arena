from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.published_release import (
    PublishedReleaseError,
    verify_downloaded_release,
    verify_reproduced_fixture,
)


SOURCE_COMMIT = "3" * 40
VERSION = "0.2.0rc2"
TAG = f"v{VERSION}"
TITLE = f"Agent Reliability Arena {TAG}"
PRIMARY_NAMES = {
    f"agent_reliability_arena-{VERSION}-py3-none-any.whl",
    f"agent_reliability_arena-{VERSION}.tar.gz",
    f"RELEASE_NOTES_v{VERSION}.md",
    "github-prerelease.json",
    "publication-manifest.json",
    "launch-package-manifest.json",
    "provenance.json",
    "supply-chain-manifest.json",
    "sbom.cdx.json",
}
EXPECTED_NAMES = PRIMARY_NAMES | {"release-record.json", "SHA256SUMS"}


class PublishedReleaseTests(unittest.TestCase):
    def test_accepts_rc2_release_record_v2_and_exact_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, release_dir, metadata_path = _build_fixture(Path(directory))

            summary = verify_downloaded_release(root, release_dir, metadata_path)

            self.assertEqual(summary["schema_version"], "arena-published-release-download-v1")
            self.assertEqual(summary["version"], VERSION)
            self.assertEqual(summary["tag"], TAG)
            self.assertEqual(summary["source_commit"], SOURCE_COMMIT)
            self.assertEqual(summary["asset_count"], 11)
            self.assertEqual(summary["checksum_entry_count"], 10)
            self.assertFalse(summary["provider_called"])
            self.assertFalse(summary["comparative_claim_permitted"])

    def test_rejects_retired_v1_record_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, release_dir, metadata_path = _build_fixture(
                Path(directory), record_schema="arena-github-prerelease-record-v1"
            )

            with self.assertRaisesRegex(PublishedReleaseError, "record schema"):
                verify_downloaded_release(root, release_dir, metadata_path)

    def test_rejects_extra_release_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, release_dir, metadata_path = _build_fixture(Path(directory))
            (release_dir / "unexpected-debug.log").write_text("not public\n", encoding="utf-8")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["assets"].append({"name": "unexpected-debug.log"})
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(PublishedReleaseError, "asset inventory"):
                verify_downloaded_release(root, release_dir, metadata_path)

    def test_rejects_checksum_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, release_dir, metadata_path = _build_fixture(Path(directory))
            wheel = release_dir / f"agent_reliability_arena-{VERSION}-py3-none-any.whl"
            wheel.write_bytes(wheel.read_bytes() + b"tamper")

            with self.assertRaisesRegex(PublishedReleaseError, "checksum|digest"):
                verify_downloaded_release(root, release_dir, metadata_path)

    def test_accepts_byte_identical_fixture_reproduction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            reference, reproduced, public_output = _build_reproduction_fixture(Path(directory))

            summary = verify_reproduced_fixture(reference, reproduced, public_output)

            self.assertEqual(summary["schema_version"], "arena-published-release-reproduction-v1")
            self.assertEqual(summary["files_verified"], 3)
            self.assertEqual(summary["general_verified_complete"], 2)
            self.assertEqual(summary["specialist_verified_complete"], 6)
            self.assertEqual(summary["additional_logical_model_calls"], 36)
            self.assertFalse(summary["provider_called"])
            self.assertFalse(summary["comparative_claim_permitted"])

    def test_rejects_reproduced_output_byte_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            reference, reproduced, public_output = _build_reproduction_fixture(Path(directory))
            report = reproduced / "report.md"
            report.write_bytes(report.read_bytes() + b"mutated")

            with self.assertRaisesRegex(PublishedReleaseError, "reproduced output mismatch"):
                verify_reproduced_fixture(reference, reproduced, public_output)


def _build_fixture(
    base: Path,
    *,
    record_schema: str = "arena-github-prerelease-record-v2",
) -> tuple[Path, Path, Path]:
    root = base / "repo"
    release_dir = base / "download"
    metadata_path = base / "release-metadata.json"
    (root / "release").mkdir(parents=True)
    release_dir.mkdir()

    contract = {
        "schema_version": "arena-github-prerelease-v2",
        "project": "Agent Reliability Arena",
        "version": VERSION,
        "tag": TAG,
        "release_title": TITLE,
        "prerelease": True,
        "source_repository": "https://github.com/Luca-1304/agent-reliability-arena",
        "attestation_signer_workflow": ".github/workflows/release.yml",
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
    (root / "release/github-prerelease.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )

    for name in sorted(PRIMARY_NAMES):
        if name == "github-prerelease.json":
            payload = json.dumps(contract, indent=2).encode("utf-8") + b"\n"
        elif name == "sbom.cdx.json":
            payload = json.dumps(
                {
                    "bomFormat": "CycloneDX",
                    "serialNumber": "urn:uuid:a051633f-39f2-5f1b-b7af-3272e34636df",
                    "specVersion": "1.6",
                },
                indent=2,
            ).encode("utf-8") + b"\n"
        else:
            payload = f"fixture:{name}\n".encode("utf-8")
        (release_dir / name).write_bytes(payload)

    artifact_hashes = {
        name: hashlib.sha256((release_dir / name).read_bytes()).hexdigest()
        for name in sorted(PRIMARY_NAMES)
    }
    record = {
        "schema_version": record_schema,
        "project": "Agent Reliability Arena",
        "version": VERSION,
        "tag": TAG,
        "release_title": TITLE,
        "prerelease": True,
        "source_commit": SOURCE_COMMIT,
        "showcase_manifest_digest": "a" * 64,
        "launch_manifest_digest": "b" * 64,
        "provenance_attestation_required": True,
        "sbom_attestation_required": True,
        "attestation_signer_workflow": ".github/workflows/release.yml",
        "artifacts": artifact_hashes,
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
    record_path = release_dir / "release-record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checksum_names = sorted(PRIMARY_NAMES | {"release-record.json"})
    checksum_lines = [
        f"{hashlib.sha256((release_dir / name).read_bytes()).hexdigest()}  {name}"
        for name in checksum_names
    ]
    (release_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    metadata = {
        "tagName": TAG,
        "name": TITLE,
        "isPrerelease": True,
        "targetCommitish": SOURCE_COMMIT,
        "publishedAt": "2026-07-23T16:31:18Z",
        "url": f"https://github.com/Luca-1304/agent-reliability-arena/releases/tag/{TAG}",
        "assets": [{"name": name} for name in sorted(EXPECTED_NAMES)],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return root, release_dir, metadata_path


def _build_reproduction_fixture(base: Path) -> tuple[Path, Path, Path]:
    reference = base / "reference"
    reproduced = base / "reproduced"
    public_output = base / "public.json"
    reference.mkdir()
    reproduced.mkdir()

    payloads = {
        "aggregate_metrics.json": b'{"fixture":true}\n',
        "paired_results.jsonl": b'{"pair":1}\n',
        "report.md": b"# Deterministic report\n",
    }
    for name, payload in payloads.items():
        (reference / name).write_bytes(payload)
        (reproduced / name).write_bytes(payload)

    public_output.write_text(
        json.dumps(
            {
                "evidence_status": "deterministic_fixture",
                "metrics": {
                    "conditions": {
                        "general": {"verified_complete": 2},
                        "specialist": {"verified_complete": 6},
                    },
                    "paired": {"additional_logical_model_calls": 36},
                },
            }
        ),
        encoding="utf-8",
    )
    return reference, reproduced, public_output


if __name__ == "__main__":
    unittest.main()
