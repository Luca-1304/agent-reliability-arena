# Integration Publication Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve automatic verification while ensuring ordinary pull requests and ordinary `main` pushes cannot deploy GitHub Pages or attest/publish the immutable `v0.2.0rc2` release.

**Architecture:** Keep the existing verification/build jobs and their evidence intact. Change only the publication authority conditions: Pages deploy and release attest/publish become `workflow_dispatch`-only, while PR and `main` push verification remains automatic. Structural tests own the event/permission/dependency contract so later workflow edits cannot silently restore implicit publication.

**Tech Stack:** GitHub Actions YAML, Python 3.10–3.13 standard-library `unittest`, existing `scripts.ci.workflow_contract` parser and repository CI/reliability policy.

## Global Constraints

- Verification may remain automatic; publication requires explicit publication intent.
- No `[skip ci]`, hidden branch convention, credential bypass, workflow weakening, Vercel mutation, provider mutation, privacy-history mutation, or branch-protection mutation.
- Pages publication authority is `workflow_dispatch` only.
- rc2 publication authority is `workflow_dispatch` only; the release tag remains hard-coded as `v0.2.0rc2` with no free-form version input.
- PR and ordinary `main` push verification must remain active.
- Existing source/staged/live CV privacy verification must remain present; live verification belongs only to the intentional Pages publication path.
- Existing release/tag collision refusal remains mandatory.
- No real Pages deploy or release publication is required during implementation or acceptance.

---

### Task 1: Add repository publication-authority contract tests

**Files:**
- Create: `tests/test_publication_authority.py`
- Read: `.github/workflows/pages.yml`
- Read: `.github/workflows/release.yml`
- Reuse: `scripts/ci/workflow_contract.py`

**Interfaces:**
- Consumes: `read_workflow_contract(path: Path) -> WorkflowContract`.
- Produces: structural test contract for trigger presence, publication job conditions, permissions, dependencies, and publication-capable steps.

- [ ] **Step 1: Write failing tests against current workflows**

Create `tests/test_publication_authority.py` with tests that assert:

```python
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
        self.assertIn('git ls-remote --exit-code --tags', publish)
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
```

- [ ] **Step 2: Run only the new test module and prove RED**

Run through GitHub Actions by committing the test-only change to the feature branch. Expected result: publication-authority tests fail because current Pages and release publication jobs still authorize on `push` to `main`, and release lacks `workflow_dispatch`.

- [ ] **Step 3: Confirm failures are isolated**

Read a Python job log. Expected: existing tests remain green and only the new publication-authority assertions fail for the intended conditions.

- [ ] **Step 4: Commit the RED contract**

Commit message:

```text
test: define explicit publication authority
```

---

### Task 2: Make Pages publication explicit without weakening verification

**Files:**
- Modify: `.github/workflows/pages.yml`
- Modify: `tests/test_pages_site.py`
- Test: `tests/test_publication_authority.py`

**Interfaces:**
- Consumes: existing `build` job and uploaded `_site` artifact.
- Produces: `deploy` job that can execute only when `github.event_name == 'workflow_dispatch'`, still requiring `build`, and still running live verification after deployment.

- [ ] **Step 1: Update the existing Pages-specific test contract**

Replace the old marker requiring push-only deployment:

```python
"if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
```

with:

```python
"workflow_dispatch:",
"if: github.event_name == 'workflow_dispatch'",
```

and keep all existing staging, privacy, permission, deployment and live-verification markers.

- [ ] **Step 2: Run tests before the workflow edit and verify RED remains**

Expected: `test_pages_workflow_verifies_stages_and_deploys_only_from_main` and the publication-authority Pages test fail because the workflow still uses the push condition.

- [ ] **Step 3: Make the minimal workflow change**

Keep:

```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch:
```

Change only the deploy authority condition from:

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

to:

```yaml
if: github.event_name == 'workflow_dispatch'
```

Do not change `needs: build`, job permissions, environment, deploy action, or live verification.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```text
python -m unittest tests.test_publication_authority tests.test_pages_site tests.test_public_cv_privacy_contract
```

Expected: Pages authority/staging/privacy tests pass; release authority remains RED until Task 3.

- [ ] **Step 5: Commit Pages guard**

Commit message:

```text
fix: require explicit Pages publication intent
```

---

### Task 3: Make rc2 attestation/publication explicit without weakening verification

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_github_prerelease.py`
- Test: `tests/test_publication_authority.py`

**Interfaces:**
- Consumes: existing release `build` job and verified `v0.2.0rc2-prerelease-assets` artifact.
- Produces: `attest` and `publish` jobs that can execute only on `workflow_dispatch`; fixed `TAG=v0.2.0rc2`; existing collision refusal and attestation verification remain unchanged.

- [ ] **Step 1: Update the existing prerelease workflow contract test**

Rename the behavioral expectation to reflect explicit publication, and require these markers:

```python
"workflow_dispatch:",
"if: github.event_name == 'workflow_dispatch'",
"needs: build",
"needs: [build, attest]",
"TAG: v0.2.0rc2",
```

Explicitly assert `github.event_name == 'push'` is absent from both `attest` and `publish` job bodies.

- [ ] **Step 2: Run focused tests before the workflow edit and verify RED**

Expected: release publication-authority tests fail because `workflow_dispatch` is absent and attest/publish are push-authorized.

- [ ] **Step 3: Make the minimal release workflow change**

Add a top-level trigger:

```yaml
  workflow_dispatch:
```

Keep the existing `pull_request` and `push` path filters for automatic verification/build.

Change both publication-authority job conditions from:

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

to:

```yaml
if: github.event_name == 'workflow_dispatch'
```

Do not add workflow inputs. Keep `TAG: v0.2.0rc2`, collision refusal, attestation permissions, `gh attestation verify`, and `gh release create` unchanged.

- [ ] **Step 4: Run focused contract tests and verify GREEN**

Run:

```text
python -m unittest tests.test_publication_authority tests.test_github_prerelease tests.test_workflow_contract tests.test_workflow_checkout_credentials
```

Expected: all focused tests pass.

- [ ] **Step 5: Commit release guard**

Commit message:

```text
fix: require explicit prerelease publication intent
```

---

### Task 4: Add repository-wide publication-capability enumeration

**Files:**
- Modify: `tests/test_publication_authority.py`
- Read: `.github/workflows/*.yml`

**Interfaces:**
- Consumes: every workflow YAML file under `.github/workflows`.
- Produces: a fail-closed inventory test that catches newly introduced publication-capable workflow steps outside the two reviewed publication jobs.

- [ ] **Step 1: Add a test that scans all workflow text**

Add a controlled marker inventory:

```python
PUBLICATION_MARKERS = {
    "actions/deploy-pages@": ("pages.yml", "deploy"),
    "actions/attest@": ("release.yml", "attest"),
    "gh release create": ("release.yml", "publish"),
}
```

For every `.yml` file, if a marker appears, assert the file is the expected workflow and the marker occurs inside the expected job body. Also assert those expected jobs contain `if: github.event_name == 'workflow_dispatch'`.

- [ ] **Step 2: Verify the inventory catches a synthetic bypass**

In the test, mutate a temporary workflow copy by appending a fake job containing `gh release create` without the dispatch condition and assert the helper rejects it. Keep mutation entirely inside a temporary directory.

- [ ] **Step 3: Run the new inventory test**

Expected: current guarded workflow set passes; synthetic bypass fails closed inside the unit test.

- [ ] **Step 4: Commit capability inventory**

Commit message:

```text
test: inventory public publication capabilities
```

---

### Task 5: Exact-head acceptance and integration hold verification

**Files:**
- No product-file changes unless a failing check exposes a genuine defect.
- PR metadata only after exact-head evidence is complete.

**Interfaces:**
- Consumes: final feature head.
- Produces: review-ready PR with no actual publication performed.

- [ ] **Step 1: Open a draft PR from the feature branch to `main`**

PR description must state that no Pages deploy, tag, attestation publication or GitHub release was intentionally executed.

- [ ] **Step 2: Verify normal Python matrix on exact PR head**

Required Python versions: 3.10, 3.11, 3.12, 3.13. Require source tests, release verifier, installed commands, wheel build and clean-wheel verification to pass.

- [ ] **Step 3: Verify Fast, Specialist and Deep role evidence**

Require:

```text
Fast — Role evidence summary
Specialist — Role evidence summary
Deep — Role evidence summary
```

Deep must complete its policy-governed repeated gates on Python 3.10 and 3.13 including diagnostic redaction/scanning.

- [ ] **Step 4: Verify independent checks**

Require CodeQL, repository history boundary, Pages verification/staging/privacy packaging, and release verification/build to pass. On a PR, Pages publish, release attest and release publish jobs must be skipped.

- [ ] **Step 5: Compare final diff to `main`**

Expected intended files only:

```text
.github/workflows/pages.yml
.github/workflows/release.yml
tests/test_pages_site.py
tests/test_github_prerelease.py
tests/test_publication_authority.py
docs/superpowers/specs/2026-08-08-integration-publication-guard-design.md
docs/superpowers/plans/2026-08-08-integration-publication-guard.md
```

- [ ] **Step 6: Mark PR ready only after all exact-head evidence is green**

Do not merge automatically until the merge-side event behavior has been checked against the final workflow source. The expected result is that the guard PR itself can merge with verification-only effects; intentional future publication remains a separate `workflow_dispatch` action.
