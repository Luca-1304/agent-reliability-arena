from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.pages_site import PagesSiteError, stage_pages_site


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_STAGED_FILES = {
    ".nojekyll",
    "app.js",
    "data/fixture-v1.json",
    "index.html",
    "styles.css",
}


class PagesSiteTests(unittest.TestCase):
    def test_stage_pages_site_copies_only_verified_public_web_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            summary = stage_pages_site(ROOT, output)

            staged = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(staged, EXPECTED_STAGED_FILES)
            self.assertEqual((output / "index.html").read_bytes(), (ROOT / "web/index.html").read_bytes())
            self.assertEqual((output / "styles.css").read_bytes(), (ROOT / "web/styles.css").read_bytes())
            self.assertEqual((output / "app.js").read_bytes(), (ROOT / "web/app.js").read_bytes())
            self.assertEqual(
                (output / "data/fixture-v1.json").read_bytes(),
                (ROOT / "web/data/fixture-v1.json").read_bytes(),
            )
            self.assertEqual((output / ".nojekyll").read_bytes(), b"")
            self.assertEqual(summary["files_staged"], 5)
            self.assertEqual(summary["staged_files"], sorted(EXPECTED_STAGED_FILES))
            self.assertFalse(summary["provider_called"])
            self.assertFalse(summary["comparative_claim_permitted"])
            self.assertEqual(summary["site_title"], "Agent Reliability Arena — Evidence-first agent evaluation")

    def test_stage_pages_site_refuses_existing_or_dirty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            output.mkdir()
            (output / "unexpected.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(PagesSiteError, "destination|empty|exist"):
                stage_pages_site(ROOT, output)
            self.assertEqual((output / "unexpected.txt").read_text(encoding="utf-8"), "do not overwrite")

    def test_staged_site_contains_no_private_operational_markers(self) -> None:
        forbidden = (
            "OPENAI_API_KEY",
            "private-evidence/",
            "provider_request_id",
            "INTERNAL_OPERATOR_NOTE",
            "external_execution_enabled=true",
            "transport-calls.jsonl",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            stage_pages_site(ROOT, output)
            combined = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output.rglob("*")
                if path.is_file() and path.name != ".nojekyll"
            )
            for marker in forbidden:
                self.assertNotIn(marker, combined)

    def test_pages_workflow_verifies_stages_and_deploys_only_from_main(self) -> None:
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        for marker in (
            "name: Deploy verified showcase to GitHub Pages",
            "pull_request:",
            "push:",
            "branches: [main]",
            "contents: read",
            "pages: write",
            "id-token: write",
            "environment:",
            "name: github-pages",
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "python scripts/verify_showcase_release.py",
            "python scripts/verify_launch_package.py",
            "python scripts/stage_pages_site.py --root . --output _site",
            "actions/upload-pages-artifact@v4",
            "path: _site",
            "actions/configure-pages@v5",
            "actions/deploy-pages@v4",
        ):
            self.assertIn(marker, workflow)


if __name__ == "__main__":
    unittest.main()
