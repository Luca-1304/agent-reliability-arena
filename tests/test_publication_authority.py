from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from scripts.ci.workflow_contract import read_workflow_contract


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PAGES = WORKFLOWS / "pages.yml"
RELEASE = WORKFLOWS / "release.yml"
PUBLICATION_AUTHORITY = (
    "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'"
)
PUBLICATION_CAPABILITIES = {
    "actions/deploy-pages@": ("pages.yml", "deploy"),
    "actions/attest@": ("release.yml", "attest"),
    "gh release create": ("release.yml", "publish"),
}
_JOB_HEADER = re.compile(r"^  (?P<job>[A-Za-z0-9_-]+):\s*$", re.MULTILINE)


def _job_body(text: str, job_id: str) -> str:
    marker = f"  {job_id}:\n"
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    next_job = _JOB_HEADER.search(tail)
    return tail if next_job is None else tail[: next_job.start()]


def _workflow_paths(workflows: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            {
                *workflows.glob("*.yml"),
                *workflows.glob("*.yaml"),
            },
            key=lambda path: path.name,
        )
    )


def _publication_inventory_violations(workflows: Path) -> list[str]:
    violations: list[str] = []
    seen: set[str] = set()
    for path in _workflow_paths(workflows):
        text = path.read_text(encoding="utf-8")
        for capability, (expected_file, expected_job) in PUBLICATION_CAPABILITIES.items():
            if capability not in text:
                continue
            seen.add(capability)
            if path.name != expected_file:
                violations.append(
                    f"{capability} appears in unapproved workflow {path.name}"
                )
                continue
            body = _job_body(text, expected_job)
            if not body:
                violations.append(
                    f"{capability} expected job {expected_job} is missing in {path.name}"
                )
                continue
            if capability not in body:
                violations.append(
                    f"{capability} appears outside approved job {expected_job} in {path.name}"
                )
            if text.count(capability) != body.count(capability):
                violations.append(
                    f"{capability} also appears outside approved job {expected_job} in {path.name}"
                )
            if f"if: {PUBLICATION_AUTHORITY}" not in body:
                violations.append(
                    f"{capability} job {expected_job} lacks main-bound dispatch authority in {path.name}"
                )
    for capability in PUBLICATION_CAPABILITIES:
        if capability not in seen:
            violations.append(f"expected publication capability is missing: {capability}")
    return sorted(set(violations))


class PublicationAuthorityTests(unittest.TestCase):
    def test_pages_keeps_pr_push_and_manual_verification_triggers(self) -> None:
        contract = read_workflow_contract(PAGES)
        self.assertIn("pull_request", contract.triggers)
        self.assertIn("push", contract.triggers)
        self.assertIn("workflow_dispatch", contract.triggers)
        self.assertEqual(contract.triggers["pull_request"].branches, ("main",))
        self.assertEqual(contract.triggers["push"].branches, ("main",))

    def test_pages_publication_requires_main_bound_manual_dispatch(self) -> None:
        text = PAGES.read_text(encoding="utf-8")
        deploy = _job_body(text, "deploy")
        self.assertIn(f"if: {PUBLICATION_AUTHORITY}", deploy)
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

    def test_release_attestation_and_publication_require_main_bound_dispatch(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        attest = _job_body(text, "attest")
        publish = _job_body(text, "publish")
        self.assertIn(f"if: {PUBLICATION_AUTHORITY}", attest)
        self.assertIn(f"if: {PUBLICATION_AUTHORITY}", publish)
        self.assertNotIn("github.event_name == 'push'", attest)
        self.assertNotIn("github.event_name == 'push'", publish)
        self.assertIn("needs: build", attest)
        self.assertIn("needs: [build, attest]", publish)

    def test_release_publication_contract_remains_fixed_rc2_and_collision_safe(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        publish = _job_body(text, "publish")
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

    def test_every_publication_capability_is_allow_listed_and_main_dispatch_only(self) -> None:
        self.assertEqual(_publication_inventory_violations(WORKFLOWS), [])

    def test_publication_inventory_rejects_alternate_unapproved_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = f"if: {PUBLICATION_AUTHORITY}\n"
            (root / "pages.yml").write_text(
                "jobs:\n  deploy:\n    " + authority
                + "    steps:\n      - uses: actions/deploy-pages@v5\n",
                encoding="utf-8",
            )
            (root / "release.yml").write_text(
                "jobs:\n  attest:\n    " + authority
                + "    steps:\n      - uses: actions/attest@v4\n"
                + "  publish:\n    " + authority
                + "    steps:\n      - run: gh release create ok\n",
                encoding="utf-8",
            )
            (root / "bypass.yaml").write_text(
                "jobs:\n  publish-anyway:\n    steps:\n      - run: gh release create bypass\n",
                encoding="utf-8",
            )
            violations = _publication_inventory_violations(root)
        self.assertTrue(
            any("unapproved workflow bypass.yaml" in item for item in violations),
            violations,
        )

    def test_publication_inventory_rejects_dispatch_from_non_main_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dispatch_only = "if: github.event_name == 'workflow_dispatch'\n"
            (root / "pages.yml").write_text(
                "jobs:\n  deploy:\n    " + dispatch_only
                + "    steps:\n      - uses: actions/deploy-pages@v5\n",
                encoding="utf-8",
            )
            (root / "release.yml").write_text(
                "jobs:\n  attest:\n    " + dispatch_only
                + "    steps:\n      - uses: actions/attest@v4\n"
                + "  publish:\n    " + dispatch_only
                + "    steps:\n      - run: gh release create ok\n",
                encoding="utf-8",
            )
            violations = _publication_inventory_violations(root)
        self.assertTrue(
            any("lacks main-bound dispatch authority" in item for item in violations),
            violations,
        )


if __name__ == "__main__":
    unittest.main()
