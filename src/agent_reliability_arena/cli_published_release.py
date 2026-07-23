from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .published_release import (
    PublishedReleaseError,
    verify_downloaded_release,
    verify_reproduced_fixture,
)


def verify_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arena-verify-published-release",
        description=(
            "Verify a downloaded public prerelease, its deterministic fixture "
            "reproduction and completed GitHub attestations."
        ),
    )
    parser.add_argument("--root", type=Path, required=True, help="Verifier repository root")
    parser.add_argument(
        "--release-dir",
        type=Path,
        required=True,
        help="Directory containing only downloaded public release assets",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="GitHub release metadata JSON",
    )
    parser.add_argument(
        "--reference-root",
        type=Path,
        required=True,
        help="Locked deterministic reference directory",
    )
    parser.add_argument(
        "--reproduced-root",
        type=Path,
        required=True,
        help="Output directory produced by the downloaded wheel",
    )
    parser.add_argument(
        "--public-output",
        type=Path,
        required=True,
        help="Public JSON export produced by the downloaded wheel",
    )
    parser.add_argument("--provenance-attestations", type=int, required=True)
    parser.add_argument("--cyclonedx-attestations", type=int, required=True)
    args = parser.parse_args(argv)

    if args.provenance_attestations != 2:
        parser.exit(1, "published-release verification failed: expected exactly 2 provenance attestations\n")
    if args.cyclonedx_attestations != 2:
        parser.exit(1, "published-release verification failed: expected exactly 2 CycloneDX attestations\n")

    try:
        release = verify_downloaded_release(args.root, args.release_dir, args.metadata)
        reproduction = verify_reproduced_fixture(
            args.reference_root,
            args.reproduced_root,
            args.public_output,
        )
    except PublishedReleaseError as exc:
        parser.exit(1, f"published-release verification failed: {exc}\n")

    record = {
        "schema_version": "arena-published-release-verification-v1",
        "project": release["project"],
        "version": release["version"],
        "tag": release["tag"],
        "release_title": release["release_title"],
        "release_url": release["release_url"],
        "published_at": release["published_at"],
        "source_commit": release["source_commit"],
        "source_repository": release["source_repository"],
        "attestation_signer_workflow": release["attestation_signer_workflow"],
        "asset_count": release["asset_count"],
        "checksum_entry_count": release["checksum_entry_count"],
        "cyclonedx_serial_number": release["cyclonedx_serial_number"],
        "reproduced_files_verified": reproduction["files_verified"],
        "general_verified_complete": reproduction["general_verified_complete"],
        "specialist_verified_complete": reproduction["specialist_verified_complete"],
        "additional_logical_model_calls": reproduction["additional_logical_model_calls"],
        "provenance_attestations_verified": args.provenance_attestations,
        "cyclonedx_attestations_verified": args.cyclonedx_attestations,
        "source_ref": "refs/heads/main",
        "provider_called": False,
        "comparative_claim_permitted": False,
        "security_certification_claimed": False,
        "production_readiness_claimed": False,
        "universal_reproducibility_claimed": False,
    }
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(verify_main())
