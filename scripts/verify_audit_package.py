from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REQUIRED = {
    "AI_AGENT_RELIABILITY_AUDIT.md",
    "AUDIT_INTAKE_TEMPLATE.md",
    "AUDIT_SCOPE_TEMPLATE.md",
    "AUDIT_EVIDENCE_REQUEST.md",
    "AUDIT_REPORT_TEMPLATE.md",
    "AUDIT_REMEDIATION_ACCEPTANCE.md",
    "AUDIT_DELIVERY_CHECKLIST.md",
    "AUDIT_OUTREACH_PLAYBOOK.md",
    "AUDIT_PACKAGE_INDEX.md",
    "AUDIT_PACKAGE_VERSION.md",
    "AUDIT_PACK_CHANGELOG.md",
    "AUDIT_PACKAGE_READINESS.md",
    "AUDIT_PACKAGE_CLAIMS_BOUNDARY.md",
    "AUDIT_PACKAGE_STATUS.json",
    "AUDIT_PACKAGE_VERIFICATION.md",
}


def verify() -> dict[str, object]:
    missing = sorted(name for name in REQUIRED if not (DOCS / name).is_file())
    if missing:
        raise ValueError(f"Missing audit package files: {', '.join(missing)}")

    status = json.loads((DOCS / "AUDIT_PACKAGE_STATUS.json").read_text(encoding="utf-8"))
    expected = {
        "schema_version": "audit-package-status-v1",
        "version": "1.0.0",
        "status": "operational-template-pack",
        "external_client_audit_completed": False,
        "client_outcome_claim_permitted": False,
        "production_reliability_claim_permitted": False,
        "last_verified_date": "2026-08-02",
    }
    if status != expected:
        raise ValueError("Audit package status does not match the reviewed 1.0.0 boundary.")

    combined = "\n".join(
        (DOCS / name).read_text(encoding="utf-8")
        for name in sorted(REQUIRED)
        if name.endswith(".md")
    )
    forbidden_patterns = {
        "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "GitHub token": r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b",
        "OpenAI key": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, combined):
            raise ValueError(f"Credential-shaped {label} found in audit package.")

    required_boundaries = [
        "not a penetration test",
        "fixed scope",
        "production mutation",
        "credentials",
        "evidence",
    ]
    public_offer = (DOCS / "AI_AGENT_RELIABILITY_AUDIT.md").read_text(encoding="utf-8").lower()
    for boundary in required_boundaries:
        if boundary not in public_offer:
            raise ValueError(f"Public audit offer is missing boundary: {boundary}")

    return {
        "schema_version": "audit-package-verification-v1",
        "version": status["version"],
        "files_verified": len(REQUIRED),
        "external_client_audit_completed": False,
        "client_outcome_claim_permitted": False,
        "production_reliability_claim_permitted": False,
        "credential_patterns_found": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
