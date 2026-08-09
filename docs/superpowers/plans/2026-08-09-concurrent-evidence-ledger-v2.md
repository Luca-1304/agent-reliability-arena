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

- [x] **Step 1: Add a thread race test**

Create multiple recorder objects before any write, synchronize their `complete()` calls with a `threading.Barrier`, then assert final sequences equal `list(range(1, N + 1))` and all call IDs appear exactly once.

- [x] **Step 2: Establish the RED behavior before implementation**

The existing design caches `_next_sequence` in each recorder, so multiple recorders created before any write can claim the same sequence. RED evidence stays on the feature branch; no RED PR is opened.

- [x] **Step 3: Add spawned-process and malformed-tail contract tests**

Use `multiprocessing.get_context("spawn")`. Child workers construct their recorder, write per-process readiness markers, wait for one shared filesystem start marker, then write one unique request. Add a second test where a recorder is constructed, a partial JSON tail is injected, and `complete()` must refuse to append beyond the invalid evidence.

- [x] **Step 4: Keep process coordination outside the mechanism under test**

Use temporary filesystem marker files rather than multiprocessing Queue/Event/Barrier objects so the cross-process ledger proof is not confounded by unrelated IPC cleanup/synchronization behavior.

---

### Task 2: Add a cross-platform exclusive ledger lock

**Files:**
- Create: `src/agent_reliability_arena/transports/_ledger_lock.py`
- Test: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- Produces: `_exclusive_ledger_lock(ledger_path: Path, *, timeout_seconds: float) -> context manager` and `validate_ledger_lock_path(ledger_path: Path) -> Path`.

- [x] **Step 1: Add focused tests for timeout and unsafe lock path**

Hold the lock from another spawned process, assert a short-timeout public verifier raises `TimeoutError`, and assert ledger bytes are unchanged. Create `<ledger>.lock` as a symlink where supported and require constructor/lock validation to reject it.

- [x] **Step 2: Implement the in-process lock registry**

Normalize the absolute sibling lock path with `os.path.abspath` and `os.path.normcase`; guard a map of `threading.Lock` objects with one registry lock.

- [x] **Step 3: Implement POSIX locking**

Open the persistent lock file read/write/create with mode `0o600`, include `O_NOFOLLOW` and `O_CLOEXEC` when available, verify `fstat` and current path are regular and consistent, and retry `fcntl.flock(fd, LOCK_EX | LOCK_NB)` until the shared deadline.

- [x] **Step 4: Implement Windows locking**

Open the persistent lock file in binary-capable read/write/create mode, seek to offset zero, and retry `msvcrt.locking(fd, LK_NBLCK, 1)` until the shared deadline. Python documents that the locked region may extend beyond EOF, so the lock file can remain empty and no byte-initialization protocol is needed. Unlock the same range on exit.

- [x] **Step 5: Keep the lock file persistent and evidence-free**

Close descriptors but never delete `<ledger>.lock` during normal release. Test that the sidecar contains zero evidence bytes.

---

### Task 3: Make verification and evidence commit transactional

**Files:**
- Modify: `src/agent_reliability_arena/transports/recording.py`
- Test: `tests/test_transport_ledger.py`
- Test: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- `verify_transport_ledger(path: Path, *, lock_timeout_seconds: float = 30.0) -> dict[str, object]`
- `RecordingTransport(..., lock_timeout_seconds: float = 30.0)`
- Private `_verify_transport_ledger_unlocked(path: Path) -> dict[str, object]` is used only when the transaction lock is already held or by the public locked wrapper.

- [x] **Step 1: Validate timeout values and stable verifier snapshots**

Reject bool, non-numeric, non-finite and non-positive timeouts. Hold the ledger lock and start verification in another thread; require verification to wait until the lock is released.

- [x] **Step 2: Split locked and unlocked verification**

Move parsing/digest/semantic verification into `_verify_transport_ledger_unlocked`; make public verification acquire `_exclusive_ledger_lock` and then call the unlocked verifier.

- [x] **Step 3: Remove cached sequence authority**

Do not use `_next_sequence` as a source of truth. Preserve constructor validation of an existing non-empty ledger, but derive sequence again at commit time while holding the lock.

- [x] **Step 4: Implement `_commit_record`**

Inside the exclusive lock, revalidate paths, fully verify an existing non-empty ledger, derive `sequence = records + 1`, construct the record with that sequence, compute `record_digest`, encode one canonical JSON line, append, flush and `fsync` before releasing.

- [x] **Step 5: Keep provider calls outside the lock**

`complete()` calls the wrapped transport first. Only recording the returned result or structured `TransportError` enters `_commit_record`. A barrier inside the fixture provider proves provider calls can overlap before commits serialize.

---

### Task 4: Prove thread/process result and error correctness

**Files:**
- Modify: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- Consumes the transactional writer from Task 3.

- [x] **Step 1: Add mixed outcome concurrency**

Run successful and `TransportError` recorders concurrently. Catch expected transport errors in workers, then assert the verified summary has exact result/error counts and every request appears once.

- [x] **Step 2: Add reopen continuation**

After an `N`-writer concurrent run, create a fresh recorder and write one more request; require exact sequences `1..N+1`.

- [x] **Step 3: Prove deterministic verifier blocking and provider parallelism**

Hold the transaction lock while a public verifier runs in another thread and require it not to finish until release. Separately put a barrier inside multiple fixture provider calls to prove model/provider work overlaps while only evidence commits serialize.

- [x] **Step 4: Repeat spawned-process probes before PR**

Exercise repeated six-process `spawn` runs with exact sequence/exit-code checks. Investigate any timing stop instead of dismissing it; filesystem-marker coordination is retained to reduce unrelated IPC noise.

---

### Task 5: Add focused Windows/Linux CI without widening authority

**Files:**
- Create: `.github/workflows/concurrent-ledger.yml`
- Modify: `git-operations-policy.json`
- Test through existing policy verifier and full PR CI.

**Interfaces:**
- Workflow matrix: `ubuntu-latest`, `windows-latest` × Python `3.10`, `3.13`.
- Permissions: top-level `contents: read`; no write jobs.

- [x] **Step 1: Add workflow**

Use pinned `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with `persist-credentials: false` and pinned `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97`. Set `PYTHONPATH: src`. Compile the ledger implementation/tests, then run `python -m unittest discover -s tests -p "test_transport_ledger*.py" -v`.

- [x] **Step 2: Register workflow in Git-operations policy**

Add `"concurrent-ledger.yml": {"write_jobs": {}}` and no new write authority.

- [ ] **Step 3: Prove policy and platform behavior in the real repository**

The pre-PR gate / PR matrix must validate the workflow policy. The dedicated PR workflow must finish green on all four Windows/Linux × Python 3.10/3.13 cells before merge.

---

### Task 6: Pre-PR and full repository verification

**Files:**
- Modify documentation only if the verified behavior merits a concise status note.

- [ ] **Step 1: Run/approximate the pre-PR green gate to the maximum available environment**

Canonical command in a full checkout: `python scripts/ci/pre_pr_green_gate.py --root . --output <report-path>` and require `pre_pr_failures == 0`. Where a full checkout cannot be materialized, use exact focused executable fixtures plus static repository-policy inspection and treat the GitHub PR matrix as the repository-level proof rather than inventing a local pass.

- [ ] **Step 2: Review feature diff for scope and authority**

Confirm no provider code, publication workflow, release authority, Git mutation capability, dependency or ledger record schema changed.

- [ ] **Step 3: Open one implementation PR only after the candidate is expected green**

No intentional RED PR run.

- [ ] **Step 4: Require the focused Windows/Linux matrix and all existing PR workflow families to finish successfully**

Intentional publication/failure-only skips remain acceptable; any genuine failed/cancelled required job blocks merge.

- [ ] **Step 5: Merge exact verified head**

Use the repository's established squash-merge path with exact-head protection. Verify `main` points to the merge result afterward without inventing unavailable push-run evidence.
