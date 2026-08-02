from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "web" / "cinematic-plus" / "Luca_Panayiotou_CV.pdf"
ALLOWED_EMAIL = "lucapanay13@gmail.com"

FORBIDDEN_PATTERNS = {
    "UK mobile number": re.compile(r"\b(?:\+44\s?7\d{3}|07\d{3})[\s-]?\d{3}[\s-]?\d{3}\b"),
    "UK postcode": re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE),
    "date-of-birth field": re.compile(r"\b(?:date\s+of\s+birth|d\.?o\.?b\.?)\b", re.IGNORECASE),
    "residential address field": re.compile(r"\b(?:home|residential)\s+address\s*[:\-]", re.IGNORECASE),
    "certificate identifier": re.compile(r"\b[A-Z]{2,6}\d{6,}\b"),
    "named referee field": re.compile(r"\breferee\s*(?:name|email|phone|contact)?\s*[:\-]", re.IGNORECASE),
    "OpenAI key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned secret": re.compile(r"\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET)\s*=", re.IGNORECASE),
    "high-entropy bare token": re.compile(r"(?<![/:])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9_-])"),
}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
REQUIRED_PUBLIC_MARKERS = {
    "Luca Panayiotou",
    "Public CV",
    "personal and referee contact details intentionally omitted",
    ALLOWED_EMAIL,
}


class PublicCvPrivacyError(ValueError):
    """Raised when the public CV violates the publication boundary."""


def _run(command: list[str]) -> str:
    executable = command[0]
    if shutil.which(executable) is None:
        raise PublicCvPrivacyError(f"Required verifier command is unavailable: {executable}")
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise PublicCvPrivacyError(f"{executable} failed: {detail}")
    return completed.stdout


def verify(pdf_path: Path = DEFAULT_PDF) -> dict[str, object]:
    pdf = Path(pdf_path)
    if not pdf.is_file() or pdf.is_symlink():
        raise PublicCvPrivacyError(f"Public CV must be a real file: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise PublicCvPrivacyError("Public CV must use the PDF format.")

    text = _run(["pdftotext", "-layout", str(pdf), "-"])
    metadata = _run(["pdfinfo", str(pdf)])
    attachments = _run(["pdfdetach", "-list", str(pdf)]).strip()
    combined = f"{text}\n{metadata}"

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(combined):
            raise PublicCvPrivacyError(f"Forbidden {label} pattern found in public CV.")

    emails = {match.casefold() for match in EMAIL_PATTERN.findall(combined)}
    if emails != {ALLOWED_EMAIL.casefold()}:
        raise PublicCvPrivacyError(
            f"Public CV email set is not the reviewed allow-list: {sorted(emails)}"
        )

    for marker in REQUIRED_PUBLIC_MARKERS:
        if marker.casefold() not in combined.casefold():
            raise PublicCvPrivacyError(f"Required public marker is missing: {marker}")

    if attachments != "0 embedded files":
        raise PublicCvPrivacyError(f"Public CV must not contain embedded files: {attachments}")

    pages_match = re.search(r"^Pages:\s+(\d+)$", metadata, re.MULTILINE)
    if pages_match is None:
        raise PublicCvPrivacyError("Public CV metadata does not expose a page count.")

    return {
        "schema_version": "public-cv-privacy-verification-v1",
        "pdf": pdf.name,
        "pages": int(pages_match.group(1)),
        "allowed_emails": sorted(emails),
        "embedded_files": 0,
        "forbidden_patterns_found": 0,
        "private_contact_details_permitted": False,
        "referee_contact_details_permitted": False,
        "credential_identifiers_permitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the sanitised public CV privacy boundary.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()
    print(json.dumps(verify(args.pdf), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
