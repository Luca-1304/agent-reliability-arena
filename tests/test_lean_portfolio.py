from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "web" / "cinematic-plus"
PAGES = ["index.html", "evidence.html", "interests.html"]
CV_NAME = "Luca_Panayiotou_CV.pdf"


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


def read(name: str) -> str:
    return (SITE / name).read_text(encoding="utf-8")


def parse(name: str) -> LinkParser:
    parser = LinkParser()
    parser.feed(read(name))
    return parser


class LeanPortfolioContract(unittest.TestCase):
    def test_canonical_files_exist(self) -> None:
        for name in [*PAGES, "portfolio.css", "site.js", CV_NAME]:
            self.assertTrue((SITE / name).is_file(), name)

    def test_every_page_uses_only_shared_assets(self) -> None:
        for page in PAGES:
            html = read(page)
            self.assertIn('href="portfolio.css"', html)
            self.assertIn('src="site.js"', html)
            for old in [
                "reviewed-preview.css",
                "secure-preview.css",
                "flagship.css",
                "interests-professional.css",
                "reviewed-preview.js",
                "interests.js",
                "cv-download.js",
            ]:
                self.assertNotIn(old, html, f"{page} references {old}")

    def test_accessible_shell_exists_on_every_page(self) -> None:
        for page in PAGES:
            html = read(page)
            self.assertIn('class="skip-link"', html)
            self.assertRegex(html, r"<nav\b")
            self.assertRegex(html, r"<main\b")
            self.assertRegex(html, r"<footer\b")
            self.assertIn('data-menu', html)
            self.assertIn('data-nav', html)

    def test_index_has_exact_five_sections(self) -> None:
        html = read("index.html")
        ids = re.findall(r"<section[^>]+id=\"([^\"]+)\"", html)
        self.assertEqual(ids, ["hero", "capabilities", "evidence", "fit", "contact"])
        self.assertNotIn("MATHEMATICS &amp; MODELLING", html)
        self.assertNotIn("MARKETS, FOREX &amp; RISK", html)
        self.assertIn('href="evidence.html"', html)
        self.assertIn('href="interests.html"', html)
        self.assertIn(f'href="{CV_NAME}"', html)

    def test_evidence_page_contains_required_proof_and_limits(self) -> None:
        html = read("evidence.html")
        for section_id in [
            "summary",
            "problem",
            "contract",
            "trace",
            "results",
            "limitations",
            "source",
        ]:
            self.assertIn(f'id="{section_id}"', html)
        for text in [
            "2/8 → 6/8",
            "3 → 0",
            "0.25 → 1.00",
            "four recovered mismatch",
            "controlled deterministic",
            "not universal production performance",
        ]:
            self.assertIn(text, html)

    def test_interests_are_direct_static_html(self) -> None:
        html = read("interests.html")
        labels = [
            "AI RELIABILITY",
            "ADAPTIVE SYSTEMS",
            "MATHEMATICS &amp; MODELLING",
            "PHYSICS &amp; MATERIALS",
            "MARKETS, FOREX &amp; RISK",
            "HUMAN–AI SYSTEMS",
            "TRUTH &amp; STEWARDSHIP",
            "VISUAL IDEAS",
        ]
        for label in labels:
            self.assertEqual(html.count(label), 1, label)
        for text in [
            "Fluid dynamics &amp; Navier–Stokes",
            "Heat transfer",
            "Material integrity",
            "Simulation",
            "Technical &amp; price-action analysis",
            "London &amp; New York sessions",
            "DXY confirmation",
            "Invalidation &amp; risk control",
        ]:
            self.assertIn(text, html)
        self.assertNotIn("refineInterestCard", html)
        self.assertNotIn("COMMON THREAD", html)

    def test_internal_links_resolve(self) -> None:
        for page in PAGES:
            parser = parse(page)
            for href in parser.links:
                parts = urlsplit(href)
                if parts.scheme or href.startswith(("mailto:", "tel:", "#")):
                    continue
                path = parts.path
                if not path:
                    continue
                target = (SITE / path).resolve()
                self.assertTrue(target.exists(), f"{page}: broken link {href}")
                if parts.fragment and target.suffix == ".html":
                    target_parser = parse(target.name)
                    self.assertIn(parts.fragment, target_parser.ids, f"{page}: {href}")

    def test_privacy_and_preview_content_are_absent(self) -> None:
        combined = "\n".join(read(page) for page in PAGES) + read("site.js")
        forbidden = [
            "07443 634 888",
            "164 Westwood Lane",
            "13 April 2004",
            "/api/contact/call",
            "data-call-luca",
            "data-call-endpoint",
            "raw.githack.com",
            "rawcdn.githack.com",
            "portfolio-public-clean",
        ]
        for value in forbidden:
            self.assertNotIn(value, combined)

    def test_site_js_is_navigation_only(self) -> None:
        js = read("site.js")
        for forbidden in [
            "innerHTML",
            "insertAdjacent",
            "createElement",
            "document.write",
            "fetch(",
            "localStorage",
        ]:
            self.assertNotIn(forbidden, js)
        self.assertIn("aria-expanded", js)
        self.assertIn("Escape", js)

    def test_mobile_navigation_has_no_javascript_fallback(self) -> None:
        css = read("portfolio.css")
        js = read("site.js")
        self.assertIn("document.documentElement.classList.add('js')", js)
        self.assertIn(".js .menu-button", css)
        self.assertIn(".js .site-nav", css)
        self.assertIn(".site-nav{display:flex", css)

    def test_mobile_trace_table_is_stacked(self) -> None:
        css = read("portfolio.css")
        self.assertIn("@media(max-width:680px)", css)
        self.assertIn(".trace-table thead{position:absolute", css)
        self.assertIn(".trace-table td{padding:4px 0;border:0;overflow-wrap:anywhere}", css)
        self.assertIn('content:"Raw state"', css)
        self.assertIn('content:"Judgement"', css)


if __name__ == "__main__":
    unittest.main()
