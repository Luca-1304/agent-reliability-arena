from __future__ import annotations

import unittest
from pathlib import Path

from scripts.ci.workflow_contract import read_workflow_contract


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / ".github" / "workflows" / "pages.yml"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
DISPATCH_ONLY = "github.event_name == 'workflow_dispatch'"


class PublicationAuthorityTests(unittest.TestCase):
    def test_pages_keeps_pr_push_and_manual_verification_triggers(self) -> None:
        contract = read_workflow_contract(PAGES)
        self.assertIn("pull_request", contract.triggers)
        self.assertIn("push", contract.triggers)
        self.assertIn("workflow_dispatch", contract.triggers)
        self.assertEqual(contract.triggers["pull_request"].branches, ("main",))
        self.assertEqual(contract.triggers["push"].branches, ("main",))

    def test_pages_publication_is_manual_dispatch_only(self) -> None:
        text = PAGES.read_text(encoding="utf-8")
        deploy = text.split("  deploy:\n", 1)[1]
        self.assertIn(f"if: {DISPATCH_ONLY}", deploy)
        self.assertNotIn("github.event_name == 'push'", deploy)
        self.assertIn("needs: build", deploy)
        self.assertIn("actions/deploy-pages@v5", deploy)
        self.assertIn("Verify live portfolio, CV, audit and Arena boundaries", deploy)

    def test_release_keeps_pr_push_and_manual_verification_triggers(self) -> None:
        contract = read_workflow_contract(RELEASE)
        self.assertIn("pull_request", contract.triggers)
        self.assertIn("push", contract.triggers)
        self.assertIn("workflow_dispatch", contract.triggers)
        self.assertEqual(contract.triggers["pull_request"].branches, ("main",))
        self.assertEqual(contract.triggers["push"].branches, ("main",))

    def test_release_attestation_and_publication_are_manual_dispatch_only(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        attest = text.split("  attest:\n", 1)[1].split("  publish:\n", 1)[0]
        publish = text.split("  publish:\n", 1)[1]
        self.assertIn(f"if: {DISPATCH_ONLY}", attest)
        self.assertIn(f"if: {DISPATCH_ONLY}", publish)
        self.assertNotIn("github.event_name == 'push'", attest)
        self.assertNotIn("github.event_name == 'push'", publish)
        self.assertIn("needs: build", attest)
        self.assertIn("needs: [build, attest]", publish)

    def test_release_publication_contract_remains_fixed_rc2_and_collision_safe(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        publish = text.split("  publish:\n", 1)[1]
        self.assertIn("TAG: v0.2.0rc2", publish)
        self.assertNotIn("inputs.", publish)
        self.assertIn("Refuse conflicting tag or release", publish)
        self.assertIn('gh release view "$TAG"', publish)
        self.assertIn("git ls-remote --exit-code --tags", publish)
        self.assertIn("gh release create", publish)

    def test_publication_permissions_remain_job_scoped(self) -> None:
        pages = read_workflow_contract(PAGES)
        release = read_workflow_contract(RELEASE)
        self.assertEqual(pages.permissions, {"contents": "read"})
        self.assertEqual(release.permissions, {"contents": "read"})
        self.assertEqual(pages.jobs["deploy"].permissions["pages"], "write")
        self.assertEqual(pages.jobs["deploy"].permissions["id-token"], "write")
        self.assertEqual(release.jobs["attest"].permissions["attestations"], "write")
        self.assertEqual(release.jobs["publish"].permissions["contents"], "write")


if __name__ == "__main__":
    unittest.main()
