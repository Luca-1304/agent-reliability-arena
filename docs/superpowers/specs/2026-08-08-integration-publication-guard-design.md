# Integration Publication Guard — Design

Date: 2026-08-08
Repository: `Luca-1304/agent-reliability-arena`
Status: implemented on feature branch; exact-head acceptance required before merge

## Purpose

Decouple ordinary Git integration from public publication without weakening automatic verification.

Before this guard, ordinary `main` pushes could cause two unrelated public writes:

1. `.github/workflows/pages.yml` could deploy the GitHub Pages site.
2. `.github/workflows/release.yml` could attest and publish the immutable `v0.2.0rc2` prerelease when release-sensitive files changed.

That made an ordinary package/tooling merge capable of changing public state merely because its paths matched a workflow trigger.

## Primary invariant

**Verification may remain automatic. Publication requires both explicit operator intent and the approved source branch.**

The canonical publication authority condition is:

```text
github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'
```

Neither changed paths, a normal `main` push, nor manual dispatch from a feature/tag/non-main ref grants publication authority.

## Non-goals

- Do not weaken Fast, Specialist, Deep, CodeQL, history, Pages privacy packaging, release verification, or clean-wheel testing.
- Do not use `[skip ci]`, hidden branches, force-pushes, credential tricks, or bypass tokens.
- Do not change Vercel/provider state, privacy-history records, branch protection, public-site content, or release artifact format.
- Do not execute a real Pages deployment, attestation publication, tag creation, or GitHub release as part of proving this guard.

## Architecture

### Verification plane

Pull requests and appropriate `main` pushes continue to run non-destructive verification/build work, including tests, package/release verification, Pages staging/privacy checks, reliability roles, CodeQL, and history checks.

Verification may produce temporary workflow artifacts. It does not acquire publication authority.

### Publication plane

Publication-capable jobs are a separate authority boundary. A public-write job must satisfy all of the following:

1. required verification dependencies passed;
2. event is `workflow_dispatch`;
3. workflow ref is exactly `refs/heads/main`;
4. write permission is scoped to the publication job, not granted globally;
5. the publication capability is one of the reviewed allow-listed jobs.

## Pages contract

The Pages workflow keeps `pull_request`, `push` to `main`, and `workflow_dispatch` triggers because all three may legitimately run verification/staging.

`Publish verified site` may execute only when:

```text
github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'
```

It still depends on the existing build/stage/privacy job, deploys that exact verified artifact, and runs the live portfolio/CV/audit/Arena boundary verification after deployment.

Consequences:

- PR: verify/stage only; deploy skipped.
- ordinary `main` push: verify/stage only; deploy skipped.
- dispatch against non-main ref: verify/stage may run; deploy skipped.
- dispatch against `main`: verified deployment is authorized.

## Release contract

The rc2 workflow keeps automatic verification/build for PRs and release-sensitive `main` changes.

`attest` and `publish` may execute only when:

```text
github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'
```

The release remains fixed to `TAG: v0.2.0rc2`. No free-form version input may alter that authority. Existing collision refusal for an already existing tag or GitHub release remains mandatory, and the attestation/publication jobs retain narrowly scoped permissions.

Future versions require a reviewed release contract rather than reusing rc2 logic by changing a dispatch input.

## Repository-wide publication capability inventory

Structural tests inventory all workflow files using both GitHub-supported extensions:

- `.github/workflows/*.yml`
- `.github/workflows/*.yaml`

The controlled publication capabilities are currently:

- `actions/deploy-pages@` → `pages.yml` / `deploy`
- `actions/attest@` → `release.yml` / `attest`
- `gh release create` → `release.yml` / `publish`

A capability appearing in another workflow, another job, or without the main-bound dispatch condition is a test failure.

Synthetic tests prove the inventory rejects:

- an alternate unapproved publication job;
- a `.yaml` bypass rather than `.yml`;
- dispatch-only publication that is not also bound to `main`.

## Source verifier alignment

`src/agent_reliability_arena/github_prerelease.py` independently verifies the release workflow authority contract. It rejects:

- normal-push authority in attest/publish;
- missing main-bound dispatch authority;
- global write permissions;
- contents write on the attestation job;
- missing contents write on the publication job;
- a publication tag that differs from the verified package version;
- workflow-input-derived release tags;
- removal of release/tag collision refusal.

This prevents YAML policy and release-domain verification from drifting apart.

## Failure behavior

- Verification failure blocks publication.
- Missing manual intent blocks publication.
- Dispatch from a non-main ref blocks publication.
- Existing tag/release collision blocks rc2 publication.
- Pages live-verification failure makes an intentional deployment fail visibly.
- No fallback publication path, `continue-on-error`, or ordinary push path is permitted.

## Anti-gaming / adaptation review

### Intended adaptation
Routine merges become verification-only. Public deployment/release becomes a conscious action sourced from `main`.

### Gaming / exploit adaptation
Likely bypass attempts include moving a publication command to another workflow, using `.yaml` instead of `.yml`, dispatching a feature branch, weakening the job condition, adding an alternate deploy/release job, or relying on path filters as authority. Structural inventory and source-verifier checks are designed to make these visible failures.

### Strategic / unexpected adaptation
Public content may become stale because merges no longer auto-deploy. That is an explicit product/deployment decision and is preferable to accidental publication authority.

### Longer-term equilibrium
Verification remains frequent and low-authority; publication remains rarer, explicit, source-bound, and auditable.

### Failure signal
The model has failed if any ordinary PR, ordinary `main` push, non-main dispatch, unreviewed workflow file, or alternate publication job can deploy Pages, create release attestations, create a tag, or create a GitHub release.

## Test strategy

RED/GREEN evidence covers:

1. original push-authorized Pages/release behavior;
2. release verifier disagreement with the first dispatch-only workflow edit;
3. manual dispatch not being bound to `main`;
4. `.yaml` workflow files escaping an initial `.yml`-only inventory.

Final acceptance requires exact-head success from:

- Python 3.10, 3.11, 3.12, 3.13 source tests, release verifier, installed commands, wheel build, clean-wheel verification, dependency check;
- Fast plus `Fast — Role evidence summary`;
- all Specialist gates plus `Specialist — Role evidence summary`;
- Deep on Python 3.10 and 3.13 plus diagnostic redaction/scanning and `Deep — Role evidence summary`;
- CodeQL;
- repository writable-history boundary;
- Pages build/stage/privacy packaging, with deploy skipped on PR;
- release verify/build, with attest and publish skipped on PR.

No real publication is needed for structural acceptance.

## Integration sequence

1. Finish exact-head verification of this guard PR.
2. Confirm final diff contains only reviewed guard implementation/tests/docs.
3. Merge guard into `main` using the exact expected head SHA.
4. Observe the resulting `main` push and explicitly verify Pages deploy and release attest/publish are skipped while verification runs.
5. Update/rebase Assurance Router PR #97 onto guarded `main` without force rewriting history.
6. Re-run #97 exact-head verification and merge only if green.
7. Observe the Router merge push and again verify publication jobs stay skipped.
8. Start a separate repository-wide Git operations control-plane audit rather than expanding this already-reviewed guard indefinitely.

## Success criteria

The guard is successful only when:

- PR and `main` verification remain active;
- ordinary `main` pushes cannot publish Pages or rc2;
- non-main manual dispatch cannot publish Pages or rc2;
- intentional `main` dispatch reruns required verification before any public write;
- publication capabilities in both `.yml` and `.yaml` workflows are allow-listed and source-bound;
- write permissions remain narrowly scoped;
- release verification and workflow authority agree;
- no security/privacy/reliability gate is weakened;
- Assurance Router PR #97 can later merge without implicitly causing public publication.
