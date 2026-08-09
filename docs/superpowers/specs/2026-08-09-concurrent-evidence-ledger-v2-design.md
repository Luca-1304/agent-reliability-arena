# Concurrent Evidence Ledger v2 — Design

Date: 2026-08-09
Status: approved for implementation
Scope: provider-free transport evidence only
Platforms: Windows and Linux from first release

## Purpose

Remove the current single-writer sequencing race in `RecordingTransport` so multiple threads and multiple spawned processes can record to one private transport ledger without duplicate sequence numbers, partial interleaving, or silent recovery from corrupted evidence.

The provider/model call itself remains concurrent. Only the short evidence-commit section is serialized.

## Existing failure mode

`RecordingTransport` currently computes `_next_sequence` when each recorder is constructed. Two recorders created before either writes can therefore both select the same next sequence and append valid-looking records with duplicate sequence values.

The current append path is durable (`O_APPEND`, flush, `fsync`) but append durability alone does not make sequence allocation concurrent-safe.

## Non-goals

- Do not change the ledger record schema from `"1"`.
- Do not add a hash-chain or `previous_record_digest` field in this change.
- Do not add provider calls, network calls, publication authority, Git mutation authority, or external services.
- Do not silently truncate, repair, or rewrite malformed evidence.
- Do not make distributed/multi-host filesystem guarantees beyond one shared local filesystem supported by the host OS.

A cryptographically chained schema may be designed separately after concurrency correctness is proven.

## Core commit protocol

For every result or structured transport error:

1. complete the wrapped provider/model call without holding the ledger lock;
2. acquire an in-process lock keyed by the ledger lock path;
3. acquire an OS-level exclusive file lock on a persistent sibling lock file `<ledger>.lock`;
4. validate the ledger path and lock path;
5. if the ledger exists and is non-empty, verify the complete ledger while still holding the lock;
6. derive `sequence = verified_record_count + 1`;
7. construct and sign the new schema-1 record;
8. append the encoded record;
9. flush to the OS and `fsync` the ledger file;
10. release the OS lock and then the in-process lock.

Ledger sequence therefore means **durable evidence commit order**, not provider-call start order.

## Lock implementation

Use Python standard library only.

### In-process lock

A process-local registry maps normalized absolute lock paths to `threading.Lock` instances. This prevents same-process threads from depending on platform-specific file-lock semantics.

### Linux/POSIX lock

Use `fcntl.flock(fd, LOCK_EX | LOCK_NB)` in a bounded retry loop.

### Windows lock

Use `msvcrt.locking(fd, LK_NBLCK, 1)` in a bounded retry loop. The persistent lock file contains at least one byte so byte-range locking is valid.

### Persistent lock file

The sibling lock file is never deleted as part of normal release. Deleting a lock file can split waiters across different inodes/files and invalidate mutual exclusion. The file contains no evidence or secret material.

The lock path must not be a symlink and, when present, must be a regular file. Use `O_NOFOLLOW` where the OS exposes it and validate the opened descriptor with `fstat`.

## Timeout and failure policy

`RecordingTransport` accepts a positive finite `lock_timeout_seconds` keyword with a conservative default. `verify_transport_ledger` accepts the same optional timeout.

If the in-process or OS lock cannot be acquired before the deadline, raise `TimeoutError` and leave the ledger unchanged.

If evidence is malformed, blank, tampered, non-UTF-8, semantically inconsistent, or has a broken sequence, fail closed. Never append past invalid evidence.

If a process crashes while holding the OS lock, the OS releases the lock when the descriptor/process dies. If the crash leaves a partial record, future verification and future writers must reject that malformed tail. No automatic truncation is permitted.

## Verification consistency

Public `verify_transport_ledger` acquires the same ledger lock before reading. A verifier therefore sees a stable snapshot before or after a committed record, never an intentionally in-progress write from a cooperating `RecordingTransport` writer.

An internal unlocked verifier is used only when the caller already holds the ledger lock.

## Backward compatibility

- Existing schema-1 ledgers remain readable and writable.
- Existing `RecordingTransport(transport, ledger_path, clock=...)` callers continue to work unchanged.
- Existing record fields and digest calculation stay unchanged.
- Existing return/error behavior stays unchanged except that a ledger-lock timeout or invalid concurrent evidence can now block the evidence commit explicitly.

## Test contract

The implementation is not complete until all of the following are proven:

1. multiple `RecordingTransport` instances created before any write can write concurrently from threads;
2. spawned processes can write concurrently to the same ledger;
3. mixed successful results and `TransportError` records remain valid under concurrency;
4. final sequences are exactly `1..N` with no duplicates or gaps caused by writer races;
5. every submitted request appears exactly once;
6. `verify_transport_ledger` validates the final ledger;
7. a verifier blocks behind a held writer lock rather than reading an in-progress state;
8. lock timeout raises and leaves ledger bytes unchanged;
9. a malformed tail prevents later writers from appending;
10. a reopened recorder after a concurrent run continues at `N+1`;
11. an unsafe lock-file symlink is rejected;
12. existing schema-1 ledger tests stay green;
13. focused concurrency tests pass on `ubuntu-latest` and `windows-latest` for Python 3.10 and 3.13;
14. the full repository PR matrix completes with zero genuine failures before merge.

All multiprocessing tests use the `spawn` start method on every OS so Linux does not accidentally pass via fork-only behavior.

## CI integration

Add one focused read-only workflow for concurrent-ledger tests:

- `ubuntu-latest`: Python 3.10 and 3.13
- `windows-latest`: Python 3.10 and 3.13

The workflow uses only already-approved pinned `actions/checkout` and `actions/setup-python`, sets `PYTHONPATH=src`, and runs the transport-ledger test subset without provider calls.

Register the new workflow in `git-operations-policy.json` with no write-capable jobs. The existing full Ubuntu Python 3.10–3.13 test workflow remains unchanged and will also discover the new tests.

## Acceptance rule

The feature branch may open a PR only when the implementation is expected green. Merge only the exact verified PR head after all required workflow families have completed with zero genuine failed or cancelled jobs. Intentional failure-only or publication-authority skips are not failures.
