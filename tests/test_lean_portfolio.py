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


def section_html(html: str, section_id: str) -> str:
    match = re.search(
        rf'<section\b[^>]*id="{re.escape(section_id)}"[^>]*>(.*?)</section>',
        html,
        flags=re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing section {section_id}")
    return match.group(1)


def css_hex_token(css: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{6}})", css)
    if not match:
        raise AssertionError(f"missing CSS token {name}")
    return match.group(1)


def relative_luminance(value: str) -> float:
    channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    high, low = sorted(
        [relative_luminance(first), relative_luminance(second)], reverse=True
    )
    return (high + 0.05) / (low + 0.05)


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
            self.assertIn("data-menu", html)
            self.assertIn("data-nav", html)

    def test_index_has_exact_five_sections(self) -> None:
        html = read("index.html")
        ids = re.findall(r'<section[^>]+id="([^"]+)"', html)
        self.assertEqual(ids, ["hero", "capabilities", "evidence", "fit", "contact"])
        self.assertNotIn("MATHEMATICS &amp; MODELLING", html)
        self.assertNotIn("MARKETS, FOREX &amp; RISK", html)
        self.assertIn('href="evidence.html"', html)
        self.assertIn('href="interests.html"', html)
        self.assertIn(f'href="{CV_NAME}"', html)

    def test_main_page_uses_premium_editorial_components(self) -> None:
        html = read("index.html")
        self.assertIn('class="capability-strip"', html)
        self.assertIn('class="engineering-range"', html)
        self.assertIn('class="flagship-layout"', html)
        self.assertEqual(html.count('class="role-lane"'), 3)
        self.assertNotIn('class="card-grid"', html)

        hero = section_html(html, "hero")
        self.assertEqual(hero.count('class="button'), 3)
        self.assertNotIn('href="interests.html"', hero)

    def test_main_page_shows_range_and_fact_checked_flagship(self) -> None:
        html = read("index.html")
        for label in [
            "Evaluation",
            "Agent architecture",
            "Python systems",
            "Adversarial testing",
            "AI assurance",
            "Release engineering",
            "Technical interfaces",
        ]:
            self.assertIn(label, html)

        for text in [
            "2/8 → 6/8",
            "3 → 0",
            "0 → 4",
            "+36 logical role calls",
            "No real-provider benchmark has been executed",
        ]:
            self.assertIn(text, html)
        self.assertNotIn("0.25 → 1.00", html)

    def test_evidence_page_contains_required_story_proof_and_limits(self) -> None:
        html = read("evidence.html")
        for section_id in [
            "summary",
            "flow",
            "trace",
            "results",
            "software",
            "boundaries",
            "next",
        ]:
            self.assertIn(f'id="{section_id}"', html)

        for text in [
            "2/8 → 6/8",
            "3 → 0",
            "0 → 4",
            "0.25 → 1.00",
            "8 → 44",
            "+36 additional calls",
            "No real-provider benchmark has been executed",
            "not production readiness",
        ]:
            self.assertIn(text, html)

        for stage in [
            "Task contract",
            "Agent action",
            "Raw evidence",
            "Independent observation",
            "Verifier",
            "Canonical verdict",
        ]:
            self.assertIn(stage, html)

    def test_evidence_page_uses_defensible_software_statuses(self) -> None:
        combined = "\n".join(read(page) for page in PAGES)
        evidence = read("evidence.html")
        for name in [
            "Agent Reliability Arena",
            "Agent Completion Verifier",
            "ACE Master Nexus",
        ]:
            self.assertIn(name, evidence)
        self.assertNotIn("Veritas Trace", evidence)
        self.assertGreaterEqual(evidence.count("Released and reproducible"), 2)
        self.assertIn("Architecture / active research", evidence)

        for upstream in [
            "gpt-oss",
            "the_well",
            "Ruflo",
            "Graphify",
            "OpenAgentSkill",
            "VisionClaw",
        ]:
            self.assertNotIn(upstream, combined)

    def test_interests_are_direct_static_paired_rows(self) -> None:
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

        self.assertEqual(html.count('class="interest-pair"'), 4)
        self.assertIn('class="personal-strip"', html)

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
        self.assertNotIn('class="interest-grid"', html)
        self.assertNotIn('class="card-grid"', section_html(html, "personal"))

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
        self.assertIn(".site-nav{display:flex", css.replace(" ", ""))

    def test_mobile_trace_table_is_stacked(self) -> None:
        css = read("portfolio.css")
        self.assertRegex(css, r"@media\s*\(max-width:\s*720px\)")
        self.assertIn(".trace-table thead", css)
        self.assertIn("overflow-wrap:anywhere", css.replace(" ", ""))
        self.assertIn('content:"Observable state"', css.replace(" ", ""))
        self.assertIn('content:"Verifier judgement"', css.replace(" ", ""))

    def test_semantic_text_tokens_meet_wcag_contrast(self) -> None:
        css = read("portfolio.css")
        pairs = [
            ("--bg", "--text-on-dark-primary", 4.5),
            ("--bg", "--text-on-dark-secondary", 4.5),
            ("--paper", "--text-on-light-primary", 4.5),
            ("--paper", "--text-on-light-secondary", 4.5),
            ("--paper", "--accent-readable-on-light", 4.5),
            ("--bg", "--focus-ring", 3.0),
            ("--paper", "--focus-ring", 3.0),
        ]
        for background, foreground, minimum in pairs:
            self.assertGreaterEqual(
                contrast_ratio(
                    css_hex_token(css, background),
                    css_hex_token(css, foreground),
                ),
                minimum,
                f"{foreground} on {background}",
            )


if __name__ == "__main__":
    unittest.main()
