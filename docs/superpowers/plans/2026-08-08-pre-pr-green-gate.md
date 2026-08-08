# Pre-PR Green Gate Implementation Plan

**Goal:** Prevent avoidable red pull-request runs with one deterministic local preflight while keeping GitHub CI authoritative.

**Architecture:** `scripts/ci/pre_pr_green_gate.py` is a thin argv-only orchestrator over existing tests/verifiers. It aggregates ordinary failures, fails closed on internal/environment faults, performs package verification in isolated temporary paths, and emits deterministic `pre-pr-green-gate-v1` evidence. It grants no network, mutation, publication, or merge authority.

## Implementation sequence

1. Add immutable logical-check/result models and deterministic report/exit-code contracts.
2. Compose canonical source compilation/tests, CI policy, Git-operations policy, release verifiers, provider-free installed-command smoke, local history boundary, wheel build, clean-wheel verification, and clean-environment dependency check.
3. Keep multi-command checks inside Python-owned argv batches; never use shell composition.
4. Build wheel/venv/smoke outputs outside the repository. Force the clean venv's scripts directory to the front of `PATH` and set `PYTHONNOUSERSITE=1` so nested test subprocesses cannot resolve developer/global commands.
5. Add unit/integration regressions for aggregation, duplicate/missing definitions, missing executables, timeout/internal exit `2`, deterministic report bytes, temp-path normalization, no mutation/shell authority, exact registry ordering, clean-wheel isolation, and repository-root fail-closed behavior.
6. Run focused off-PR fixture verification before creating the PR. Because the current chat environment cannot clone/materialize the full GitHub repository, use the first PR run as the authoritative real-repository execution and block merge on any genuine failure.
7. Add README usage only after the real repository candidate proves green.
8. On every PR head, inspect both workflow families and individual jobs. Required `failure`, `cancelled`, or unexplained non-success blocks merge; documented failure-only/publication safety skips are allowed only when their condition is false.
9. If a genuine failure appears, root-cause it, make the smallest fix, rerun applicable preflight verification, and restart exact-head CI verification.
10. Squash-merge with `expected_head_sha` only after the final exact head has zero failed required jobs.

## Current off-PR evidence

- Gate unit/integration fixture: 19/19 passing after clean-venv PATH hardening.
- Clean-wheel dummy package path exercised: build, no-deps install, import outside workspace, clean source-test slot, release-verifier batch, all seven installed-command slots, and dependency check.
- Engine blob pushed to the feature branch matches the locally verified blob.
- Feature branch must remain `behind_by=0` before PR creation.

## Safety constraints

Do not weaken Fast/Specialist/Deep/CodeQL/history/privacy/publication controls. Do not call provider APIs. Do not mutate refs/tags/settings. Do not publish. Do not auto-delete branches. Do not treat this gate as merge authority.
