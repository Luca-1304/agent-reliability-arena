from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HostingPrivacyBoundaryTests(unittest.TestCase):
    def test_canonical_hosting_policy_is_explicit(self) -> None:
        policy = (ROOT / "docs" / "HOSTING_PRIVACY_BOUNDARY.md").read_text(encoding="utf-8")
        self.assertIn("GitHub Pages is the only supported public hosting route", policy)
        self.assertIn("Vercel is not a supported publication route", policy)
        self.assertIn("No real-provider pilot", policy)
        self.assertIn("affected immutable Vercel deployment URLs return `404` or `410`", policy)

    def test_vercel_remains_fail_closed_until_platform_deletion(self) -> None:
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config.get("ignoreCommand"), "exit 0")
        self.assertEqual(config.get("outputDirectory"), "web/cinematic-plus")

    def test_pages_keeps_source_staged_and_live_cv_verification(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(workflow.count("verify_public_cv.py"), 3)
        self.assertIn("Stage exact Pages artifact", workflow)
        self.assertIn("Verify staged allow-list and CV privacy", workflow)
        self.assertIn("Verify live portfolio, CV, audit and Arena boundaries", workflow)

    def test_tracked_public_text_has_no_deployment_urls_or_ids(self) -> None:
        allowed_suffixes = {".md", ".html", ".css", ".js", ".json", ".yml", ".yaml", ".toml", ".py"}
        forbidden_host = "vercel" + ".app"
        deployment_id = re.compile(r"\bdpl_[A-Za-z0-9]{20,}\b")
        offenders: list[str] = []

        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
                continue
            if any(part in {".git", ".venv", "node_modules"} for part in path.parts):
                continue
            if path == Path(__file__).resolve():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if forbidden_host in text.lower() or deployment_id.search(text):
                offenders.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
