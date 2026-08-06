from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "web" / "cinematic-plus" / "site.js"


class AuditMailtoLimitContract(unittest.TestCase):
    def test_oversized_mailto_is_blocked_before_navigation(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("const maxMailtoLength = 1900", script)
        self.assertIn("if (href.length > maxMailtoLength)", script)
        self.assertIn("Use “Copy enquiry” instead", script)
        self.assertLess(
            script.index("if (href.length > maxMailtoLength)"),
            script.index("window.location.href = href"),
        )


if __name__ == "__main__":
    unittest.main()
