from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_public_cv.py"
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"


class PublicCvPrivacyContract(unittest.TestCase):
    def test_verifier_exists_and_is_fail_closed(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            "PublicCvPrivacyError",
            "pdftotext",
            "pdfinfo",
            "pdfdetach",
            "FORBIDDEN_PATTERNS",
            "ALLOWED_EMAIL",
            "private_contact_details_permitted",
            "referee_contact_details_permitted",
            "credential_identifiers_permitted",
        ):
            self.assertIn(marker, text)

    def test_privacy_rules_are_generic_not_personal_blocklists(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            "UK mobile number",
            "UK postcode",
            "date-of-birth field",
            "residential address field",
            "certificate identifier",
            "named referee field",
            "OpenAI key",
            "GitHub token",
            "private key",
            "assigned secret",
            "high-entropy bare token",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("EXACT_FORBIDDEN", text)

    def test_pages_pipeline_verifies_source_staged_and_live_cv(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "sudo apt-get update",
            "sudo apt-get install --yes poppler-utils",
            "python scripts/verify_public_cv.py",
            "python scripts/verify_public_cv.py --pdf _site/Luca_Panayiotou_CV.pdf",
            "pages-public-cv.pdf",
            "python scripts/verify_public_cv.py --pdf /tmp/pages-public-cv.pdf",
            "tests.test_public_cv_privacy_contract",
        ):
            self.assertIn(marker, workflow)


if __name__ == "__main__":
    unittest.main()
