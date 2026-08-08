# Pre-PR Green Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one deterministic, provider-free pre-PR command that reuses the repository’s trusted local checks, aggregates failures, emits machine-readable evidence, and prevents avoidable red PR runs without replacing GitHub CI.

**Architecture:** Add a focused `scripts/ci/pre_pr_green_gate.py` orchestrator with an explicit argv-only check registry and deterministic JSON report. Keep all policy truth in existing verifiers/tests; the new gate only composes them, bounds diagnostics, aggregates failures, and fails closed. Add unit tests for orchestration/safety plus an integration contract that proves the real repository can execute the gate before a PR is opened.

**Tech Stack:** Python 3.10+, `unittest`, `subprocess`, `json`, `pathlib`, existing repository verification scripts and package build tooling.

## Global Constraints

- No shell evaluation; subprocess execution must use argv lists with `shell=False`/default.
- No GitHub API, provider API, credentials, secrets, publication, branch/ref/tag mutation, repository-settings mutation, or automatic PR creation.
- `network_used` is always `false`; `mutation_supported` is always `false`; `merge_authority` is always `false`.
- The strongest success claim is `pre_pr_failures = 0` for checks actually executed.
- Missing checks, duplicate identifiers, malformed configuration, unsupported environment, or internal gate errors fail closed.
- Final GitHub PR CI remains authoritative; merge only after the exact PR head has zero failed required jobs.
- Intentional TDD RED stays off an open PR whenever practical.

---

## File Map

- Create `scripts/ci/pre_pr_green_gate.py` — check registry, argv-only execution, deterministic report, CLI and exit-code contract.
- Create `tests/test_pre_pr_green_gate.py` — unit tests for aggregation, fail-closed behavior, deterministic evidence, safety and claim boundaries.
- Create `tests/test_pre_pr_green_gate_integration.py` — repository integration/contract tests for canonical checks and current-tree execution assumptions.
- Modify `README.md` only if a concise developer workflow entry is needed after implementation is proven; do not document an unverified command.
- Keep existing CI workflows unchanged in v1 unless a regression test proves a minimal integration marker is necessary.

---

### Task 1: Deterministic orchestration and report contract

**Files:**
- Create: `scripts/ci/pre_pr_green_gate.py`
- Create: `tests/test_pre_pr_green_gate.py`

**Interfaces:**
- Produces `CheckSpec(identifier: str, argv: tuple[str, ...], timeout_seconds: int)`.
- Produces `CheckResult(identifier: str, argv: tuple[str, ...], returncode: int, status: str, diagnostic_excerpt: str)`.
- Produces `validate_check_specs(specs: Sequence[CheckSpec]) -> None`.
- Produces `run_check(spec: CheckSpec, *, cwd: Path) -> CheckResult`.
- Produces `run_gate(specs: Sequence[CheckSpec], *, cwd: Path) -> tuple[int, dict[str, object]]`.
- Produces CLI `python scripts/ci/pre_pr_green_gate.py --report <path>`.

- [ ] **Step 1: Write unit tests for the v1 report and exit codes**

Add tests that use tiny Python subprocess fixtures rather than repository checks:

```python
class PrePRGreenGateTests(unittest.TestCase):
    def test_all_success_returns_zero_and_zero_failures(self) -> None:
        specs = (
            CheckSpec("a", (sys.executable, "-c", "print('ok-a')"), 10),
            CheckSpec("b", (sys.executable, "-c", "print('ok-b')"), 10),
        )
        code, report = run_gate(specs, cwd=ROOT)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["pre_pr_failures"], 0)
        self.assertEqual(report["checks_run"], 2)
        self.assertEqual(report["checks_passed"], 2)
        self.assertEqual(report["checks_failed"], 0)
        self.assertFalse(report["network_used"])
        self.assertFalse(report["mutation_supported"])
        self.assertFalse(report["merge_authority"])

    def test_multiple_failures_are_aggregated(self) -> None:
        specs = (
            CheckSpec("a", (sys.executable, "-c", "raise SystemExit(7)"), 10),
            CheckSpec("b", (sys.executable, "-c", "raise SystemExit(9)"), 10),
        )
        code, report = run_gate(specs, cwd=ROOT)
        self.assertEqual(code, 1)
        self.assertEqual(report["pre_pr_failures"], 2)
        self.assertEqual([c["identifier"] for c in report["checks"]], ["a", "b"])
```

Also test one success + one failure, and verify execution continues after the first failure.

- [ ] **Step 2: Run only the new unit test module and confirm RED**

Run:

```bash
python -m unittest tests.test_pre_pr_green_gate -v
```

Expected: import failure because `scripts.ci.pre_pr_green_gate` does not exist.

- [ ] **Step 3: Implement minimal immutable check/result data structures and validator**

Use frozen dataclasses and reject invalid registries:

```python
@dataclass(frozen=True)
class CheckSpec:
    identifier: str
    argv: tuple[str, ...]
    timeout_seconds: int = 900


def validate_check_specs(specs: Sequence[CheckSpec]) -> None:
    identifiers = [spec.identifier for spec in specs]
    if not identifiers:
        raise GateConfigurationError("at least one check is required")
    if len(set(identifiers)) != len(identifiers):
        raise GateConfigurationError("check identifiers must be unique")
    for spec in specs:
        if not spec.identifier or not spec.argv or any(not part for part in spec.argv):
            raise GateConfigurationError("check definitions must be complete")
        if spec.timeout_seconds <= 0:
            raise GateConfigurationError("timeout_seconds must be positive")
```

- [ ] **Step 4: Implement argv-only subprocess execution and bounded diagnostics**

Use:

```python
completed = subprocess.run(
    list(spec.argv),
    cwd=cwd,
    check=False,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    timeout=spec.timeout_seconds,
)
```

Do not pass `shell=True`. Bound the stored diagnostic to a stable maximum (for example 8,000 characters), preserving the tail so the actual exception/failure remains visible.

Map non-zero child return codes to check `status="fail"`. Convert missing executable, timeout, or internal execution exception into a gate-level internal error path rather than pretending the child merely failed.

- [ ] **Step 5: Implement deterministic report construction**

The report must contain exactly:

```python
{
    "schema_version": "pre-pr-green-gate-v1",
    "status": "pass" | "fail",
    "checks_run": int,
    "checks_passed": int,
    "checks_failed": int,
    "pre_pr_failures": int,
    "network_used": False,
    "mutation_supported": False,
    "merge_authority": False,
    "checks": [...],
}
```

Do not put elapsed wall-clock time in deterministic JSON bytes. If timing is retained at all, emit it only in the human console summary, not the canonical report.

Serialize with:

```python
json.dumps(report, indent=2, sort_keys=True) + "\n"
```

- [ ] **Step 6: Implement CLI and exit-code contract**

`main()` must parse `--root` (default `.`) and required/optional `--report`. Return:

- `0` when all required checks pass;
- `1` when one or more checks execute and fail;
- `2` for invalid invocation/configuration, missing executable, timeout, unsupported environment, malformed report path, or internal gate error.

Write the report atomically when possible: create parent directory, write to a sibling temporary file, then `replace()`.

- [ ] **Step 7: Run the new unit test module and confirm GREEN**

Run:

```bash
python -m unittest tests.test_pre_pr_green_gate -v
```

Expected: all tests pass.

- [ ] **Step 8: Add deterministic/safety regression tests**

Add tests proving:

```python
self.assertEqual(render_report(report_a), render_report(report_b))
self.assertNotIn("merge_safe", payload)
self.assertNotIn("github_ci_passed", payload)
self.assertNotIn("shell=True", source_text)
self.assertNotIn("git push", source_text)
self.assertNotIn("git update-ref", source_text)
```

Also reject duplicate IDs and an empty registry.

- [ ] **Step 9: Commit Task 1**

```bash
git add scripts/ci/pre_pr_green_gate.py tests/test_pre_pr_green_gate.py
git commit -m "feat: add deterministic pre-pr gate core"
```

---

### Task 2: Canonical repository check registry

**Files:**
- Modify: `scripts/ci/pre_pr_green_gate.py`
- Create: `tests/test_pre_pr_green_gate_integration.py`

**Interfaces:**
- Produces `default_check_specs(*, python_executable: str = sys.executable) -> tuple[CheckSpec, ...]`.
- Consumes only existing repository scripts/commands; it must not duplicate their internal rules.

- [ ] **Step 1: Write contract tests for the exact ordered check identifiers**

Require this ordered registry:

```python
EXPECTED_IDS = (
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

The test must assert exact IDs and uniqueness so later additions require deliberate review.

- [ ] **Step 2: Add contract tests for canonical argv**

Require the existing trusted commands rather than equivalents.

Compilation:

```text
python -m compileall -q src tests scripts
```

Source tests:

```text
python -m unittest discover -s tests -v
```

CI structure:

```text
python scripts/ci/verify_ci_policy.py --policy reliability-policy.json
```

Git operations:

```text
python scripts/ci/verify_git_operations.py --policy git-operations-policy.json
```

Release verifier group must invoke, in order:

```text
python scripts/verify_release.py
python scripts/verify_disclosure_release.py
python scripts/verify_repeated_release.py
python scripts/verify_showcase_release.py
python scripts/verify_launch_package.py
python scripts/verify_citation_package.py
python scripts/verify_supply_chain.py
```

Local history:

```text
python scripts/verify_history_boundary.py
```

Wheel build must use the trusted no-network dependency path:

```text
python -m pip wheel --disable-pip-version-check --no-input --no-deps --no-build-isolation --wheel-dir <temp-dist> .
```

- [ ] **Step 3: Run integration-contract tests and confirm RED**

Run:

```bash
python -m unittest tests.test_pre_pr_green_gate_integration -v
```

Expected: missing `default_check_specs` / canonical registry failures.

- [ ] **Step 4: Implement the registry without shell composition**

For multi-command logical checks, do not hide commands inside `bash -c`. Either model `CheckSpec.argv_batches: tuple[tuple[str, ...], ...]` from Task 1 or represent each release verifier as a child command inside one Python-owned logical check. The Python orchestrator must execute each argv directly and aggregate its output into the logical check record.

If Task 1 used only a single `argv`, refactor it now to:

```python
@dataclass(frozen=True)
class CheckSpec:
    identifier: str
    commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int = 900
```

Update Task 1 tests in the same RED/GREEN cycle. This is preferred over introducing shell syntax.

- [ ] **Step 5: Implement isolated build paths under a temporary directory**

Use Python `tempfile.TemporaryDirectory(prefix="arena-pre-pr-")` owned by the gate. The wheel output and venv must live outside the repository tree. Do not write `dist/` or environment state into the working tree.

The wheel verification logical check must:

1. create a venv outside the workspace;
2. install the exactly one built wheel with `--no-deps`;
3. change child `cwd` to the temporary directory for import verification;
4. prove `agent_reliability_arena.__file__` does not resolve inside the workspace;
5. execute `arena-run --help`, `arena-replay --help`, and `arena-export-web --help` from the venv.

Implement this as a small Python helper mode inside the same script if required, e.g.:

```text
python scripts/ci/pre_pr_green_gate.py --internal-verify-wheel <wheel> <workspace> <venv>
```

The public default command remains `--report`; internal helper mode must not claim gate success.

- [ ] **Step 6: Add explicit dependency check using the clean wheel venv**

Run the venv interpreter’s:

```text
python -m pip check
```

Do not use the developer environment’s dependency state as the authoritative package check.

- [ ] **Step 7: Run focused unit + integration tests and confirm GREEN**

Run:

```bash
python -m unittest \
  tests.test_pre_pr_green_gate \
  tests.test_pre_pr_green_gate_integration \
  -v
```

Expected: all pass.

- [ ] **Step 8: Commit Task 2**

```bash
git add scripts/ci/pre_pr_green_gate.py tests/test_pre_pr_green_gate.py tests/test_pre_pr_green_gate_integration.py
git commit -m "feat: compose canonical pre-pr checks"
```

---

### Task 3: Fail-closed environment and bottleneck regressions

**Files:**
- Modify: `scripts/ci/pre_pr_green_gate.py`
- Modify: `tests/test_pre_pr_green_gate.py`
- Modify: `tests/test_pre_pr_green_gate_integration.py`

**Interfaces:**
- No new public API beyond Task 1/2.

- [ ] **Step 1: Add regression test for the failure that motivated this feature**

Construct a temporary mini-workspace with a workflow contract and test that intentionally disagree, then run a synthetic `source-tests` child and assert:

- gate exit is `1`;
- the failing logical check is `source-tests`;
- later independent synthetic checks still execute;
- the report contains all failures in one run.

This prevents a return to “discover one stale contract per PR run.”

- [ ] **Step 2: Add fail-closed tests for unsupported execution environments**

At minimum cover:

- repository root missing `pyproject.toml`;
- repository root not a Git worktree when history check is enabled;
- Python executable missing;
- child timeout;
- report destination unwritable/malformed.

Expected gate exit: `2`.

- [ ] **Step 3: Add source-level authority scan**

Read `scripts/ci/pre_pr_green_gate.py` and fail if it contains mutation/publication/provider capabilities such as:

```text
git push
git update-ref
git tag
gh api
gh release
workflow_dispatch
repository_dispatch
pages deploy
vercel
```

Allow descriptive references only in comments/tests if necessary; preferably keep the implementation free of these strings entirely.

- [ ] **Step 4: Add exact claim-boundary assertions**

Require:

```python
self.assertEqual(report["merge_authority"], False)
self.assertEqual(report["network_used"], False)
self.assertEqual(report["mutation_supported"], False)
self.assertNotIn("safe_to_merge", json.dumps(report))
self.assertNotIn("all_ci_passed", json.dumps(report))
```

- [ ] **Step 5: Run all gate tests**

Run:

```bash
python -m unittest \
  tests.test_pre_pr_green_gate \
  tests.test_pre_pr_green_gate_integration \
  -v
```

Expected: all pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add scripts/ci/pre_pr_green_gate.py tests/test_pre_pr_green_gate.py tests/test_pre_pr_green_gate_integration.py
git commit -m "test: harden pre-pr gate failure boundaries"
```

---

### Task 4: Real repository preflight and developer workflow

**Files:**
- Modify: `README.md` only after the real gate passes.
- Modify tests only if the real run exposes a genuine missing contract.

**Interfaces:**
- Public command: `python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green.json`.

- [ ] **Step 1: Run the complete existing source suite before the new gate**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: zero failures/errors.

If this fails, stop and debug the existing failure before blaming the new gate.

- [ ] **Step 2: Run the real pre-PR gate**

Run:

```bash
python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green.json
```

Acceptance:

```text
exit = 0
status = pass
pre_pr_failures = 0
checks_failed = 0
network_used = false
mutation_supported = false
merge_authority = false
```

- [ ] **Step 3: Re-run the gate and prove deterministic report bytes**

Run twice to two files:

```bash
python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green-a.json
python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green-b.json
cmp /tmp/pre-pr-green-a.json /tmp/pre-pr-green-b.json
```

Expected: `cmp` exits `0`.

- [ ] **Step 4: Add concise README developer workflow only after proof**

Document:

```text
Before opening a PR:
python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green.json

A zero exit means only that the deterministic local pre-PR checks passed. The full GitHub Actions matrix remains required before merge.
```

Do not describe the gate as merge authority or as a CI replacement.

- [ ] **Step 5: Run the full existing source suite and pre-PR gate again after docs change**

Run:

```bash
python -m unittest discover -s tests -v
python scripts/ci/pre_pr_green_gate.py --report /tmp/pre-pr-green-final.json
```

Expected: both exit `0`, report has `pre_pr_failures = 0`.

- [ ] **Step 6: Commit Task 4**

```bash
git add README.md scripts/ci/pre_pr_green_gate.py tests/test_pre_pr_green_gate.py tests/test_pre_pr_green_gate_integration.py
git commit -m "docs: require green pre-pr preflight"
```

---

### Task 5: Open one GREEN implementation PR and enforce zero-failure merge

**Files:**
- No implementation changes unless GitHub CI reveals a genuine defect not reproducible locally.

**Interfaces:**
- Consumes the exact implementation branch head proven by Task 4.

- [ ] **Step 1: Compare implementation branch with `main`**

Require `behind_by = 0` before PR creation. If `main` moved, update/rebase the branch first and rerun Task 4’s full verification from the new exact head.

- [ ] **Step 2: Open one implementation PR only after off-PR preflight is green**

PR body must record:

- exact head SHA;
- local/source suite result;
- pre-PR report result `pre_pr_failures = 0`;
- safety boundaries;
- statement that full GitHub matrix is still required.

- [ ] **Step 3: Inspect every PR-triggered workflow family on the exact head**

Require top-level success for all required families that trigger on the change, including tests, Fast, Specialist, Deep, CodeQL, history/lifecycle, Pages verification, release verification if triggered, and pilot checks if triggered.

- [ ] **Step 4: Inspect individual jobs**

Treat required `failure`, `cancelled`, or unexplained non-success as blocking. Deliberate failure-only or publication-authority skips may remain skipped when their documented condition is false.

- [ ] **Step 5: If any genuine failure occurs, do not merge**

Use systematic debugging. Make the smallest root-cause fix on the implementation branch, rerun the pre-PR gate where applicable, then restart exact-head GitHub verification. Do not disable, skip, or weaken a check just to obtain green status.

- [ ] **Step 6: Merge with expected-head guard only at zero failed required jobs**

Use squash merge and pass the exact verified head SHA. Preserve the feature branch unless/until the separate branch-retirement authority project approves deletion.

- [ ] **Step 7: Verify resulting `main` SHA**

Confirm the merge result is current `main`. Do not claim push-triggered post-merge workflow evidence unless the connected GitHub surface can actually expose it.
