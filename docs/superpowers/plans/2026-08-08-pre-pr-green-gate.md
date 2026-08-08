# Pre-PR Green Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one deterministic, provider-free command that catches avoidable repository, policy, test and packaging failures before a pull request is opened.

**Architecture:** Add `scripts/ci/pre_pr_green_gate.py` as a thin Python orchestrator. It owns only check ordering, argv-only subprocess execution, bounded diagnostics, deterministic reporting and fail-closed exit codes; existing tests/verifiers remain the source of truth. Multi-command logical checks are native from the start so release/package verification does not require shell composition or a later refactor.

**Tech Stack:** Python 3.10+, `unittest`, `subprocess`, `json`, `pathlib`, `tempfile`, existing repository verification scripts and package tooling.

## Global Constraints

- No `shell=True`, network/API calls, credentials, provider actions, publication, branch/ref/tag mutation, settings mutation, or automatic PR creation.
- `network_used=false`, `mutation_supported=false`, `merge_authority=false` in every successful gate report.
- Missing/duplicate checks, unsupported environment, missing executable, timeout or internal error fail closed with exit `2`.
- Child check failures aggregate and return exit `1`; all checks passing returns `0`.
- The gate may claim only that its own required pre-PR checks passed. GitHub CI remains authoritative for merge.
- Intentional TDD RED remains off an open PR whenever practical.

## File Map

- Create `scripts/ci/pre_pr_green_gate.py` — immutable check model, canonical registry, execution, clean-wheel helper, deterministic report and CLI.
- Create `tests/test_pre_pr_green_gate.py` — orchestration, aggregation, determinism, fail-closed and safety tests.
- Create `tests/test_pre_pr_green_gate_integration.py` — exact registry/command contracts and current-repository integration assumptions.
- Modify `README.md` only after the real gate passes.

---

### Task 1: Core orchestration and deterministic evidence

**Files:**
- Create: `scripts/ci/pre_pr_green_gate.py`
- Create: `tests/test_pre_pr_green_gate.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class CheckSpec:
    identifier: str
    commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int = 900

@dataclass(frozen=True)
class CheckResult:
    identifier: str
    commands: tuple[tuple[str, ...], ...]
    returncode: int
    status: str
    diagnostic_excerpt: str

def validate_check_specs(specs: Sequence[CheckSpec]) -> None: ...
def run_check(spec: CheckSpec, *, cwd: Path, env: Mapping[str, str] | None = None) -> CheckResult: ...
def run_gate(specs: Sequence[CheckSpec], *, cwd: Path) -> tuple[int, dict[str, object]]: ...
def render_report(report: Mapping[str, object]) -> str: ...
```

- [ ] Write RED tests for two passing checks, one failure, multiple aggregated failures, empty registry and duplicate identifiers.
- [ ] Run `python -m unittest tests.test_pre_pr_green_gate -v`; expected RED because module is absent.
- [ ] Implement frozen data structures and validation. Reject empty IDs, empty command batches, empty argv elements and non-positive timeouts.
- [ ] Execute every command using `subprocess.run(list(argv), shell=False/default, check=False, text=True, stdout=PIPE, stderr=STDOUT, timeout=...)`. Continue through ordinary non-zero child results; convert missing executable/timeout/internal execution errors to `GateInternalError`.
- [ ] Bound diagnostics to 8,000 characters, keeping the tail.
- [ ] Build report with exactly `schema_version`, `status`, `checks_run`, `checks_passed`, `checks_failed`, `pre_pr_failures`, `network_used`, `mutation_supported`, `merge_authority`, `checks`.
- [ ] Serialize with `json.dumps(..., indent=2, sort_keys=True) + "\n"`; exclude elapsed time and temp paths from canonical report bytes.
- [ ] Add CLI `--root` and `--report`; atomically write report via sibling temporary file + `Path.replace()`.
- [ ] Verify exit contract `0/1/2` with tests.
- [ ] Add source assertions that implementation does not contain `shell=True`, destructive Git commands or claims such as `safe_to_merge`/`all_ci_passed`.
- [ ] Run focused tests to GREEN and commit `feat: add deterministic pre-pr gate core`.

---

### Task 2: Canonical repository check registry and isolated package verification

**Files:**
- Modify: `scripts/ci/pre_pr_green_gate.py`
- Create: `tests/test_pre_pr_green_gate_integration.py`

**Interface:**

```python
def default_check_specs(*, python_executable: str = sys.executable, temp_root: Path) -> tuple[CheckSpec, ...]: ...
```

Required ordered IDs:

```python
(
    "compile-source",
    "source-tests",
    "ci-policy",
    "git-operations-policy",
    "release-verifiers",
    "history-boundary-local",
    "build-wheel",
    "verify-wheel-import-and-commands",
    "dependency-check",
)
```

- [ ] Write RED contract tests requiring the exact ordered IDs and exact existing commands.
- [ ] Canonical commands must reuse current CI:
  - `python -m compileall -q src tests scripts`
  - `python -m unittest discover -s tests -v`
  - `python scripts/ci/verify_ci_policy.py --policy reliability-policy.json`
  - `python scripts/ci/verify_git_operations.py --policy git-operations-policy.json`
  - release batch, in order: `verify_release.py`, `verify_disclosure_release.py`, `verify_repeated_release.py`, `verify_showcase_release.py`, `verify_launch_package.py`, `verify_citation_package.py`, `verify_supply_chain.py`
  - `python scripts/verify_history_boundary.py` without remote fetch mode
  - wheel build with `python -m pip wheel --disable-pip-version-check --no-input --no-deps --no-build-isolation --wheel-dir <temp-dist> .`
- [ ] Run integration-contract tests; expected RED for missing registry.
- [ ] Implement registry using direct argv batches only.
- [ ] Own build state under `TemporaryDirectory(prefix="arena-pre-pr-")`; never write `dist/` or a venv into the repository.
- [ ] Implement an internal Python helper path for wheel verification rather than `bash -c`: create clean venv, install exactly one wheel with `--no-deps`, run import verification from outside workspace, then run clean-venv `arena-run --help`, `arena-replay --help`, `arena-export-web --help`.
- [ ] Make `dependency-check` run clean-venv `python -m pip check`, not the developer environment.
- [ ] Keep temp paths out of deterministic report argv; normalize temp-root arguments to stable placeholders in report rendering while executing real paths internally.
- [ ] Run `python -m unittest tests.test_pre_pr_green_gate tests.test_pre_pr_green_gate_integration -v` to GREEN.
- [ ] Commit `feat: compose canonical pre-pr checks`.

---

### Task 3: Bottleneck regressions and fail-closed environment

**Files:**
- Modify: `scripts/ci/pre_pr_green_gate.py`
- Modify: `tests/test_pre_pr_green_gate.py`
- Modify: `tests/test_pre_pr_green_gate_integration.py`

- [ ] Add a regression reproducing the motivating stale workflow/test-contract mismatch: `source-tests` fails, later independent checks still run, and all failures appear in one report.
- [ ] Add exit-`2` tests for missing `pyproject.toml`, non-Git worktree when the real registry is requested, missing Python executable, subprocess timeout and invalid report destination.
- [ ] Add exact claim-boundary assertions: report has `merge_authority=false`, `network_used=false`, `mutation_supported=false`, and never claims GitHub CI/merge safety.
- [ ] Add implementation-source authority scan prohibiting remote mutation/publication/provider command strings.
- [ ] Run focused gate tests to GREEN.
- [ ] Run `python -m unittest discover -s tests -v`; require zero failures/errors before proceeding.
- [ ] Commit `test: harden pre-pr gate failure boundaries`.

---

### Task 4: Real preflight proof and developer workflow

**Files:**
- Modify: `README.md` only after proof.

- [ ] Run `python -m unittest discover -s tests -v`; require exit `0`.
- [ ] Run `python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green.json`; require exit `0`, `status=pass`, `pre_pr_failures=0`, `checks_failed=0`, and all three authority flags false.
- [ ] Run the gate twice to `/tmp/pre-pr-green-a.json` and `/tmp/pre-pr-green-b.json`; `cmp` must return `0`.
- [ ] Only now document the command in `README.md` with the explicit warning that GitHub Actions remains required before merge.
- [ ] Re-run the full source suite and real gate after documentation change; both must exit `0`.
- [ ] Commit `docs: require green pre-pr preflight`.

---

### Task 5: One GREEN PR and zero-failure merge

- [ ] Confirm implementation branch is `behind_by=0` versus `main`; if not, update it and rerun Task 4 verification.
- [ ] Open one PR only after off-PR preflight is green. Record exact head SHA and `pre_pr_failures=0` in PR body.
- [ ] Inspect every triggered workflow family on that exact head: tests, Fast, Specialist, Deep, CodeQL, history/lifecycle, Pages verification and any release/pilot checks that trigger.
- [ ] Inspect individual jobs, not just top-level conclusions. Required `failure`, `cancelled`, or unexplained non-success blocks merge. Documented failure-only/publication safety skips are allowed when their condition is false.
- [ ] If any genuine failure occurs, use systematic debugging, fix root cause, rerun applicable preflight checks and restart exact-head CI verification. Never disable or weaken a gate to obtain green status.
- [ ] Squash-merge with `expected_head_sha` only after zero failed required jobs on the exact head.
- [ ] Confirm resulting merge SHA is current `main`; do not claim post-merge push CI unless the connected GitHub surface exposes it.

## Self-review result

- Spec coverage: complete; every required local check, report field, safety boundary and PR acceptance rule maps to a task.
- Placeholder scan: no TBD/TODO/"implement later" instructions.
- Type consistency: `CheckSpec.commands` is the single model from Task 1 onward; no planned single-argv refactor remains.
- Scope: one subsystem only; no branch deletion/settings/publication work included.
