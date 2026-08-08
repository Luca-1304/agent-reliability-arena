from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.git_operations_policy import (
    GitOperationsPolicyError,
    load_git_operations_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "git-operations-policy.json"
WORKFLOWS = ROOT / ".github" / "workflows"


class GitOperationsPolicyTests(unittest.TestCase):
    def test_repository_policy_covers_every_workflow_extension_exactly(self) -> None:
        policy = load_git_operations_policy(POLICY)
        discovered = {
            path.name
            for path in (*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))
            if path.is_file()
        }
        self.assertGreater(len(discovered), 0)
        self.assertEqual(set(policy.workflows), discovered)

    def test_policy_rejects_unknown_top_level_key(self) -> None:
        payload = json.loads(POLICY.read_text(encoding="utf-8"))
        payload["unexpected"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(GitOperationsPolicyError):
                load_git_operations_policy(path)

    def test_policy_has_only_reviewed_write_capable_jobs(self) -> None:
        policy = load_git_operations_policy(POLICY)
        actual = {
            (workflow_name, job_name)
            for workflow_name, workflow in policy.workflows.items()
            for job_name in workflow.write_jobs
        }
        self.assertEqual(
            actual,
            {
                ("codeql.yml", "analyze"),
                ("pages.yml", "deploy"),
                ("release.yml", "attest"),
                ("release.yml", "publish"),
            },
        )

    def test_external_github_settings_are_not_claimed_verified(self) -> None:
        policy = load_git_operations_policy(POLICY)
        self.assertGreater(len(policy.external_settings), 0)
        self.assertEqual(
            set(policy.external_settings.values()),
            {"externally_required_unverified"},
        )


if __name__ == "__main__":
    unittest.main()
