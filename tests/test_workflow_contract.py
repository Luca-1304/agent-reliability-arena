from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ci.workflow_contract import read_workflow_contract


ROOT = Path(__file__).resolve().parents[1]
DEEP_WORKFLOW = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"


class WorkflowContractTests(unittest.TestCase):
    def test_on_is_preserved_as_trigger_key(self) -> None:
        contract = read_workflow_contract(DEEP_WORKFLOW)
        self.assertIn("pull_request", contract.triggers)
        self.assertIn("push", contract.triggers)
        self.assertIn("workflow_dispatch", contract.triggers)

    def test_trigger_paths_and_branches_are_structured(self) -> None:
        contract = read_workflow_contract(DEEP_WORKFLOW)
        pull_request = contract.triggers["pull_request"]
        push = contract.triggers["push"]
        self.assertIn("reliability-policy.json", pull_request.paths)
        self.assertIn(".github/workflows/**", pull_request.paths)
        self.assertEqual(push.branches, ("main",))
        self.assertIn("schemas/**", push.paths)

    def test_job_and_step_controls_are_structured(self) -> None:
        contract = read_workflow_contract(DEEP_WORKFLOW)
        verify = contract.jobs["verify"]
        self.assertEqual(verify.runs_on, "ubuntu-24.04")
        self.assertEqual(verify.timeout_minutes, 180)
        self.assertEqual(contract.permissions, {"contents": "read"})

        checkout = next(step for step in verify.steps if step.uses.startswith("actions/checkout@"))
        self.assertIs(checkout.with_values["persist-credentials"], False)

        uploads = [step for step in verify.steps if step.uses.startswith("actions/upload-artifact@")]
        self.assertEqual(len(uploads), 2)
        self.assertTrue(all(step.with_values["retention-days"] == 14 for step in uploads))
        self.assertTrue(all("always()" in (step.if_condition or "") for step in uploads))

    def test_github_expression_is_preserved_as_raw_string(self) -> None:
        contract = read_workflow_contract(DEEP_WORKFLOW)
        self.assertEqual(
            contract.concurrency["group"],
            "fifteen-pass-${{ github.event.pull_request.number || github.ref }}",
        )

    def test_parser_rejects_tabs_in_structural_indentation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text("on:\n\tpull_request:\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "tab"):
                read_workflow_contract(path)


if __name__ == "__main__":
    unittest.main()
