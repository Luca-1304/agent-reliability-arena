from pathlib import Path


PORTFOLIO_ROOT = Path("web/cinematic-plus")
PUBLIC_PAGES = ("index.html", "evidence.html", "interests.html")


def test_public_pages_load_desktop_heading_overrides_after_base_styles() -> None:
    for page_name in PUBLIC_PAGES:
        html = (PORTFOLIO_ROOT / page_name).read_text(encoding="utf-8")
        base_position = html.index('href="portfolio.css"')
        override_position = html.index('href="desktop-headings.css"')

        assert base_position < override_position


def test_heading_override_is_desktop_only() -> None:
    css = (PORTFOLIO_ROOT / "desktop-headings.css").read_text(encoding="utf-8")
    first_rule = css.index("@media")

    assert css[first_rule:].startswith("@media (min-width: 900px)")
    assert css[:first_rule].strip().startswith("/*")
    assert "@media (max-width" not in css
    assert css.count("@media") == 1


def test_desktop_titles_expand_without_changing_content() -> None:
    css = (PORTFOLIO_ROOT / "desktop-headings.css").read_text(encoding="utf-8")

    assert ".section-intro h2" in css
    assert ".evidence-opening h1" in css
    assert ".interests-opening h1" in css
    assert ".hero-editorial" in css
    assert ".flagship-copy" in css
    assert "max-width: none" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
