# Git Operations Control Plane Design

## Purpose

Create a source-controlled, fail-closed Git operations policy that governs every GitHub Actions workflow in the repository without overloading the existing reliability-role policy.

The control plane must make repository mutation authority explicit, keep ordinary validation read-only, require immutable external-action identities, and detect dangerous trigger/permission/ref combinations before they can merge.

This design does not delete branches, change GitHub account-level rulesets, modify provider resources, publish Pages, publish releases, or claim that GitHub-side settings are configured.

## Architecture decision

Use a separate `git-operations-policy.json` and standard-library verifier that reuses the existing narrow GitHub Actions parser in `scripts/ci/workflow_contract.py`.

`reliability-policy.json` remains authoritative for Fast / Deep / Specialist / Scheduled reliability semantics. The Git operations policy is authoritative for repository-operation authority across every workflow, including tests, CodeQL, Pages, release, pilot-candidate and reliability workflows.

This separation avoids weakening the reliability policy's `contents: read` ceiling merely to accommodate legitimate Pages, CodeQL or release writes.

## Workflow discovery

The verifier discovers every regular file under `.github/workflows` ending in `.yml` or `.yaml`.

Policy workflow names must match discovered workflow names exactly. A newly added workflow therefore fails closed until it is classified in policy.

No workflow may escape policy by switching extension.

## Global invariants

Every workflow must:

- declare top-level permissions explicitly;
- default to `contents: read` unless the policy explicitly defines a narrower equivalent;
- use immutable 40-character commit SHAs for external GitHub Actions;
- use immutable image digests for external Docker actions;
- set `persist-credentials: false` for every `actions/checkout` step;
- avoid unsupported parser forms that could hide policy-relevant structure;
- avoid unreviewed remote mutation commands.

The existing repository-wide checkout-credential regression remains in force and is not duplicated as a second source of truth.

## Permission and write-authority model

Write-capable permissions are deny-by-default and job-scoped.

Allowed write-capable jobs are:

- `codeql.yml / analyze`: `security-events: write`; other declared scopes remain read-only;
- `pages.yml / deploy`: `pages: write` and `id-token: write`, only when publication authority is `workflow_dispatch` on `refs/heads/main`;
- `release.yml / attest`: `id-token: write`, `attestations: write`, `artifact-metadata: write`, only when release authority is `workflow_dispatch` on `refs/heads/main`;
- `release.yml / publish`: `contents: write`, only when release authority is `workflow_dispatch` on `refs/heads/main`.

No other job may request a write permission.

The policy records the exact permission map for each exception rather than a broad list of acceptable write scopes.

## Trigger and ref authority

Dangerous trigger classes are denied unless explicitly added to policy:

- `pull_request_target`;
- `workflow_run`;
- `repository_dispatch`.

A write-capable job must have an explicit policy authority rule. For current publication jobs the accepted rule is exactly:

```text
github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'
```

A dispatch-only condition without the main-ref binding is insufficient.

## Remote mutation command inventory

The verifier scans workflow `run:` bodies as well as action `uses:` entries for repository mutation capabilities.

Deny by default:

- `git push`;
- `git tag` when it creates or changes a remote-relevant release ref;
- `git update-ref`;
- remote branch or tag deletion;
- mutating `gh api` methods;
- `gh release create`, except the reviewed `release.yml / publish` job;
- other explicit remote-write primitives added to the policy vocabulary later.

Read-only commands such as `git fetch`, `git ls-remote`, `gh release view` and `gh attestation verify` remain permitted.

## Expression injection boundary

Workflow shell commands must not directly interpolate untrusted GitHub event text such as pull-request titles, issue bodies, comments or branch names into a `run:` script.

The first implementation covers a conservative deny-list of high-risk `${{ github.event.* }}` expression families inside `run:` blocks. Values that must be consumed by shell code should be passed through a reviewed environment boundary and handled as data, not shell source.

The implementation must prefer false-positive visibility over silently accepting an expression class it cannot reason about.

## Action pinning and updates

All external actions are converted from moving tags such as `@v7` or `@v4` to full commit SHAs with a same-line human-readable version comment where useful.

Dependabot's existing `github-actions` weekly update configuration remains the update path for these immutable references.

The verifier fails any future moving tag, branch or short SHA.

## Existing hash-lock interactions

`security/supply-chain-manifest.json` currently pins `.github/workflows/codeql.yml`; changing CodeQL requires refreshing that file's SHA-256 entry.

`release/github-prerelease.json` pins the supply-chain manifest; changing the supply-chain manifest requires refreshing `source_supply_chain_manifest_sha256`.

These updates are part of the same reviewed change and must be generated from actual final file bytes rather than guessed.

## Branch lifecycle boundary

Branch cleanup is intentionally not implemented in this control-plane PR.

A subsequent report-only lifecycle tool will classify remote branches as:

- active;
- merged/superseded candidate;
- historical evidence retain;
- release/archive retain;
- temporary/obsolete candidate;
- uncertain.

The first lifecycle generation performs no deletion and preserves TDD/evidence branches as live branches.

## GitHub settings boundary

Repository-side policy records but cannot prove external settings such as:

- branch/ruleset enforcement;
- required status checks;
- force-push/deletion protection;
- repository-level full-SHA action enforcement;
- automatic deletion of merged branches;
- default workflow-token permissions.

Until inspected through a supported GitHub settings interface, these remain `externally_required_unverified`, never `verified`.

## Lucas Critique / adaptive failure analysis

Intended adaptation:
- contributors update actions through reviewed immutable-SHA changes;
- write jobs remain rare, explicit and main-bound;
- new workflows declare authority before merge.

Gaming adaptation:
- switching `.yml` to `.yaml` must not escape discovery;
- hiding writes in another job must fail because policy workflow/job maps are exact;
- replacing `gh release create` with another remote-write primitive must remain visible through mutation inventory;
- weakening a write condition from main-bound dispatch to dispatch-only must fail.

Strategic/unexpected adaptation:
- a future legitimate write workflow should require an explicit policy change and tests rather than inheriting permission from an existing exception;
- reusable/local actions should not be mistaken for external unpinned actions;
- legitimate read-only `git fetch` and verification commands must remain usable.

Longer-term equilibrium:
- repository writes become explicit capabilities rather than incidental workflow side effects;
- Dependabot maintains immutable action identities;
- branch lifecycle and GitHub settings verification can build on the same policy without changing reliability-role semantics.

Failure signals:
- discovered workflow not represented in policy;
- action reference not immutable;
- write permission outside exact allow-list;
- write-capable job without exact authority condition;
- denied mutation command;
- dangerous trigger;
- unsupported workflow syntax that hides policy-relevant fields;
- policy claims an external GitHub setting is verified without evidence.

## Acceptance criteria

The implementation is accepted only when:

1. tests first fail on the current moving-tag workflows and absent Git operations verifier;
2. every `.yml` and `.yaml` workflow is discovered and classified;
3. all external Actions use full immutable SHAs or immutable image digests;
4. only the four reviewed write-capable job exceptions remain;
5. Pages and release write jobs remain exact main-bound manual dispatch;
6. synthetic `.yaml`, alternate-job, dangerous-trigger, permission-widening, dispatch-only and hidden-mutation fixtures fail;
7. existing checkout-token, publication-authority, reliability-policy, release, supply-chain, Pages and history tests remain green;
8. CodeQL/supply-chain/prerelease hash locks are refreshed from final bytes if CodeQL changes;
9. PR-triggered publication jobs remain skipped;
10. no branch deletion, provider mutation, public deployment or release publication occurs as part of this work.
