from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

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
FORBIDDEN_PUBLIC_HOST_SUFFIXES = ("vercel.app",)
FORBIDDEN_URL_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "token",
    "secret",
    "key",
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


def _extract_pdf_urls(output: str) -> tuple[str, ...]:
    urls: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Page  Type"):
            continue
        fields = stripped.split(maxsplit=2)
        if len(fields) != 3:
            raise PublicCvPrivacyError(f"Unrecognised pdfinfo URL row: {stripped}")
        urls.append(fields[2].strip())
    return tuple(urls)


def _host_is_private(host: str) -> bool:
    folded = host.casefold()
    if folded in {"localhost", "localhost.localdomain"} or folded.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return not address.is_global


def _validate_pdf_urls(output: str) -> tuple[str, ...]:
    urls = _extract_pdf_urls(output)
    for raw_url in urls:
        parsed = urlsplit(raw_url)
        scheme = parsed.scheme.casefold()
        if scheme == "mailto":
            address = unquote(parsed.path).casefold()
            if address != ALLOWED_EMAIL.casefold() or parsed.query or parsed.fragment:
                raise PublicCvPrivacyError(
                    "PDF mail link is outside the reviewed public email allow-list."
                )
            continue
        if scheme != "https":
            raise PublicCvPrivacyError(
                f"PDF contains a non-HTTPS external link: {scheme or '(missing scheme)'}."
            )
        if parsed.username or parsed.password:
            raise PublicCvPrivacyError("PDF URL must not contain embedded credentials.")
        host = (parsed.hostname or "").casefold().rstrip(".")
        if not host:
            raise PublicCvPrivacyError("PDF HTTPS URL is missing a host.")
        if parsed.port not in (None, 443):
            raise PublicCvPrivacyError("PDF URL uses a non-standard public HTTPS port.")
        if _host_is_private(host):
            raise PublicCvPrivacyError("PDF URL points to a local or non-public host.")
        if any(
            host == suffix or host.endswith(f".{suffix}")
            for suffix in FORBIDDEN_PUBLIC_HOST_SUFFIXES
        ):
            raise PublicCvPrivacyError("PDF contains a link to a retired publication host.")
        query_keys = {
            key.casefold()
            for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        }
        if query_keys & FORBIDDEN_URL_QUERY_KEYS:
            raise PublicCvPrivacyError(
                "PDF URL contains a credential-like query parameter."
            )
    return urls


def verify(pdf_path: Path = DEFAULT_PDF) -> dict[str, object]:
    pdf = Path(pdf_path)
    if not pdf.is_file() or pdf.is_symlink():
        raise PublicCvPrivacyError(f"Public CV must be a real file: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise PublicCvPrivacyError("Public CV must use the PDF format.")

    text = _run(["pdftotext", "-layout", str(pdf), "-"])
    metadata = _run(["pdfinfo", str(pdf)])
    custom_metadata = _run(["pdfinfo", "-custom", str(pdf)])
    xmp_metadata = _run(["pdfinfo", "-meta", str(pdf)])
    url_objects = _run(["pdfinfo", "-url", str(pdf)])
    javascript = _run(["pdfinfo", "-js", str(pdf)])
    attachments = _run(["pdfdetach", "-list", str(pdf)]).strip()
    urls = _validate_pdf_urls(url_objects)
    if javascript.strip():
        raise PublicCvPrivacyError("Public CV must not contain embedded JavaScript.")
    combined = "\n".join(
        (text, metadata, custom_metadata, xmp_metadata, url_objects, javascript)
    )

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
        raise PublicCvPrivacyError(
            f"Public CV must not contain embedded files: {attachments}"
        )

    pages_match = re.search(r"^Pages:\s+(\d+)$", metadata, re.MULTILINE)
    if pages_match is None:
        raise PublicCvPrivacyError("Public CV metadata does not expose a page count.")

    return {
        "schema_version": "public-cv-privacy-verification-v2",
        "pdf": pdf.name,
        "pages": int(pages_match.group(1)),
        "allowed_emails": sorted(emails),
        "embedded_files": 0,
        "url_objects_checked": len(urls),
        "javascript_actions": 0,
        "custom_and_xmp_metadata_checked": True,
        "forbidden_patterns_found": 0,
        "private_contact_details_permitted": False,
        "referee_contact_details_permitted": False,
        "credential_identifiers_permitted": False,
        "retired_host_links_permitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the sanitised public CV privacy boundary."
    )
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()
    print(json.dumps(verify(args.pdf), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
