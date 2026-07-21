from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_readme_leads_with_hypothesis_fixture_status_and_reproduction(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Same model. Same tools. Same evidence rules.", text)
        self.assertIn("Deterministic fixture", text)
        self.assertIn("arena-run", text)
        self.assertIn("arena-replay", text)
        self.assertIn("web/arena-preview.png", text)
        self.assertIn("2/8", text)
        self.assertIn("6/8", text)
        self.assertIn("+36", text)

    def test_methodology_defines_fairness_and_claims_boundary(self) -> None:
        text = (ROOT / "docs" / "METHODOLOGY.md").read_text(encoding="utf-8")
        for phrase in (
            "Independent variable",
            "Held constant",
            "Independent observation",
            "Logical role calls",
            "not external-model performance",
        ):
            self.assertIn(phrase, text)

    def test_demo_script_does_not_substitute_one_trace_for_aggregate_evidence(self) -> None:
        text = (ROOT / "docs" / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
        self.assertIn("90-second", text)
        self.assertIn("false success", text.lower())
        self.assertIn("one trace is illustrative", text.lower())
        self.assertIn("aggregate fixture report", text.lower())

    def test_contribution_statement_is_transparent_about_ai_assistance(self) -> None:
        text = (ROOT / "docs" / "CONTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("Luca Panayiotou", text)
        self.assertIn("AI-assisted", text)
        self.assertIn("reproducible", text)
        self.assertIn("does not claim", text)

    def test_ci_matrix_covers_four_python_versions_and_clean_wheel(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        for version in ('"3.10"', '"3.11"', '"3.12"', '"3.13"'):
            self.assertIn(version, text)
        self.assertIn("Run source tests", text)
        self.assertIn("Build wheel", text)
        self.assertIn("Verify wheel in clean environment", text)
        self.assertIn("arena-export-web", text)
        self.assertIn("pip check", text)

    def test_public_documents_avoid_breakthrough_and_universal_claims(self) -> None:
        paths = [ROOT / "README.md", ROOT / "RESULTS.md"] + sorted((ROOT / "docs").glob("*.md"))
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
        for forbidden in (
            "proof of consciousness",
            "universal intelligence score",
            "guaranteed better",
            "breakthrough ai",
            "beats every model",
        ):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
