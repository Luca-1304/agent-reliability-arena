from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.ci.git_operations_policy import load_git_operations_policy
from scripts.ci.verify_git_operations import verify_repository


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "git-operations-policy.json"


def _write_workflow(root: Path, name: str, text: str) -> None:
    workflow_root = root / ".github" / "workflows"
    workflow_root.mkdir(parents=True, exist_ok=True)
    (workflow_root / name).write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def _write_single_workflow_policy(
    root: Path,
    *,
    workflow_name: str,
    write_jobs: dict[str, object] | None = None,
) -> Path:
    payload = {
        "schema_version": "git-operations-policy-v1",
        "workflow_directory": ".github/workflows",
        "default_permissions": {"contents": "read"},
        "denied_triggers": ["pull_request_target", "repository_dispatch", "workflow_run"],
        "untrusted_run_expression_prefixes": [
            "github.event.pull_request.",
            "github.event.issue.",
            "github.event.comment."
        ],
        "workflows": {
            workflow_name: {
                "write_jobs": write_jobs or {},
            }
        },
        "external_settings": {
            "main_branch_ruleset": "externally_required_unverified",
            "full_sha_action_enforcement": "externally_required_unverified",
        },
    }
    path = root / "policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _codes(root: Path, policy_path: Path) -> set[str]:
    policy = load_git_operations_policy(policy_path)
    return {violation.code for violation in verify_repository(root, policy)}


class GitOperationsMutationTests(unittest.TestCase):
    def test_yaml_extension_cannot_escape_workflow_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "known.yml",
                """
                name: known
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: ./local-action
                """,
            )
            _write_workflow(
                root,
                "hidden.yaml",
                """
                name: hidden
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: ./local-action
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="known.yml")
            self.assertIn("workflow-unclassified", _codes(root, policy_path))

    def test_moving_action_tag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "test.yml",
                """
                name: test
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@v7
                        with:
                          persist-credentials: false
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="test.yml")
            self.assertIn("action-not-sha-pinned", _codes(root, policy_path))

    def test_unlisted_contents_write_job_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "test.yml",
                """
                name: test
                on:
                  workflow_dispatch:
                permissions:
                  contents: read
                jobs:
                  mutate:
                    runs-on: ubuntu-latest
                    permissions:
                      contents: write
                    steps:
                      - uses: ./local-action
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="test.yml")
            self.assertIn("write-job-not-allowed", _codes(root, policy_path))

    def test_dispatch_only_publication_authority_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "pages.yml",
                """
                name: pages
                on:
                  workflow_dispatch:
                permissions:
                  contents: read
                jobs:
                  deploy:
                    if: github.event_name == 'workflow_dispatch'
                    runs-on: ubuntu-latest
                    permissions:
                      contents: read
                      pages: write
                      id-token: write
                    steps:
                      - uses: ./local-action
                """,
            )
            write_jobs = {
                "deploy": {
                    "permissions": {
                        "contents": "read",
                        "pages": "write",
                        "id-token": "write",
                    },
                    "authority_if": "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'",
                    "allowed_mutations": [],
                }
            }
            policy_path = _write_single_workflow_policy(
                root,
                workflow_name="pages.yml",
                write_jobs=write_jobs,
            )
            self.assertIn("write-authority-condition", _codes(root, policy_path))

    def test_dangerous_trigger_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "test.yml",
                """
                name: test
                on:
                  pull_request_target:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: ./local-action
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="test.yml")
            self.assertIn("dangerous-trigger", _codes(root, policy_path))

    def test_unlisted_git_push_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "test.yml",
                """
                name: test
                on:
                  workflow_dispatch:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - name: hidden remote mutation
                        run: |
                          git push origin HEAD:refs/heads/other
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="test.yml")
            self.assertIn("remote-mutation-not-allowed", _codes(root, policy_path))

    def test_untrusted_event_text_inside_run_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "test.yml",
                """
                name: test
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - name: unsafe interpolation
                        run: echo "${{ github.event.pull_request.title }}"
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="test.yml")
            self.assertIn("untrusted-expression-in-run", _codes(root, policy_path))

    def test_structured_pull_request_sha_is_not_treated_as_untrusted_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_workflow(
                root,
                "test.yml",
                """
                name: test
                on:
                  pull_request:
                permissions:
                  contents: read
                jobs:
                  verify:
                    runs-on: ubuntu-latest
                    steps:
                      - name: record source identity
                        run: printf '%s\\n' '${{ github.event.pull_request.head.sha || github.sha }}'
                """,
            )
            policy_path = _write_single_workflow_policy(root, workflow_name="test.yml")
            self.assertNotIn("untrusted-expression-in-run", _codes(root, policy_path))


if __name__ == "__main__":
    unittest.main()
