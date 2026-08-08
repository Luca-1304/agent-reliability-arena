# Git Operations Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed, source-controlled Git operations policy covering every GitHub Actions workflow, then lift all external action references to immutable identities without changing publication authority.

**Architecture:** Keep `reliability-policy.json` focused on reliability-role semantics. Add a separate `git-operations-policy.json` plus standard-library verifier that reuses `scripts/ci/workflow_contract.py`, discovers both `.yml` and `.yaml`, and validates global action pins, permissions, write-job authority, dangerous triggers and remote mutation capabilities. Preserve existing publication and history controls; do not delete branches or change GitHub account settings in this plan.

**Tech Stack:** Python 3.10–3.13 standard library, `unittest`, GitHub Actions YAML, JSON policy, existing repository workflow parser and release/supply-chain verifiers.

## Global Constraints

- No branch deletion.
- No GitHub ruleset/settings mutation.
- No provider/Vercel mutation.
- No Pages deployment or GitHub Release publication.
- No credentials or secret values added.
- External actions must use full 40-character commit SHAs; external Docker actions must use immutable SHA-256 digests.
- Checkout remains `persist-credentials: false` everywhere.
- Pages and release public-write authority remains exactly `github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'`.
- Existing `reliability-policy.json` role semantics remain unchanged.
- Refresh CodeQL supply-chain and prerelease hash locks only from final bytes.

---

### Task 1: Define failing Git operations policy contracts

**Files:**
- Create: `tests/test_git_operations_policy.py`
- Create: `tests/test_git_operations_mutations.py`
- Create: `tests/test_git_operations_workflow_inventory.py`

**Interfaces:**
- Consumes: `scripts.ci.workflow_contract.read_workflow_contract(path: Path) -> WorkflowContract`
- Produces expected future interface: `scripts.ci.git_operations_policy.load_git_operations_policy(path: Path) -> GitOperationsPolicy`
- Produces expected future interface: `scripts.ci.verify_git_operations.verify_repository(root: Path, policy: GitOperationsPolicy) -> list[GitOperationsViolation]`

- [ ] **Step 1: Write policy-loader tests**

Tests require a closed top-level schema containing workflow inventory, default permissions, allowed write jobs, dangerous triggers, allowed mutation capabilities, and external-settings evidence states. Unknown keys and broadened write authority must fail loading.

- [ ] **Step 2: Write repository-inventory tests**

Discover both `.github/workflows/*.yml` and `*.yaml` and require policy workflow names to equal the discovered set exactly.

- [ ] **Step 3: Write immutable-action tests**

Assert the current repository fails while any external `uses:` reference is a moving tag, short SHA, or branch. Local `./` actions remain allowed.

- [ ] **Step 4: Write permission/authority mutation tests**

Synthetic workflows must fail when:
- a new job gets `contents: write`;
- Pages deploy loses the main-ref condition;
- release attest/publish loses the main-ref condition;
- a write job is moved into an unlisted workflow/job;
- a dangerous trigger is introduced.

- [ ] **Step 5: Write mutation-command tests**

Synthetic workflow `run:` blocks must fail for unlisted `git push`, `git update-ref`, remote ref deletion, mutating `gh api`, and `gh release create`; reviewed release publish remains the only `gh release create` capability.

- [ ] **Step 6: Write expression-injection tests**

Synthetic shell steps interpolating high-risk `${{ github.event.* }}` text directly into `run:` must fail; passing controlled values through an environment boundary remains representable.

- [ ] **Step 7: Observe RED on the PR**

Run through the repository's normal PR matrix. Expected failure: the new tests cannot import the not-yet-created policy/verifier modules and/or report current moving action tags. Existing unrelated tests should remain green.

- [ ] **Step 8: Commit**

Commit only tests plus the already-reviewed design/plan before production verifier code.

---

### Task 2: Extend workflow parser for run-command inspection

**Files:**
- Modify: `scripts/ci/workflow_contract.py`
- Test: `tests/test_git_operations_policy.py`
- Test: existing workflow parser/policy tests

**Interfaces:**
- Consumes: existing `WorkflowStep` structure
- Produces: `WorkflowStep.run: str` preserving block-scalar command text needed for policy scanning

- [ ] **Step 1: Add a failing parser test for `run: |`**

The test constructs a minimal workflow and asserts the parser preserves the complete multi-line shell body without evaluating expressions.

- [ ] **Step 2: Verify RED**

Expected: `WorkflowStep` has no `run` field or block scalar is not preserved.

- [ ] **Step 3: Implement minimal block-scalar parsing**

Add only enough parsing to retain `run: |` and simple scalar `run:` values while keeping the parser fail-closed on ambiguous flow/anchor forms.

- [ ] **Step 4: Verify parser GREEN**

Run focused parser and existing CI-policy tests.

- [ ] **Step 5: Commit**

Commit parser support separately so command-inspection behavior is reviewable on its own.

---

### Task 3: Implement closed Git operations policy loader

**Files:**
- Create: `git-operations-policy.json`
- Create: `scripts/ci/git_operations_policy.py`
- Test: `tests/test_git_operations_policy.py`

**Interfaces:**
- Produces: frozen `GitOperationsPolicy`
- Produces: `load_git_operations_policy(path: Path) -> GitOperationsPolicy`
- Exposes exact workflow inventory, default permission map, write-job exceptions, denied triggers, mutation exception map and external-settings evidence state vocabulary

- [ ] **Step 1: Verify loader tests are RED**

Expected: missing module/file.

- [ ] **Step 2: Add minimal closed JSON policy**

List every current workflow explicitly and record only four write-capable jobs: CodeQL analyze, Pages deploy, release attest, release publish.

- [ ] **Step 3: Implement standard-library validation**

Reject unknown/missing keys, duplicate workflows, unsupported permission values, wildcard write exceptions, unknown dangerous-trigger vocabulary, invalid authority conditions, and any external-setting state outside `externally_required_unverified` / later evidence-backed states.

- [ ] **Step 4: Verify loader GREEN**

Run focused tests.

- [ ] **Step 5: Commit**

Commit policy and loader.

---

### Task 4: Implement repository Git operations verifier

**Files:**
- Create: `scripts/ci/verify_git_operations.py`
- Test: `tests/test_git_operations_policy.py`
- Test: `tests/test_git_operations_mutations.py`
- Test: `tests/test_git_operations_workflow_inventory.py`

**Interfaces:**
- Produces: frozen ordered `GitOperationsViolation(code, location, message)`
- Produces: `verify_repository(root: Path, policy: GitOperationsPolicy) -> list[GitOperationsViolation]`
- CLI: `python scripts/ci/verify_git_operations.py --policy git-operations-policy.json`
- CLI exit 0 on zero violations, 1 on policy violations, fail-closed machine-readable JSON output

- [ ] **Step 1: Verify repository tests remain RED**

Expected current violations include moving action tags.

- [ ] **Step 2: Implement workflow discovery and exact inventory matching**

Discover both extensions and reject unclassified/missing workflows.

- [ ] **Step 3: Implement immutable-action checks**

Reuse the existing full-SHA/digest semantics; local actions are exempt.

- [ ] **Step 4: Implement permission checks**

Top-level permissions must match policy default. Job write permissions must match an exact allow-listed workflow/job permission map.

- [ ] **Step 5: Implement trigger/ref authority checks**

Reject denied triggers and require exact reviewed conditions for write-capable Pages/release jobs.

- [ ] **Step 6: Implement mutation-command inventory**

Inspect preserved `run` bodies. Deny remote mutation primitives unless exact workflow/job/capability is allow-listed.

- [ ] **Step 7: Implement expression-injection boundary**

Reject direct high-risk event expressions inside shell source while avoiding false positives for safe GitHub context fields used as controlled environment values.

- [ ] **Step 8: Verify focused GREEN except expected action-pin violations**

Mutation fixtures must pass because they are correctly rejected; repository verification should still identify the real moving action tags until Task 5.

- [ ] **Step 9: Commit**

Commit verifier implementation.

---

### Task 5: Convert every external Action to immutable identities

**Files:**
- Modify: `.github/workflows/tests.yml`
- Modify: `.github/workflows/codeql.yml`
- Modify: `.github/workflows/history-boundary.yml`
- Modify: `.github/workflows/pages.yml`
- Modify: `.github/workflows/pilot-candidate.yml`
- Modify: `.github/workflows/release.yml`
- Modify only if needed: any additional current workflow discovered with a moving external action
- Modify: `security/supply-chain-manifest.json`
- Modify: `release/github-prerelease.json`

**Interfaces:**
- Consumes exact upstream commit SHAs for the currently reviewed action versions
- Preserves workflow behavior and permission/ref conditions

- [ ] **Step 1: Resolve immutable upstream SHAs**

For each currently used action version, resolve its exact current tag target from the official action repository. Record a same-line version comment where it improves maintainability.

- [ ] **Step 2: Replace moving tags only**

Do not change action major versions, workflow behavior, permissions, conditions, paths or publication authority in this task.

- [ ] **Step 3: Recompute CodeQL file SHA-256**

Generate from exact final `.github/workflows/codeql.yml` bytes and update only its entry in `security/supply-chain-manifest.json`.

- [ ] **Step 4: Recompute supply-chain manifest SHA-256**

Generate from exact final `security/supply-chain-manifest.json` bytes and update only `source_supply_chain_manifest_sha256` in `release/github-prerelease.json`.

- [ ] **Step 5: Verify repository policy GREEN**

`python scripts/ci/verify_git_operations.py --policy git-operations-policy.json` must report zero violations.

- [ ] **Step 6: Verify existing supply-chain and prerelease verifiers GREEN**

Run `python scripts/verify_supply_chain.py` and `python scripts/verify_github_prerelease.py`.

- [ ] **Step 7: Commit**

Commit immutable action pins and exact hash-lock refresh together.

---

### Task 6: Wire control-plane verification into merge-relevant CI

**Files:**
- Modify: `.github/workflows/reliability-fast.yml`
- Modify: `reliability-policy.json` only if a trigger-surface addition is genuinely required; do not change role semantics
- Test: existing structural CI-policy tests
- Test: new Git operations tests

**Interfaces:**
- Fast role invokes `python scripts/ci/verify_git_operations.py --policy git-operations-policy.json` before expensive build work

- [ ] **Step 1: Write failing workflow-contract test**

Require the Fast workflow to invoke the Git operations verifier.

- [ ] **Step 2: Verify RED**

Expected: Fast workflow does not yet invoke it.

- [ ] **Step 3: Add the verifier step**

Place it alongside existing structural policy/privacy checks before build work.

- [ ] **Step 4: Verify focused GREEN**

Run workflow contract tests and Git operations tests.

- [ ] **Step 5: Commit**

Commit CI integration separately.

---

### Task 7: Full exact-head acceptance and PR review

**Files:**
- Modify documentation only if final behavior differs from the design/plan

**Interfaces:**
- No new interface; evidence task

- [ ] **Step 1: Run complete source test suite**

Expected: zero failures across the repository's supported Python matrix through CI.

- [ ] **Step 2: Run dedicated verifiers**

Require Git operations, reliability CI policy, supply chain, prerelease, Pages/publication authority and history boundary verifiers to pass.

- [ ] **Step 3: Inspect PR workflow jobs**

Require Fast, Specialist, Deep, normal tests, CodeQL, history and relevant Pages/release verification jobs to pass on the exact head.

- [ ] **Step 4: Confirm write jobs are skipped on PR**

Pages `Publish verified site`, release attestation and release publication must remain skipped.

- [ ] **Step 5: Review diff and review threads**

Confirm no branch deletion, GitHub settings mutation, provider mutation, release publication, public deployment or unrelated feature change.

- [ ] **Step 6: Merge only with exact expected head SHA**

Use an expected-head merge guard and preserve the repository's established evidence boundary for push-triggered runs if the connector still cannot expose them.
