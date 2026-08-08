# Pre-PR Green Gate — Design

Date: 2026-08-08
Base: `main` at `64bf81047b0dd2f85b5aa0517e021b61b8424ea3`
Status: approved design for implementation planning

## Purpose

Prevent avoidable red pull-request runs by catching local repository, policy, test, and packaging failures before a PR is opened.

The gate is a preflight, not a replacement for GitHub CI. The final PR matrix remains authoritative for Python-version coverage, Fast/Specialist/Deep reliability evidence, CodeQL, Pages verification, and merge acceptance.

## Core rule

The development flow becomes:

1. build on a branch off `main`;
2. run one deterministic pre-PR command;
3. open a PR only when that command reports zero failures;
4. run the full GitHub PR matrix;
5. merge only when the exact PR head has zero failed jobs.

Intentional TDD RED evidence must be produced outside an open PR whenever practical so expected failures do not pollute the PR Actions history.

## Architecture

Add one thin orchestration layer under `scripts/ci/`. It reuses existing repository verifiers and tests through argv-based subprocess execution. It does not reimplement their policies.

Canonical entry point:

`python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green.json`

The command runs from the repository root and emits a versioned machine-readable report plus a concise human summary.

No shell evaluation is permitted. Every command is represented as an argv list and executed without `shell=True`.

## Required checks

Version 1 runs only checks that are deterministic, local, and appropriate before PR creation. It mirrors the trusted single-interpreter portions of `.github/workflows/tests.yml` without copying policy logic.

1. Source compilation and full source tests.
2. CI-structure and Git-operations authority verification.
3. Canonical release/package verifiers.
4. Full provider-free installed-command fixture smoke.
5. Wheel build and clean installed verification, including source tests, release verifiers, installed commands and dependency checks.
6. Local clean-history-boundary validation without fetching/mutating remotes.

The gate must not run Deep repetition, Specialist evidence suites, CodeQL, Pages deployment, release publication, provider calls, or any network-dependent action. Those remain GitHub-side final acceptance checks.

## Execution model

The gate runs all independent pre-PR checks and aggregates their outcomes instead of stopping at the first ordinary check failure. Environment/setup failures that make later results meaningless may stop execution with exit `2`, but already-completed check evidence must still be retained in the report.

Successful checks do not retain noisy stdout in canonical evidence. Failed checks retain a bounded diagnostic tail. Temporary/workspace paths are normalized so equivalent green runs produce deterministic JSON bytes.

## Report contract

Schema: `pre-pr-green-gate-v1`.

Required top-level fields are `schema_version`, `status`, `checks_run`, `checks_passed`, `checks_failed`, `pre_pr_failures`, `network_used`, `mutation_supported`, `merge_authority`, and ordered `checks`.

Exit codes:
- `0`: all required pre-PR checks passed;
- `1`: one or more required checks completed and failed;
- `2`: invalid invocation, unsupported environment, malformed configuration, missing required executable, timeout, or internal gate error.

`network_used`, `mutation_supported`, and `merge_authority` are always false for normal gate evidence. The gate must never claim that GitHub CI passed or that a branch is safe to merge.

## Safety boundaries

The gate must never call GitHub/provider APIs, use credentials/secrets, mutate refs/tags/branches, publish Pages/releases, edit GitHub settings, create/merge pull requests, or weaken existing Fast/Specialist/Deep/CodeQL/privacy/history/publication controls.

## Testing strategy

Use TDD off an open PR whenever practical. Required coverage includes all-success, single/multiple failures, failure aggregation, internal fail-closed behavior, deterministic report bytes, duplicate/missing check rejection, no-shell/no-mutation authority scans, clean-wheel import outside workspace, venv command-path isolation, and temporary-output collision protection.

## PR workflow and zero-failure rule

After off-PR implementation verification is green, open one PR, freeze the exact head, inspect workflow families and individual jobs, allow only documented conditional safety skips, and do not merge while any required job is failed, cancelled, or unexplained non-success. If a new commit is required, restart exact-head verification.

## Non-goals

Version 1 does not replace GitHub Actions, emulate every Python version locally, run Deep/Specialist/CodeQL locally, automate branch deletion, change `allow_update_branch`/rulesets, add an independent policy language, or automatically open a PR.

## Success criteria

The feature is complete when one provider-free command runs the agreed pre-PR checks and emits deterministic evidence; synthetic failures are caught before PR creation; no new mutation/publication authority exists; and the implementation PR reaches final exact-head GitHub verification with zero failed required jobs before merge.
