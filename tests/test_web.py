from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from agent_reliability_arena.public_export import build_public_export


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class WebViewerTests(unittest.TestCase):
    def test_index_has_employer_facing_message_and_fixture_badge(self) -> None:
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("Agent Reliability Arena", html)
        self.assertIn("Same model. Same tools. Same evidence rules.", html)
        self.assertIn("Deterministic fixture", html)
        self.assertIn("<main", html)

    def test_scenario_selector_is_accessibly_labelled(self) -> None:
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'<label[^>]+for="scenario-select"')
        self.assertRegex(html, r'<select[^>]+id="scenario-select"')
        self.assertIn('aria-live="polite"', html)
        self.assertIn('aria-describedby="fixture-note"', html)

    def test_no_placeholder_or_unqualified_winner_language(self) -> None:
        text = "\n".join(
            (WEB / name).read_text(encoding="utf-8")
            for name in ("index.html", "styles.css", "app.js")
        ).lower()
        for forbidden in ("tbd", "todo", "lorem ipsum", "coming soon", "best model", "winner"):
            self.assertNotIn(forbidden, text)

    def test_public_data_has_locked_metrics_and_all_scenarios(self) -> None:
        data = json.loads((WEB / "data" / "fixture-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(data["evidence_status"], "deterministic_fixture")
        self.assertEqual(data["metrics"]["conditions"]["general"]["verified_complete"], 2)
        self.assertEqual(data["metrics"]["conditions"]["specialist"]["verified_complete"], 6)
        self.assertEqual(data["metrics"]["paired"]["additional_logical_model_calls"], 36)
        self.assertEqual(len(data["scenarios"]), 8)
        self.assertTrue(all("general" in row and "specialist" in row for row in data["scenarios"]))

    def test_every_trace_exposes_independent_trust_basis(self) -> None:
        data = json.loads((WEB / "data" / "fixture-v1.json").read_text(encoding="utf-8"))
        for scenario in data["scenarios"]:
            for condition in ("general", "specialist"):
                attempts = scenario[condition]["attempts"]
                self.assertTrue(attempts)
                self.assertTrue(
                    all(attempt["evidence"]["trust_basis"] == "independent_local_state" for attempt in attempts)
                )

    def test_javascript_fetches_only_local_export_and_avoids_dynamic_code(self) -> None:
        script = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('fetch("data/fixture-v1.json")', script)
        self.assertNotRegex(script, r'https?://')
        self.assertNotIn("eval(", script)
        self.assertNotIn("new Function", script)
        self.assertIn("textContent", script)

    def test_css_has_responsive_and_reduced_motion_support(self) -> None:
        css = (WEB / "styles.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 860px)", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(":focus-visible", css)

    def test_export_file_matches_verified_reference_artifacts(self) -> None:
        expected = build_public_export(ROOT / "reference_runs" / "fixture-v1")
        actual = json.loads((WEB / "data" / "fixture-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_html_has_no_external_runtime_dependencies(self) -> None:
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'<script[^>]+src="https?://')
        self.assertNotRegex(html, r'<link[^>]+href="https?://')
        self.assertEqual(len(re.findall(r'<script[^>]+src=', html)), 1)


if __name__ == "__main__":
    unittest.main()
