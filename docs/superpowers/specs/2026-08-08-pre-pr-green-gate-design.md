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

Proposed entry point:

`python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green.json`

The command runs from the repository root and emits a versioned machine-readable report plus a concise human summary.

No shell evaluation is permitted. Every command is represented as an argv list and executed without `shell=True`.

## Required checks

The first version runs only checks that are deterministic, local, and cheap enough to be useful before PR creation:

1. **Source compilation**
   - `python -m compileall -q src tests scripts`

2. **Full source test suite on the current interpreter**
   - `python -m unittest discover -s tests -p test_*.py -v`
   - This deliberately reuses the repository's existing unit contracts, including CI-policy, Git-operations, release, privacy, history, lifecycle, and workflow-contract tests.

3. **Repository Git-operations authority verifier**
   - run the existing `scripts/ci/verify_git_operations.py` directly as an explicit policy boundary, even though related tests also cover it;
   - this keeps a clear named failure in the preflight report if workflow authority drifts.

4. **Release/package verifier**
   - run the repository's existing release verification command directly;
   - do not duplicate release rules inside the new gate.

5. **Wheel build and clean installed verification**
   - build the wheel using the same provider-free/local path used by trusted CI primitives;
   - install/test it outside the source workspace so editable-import success cannot hide packaging defects.

6. **Local history-boundary validation**
   - verify the checked-out branch still descends from the clean history boundary using existing history logic;
   - do not fetch or mutate remotes;
   - remote freshness and full remote-branch coverage remain responsibilities of the GitHub history job.

The gate must not run Deep repetition, Specialist evidence suites, CodeQL, Pages deployment, release publication, provider calls, or any network-dependent action. Those remain GitHub-side final acceptance checks.

## Execution model

The gate should run all independent cheap checks and aggregate their outcomes instead of stopping at the first failure. This avoids repeated edit-run cycles caused by discovering one failure at a time.

Each check records:

- stable check identifier;
- argv used;
- exit status;
- pass/fail state;
- bounded diagnostic excerpt;
- elapsed duration as observational metadata only.

The gate must not declare a branch safe to merge. Its strongest allowed claim is: `pre_pr_failures = 0` for the checks it executed.

## Report contract

Schema: `pre-pr-green-gate-v1`

Top-level fields:

- `schema_version`
- `status`: `pass` or `fail`
- `checks_run`
- `checks_passed`
- `checks_failed`
- `pre_pr_failures`
- `network_used`: always `false`
- `mutation_supported`: always `false`
- `merge_authority`: always `false`
- `checks`: ordered per-check records

Exit codes:

- `0`: all required pre-PR checks passed;
- `1`: one or more checks failed;
- `2`: invalid invocation, unsupported environment, malformed configuration, or internal gate error.

A report with missing checks, duplicate check identifiers, unsupported schema fields, or an internal exception must fail closed.

## Safety boundaries

The gate must never:

- call GitHub APIs;
- access provider APIs;
- use credentials or secrets;
- run `git push`, `git update-ref`, branch deletion, tag mutation, or release mutation;
- publish Pages or releases;
- edit GitHub settings;
- create or merge pull requests;
- treat skipped/omitted checks as passes;
- weaken existing Fast, Specialist, Deep, CodeQL, publication, privacy, or history controls.

## Testing strategy

Use TDD on the implementation branch, but keep expected RED work off an open PR.

Required tests include:

1. all-success fixture returns exit `0` and `pre_pr_failures = 0`;
2. one failing command produces exit `1` and identifies that exact check;
3. multiple independent failures are all reported in one run;
4. missing executable/internal execution error fails closed with exit `2`;
5. command execution never uses a shell;
6. report ordering and JSON bytes are deterministic for equivalent results;
7. duplicate/missing check definitions are rejected;
8. source scan proves no destructive Git/GitHub/provider command is present;
9. the gate cannot claim merge safety or GitHub CI success;
10. current repository integration passes before a PR is opened.

## PR workflow and zero-failure rule

After local/off-PR implementation verification is green:

1. open one PR from the implementation branch;
2. freeze the exact head while the matrix runs;
3. inspect workflow families and individual jobs, not only top-level workflow conclusions;
4. distinguish deliberate safety skips from failures;
5. do not merge if any required job has `failure`, `cancelled`, or unexplained non-success;
6. merge with an expected-head SHA guard only after zero failed jobs are observed on the exact head.

If a new commit is required after PR opening, the zero-failure acceptance process restarts for the new exact head.

## Non-goals

Version 1 will not:

- replace GitHub Actions;
- emulate every Python version locally;
- run Deep/Specialist/CodeQL locally;
- automate branch deletion;
- change `allow_update_branch` or repository rulesets;
- add another independent policy language;
- automatically open a PR after passing.

## Success criteria

The feature is complete when:

- one provider-free command runs the agreed pre-PR checks and emits deterministic evidence;
- current repository state passes it with zero failures;
- synthetic failures are caught before PR creation;
- no new mutation/publication authority exists;
- the first implementation PR reaches final exact-head GitHub verification with zero failed required jobs before merge.
