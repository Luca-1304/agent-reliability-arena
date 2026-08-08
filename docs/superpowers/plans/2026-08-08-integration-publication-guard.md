# Integration Publication Guard Implementation Plan

**Goal:** Keep repository verification automatic while making every reviewed public-write path require explicit manual intent from the approved `main` ref.

**Final authority condition:**

```text
github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'
```

**Tech stack:** GitHub Actions YAML, Python 3.10–3.13, standard-library `unittest`, existing workflow parser/release verifier/reliability policy.

## Constraints

- No real Pages deploy, release attestation publication, tag creation, or GitHub release during implementation/PR acceptance.
- No `[skip ci]`, force push, hidden branch bypass, workflow weakening, Vercel/provider mutation, privacy-history mutation, or branch-protection mutation.
- Verification remains active on PRs and appropriate `main` pushes.
- Dispatch from a feature branch/tag/non-main ref is not publication authority.
- Both `.yml` and `.yaml` workflow files are in publication-capability scope.
- `v0.2.0rc2` remains fixed; no free-form version input.

## Task 1 — Prove the original implicit-publication problem

- [x] Add `tests/test_publication_authority.py`.
- [x] Prove RED against the original workflows.
- [x] Confirm exactly three new authority failures while surrounding tests remain green.

Observed RED: Pages push publication, release push attest/publish, and missing release manual trigger were isolated by the new contract.

## Task 2 — Separate verification from Pages publication

- [x] Keep `pull_request`, `push` to `main`, and `workflow_dispatch` as verification/staging triggers.
- [x] Change `Publish verified site` away from ordinary-push authority.
- [x] Preserve `needs: build`, Pages job permissions, environment, deployment action, staged privacy checks and live post-deployment verification.
- [x] Update `tests/test_pages_site.py`.

## Task 3 — Separate verification from rc2 attestation/publication

- [x] Add `workflow_dispatch` to release workflow while retaining automatic PR/main verification/build triggers.
- [x] Remove normal-push authority from `attest` and `publish`.
- [x] Preserve fixed `TAG: v0.2.0rc2`, collision refusal, attestations, SBOM, provenance verification and scoped permissions.
- [x] Update `tests/test_github_prerelease.py`.

## Task 4 — Align the release-domain verifier

Initial YAML changes exposed a deeper contract mismatch: `github_prerelease.py` still required `main`-push attestation.

- [x] Trace the verifier failure to `_verify_workflow`.
- [x] Make the verifier enforce explicit publication authority for both `attest` and `publish`.
- [x] Reject normal-push publication authority.
- [x] Enforce scoped write permissions.
- [x] Enforce fixed version/tag and collision refusal.
- [x] Reject workflow-input-derived rc2 tag authority.

## Task 5 — Harden manual publication to the approved source ref

Adversarial review found that `workflow_dispatch` can target a selected ref, so dispatch-only publication was insufficient.

- [x] Add RED tests requiring dispatch **and** `refs/heads/main`.
- [x] Confirm exactly three failures: Pages, release, and capability inventory.
- [x] Update Pages deploy authority to main-bound dispatch.
- [x] Update release attest/publish authority to main-bound dispatch.
- [x] Update `github_prerelease.py` to enforce the same condition.
- [x] Update legacy Pages/release tests.

## Task 6 — Inventory publication capabilities across every workflow location

Controlled capabilities:

```text
actions/deploy-pages@  -> pages.yml / deploy
actions/attest@        -> release.yml / attest
gh release create      -> release.yml / publish
```

- [x] Reject capability use in any unapproved workflow/job.
- [x] Require the main-bound manual authority condition in every allow-listed publication job.
- [x] Add a synthetic alternate-publication-job rejection test.
- [x] Add a synthetic dispatch-from-non-main rejection test.
- [x] Prove RED when the inventory scanned only `*.yml` and a bypass used `*.yaml`.
- [x] Expand discovery to both `*.yml` and `*.yaml`.

## Task 7 — Remove implementation scaffolding

- [x] Remove temporary RED markers/notes from the operative branch.
- [x] Preserve RED/GREEN evidence in Git history rather than shipping scaffolding.
- [x] Avoid force rewriting/deleting remote branch history merely for cosmetic cleanup.

## Task 8 — Freeze documents and final diff

Expected durable files:

```text
.github/workflows/pages.yml
.github/workflows/release.yml
src/agent_reliability_arena/github_prerelease.py
tests/test_pages_site.py
tests/test_github_prerelease.py
tests/test_publication_authority.py
docs/superpowers/specs/2026-08-08-integration-publication-guard-design.md
docs/superpowers/plans/2026-08-08-integration-publication-guard.md
```

- [x] Update design/spec to main-bound publication authority.
- [x] Document `.yml` + `.yaml` inventory coverage.
- [x] Document source-verifier alignment.
- [ ] Re-run compare after final docs commit and confirm no other file remains in the diff.

## Task 9 — Exact-head PR acceptance

On the final frozen PR head require:

- [ ] Python 3.10 source tests, release verifier, installed commands, wheel, clean-wheel, dependency check.
- [ ] Python 3.11 same.
- [ ] Python 3.12 same.
- [ ] Python 3.13 same.
- [ ] Fast Python 3.10–3.13 and `Fast — Role evidence summary`.
- [ ] All Specialist gates and `Specialist — Role evidence summary`.
- [ ] Deep Python 3.10 and 3.13 full repeated gates, diagnostic redaction/scanning and `Deep — Role evidence summary`.
- [ ] CodeQL.
- [ ] Repository writable-history boundary.
- [ ] Pages verification/staging/privacy packaging succeeds; `Publish verified site` is skipped on PR.
- [ ] Release verify/build succeeds; `attest` and `publish` are skipped on PR.

Do not mark PR ready before all checks above are green on the exact final documentation head.

## Task 10 — Merge-side proof

After exact-head acceptance:

- [ ] Re-read final workflow source and capability inventory.
- [ ] Mark PR #98 ready for review.
- [ ] Merge with `expected_head_sha`; do not force or bypass checks.
- [ ] Inspect workflows on the exact merge commit.
- [ ] Prove the ordinary `main` push still runs verification but skips Pages deployment.
- [ ] Prove the ordinary `main` push still runs release verification/build but skips attest and immutable release publication.
- [ ] Confirm no public Pages/release write occurred during guard integration.

## Task 11 — Unblock Assurance Router

- [ ] Move PR #97 onto guarded `main` without force rewriting history.
- [ ] Re-run #97 exact-head full acceptance.
- [ ] Confirm Router merge push is verification-only under the new guard.
- [ ] Merge #97 only when evidence is green.

## Follow-on: repository-wide Git operations control plane

Do **not** broaden PR #98 indefinitely. After the guard and Router are integrated, create a separate design/PR covering Git operation quality across all repository locations, including:

- both workflow extensions;
- checkout credential persistence;
- top-level and job-level permissions;
- all remote-write commands/actions;
- branch/ref semantics;
- complete-history checks and writable branches;
- local/nested Git adapters;
- path/ref fidelity;
- publication authority;
- trigger-surface coverage;
- anti-gaming tests for alternate workflow/job/file locations.
