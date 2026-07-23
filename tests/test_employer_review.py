from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMPLOYER = ROOT / "EMPLOYER_REVIEW.md"
README = ROOT / "README.md"
CONTRIBUTION = ROOT / "docs/CONTRIBUTION.md"
PROJECT_STATUS = ROOT / "docs/PROJECT_STATUS.md"

REQUIRED_HEADINGS = (
    "## 30-second summary",
    "## Verified evidence",
    "## What Luca owned",
    "## Review in five minutes",
    "## Code-review map",
    "## Technical decisions and trade-offs",
    "## Reproduce the public fixture",
    "## Role fit",
    "## What remains unproven",
)

REQUIRED_PATHS = (
    "src/agent_reliability_arena/live_orchestration.py",
    "src/agent_reliability_arena/private_pilot.py",
    "src/agent_reliability_arena/github_prerelease.py",
    "src/agent_reliability_arena/supply_chain.py",
    "tests/test_live_orchestration.py",
    "tests/test_private_pilot.py",
    "tests/test_github_prerelease.py",
    "tests/test_supply_chain_security.py",
    "reference_runs/fixture-v1/manifest.json",
    "web/index.html",
)

PROHIBITED_AFFIRMATIVE_CLAIMS = (
    "real-model benchmark completed",
    "production ready",
    "universally superior",
    "fully secure",
    "guaranteed safe",
    "measured provider cost efficiency",
)


class EmployerReviewTests(unittest.TestCase):
    def test_employer_review_contains_required_evidence_and_routes(self) -> None:
        self.assertTrue(EMPLOYER.is_file(), "EMPLOYER_REVIEW.md is required")
        text = EMPLOYER.read_text(encoding="utf-8")

        for heading in REQUIRED_HEADINGS:
            self.assertIn(heading, text)

        for relative in REQUIRED_PATHS:
            self.assertTrue((ROOT / relative).exists(), relative)
            self.assertIn(f"`{relative}`", text)

        for marker in (
            "2/8",
            "6/8",
            "36 additional logical role calls",
            "v0.2.0rc2",
            "provider_called: false",
            "comparative_claim_permitted: false",
            "AI-assisted implementation",
        ):
            self.assertIn(marker, text)

    def test_readme_first_contact_is_current_and_evidence_first(self) -> None:
        first_contact = "\n".join(
            README.read_text(encoding="utf-8").splitlines()[:90]
        )

        for marker in (
            "EMPLOYER_REVIEW.md",
            "v0.2.0rc2",
            "actions/workflows/tests.yml/badge.svg",
            "actions/workflows/codeql.yml/badge.svg",
            "actions/workflows/release.yml/badge.svg",
            "deterministic fixture",
            "provider-free integration",
            "No real-provider benchmark request or provider spend has been executed.",
        ):
            self.assertIn(marker, first_contact)

    def test_ownership_record_is_specific_and_transparent(self) -> None:
        text = CONTRIBUTION.read_text(encoding="utf-8")
        for marker in (
            "## Problem framing and acceptance standard",
            "## Architecture and authority constraints",
            "## Review and defect correction",
            "## AI-assisted implementation",
            "independently observed state",
            "repository evidence",
        ):
            self.assertIn(marker, text)

    def test_project_status_is_current_and_preserves_empirical_boundary(self) -> None:
        text = PROJECT_STATUS.read_text(encoding="utf-8")
        for marker in (
            "Last verified: 23 July 2026",
            "published prerelease",
            "attested",
            "Execution pending",
            "No real provider request has been used as benchmark evidence.",
        ):
            self.assertIn(marker, text)

    def test_employer_layer_rejects_unsupported_affirmative_claims(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (EMPLOYER, README, CONTRIBUTION, PROJECT_STATUS)
            if path.exists()
        )
        for claim in PROHIBITED_AFFIRMATIVE_CLAIMS:
            self.assertNotIn(claim, combined)


if __name__ == "__main__":
    unittest.main()
