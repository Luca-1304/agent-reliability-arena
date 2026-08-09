# Concurrent Evidence Ledger v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make schema-1 private transport evidence safe for concurrent threads and spawned processes on Windows and Linux while keeping provider calls parallel and preserving fail-closed verification.

**Architecture:** Add one internal cross-platform ledger-lock module and refactor `RecordingTransport` so sequence allocation plus durable append occur inside one transaction lock. Public verification uses the same lock for stable snapshots. A focused read-only GitHub workflow proves the transport ledger on Windows and Linux while the existing full matrix remains authoritative for the repository.

**Tech Stack:** Python 3.10–3.13 standard library (`threading`, `fcntl`, `msvcrt`, `os`, `time`, `multiprocessing`), `unittest`, GitHub Actions.

## Global Constraints

- Windows and Linux are supported from the first release.
- Runtime dependencies remain empty.
- Ledger schema remains `"1"`; no hash-chain migration in this change.
- Provider/model calls happen outside the ledger lock.
- Only sequence allocation, signing and durable append are serialized.
- Lock acquisition is bounded and fails closed with `TimeoutError`.
- Malformed evidence is never automatically truncated, repaired or written past.
- Existing schema-1 ledgers and existing `RecordingTransport` call sites remain compatible.
- No provider calls, publication authority, Git mutation authority or external service is added.
- Multiprocessing tests use `spawn` on every platform.
- Merge requires the exact PR head to complete all required workflows with zero genuine failures/cancellations.

---

### Task 1: Prove the cached-sequence race and concurrent contract

**Files:**
- Create: `tests/test_transport_ledger_concurrency.py`
- Existing behavior under test: `src/agent_reliability_arena/transports/recording.py`

**Interfaces:**
- Consumes: `RecordingTransport`, `ModelCallRequest`, `ModelCallResult`, `ModelUsage`, `TransportError`, `verify_transport_ledger`.
- Produces: failing tests that require concurrent-safe sequence allocation and fail-closed commits.

- [ ] **Step 1: Add a thread race test**

Create multiple recorder objects before any write, synchronize their `complete()` calls with a `threading.Barrier`, then assert final sequences equal `list(range(1, N + 1))` and all call IDs appear exactly once.

- [ ] **Step 2: Run the focused test against the current implementation**

Run: `PYTHONPATH=src python -m unittest discover -s tests -p "test_transport_ledger_concurrency.py" -v`

Expected: FAIL because current recorders cache the same `_next_sequence` before concurrent writes.

- [ ] **Step 3: Add spawned-process and malformed-tail RED tests**

Use `multiprocessing.get_context("spawn")`. Child workers construct their recorder, report readiness, wait on a shared start event, then write one unique request. Add a second test where a recorder is constructed, a partial JSON tail is injected, and `complete()` must refuse to append beyond the invalid evidence.

- [ ] **Step 4: Re-run to confirm the failures are caused by missing concurrency protection**

Expected: at least the concurrent sequence assertion and/or final ledger verification fails for the current implementation; malformed-tail writer must demonstrate the current write-past-invalid behavior for a recorder constructed before corruption.

- [ ] **Step 5: Commit the RED evidence on the feature branch only**

No PR is opened at this stage.

---

### Task 2: Add a cross-platform exclusive ledger lock

**Files:**
- Create: `src/agent_reliability_arena/transports/_ledger_lock.py`
- Test: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- Produces: `_exclusive_ledger_lock(ledger_path: Path, *, timeout_seconds: float) -> context manager` and `validate_ledger_lock_path(ledger_path: Path) -> None`.

- [ ] **Step 1: Add focused tests for timeout and unsafe lock path**

Hold the lock from another spawned process, assert a short-timeout public verifier raises `TimeoutError`, and assert ledger bytes are unchanged. Create `<ledger>.lock` as a symlink where supported and require constructor/lock validation to reject it.

- [ ] **Step 2: Implement the in-process lock registry**

Normalize the absolute sibling lock path with `os.path.abspath` and `os.path.normcase`; guard a map of `threading.Lock` objects with one registry lock.

- [ ] **Step 3: Implement POSIX locking**

Open the persistent lock file read/write/create with mode `0o600`, include `O_NOFOLLOW` and `O_CLOEXEC` when available, verify `fstat` is a regular file, and retry `fcntl.flock(fd, LOCK_EX | LOCK_NB)` until the shared deadline.

- [ ] **Step 4: Implement Windows locking**

Open the lock file in binary read/write mode, ensure it contains at least one byte, seek to byte zero, and retry `msvcrt.locking(fd, LK_NBLCK, 1)` until the shared deadline. Unlock the same byte on exit.

- [ ] **Step 5: Keep the lock file persistent**

Close descriptors but never delete `<ledger>.lock` during normal release.

- [ ] **Step 6: Run the lock-focused tests**

Expected: PASS for lock timeout/path tests on the host OS.

---

### Task 3: Make verification and evidence commit transactional

**Files:**
- Modify: `src/agent_reliability_arena/transports/recording.py`
- Modify if export is useful: `src/agent_reliability_arena/transports/__init__.py`
- Test: `tests/test_transport_ledger.py`
- Test: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- `verify_transport_ledger(path: Path, *, lock_timeout_seconds: float = 30.0) -> dict[str, object]`
- `RecordingTransport(..., lock_timeout_seconds: float = 30.0)`
- Private `_verify_transport_ledger_unlocked(path: Path) -> dict[str, object]` is callable only while the transaction lock is already held or during carefully controlled internal validation.

- [ ] **Step 1: Add validation tests for timeout values and verifier snapshot blocking**

Reject bool, non-numeric, non-finite and non-positive timeouts. Hold the ledger lock and start verification in another thread; assert verification does not finish until the lock is released.

- [ ] **Step 2: Split locked and unlocked verification**

Move current parsing/digest/semantic verification into `_verify_transport_ledger_unlocked`; make public verification acquire `_exclusive_ledger_lock` and then call the unlocked verifier.

- [ ] **Step 3: Remove cached sequence authority**

Stop using `_next_sequence` as the source of truth. Preserve constructor validation of any existing non-empty ledger, but derive the sequence again at commit time while holding the lock.

- [ ] **Step 4: Implement `_commit_record`**

Inside the exclusive lock, revalidate paths, fully verify an existing non-empty ledger, derive `sequence = records + 1`, construct the record with that sequence, compute `record_digest`, encode one canonical JSON line, append, flush and `fsync` before releasing.

- [ ] **Step 5: Keep provider calls outside the lock**

`complete()` calls the wrapped transport first. Only recording the returned result or structured `TransportError` enters `_commit_record`.

- [ ] **Step 6: Run existing plus new ledger tests**

Run: `PYTHONPATH=src python -m unittest discover -s tests -p "test_transport_ledger*.py" -v`

Expected: all PASS.

---

### Task 4: Prove thread/process result and error correctness

**Files:**
- Modify: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- Consumes the transactional writer from Task 3.

- [ ] **Step 1: Add mixed outcome concurrency**

Run successful and `TransportError` recorders concurrently. Catch the expected transport errors in workers, then assert the verified summary has exact result/error counts and every request appears once.

- [ ] **Step 2: Add reopen continuation**

After an `N`-writer concurrent run, create a fresh recorder and write one more request; require exact sequences `1..N+1`.

- [ ] **Step 3: Add verifier/writer stress**

While cooperating writers are active, repeatedly call public verification and accept only valid complete snapshots; after writers join, require the complete final ledger.

- [ ] **Step 4: Run the focused suite repeatedly**

Run the focused ledger suite multiple times locally/where available to expose timing-sensitive races before PR.

---

### Task 5: Add focused Windows/Linux CI without widening authority

**Files:**
- Create: `.github/workflows/concurrent-ledger.yml`
- Modify: `git-operations-policy.json`
- Test through existing policy verifier.

**Interfaces:**
- Workflow matrix: `ubuntu-latest`, `windows-latest` × Python `3.10`, `3.13`.
- Permissions: top-level `contents: read`; no write jobs.

- [ ] **Step 1: Add workflow**

Use pinned `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with `persist-credentials: false` and pinned `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97`. Set `PYTHONPATH: src`. Run `python -m unittest discover -s tests -p "test_transport_ledger*.py" -v`.

- [ ] **Step 2: Register workflow in Git-operations policy**

Add `"concurrent-ledger.yml": {"write_jobs": {}}` and no new write authority.

- [ ] **Step 3: Run policy verification**

Run: `python scripts/ci/verify_git_operations.py --root . --policy git-operations-policy.json`

Expected: PASS.

---

### Task 6: Pre-PR and full repository verification

**Files:**
- Modify documentation only if the verified behavior merits a concise status note.

- [ ] **Step 1: Run the pre-PR green gate**

Run: `python scripts/ci/pre_pr_green_gate.py --root . --output /tmp/pre-pr-green-gate.json`

Expected: exit 0 and `pre_pr_failures == 0`.

- [ ] **Step 2: Review feature diff for scope and authority**

Confirm no provider code, publication workflow, release authority, Git mutation capability, dependency or ledger schema changed.

- [ ] **Step 3: Open one implementation PR only after the candidate is expected green**

No intentional RED PR run.

- [ ] **Step 4: Require the focused Windows/Linux matrix and all existing PR workflow families to finish successfully**

Intentional publication/failure-only skips remain acceptable; any genuine failed/cancelled required job blocks merge.

- [ ] **Step 5: Merge exact verified head**

Use the repository's established squash-merge path with exact-head protection. Verify `main` points to the merge result afterward without inventing unavailable push-run evidence.
