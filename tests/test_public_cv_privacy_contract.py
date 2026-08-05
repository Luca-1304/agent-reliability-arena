from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verify_public_cv import PublicCvPrivacyError, _validate_pdf_urls

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_public_cv.py"
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"


def pdfinfo_urls(*urls: str) -> str:
    rows = ["Page  Type          URL"]
    rows.extend(
        f"{index:4d}  Annotation    {url}"
        for index, url in enumerate(urls, start=1)
    )
    return "\n".join(rows) + "\n"


class PublicCvPrivacyContract(unittest.TestCase):
    def test_verifier_exists_and_is_fail_closed(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            "PublicCvPrivacyError",
            "pdftotext",
            "pdfinfo",
            "-custom",
            "-meta",
            "-url",
            "-js",
            "pdfdetach",
            "FORBIDDEN_PATTERNS",
            "ALLOWED_EMAIL",
            "private_contact_details_permitted",
            "referee_contact_details_permitted",
            "credential_identifiers_permitted",
            "retired_host_links_permitted",
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

    def test_reviewed_public_links_are_accepted(self) -> None:
        urls = _validate_pdf_urls(
            pdfinfo_urls(
                "https://github.com/Luca-1304",
                "https://luca-1304.github.io/agent-reliability-arena/",
                "mailto:lucapanay13@gmail.com",
            )
        )
        self.assertEqual(len(urls), 3)

    def test_retired_host_annotation_is_rejected(self) -> None:
        with self.assertRaisesRegex(PublicCvPrivacyError, "retired publication host"):
            _validate_pdf_urls(
                pdfinfo_urls("https://old-portfolio.example.vercel.app/cv")
            )

    def test_non_https_and_script_links_are_rejected(self) -> None:
        for url in (
            "http://example.com/cv",
            "javascript:alert(1)",
            "file:///tmp/private.txt",
        ):
            with self.subTest(url=url), self.assertRaisesRegex(
                PublicCvPrivacyError, "non-HTTPS"
            ):
                _validate_pdf_urls(pdfinfo_urls(url))

    def test_private_hosts_and_credential_urls_are_rejected(self) -> None:
        cases = (
            ("https://127.0.0.1/private", "non-public host"),
            ("https://localhost/private", "non-public host"),
            ("https://user:pass@example.com/", "embedded credentials"),
            ("https://example.com/cv?api_key=value", "credential-like"),
            ("https://example.com:8443/cv", "non-standard"),
        )
        for url, message in cases:
            with self.subTest(url=url), self.assertRaisesRegex(
                PublicCvPrivacyError, message
            ):
                _validate_pdf_urls(pdfinfo_urls(url))

    def test_mail_link_is_exactly_allow_listed(self) -> None:
        with self.assertRaisesRegex(PublicCvPrivacyError, "email allow-list"):
            _validate_pdf_urls(pdfinfo_urls("mailto:private@example.com"))

    def test_unrecognised_pdfinfo_url_rows_fail_closed(self) -> None:
        with self.assertRaisesRegex(PublicCvPrivacyError, "Unrecognised"):
            _validate_pdf_urls("unexpected row\n")

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
