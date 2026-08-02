from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "cinematic-plus"
PAGE = SITE / "audit.html"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        if tag in {"a", "link", "script"}:
            target = values.get("href") or values.get("src")
            if target:
                self.links.append(target)


class AuditServicePageContract(unittest.TestCase):
    def setUp(self) -> None:
        self.html = PAGE.read_text(encoding="utf-8")
        self.parser = LinkParser()
        self.parser.feed(self.html)

    def test_page_has_accessible_shared_shell(self) -> None:
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('href="portfolio.css"', self.html)
        self.assertIn('src="site.js"', self.html)
        self.assertIn("data-menu", self.html)
        self.assertIn("data-nav", self.html)
        self.assertIn("<main", self.html)
        self.assertIn("<footer", self.html)

    def test_page_contains_exact_service_story(self) -> None:
        self.assertEqual(
            self.parser.ids,
            {"main", "site-nav", "overview", "problem", "deliverables", "fit", "intake"},
        )
        for text in (
            "AI Agent Reliability Audit",
            "One clearly bounded workflow",
            "Completion contract",
            "Trace and adversarial review",
            "Findings report",
            "Implementation plan",
            "Remediation verification",
        ):
            self.assertIn(text, self.html)

    def test_claims_and_access_boundaries_are_visible(self) -> None:
        for text in (
            "No production mutation or provider spend without separate written approval",
            "Penetration testing",
            "Legal or compliance certification",
            "Formal safety certification",
            "Unrestricted production access",
            "A guarantee that every hidden defect is eliminated",
            "Do not send passwords, API keys, private customer data or unrestricted production credentials",
        ):
            self.assertIn(text, self.html)

    def test_internal_links_resolve(self) -> None:
        for href in self.parser.links:
            parts = urlsplit(href)
            if parts.scheme or href.startswith(("mailto:", "tel:", "#")):
                continue
            if not parts.path:
                continue
            target = (SITE / parts.path).resolve()
            self.assertTrue(target.is_file(), href)

    def test_no_sensitive_or_unearned_content(self) -> None:
        forbidden = (
            "sk-proj-",
            "ghp_",
            "BEGIN PRIVATE KEY",
            "client audit completed",
            "certified safe",
            "guaranteed reliable",
            "the_well",
        )
        for value in forbidden:
            self.assertNotIn(value, self.html)


if __name__ == "__main__":
    unittest.main()
