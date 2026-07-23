from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublishedReleaseWorkflowTests(unittest.TestCase):
    def test_workflow_is_read_only_external_and_fail_closed(self) -> None:
        workflow = (ROOT / ".github/workflows/verify-published-release.yml").read_text(
            encoding="utf-8"
        )

        for marker in (
            "name: Verify published v0.2.0rc2 release",
            "workflow_dispatch:",
            "schedule:",
            "pull_request:",
            "contents: read",
            "attestations: read",
            "TAG: v0.2.0rc2",
            "gh release view",
            "gh release download",
            "gh attestation verify",
            "--predicate-type https://cyclonedx.org/bom",
            "python -m venv",
            "python -m pip install --no-deps",
            "arena-run --config examples/fixture_experiment.json",
            "arena-export-web",
            "arena-verify-published-release",
            "reference_runs/fixture-v1",
            "actions/upload-artifact@v4",
        ):
            self.assertIn(marker, workflow)

        global_permissions = workflow.split("jobs:", 1)[0]
        self.assertIn("contents: read", global_permissions)
        self.assertIn("attestations: read", global_permissions)
        for prohibited in (
            "contents: write",
            "attestations: write",
            "id-token: write",
            "artifact-metadata: write",
            "gh release create",
            "python -m build",
            "dist/*.whl",
        ):
            self.assertNotIn(prohibited, workflow)


if __name__ == "__main__":
    unittest.main()
