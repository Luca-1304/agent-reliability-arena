from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_audit_package import DOCS, REQUIRED, verify


class AuditPackageTests(unittest.TestCase):
    def test_reviewed_package_verifies(self) -> None:
        result = verify()
        self.assertEqual(result["version"], "1.0.0")
        self.assertEqual(result["files_verified"], len(REQUIRED))
        self.assertFalse(result["external_client_audit_completed"])
        self.assertFalse(result["client_outcome_claim_permitted"])
        self.assertFalse(result["production_reliability_claim_permitted"])
        self.assertEqual(result["credential_patterns_found"], 0)

    def test_missing_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in REQUIRED:
                source = DOCS / name
                target = root / name
                target.write_bytes(source.read_bytes())
            (root / next(iter(REQUIRED))).unlink()
            with patch("scripts.verify_audit_package.DOCS", root):
                with self.assertRaisesRegex(ValueError, "Missing audit package files"):
                    verify()

    def test_status_claim_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in REQUIRED:
                source = DOCS / name
                target = root / name
                target.write_bytes(source.read_bytes())
            status_path = root / "AUDIT_PACKAGE_STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["external_client_audit_completed"] = True
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with patch("scripts.verify_audit_package.DOCS", root):
                with self.assertRaisesRegex(ValueError, "does not match"):
                    verify()


if __name__ == "__main__":
    unittest.main()
