# Tamper-Evident Transport Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every model transport result or structured failure in an append-only, independently verifiable JSONL ledger.

**Architecture:** Add a provider-neutral `RecordingTransport` decorator and a read-only `verify_transport_ledger()` function in one focused module. Each line contains a canonical request, exactly one result or error, a contiguous sequence and a SHA-256 digest over the record; the verifier checks all cross-field invariants and exact ledger bytes.

**Tech Stack:** Python 3.10–3.13 standard library, `dataclasses`, `pathlib`, canonical JSON, SHA-256, `unittest`, GitHub Actions.

## Global Constraints

- No external dependency or live API request.
- One writer per ledger; concurrent writers remain unsupported.
- Existing non-empty ledgers must verify before append.
- Symlink and non-regular ledger paths must fail closed.
- Only `TransportError` failures are persisted and re-raised.
- Raw API keys and raw response bytes are never written.
- Full source, release, CLI, wheel and clean-wheel verification must pass on Python 3.10–3.13.

---

### Task 1: Define result and error recording behaviour

**Files:**
- Create: `tests/test_transport_ledger.py`
- Create: `src/agent_reliability_arena/transports/recording.py`

**Interfaces:**
- Consumes: `ModelTransport.complete(request) -> ModelCallResult`, `TransportError.to_dict()`, `canonical_json_sha256(payload)`.
- Produces: `RecordingTransport(transport: ModelTransport, ledger_path: Path, clock: Callable[[], datetime] | None = None)`.

- [ ] **Step 1: Write failing success-record test**

```python
class StaticTransport:
    provider = "fixture-provider"

    def __init__(self, result):
        self.result = result
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return self.result


def test_records_success_and_returns_original_result(self):
    with tempfile.TemporaryDirectory() as directory:
        ledger = Path(directory) / "calls.jsonl"
        model_request = make_request()
        expected = make_result(model_request)
        wrapped = StaticTransport(expected)
        recorder = RecordingTransport(
            wrapped,
            ledger,
            clock=lambda: datetime(2026, 7, 22, tzinfo=timezone.utc),
        )

        actual = recorder.complete(model_request)

        self.assertIs(actual, expected)
        self.assertEqual(wrapped.calls, 1)
        row = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual(row["sequence"], 1)
        self.assertEqual(row["outcome_type"], "result")
        self.assertEqual(row["request_digest"], model_request.digest)
        self.assertEqual(row["result"], expected.to_dict())
        self.assertIsNone(row["error"])
```

- [ ] **Step 2: Run focused test and verify RED**

Run:

```bash
python -m unittest tests.test_transport_ledger.TransportLedgerTests.test_records_success_and_returns_original_result -v
```

Expected: import failure because `RecordingTransport` does not exist.

- [ ] **Step 3: Implement minimal canonical append path**

Create `recording.py` with:

```python
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .base import ModelCallRequest, ModelCallResult, ModelTransport, TransportError, canonical_json_sha256

SCHEMA_VERSION = "1"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Ledger clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class RecordingTransport:
    provider: str

    def __init__(self, transport: ModelTransport, ledger_path: Path, clock: Callable[[], datetime] = _utc_now) -> None:
        if not isinstance(transport, ModelTransport):
            raise ValueError("'transport' must implement ModelTransport.")
        self.transport = transport
        self.provider = transport.provider
        self.ledger_path = Path(ledger_path)
        self.clock = clock
        self._next_sequence = 1

    def _append(self, payload: dict[str, object]) -> None:
        payload["record_digest"] = canonical_json_sha256(payload)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        with self.ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        result = self.transport.complete(request)
        self._append({
            "schema_version": SCHEMA_VERSION,
            "sequence": self._next_sequence,
            "recorded_at": _timestamp(self.clock()),
            "provider": self.provider,
            "request": request.to_dict(),
            "request_digest": request.digest,
            "outcome_type": "result",
            "result": result.to_dict(),
            "error": None,
        })
        self._next_sequence += 1
        return result
```

- [ ] **Step 4: Run focused test and verify GREEN**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Write failing structured-error test**

```python
def test_records_transport_error_and_reraises_same_error(self):
    error = TransportError("rate limited", category="http_error", retryable=True, status_code=429)
    wrapped = ErrorTransport(error)
    recorder = RecordingTransport(wrapped, ledger, clock=fixed_clock)

    with self.assertRaises(TransportError) as raised:
        recorder.complete(model_request)

    self.assertIs(raised.exception, error)
    row = json.loads(ledger.read_text(encoding="utf-8"))
    self.assertEqual(row["outcome_type"], "error")
    self.assertEqual(row["error"], error.to_dict())
    self.assertIsNone(row["result"])
```

- [ ] **Step 6: Run error test and verify RED**

Expected: no ledger file because the error path is not implemented.

- [ ] **Step 7: Implement error record and re-raise**

Wrap the provider call:

```python
try:
    result = self.transport.complete(request)
except TransportError as error:
    self._append(self._record(request, outcome_type="error", result=None, error=error.to_dict()))
    self._next_sequence += 1
    raise
```

- [ ] **Step 8: Run both focused tests and verify GREEN**

```bash
python -m unittest tests.test_transport_ledger -v
```

Expected: both tests pass.

- [ ] **Step 9: Commit**

```bash
git add tests/test_transport_ledger.py src/agent_reliability_arena/transports/recording.py
git commit -m "Add transport call recording"
```

---

### Task 2: Verify existing ledgers before replay or append

**Files:**
- Modify: `tests/test_transport_ledger.py`
- Modify: `src/agent_reliability_arena/transports/recording.py`

**Interfaces:**
- Produces: `verify_transport_ledger(path: Path) -> dict[str, object]`.

- [ ] **Step 1: Write failing verification and continuation tests**

```python
def test_verifies_ledger_and_continues_sequence_after_reopen(self):
    first = RecordingTransport(StaticTransport(result1), ledger, clock=first_clock)
    first.complete(request1)

    summary = verify_transport_ledger(ledger)
    self.assertEqual(summary["records"], 1)
    self.assertEqual(summary["results"], 1)
    self.assertEqual(summary["errors"], 0)
    self.assertEqual(summary["ledger_sha256"], hashlib.sha256(ledger.read_bytes()).hexdigest())

    second = RecordingTransport(StaticTransport(result2), ledger, clock=second_clock)
    second.complete(request2)
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    self.assertEqual([row["sequence"] for row in rows], [1, 2])
```

- [ ] **Step 2: Run test and verify RED**

Expected: `verify_transport_ledger` is missing and reopened recorder starts again at sequence 1.

- [ ] **Step 3: Implement read-only verifier**

For every non-empty line:

```python
expected_digest = row.pop("record_digest")
if canonical_json_sha256(row) != expected_digest:
    raise ValueError(f"Ledger record {line_number} digest mismatch.")
if row["sequence"] != line_number:
    raise ValueError(f"Ledger sequence mismatch at line {line_number}.")
if canonical_json_sha256(row["request"]) != row["request_digest"]:
    raise ValueError(f"Ledger request digest mismatch at line {line_number}.")
```

Validate result/error exclusivity and result cross-fields. Return exact byte digest and counts.

- [ ] **Step 4: Verify existing ledger during recorder construction**

If the ledger exists and is non-empty:

```python
summary = verify_transport_ledger(self.ledger_path)
self._next_sequence = int(summary["records"]) + 1
```

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
python -m unittest tests.test_transport_ledger -v
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_transport_ledger.py src/agent_reliability_arena/transports/recording.py
git commit -m "Verify and resume transport ledgers"
```

---

### Task 3: Fail closed on tampering and unsafe paths

**Files:**
- Modify: `tests/test_transport_ledger.py`
- Modify: `src/agent_reliability_arena/transports/recording.py`

**Interfaces:**
- Preserves: `RecordingTransport`, `verify_transport_ledger`.

- [ ] **Step 1: Write failing tamper tests**

Cover changed request text, changed result call ID, changed sequence, changed digest, blank line and malformed JSON. Each must raise `ValueError` containing the failing line number.

- [ ] **Step 2: Write failing path tests**

```python
def test_rejects_missing_parent_and_symlink_ledger(self):
    with self.assertRaisesRegex(ValueError, "parent"):
        RecordingTransport(transport, root / "missing" / "calls.jsonl")
    target = root / "target.jsonl"
    target.write_text("", encoding="utf-8")
    link = root / "link.jsonl"
    link.symlink_to(target)
    with self.assertRaisesRegex(ValueError, "symlink"):
        RecordingTransport(transport, link)
```

Skip the symlink assertion only when the platform refuses symlink creation.

- [ ] **Step 3: Run tests and verify RED**

```bash
python -m unittest tests.test_transport_ledger -v
```

- [ ] **Step 4: Implement path and schema checks**

Reject missing parents, non-directory parents, symlinks, non-regular existing files, blank lines, invalid UTF-8/JSON, unsupported schema versions, non-contiguous sequences, mismatched digests and invalid outcome shapes.

- [ ] **Step 5: Run transport-ledger and full source tests**

```bash
python -m unittest tests.test_transport_ledger -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: zero failures.

- [ ] **Step 6: Commit**

```bash
git add tests/test_transport_ledger.py src/agent_reliability_arena/transports/recording.py
git commit -m "Harden transport ledger verification"
```

---

### Task 4: Export, document and run release gates

**Files:**
- Modify: `src/agent_reliability_arena/transports/__init__.py`
- Modify: `docs/LIVE_MODEL_TRANSPORT.md`
- Modify: `scripts/verify_release.py`

**Interfaces:**
- Public exports: `RecordingTransport`, `verify_transport_ledger`.

- [ ] **Step 1: Export ledger API**

```python
from .recording import RecordingTransport, verify_transport_ledger
```

Add both names to `__all__`.

- [ ] **Step 2: Extend release verification**

Require at least the new total test count and execute one temporary success ledger plus `verify_transport_ledger()` without network access.

- [ ] **Step 3: Document privacy and concurrency boundaries**

State that ledgers may contain prompts, are private evidence, reject tampering and support one writer only.

- [ ] **Step 4: Run complete local gates**

```bash
python -m compileall -q src tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verify_release.py
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
python -m pip check
```

Expected: all commands exit `0`.

- [ ] **Step 5: Open draft PR and verify GitHub matrix**

GitHub Actions must pass source compilation, all tests, release verification, installed commands, wheel build, clean-wheel tests and dependency checks on Python 3.10, 3.11, 3.12 and 3.13.

- [ ] **Step 6: Commit**

```bash
git add src/agent_reliability_arena/transports/__init__.py docs/LIVE_MODEL_TRANSPORT.md scripts/verify_release.py
git commit -m "Document and verify transport ledger"
```
