# Integration Publication Guard — Design

Date: 2026-08-08
Repository: `Luca-1304/agent-reliability-arena`
Status: approved design, implementation not started

## Purpose

Decouple ordinary repository integration from public publication without weakening verification.

The repository currently has two important side effects on `main` pushes:

1. `.github/workflows/pages.yml` publishes the GitHub Pages site after verification.
2. `.github/workflows/release.yml` can attest and publish the immutable `v0.2.0rc2` prerelease when release-sensitive paths such as `pyproject.toml` change.

That coupling means an otherwise local package change can trigger unrelated public deployment and release actions. The guard must make publication an intentional event while preserving automatic verification.

## Primary invariant

**Verification may remain automatic; publication requires explicit publication intent.**

A normal pull request or merge must never gain public publication authority merely because a changed file happens to match a broad workflow path filter.

## Non-goals

- Do not weaken or bypass Fast, Specialist, Deep, CodeQL, history, Pages privacy packaging, or release verification.
- Do not use `[skip ci]`, hidden branch conventions, or token-based bypasses.
- Do not disable existing privacy verification.
- Do not change Vercel state, provider state, historical privacy records, or branch protection.
- Do not publish a release as part of implementing this guard.
- Do not redesign the public site or release artifact format.

## Approaches considered

### A. Path-filter-only refinement

Narrow the existing `push` path filters so fewer ordinary changes trigger publication.

Rejected as the primary solution. It reduces frequency but keeps publication authority implicit in file selection. A future path-list edit could silently recreate the problem.

### B. Separate verification from publication using explicit workflow intent — recommended

Keep verification jobs automatic on pull requests and appropriate `main` changes. Move public publication into explicit, narrowly defined execution paths.

For Pages, verification/staging remains automatic, while the deploy job requires a deliberate publication condition rather than every `main` push.

For releases, verification/build remains automatic on release-relevant changes, while attest/publish requires an explicit release event or manual dispatch with a fixed version contract.

This approach preserves evidence while removing accidental authority.

### C. External release/deployment orchestration

Move publication entirely outside GitHub Actions into a separate deployment system.

Rejected for now. It adds infrastructure and operational complexity without being necessary to solve the current coupling.

## Architecture

### 1. Verification plane

Existing verification remains automatic and non-destructive:

- source tests;
- package build and clean-wheel verification;
- release-boundary verification;
- Pages site staging;
- public-CV privacy verification;
- Fast, Specialist and Deep reliability gates;
- CodeQL and history checks.

The verification plane may create short-lived workflow artifacts, but it does not publish a site, create a Git tag/release, or write public deployment state.

### 2. Publication plane

Publication is a separate authority boundary.

A publication job must satisfy both:

1. all required verification dependencies passed; and
2. an explicit publication-intent condition is true.

The intent signal must be visible in workflow source and auditable from the triggering GitHub event. It must not be inferred solely from a changed path.

### 3. Pages contract

The Pages workflow keeps pull-request and `main` verification/staging behavior.

The actual `Publish verified site` job must no longer run merely because the event is a push to `main`.

Recommended publication mechanism:

- `workflow_dispatch` is the publication-authority event;
- the dispatch reruns the same build/privacy/staging verification before deploy;
- deployment uses the exact verified artifact from that dispatch run;
- ordinary PRs and `main` pushes stop after verification/staging.

This preserves the existing live verification after deployment while making the public write deliberate.

### 4. Release contract

The rc2 workflow keeps automatic verification/build for PRs and release-sensitive changes.

The attestation and immutable release publication jobs must not execute from an ordinary `main` push.

Recommended publication mechanism:

- add `workflow_dispatch` with an explicit expected version input fixed to `v0.2.0rc2` while this release workflow exists;
- attest/publish jobs require `workflow_dispatch` plus exact expected-version validation;
- verification/build reruns in the same dispatch before attestation;
- existing refusal to overwrite an existing tag/release remains mandatory;
- no version is inferred from free-form user text;
- future versions should use a new reviewed release contract rather than silently reusing rc2 logic.

If GitHub's workflow input model makes the fixed-version input add no safety value, the implementation may use dispatch itself as the authority signal, but the workflow must retain an explicit hard-coded `TAG=v0.2.0rc2` consistency check.

## Data and control flow

### Normal pull request

change → automatic verification → evidence only → stop

### Normal merge / push to main

change → automatic verification → evidence only → stop

### Intentional Pages publication

manual dispatch → full Pages verification/staging → deploy verified artifact → live boundary verification

### Intentional rc2 publication

manual dispatch → release verification/build → version/refusal checks → attest → immutable prerelease publish → published metadata verification

## Failure behavior

- Verification failure blocks publication.
- Missing or invalid publication intent blocks publication.
- Existing release/tag collision blocks publication.
- Pages live verification failure makes the publication workflow fail visibly.
- No fallback path may publish when the intended gate fails.
- No `continue-on-error` may be added to publication-authority checks.

## Anti-gaming / adaptation review

Changing publication policy changes operator and automation behavior, so the design explicitly checks likely adaptations.

### Intended adaptation

Routine merges become safe to perform without causing unrelated public writes. Publication becomes a conscious release/deployment action.

### Gaming / exploit adaptation

Potential bypasses include relabeling an ordinary push as publication, weakening the event condition, adding an alternate deploy job, or using a path-filter exception.

Countermeasure: structural tests must enumerate every job/action capable of Pages deploy, attestation, tag creation or GitHub release creation and require the explicit publication-intent contract.

### Strategic / unexpected adaptation

Developers may stop noticing stale public content because merges no longer auto-deploy. This is acceptable: deployment freshness is a product decision, not a justification for implicit publication authority.

### Longer-term equilibrium

Verification becomes frequent and cheap in authority terms; publication becomes rarer and deliberate. This is the intended equilibrium.

### Failure signal

The model is failing if any ordinary PR or ordinary `main` push can execute a public deploy, create an attestation intended for release publication, create a tag, or create a GitHub release.

## Test strategy

Implementation must use RED/GREEN TDD.

Required structural tests before workflow edits:

1. A normal `main` push cannot satisfy the Pages deploy condition.
2. A normal `main` push cannot satisfy rc2 attest/publish conditions.
3. Pages dispatch still requires the existing build/stage/privacy job before deployment.
4. Release dispatch still requires verified build before attestation and publication.
5. Release workflow retains collision refusal for existing tag/release.
6. No alternate publication-capable job bypasses the explicit-intent condition.
7. PR verification remains active for both workflows.
8. Existing public-CV source/staged/live verification contract remains present; live verification belongs to the intentional publication path.
9. Existing checkout credential and permission boundaries remain intact.
10. Existing workflow parser/CI-policy tests stay green.

Acceptance after implementation requires the repository's normal Python matrix, Fast, Specialist, Deep, CodeQL, Pages/privacy packaging, release verification and history checks on the exact PR head.

No real Pages deploy or release publication is required to prove the structural guard. A later intentional publication event remains a separate operational decision.

## Integration sequence

1. Implement this guard in a dedicated PR from current `main`.
2. Prove RED tests fail against the current implicit-publication workflows.
3. Make the smallest workflow changes that satisfy the explicit-intent contract.
4. Run full exact-head acceptance.
5. Merge the guard only after evidence is green.
6. Rebase or update Assurance Router PR #97 onto the guarded `main`.
7. Re-run #97 exact-head verification.
8. Merge #97; the merge should now produce verification only, not Pages/release publication.

## Rollback

The guard is workflow-only behavior. If its implementation causes verification regressions, do not merge it. If a later merged guard must be reverted, revert the guard commit through a reviewed PR; do not bypass checks or manually mutate publication state as a shortcut.

## Success criteria

The design succeeds when all of the following are true:

- ordinary PRs still receive the established verification evidence;
- ordinary `main` pushes still receive appropriate verification;
- ordinary `main` pushes cannot publish Pages;
- ordinary `main` pushes cannot attest/publish rc2;
- intentional publication still reruns required verification before any public write;
- no CI/security/privacy gate is weakened;
- Assurance Router PR #97 can eventually merge without implicitly causing public publication.
