# Reliability Gate v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repository-owned reliability gate that proves 15-pass determinism, editable-versus-wheel package parity, structured diagnostics, and immutable CI dependencies.

**Architecture:** A standard-library Python runner owns all verification orchestration and evidence generation. GitHub Actions becomes a thin, least-privilege adapter that installs a hash-locked CI toolchain, invokes the runner, publishes its summary, and uploads diagnostics under all outcomes.

**Tech Stack:** Python 3.10–3.13 standard library, `unittest`, GitHub Actions, pip/setuptools/wheel.

## Global Constraints

- No runtime package dependencies.
- No live provider calls.
- No changes to package behaviour, deployment, privacy state, public claims, or NASA production.
- External GitHub Actions must be pinned to full-length 40-character commit SHAs.
- CI packaging tools must use exact versions and SHA-256 hashes.
- The workflow token must remain `contents: read` only.
- Every reliability control must be covered by repository tests.

---

### Task 1: Lock the design and implementation contract

**Files:**
- Create: `docs/superpowers/specs/2026-08-06-reliability-gate-v2-design.md`
- Create: `docs/superpowers/plans/2026-08-06-reliability-gate-v2.md`

**Interfaces:**
- Consumes: current fifteen-pass workflow and repository verification commands.
- Produces: exact evidence schema, failure taxonomy, scope boundary, and acceptance criteria.

- [x] **Step 1: Document current gaps and the target architecture.**
- [x] **Step 2: Define evidence files, verification phases, canonical comparison, and failure classes.**
- [x] **Step 3: Define testable acceptance criteria and non-goals.**
- [x] **Step 4: Commit the design and plan.**

### Task 2: Add red contract tests

**Files:**
- Create: `tests/test_reliability_gate.py`
- Modify: `tests/test_fifteen_pass_workflow_resilience.py`

**Interfaces:**
- Consumes: future module loaded from `scripts/ci/reliability_gate.py`.
- Produces: tests for `canonical_digest`, `tree_manifest`, `build_pass_environment`, `compare_manifest`, `FailureRecord`, and workflow hardening.

- [ ] **Step 1: Write tests that require the runner file and public helpers.**
- [ ] **Step 2: Test equivalent JSON formatting produces one digest and semantic drift produces different digests.**
- [ ] **Step 3: Test tree manifests normalize ordering and detect changed content.**
- [ ] **Step 4: Test deterministic pass environments isolate `HOME`, temp, cache, hash seed, locale, timezone, and source epoch.**
- [ ] **Step 5: Test failure records serialize exact phase, command, pass, seed, exit code, duration, and log path.**
- [ ] **Step 6: Extend workflow tests to require the runner, SHA-pinned actions, hash-locked CI tools, expanded path triggers, 15 passes, and always-uploaded diagnostics.**
- [ ] **Step 7: Push the tests and verify they fail for the intended missing v2 controls.**

### Task 3: Add the hash-locked CI toolchain

**Files:**
- Create: `requirements/ci-tools.txt`

**Interfaces:**
- Consumes: PyPI wheel releases for pip, setuptools, and wheel.
- Produces: a `pip --require-hashes` compatible CI bootstrap lock.

- [ ] **Step 1: Add exact versions for pip 26.2.1, setuptools 83.0.0, and wheel 0.47.0.**
- [ ] **Step 2: Add the SHA-256 digest for each universal wheel.**
- [ ] **Step 3: Ensure no ranges, editable requirements, indexes, or transitive dependencies are present.**
- [ ] **Step 4: Add tests that reject unpinned or unhashed CI tool entries.**

### Task 4: Implement evidence and comparison primitives

**Files:**
- Create: `scripts/ci/reliability_gate.py`
- Test: `tests/test_reliability_gate.py`

**Interfaces:**
- Produces:
  - `canonical_digest(path: Path) -> dict[str, object]`
  - `tree_manifest(root: Path) -> dict[str, dict[str, object]]`
  - `compare_manifest(expected, actual, *, label: str) -> None`
  - `build_pass_environment(base, *, pass_number, pass_root) -> dict[str, str]`
  - `FailureRecord.to_dict() -> dict[str, object]`

- [ ] **Step 1: Implement canonical JSON and raw-byte digests using SHA-256.**
- [ ] **Step 2: Implement stable relative-path tree manifests.**
- [ ] **Step 3: Implement manifest comparison with explicit missing, unexpected, and changed entries.**
- [ ] **Step 4: Implement deterministic, pass-isolated environments.**
- [ ] **Step 5: Implement sorted, atomic JSON writes and append-only JSONL events.**
- [ ] **Step 6: Run focused unit tests and make them pass.**

### Task 5: Implement command execution and failure evidence

**Files:**
- Modify: `scripts/ci/reliability_gate.py`
- Test: `tests/test_reliability_gate.py`

**Interfaces:**
- Produces:
  - `CommandSpec`
  - `CommandResult`
  - `run_command(spec, context) -> CommandResult`
  - exact command logs and start/finish events.

- [ ] **Step 1: Execute argv lists without a shell and capture stdout/stderr separately.**
- [ ] **Step 2: Write one log per command with metadata and output sections.**
- [ ] **Step 3: Emit command-started and command-finished JSONL events.**
- [ ] **Step 4: Raise a typed gate failure on non-zero exit, timeout, missing output, or malformed JSON.**
- [ ] **Step 5: Serialize `failure.json` before returning a non-zero gate exit.**
- [ ] **Step 6: Test success, non-zero exit, malformed JSON, and failure serialization with harmless subprocesses.**

### Task 6: Implement one complete pass

**Files:**
- Modify: `scripts/ci/reliability_gate.py`

**Interfaces:**
- Consumes: repository scripts, fixture config, editable entry points, built wheel entry points.
- Produces: `passes/NN/pass.json`, command logs, output JSON, artifact manifests, and a pass digest set.

- [ ] **Step 1: Compile source and run all tests against the editable installation.**
- [ ] **Step 2: Run all seven repository verification scripts.**
- [ ] **Step 3: Execute and capture all fixture-safe editable CLI surfaces.**
- [ ] **Step 4: Build a wheel, record its SHA-256 digest, create a fresh virtual environment, and install only that wheel.**
- [ ] **Step 5: Run the full tests and repository verifiers with the wheel interpreter.**
- [ ] **Step 6: Execute and capture the equivalent wheel CLI surfaces.**
- [ ] **Step 7: Run editable and wheel `pip check`.**
- [ ] **Step 8: Compare editable/wheel JSON outputs and generated artifact trees.**
- [ ] **Step 9: Remove the disposable virtual environment after evidence is written.**

### Task 7: Implement cross-pass determinism and final summaries

**Files:**
- Modify: `scripts/ci/reliability_gate.py`

**Interfaces:**
- Consumes: pass digest sets.
- Produces: `run.json`, `environment.json`, `events.jsonl`, `summary.json`, and `summary.md`.

- [ ] **Step 1: Store pass one as the baseline digest set.**
- [ ] **Step 2: Compare passes 2–15 to the baseline and fail on any drift.**
- [ ] **Step 3: Aggregate command counts, durations, wheel digests, parity status, and determinism status.**
- [ ] **Step 4: Generate a concise Markdown summary suitable for `$GITHUB_STEP_SUMMARY`.**
- [ ] **Step 5: Return zero only when every requested pass completed, package parity held, and all digests matched the baseline.**

### Task 8: Replace the workflow shell loop with the adapter

**Files:**
- Modify: `.github/workflows/fifteen-pass-verification.yml`
- Modify: `tests/test_fifteen_pass_workflow_resilience.py`

**Interfaces:**
- Consumes: `requirements/ci-tools.txt`, `scripts/ci/reliability_gate.py`.
- Produces: two matrix jobs invoking the same gate on Python 3.10 and 3.13.

- [ ] **Step 1: Pin checkout to `3d3c42e5aac5ba805825da76410c181273ba90b1`.**
- [ ] **Step 2: Pin setup-python to `5fda3b95a4ea91299a34e894583c3862153e4b97`.**
- [ ] **Step 3: Pin upload-artifact to `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`.**
- [ ] **Step 4: Install CI tools with `python -m pip install --require-hashes -r requirements/ci-tools.txt`.**
- [ ] **Step 5: Install the package editable with build isolation disabled after the locked toolchain is present.**
- [ ] **Step 6: Invoke the gate with 15 passes and explicit workspace, work, diagnostics, and Python-label arguments.**
- [ ] **Step 7: Append `summary.md` to `$GITHUB_STEP_SUMMARY` under `if: always()`.**
- [ ] **Step 8: Upload diagnostics under `if: always()` with collision-safe naming and 30-day retention.**
- [ ] **Step 9: Expand path filters to include the runner, lock, tests, workflow, and all reliability surfaces.**

### Task 9: Verify, diagnose, and refine

**Files:**
- Modify only files required by evidence from CI.

**Interfaces:**
- Consumes: PR checks, workflow logs, and uploaded diagnostics.
- Produces: a green, evidence-backed v2 gate.

- [ ] **Step 1: Run the standard Python 3.10–3.13 matrix.**
- [ ] **Step 2: Run the full gate 15/15 on Python 3.10 and 3.13.**
- [ ] **Step 3: Inspect any parity or determinism drift and normalize only proven volatile fields; never suppress unexplained drift.**
- [ ] **Step 4: Verify CodeQL, history protection, privacy packaging, repository health, and existing release checks remain green.**
- [ ] **Step 5: Confirm both diagnostics artifacts contain the required JSON, JSONL, Markdown, pass, command, output, and manifest evidence.**
- [ ] **Step 6: Review the final diff for scope leakage and accidental personal data.**
- [ ] **Step 7: Merge only after all required checks and the full stress gate are green.**
