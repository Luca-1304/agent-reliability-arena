from __future__ import annotations

import unittest
from pathlib import Path

from scripts.ci.git_operations_policy import load_git_operations_policy
from scripts.ci.verify_git_operations import verify_repository


ROOT = Path(__file__).resolve().parents[1]


class GitOperationsWorkflowInventoryTests(unittest.TestCase):
    def test_current_repository_has_no_unreviewed_git_operation_authority(self) -> None:
        policy = load_git_operations_policy(ROOT / "git-operations-policy.json")
        violations = verify_repository(ROOT, policy)
        self.assertEqual(
            violations,
            [],
            "Git operations policy violations:\n"
            + "\n".join(
                f"{item.code} {item.location}: {item.message}" for item in violations
            ),
        )


if __name__ == "__main__":
    unittest.main()
