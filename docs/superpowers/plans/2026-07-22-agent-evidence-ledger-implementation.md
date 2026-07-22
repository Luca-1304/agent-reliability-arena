# Agent Evidence Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a standalone, local-first, tamper-evident evidence ledger for one tool-using agent execution, with canonical events, legal lifecycle transitions, crash-resumable sealing, deterministic tamper fixtures, three CLIs and an employer-facing static viewer.

**Architecture:** One ledger directory contains a canonical JSONL event stream, content-addressed artifacts, a final seal and a deterministic manifest. A read-only verifier separately checks canonical bytes, hash chaining, references, lifecycle rules, artifact integrity, closure and optional external checkpoints. Public disclosure is generated into a separate directory and never mutates the source ledger.

**Tech Stack:** Python 3.10–3.13 standard library, `unittest`, `dataclasses`, `argparse`, SHA-256, platform advisory locks (`fcntl`/`msvcrt`), HTML5, CSS and vanilla JavaScript. Build backend: setuptools. No runtime dependency and no network or paid-model call in tests.

## Global Constraints

- One ledger represents one execution trace and one declared completion contract.
- The supported writer is append-only by protocol; filesystem immutability is not claimed.
- Actor identifiers and `independent_observation` are protocol labels, not cryptographic identity or proof of organisational independence.
- Canonical JSON uses NFC-normalised strings, post-normalisation duplicate-key rejection, safe-range integers and exact byte comparison.
- Event lines are limited to 1 MiB, nesting depth to 32 and references to 128.
- Artifacts use `artifacts/<sha256>` with a default 64 MiB limit and no symbolic links.
- `ledger-verify` is read-only and distinguishes open, sealed, expected-root and invalid assurance states.
- Normal disclosure export requires a valid sealed ledger; invalid fixture display requires explicit diagnostic mode with no payload or artifact export.
- Public wording must not claim legal non-repudiation, authenticated identity, trusted time, observation truth, blockchain properties, compliance certification or external-model performance.
- Every milestone ends with source tests, an independently reviewable commit and no hollow version increase.

---

## Milestone 1 — Protocol core

### Task 1: Create the standalone package and typed error model

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_evidence_ledger/__init__.py`
- Create: `src/agent_evidence_ledger/errors.py`
- Create: `src/agent_evidence_ledger/models.py`
- Create: `tests/test_public_api.py`
- Create: `tests/test_errors.py`

**Interfaces:**
- Produces: `Event`, `VerificationProblem`, `VerificationReport`, `AssuranceLevel`, `LedgerError` subclasses.
- Later tasks import these exact names from `agent_evidence_ledger`.

- [ ] **Step 1: Write failing public API tests**

```python
# tests/test_public_api.py
import unittest


class PublicApiTests(unittest.TestCase):
    def test_public_types_import(self) -> None:
        from agent_evidence_ledger import (
            AssuranceLevel,
            Event,
            VerificationProblem,
            VerificationReport,
        )

        self.assertEqual(AssuranceLevel.OPEN_CHAIN_VALID.value, "OPEN_CHAIN_VALID")
        self.assertEqual(Event.__name__, "Event")
        self.assertEqual(VerificationProblem.__name__, "VerificationProblem")
        self.assertEqual(VerificationReport.__name__, "VerificationReport")


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/test_errors.py
import unittest


class ErrorTests(unittest.TestCase):
    def test_error_codes_are_stable(self) -> None:
        from agent_evidence_ledger.errors import ChainIntegrityError

        error = ChainIntegrityError("broken previous hash")
        self.assertEqual(error.code, "CHAIN_INTEGRITY_ERROR")
        self.assertEqual(str(error), "broken previous hash")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm the package is absent**

Run:

```bash
python -m unittest tests.test_public_api tests.test_errors -v
```

Expected: both modules fail with `ModuleNotFoundError: No module named 'agent_evidence_ledger'`.

- [ ] **Step 3: Add package metadata and typed models**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=70", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-evidence-ledger"
version = "0.1.0"
description = "A tamper-evident evidence ledger for tool-using agents"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "Luca Panayiotou"}]
dependencies = []

[project.scripts]
ledger-record = "agent_evidence_ledger.record_cli:main"
ledger-verify = "agent_evidence_ledger.verify_cli:main"
ledger-export = "agent_evidence_ledger.export_cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

```python
# src/agent_evidence_ledger/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssuranceLevel(str, Enum):
    OPEN_CHAIN_VALID = "OPEN_CHAIN_VALID"
    INTERNAL_CHAIN_VALID = "INTERNAL_CHAIN_VALID"
    EXPECTED_ROOT_MATCHED = "EXPECTED_ROOT_MATCHED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class Event:
    schema_version: str
    ledger_id: str
    sequence: int
    event_id: str
    event_type: str
    recorded_at: str
    actor: dict[str, str]
    evidence_class: str
    references: tuple[str, ...]
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


@dataclass(frozen=True)
class VerificationProblem:
    code: str
    message: str
    sequence: int | None = None
    event_id: str | None = None
    expected: str | int | None = None
    actual: str | int | None = None


@dataclass(frozen=True)
class VerificationReport:
    valid: bool
    assurance_level: AssuranceLevel
    ledger_id: str | None
    event_count: int
    final_event_hash: str | None
    problems: tuple[VerificationProblem, ...] = field(default_factory=tuple)
```

```python
# src/agent_evidence_ledger/errors.py
class LedgerError(Exception):
    code = "LEDGER_ERROR"


class CanonicalizationError(LedgerError):
    code = "CANONICALIZATION_ERROR"


class SchemaError(LedgerError):
    code = "SCHEMA_ERROR"


class ChainIntegrityError(LedgerError):
    code = "CHAIN_INTEGRITY_ERROR"


class LifecycleError(LedgerError):
    code = "LIFECYCLE_ERROR"


class ReferenceError(LedgerError):
    code = "REFERENCE_ERROR"


class ArtifactIntegrityError(LedgerError):
    code = "ARTIFACT_INTEGRITY_ERROR"


class SealError(LedgerError):
    code = "SEAL_ERROR"


class ExpectedRootMismatch(LedgerError):
    code = "EXPECTED_ROOT_MISMATCH"


class LockError(LedgerError):
    code = "LOCK_ERROR"


class OperationalError(LedgerError):
    code = "OPERATIONAL_ERROR"
```

```python
# src/agent_evidence_ledger/__init__.py
from .models import AssuranceLevel, Event, VerificationProblem, VerificationReport

__all__ = [
    "AssuranceLevel",
    "Event",
    "VerificationProblem",
    "VerificationReport",
]

__version__ = "0.1.0"
```

- [ ] **Step 4: Run the focused tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_public_api tests.test_errors -v
```

Expected: `Ran 2 tests ... OK`.

- [ ] **Step 5: Commit the package boundary**

```bash
git add pyproject.toml src/agent_evidence_ledger tests/test_public_api.py tests/test_errors.py
git commit -m "feat: establish evidence ledger package boundary"
```

### Task 2: Implement canonical JSON and event hashing

**Files:**
- Create: `src/agent_evidence_ledger/canonical.py`
- Create: `src/agent_evidence_ledger/hashing.py`
- Create: `tests/test_canonical.py`
- Create: `tests/test_hashing.py`

**Interfaces:**
- Produces: `canonicalize(value: object) -> bytes`, `parse_canonical_line(line: bytes) -> dict[str, object]`, `calculate_event_hash(event_without_hash: dict[str, object]) -> str`.
- Consumes: `CanonicalizationError`.

- [ ] **Step 1: Write canonicalisation failures first**

```python
# tests/test_canonical.py
import unittest

from agent_evidence_ledger.canonical import canonicalize, parse_canonical_line
from agent_evidence_ledger.errors import CanonicalizationError


class CanonicalTests(unittest.TestCase):
    def test_sorts_keys_and_normalises_nfc(self) -> None:
        self.assertEqual(canonicalize({"b": 1, "a": "e\u0301"}), b'{"a":"\\u00e9","b":1}')

    def test_rejects_float(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonicalize({"value": 1.5})

    def test_rejects_post_normalisation_duplicate_keys(self) -> None:
        raw = b'{"\\u00e9":1,"e\\u0301":2}\n'
        with self.assertRaises(CanonicalizationError):
            parse_canonical_line(raw)

    def test_rejects_noncanonical_key_order(self) -> None:
        with self.assertRaises(CanonicalizationError):
            parse_canonical_line(b'{"b":1,"a":2}\n')
```

```python
# tests/test_hashing.py
import unittest

from agent_evidence_ledger.hashing import calculate_event_hash


class HashingTests(unittest.TestCase):
    def test_event_hash_is_deterministic_lowercase_sha256(self) -> None:
        event = {"schema_version": "1", "sequence": 0, "payload": {}}
        first = calculate_event_hash(event)
        second = calculate_event_hash(dict(reversed(tuple(event.items()))))
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
```

- [ ] **Step 2: Run the tests and confirm missing modules**

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_hashing -v
```

Expected: import errors for `canonical` and `hashing`.

- [ ] **Step 3: Implement the bounded canonical profile**

```python
# src/agent_evidence_ledger/canonical.py
from __future__ import annotations

import json
import unicodedata
from typing import Any

from .errors import CanonicalizationError

MAX_SAFE_INTEGER = (1 << 53) - 1
MAX_DEPTH = 32
MAX_EVENT_BYTES = 1024 * 1024


def _normalise(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise CanonicalizationError("maximum nesting depth exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise CanonicalizationError("integer outside safe JSON range")
        return value
    if isinstance(value, float):
        raise CanonicalizationError("floating-point values are forbidden")
    if isinstance(value, str):
        normalised = unicodedata.normalize("NFC", value)
        if any(0xD800 <= ord(char) <= 0xDFFF for char in normalised):
            raise CanonicalizationError("lone Unicode surrogate is forbidden")
        return normalised
    if isinstance(value, list):
        return [_normalise(item, depth + 1) for item in value]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("object keys must be strings")
            normalised_key = _normalise(key, depth + 1)
            if normalised_key in output:
                raise CanonicalizationError("duplicate key after NFC normalisation")
            output[normalised_key] = _normalise(item, depth + 1)
        return output
    raise CanonicalizationError(f"unsupported value type: {type(value).__name__}")


def canonicalize(value: object) -> bytes:
    normalised = _normalise(value)
    encoded = json.dumps(
        normalised,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise CanonicalizationError("canonical event exceeds 1 MiB")
    return encoded


def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    raw_keys: set[str] = set()
    for key, value in pairs:
        if key in raw_keys:
            raise CanonicalizationError("duplicate object key")
        raw_keys.add(key)
        normalised = unicodedata.normalize("NFC", key)
        if normalised in output:
            raise CanonicalizationError("duplicate key after NFC normalisation")
        output[normalised] = value
    return output


def parse_canonical_line(line: bytes) -> dict[str, object]:
    if not line.endswith(b"\n"):
        raise CanonicalizationError("ledger line must end with newline")
    body = line[:-1]
    if len(body) > MAX_EVENT_BYTES:
        raise CanonicalizationError("canonical event exceeds 1 MiB")
    try:
        decoded = json.loads(body.decode("utf-8"), object_pairs_hook=_pairs_hook)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalizationError("invalid UTF-8 JSON event") from exc
    if not isinstance(decoded, dict):
        raise CanonicalizationError("event must be a JSON object")
    normalised = _normalise(decoded)
    if canonicalize(normalised) != body:
        raise CanonicalizationError("event line is not canonical")
    return normalised
```

```python
# src/agent_evidence_ledger/hashing.py
from __future__ import annotations

import hashlib

from .canonical import canonicalize

EVENT_DOMAIN = b"agent-evidence-ledger:event:v1\n"


def calculate_event_hash(event_without_hash: dict[str, object]) -> str:
    return hashlib.sha256(EVENT_DOMAIN + canonicalize(event_without_hash)).hexdigest()
```

- [ ] **Step 4: Run canonical and hash tests**

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_hashing -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit canonical bytes and hashing**

```bash
git add src/agent_evidence_ledger/canonical.py src/agent_evidence_ledger/hashing.py tests/test_canonical.py tests/test_hashing.py
git commit -m "feat: add canonical event encoding and hashing"
```

### Task 3: Implement event schemas, references and lifecycle state

**Files:**
- Create: `src/agent_evidence_ledger/schemas.py`
- Create: `src/agent_evidence_ledger/state_machine.py`
- Create: `tests/test_schemas.py`
- Create: `tests/test_state_machine.py`

**Interfaces:**
- Produces: `validate_event_envelope(event)`, `validate_reference_rules(events, event)`, `LedgerState`, `apply_event(state, event) -> LedgerState`.
- Consumes: canonical dictionaries, `SchemaError`, `ReferenceError`, `LifecycleError`.

- [ ] **Step 1: Write illegal-transition tests**

```python
# tests/test_state_machine.py
import unittest

from agent_evidence_ledger.errors import LifecycleError
from agent_evidence_ledger.state_machine import LedgerState, apply_event


def event(event_type: str, sequence: int, **payload: object) -> dict[str, object]:
    return {
        "event_type": event_type,
        "sequence": sequence,
        "event_id": f"evt_{sequence:06d}",
        "references": [],
        "payload": payload,
        "evidence_class": "context",
    }


class StateMachineTests(unittest.TestCase):
    def test_request_before_open_is_illegal(self) -> None:
        with self.assertRaises(LifecycleError):
            apply_event(LedgerState(), event("request_received", 0))

    def test_verified_complete_requires_matching_observation(self) -> None:
        state = LedgerState(opened=True, requested=True, contracted=True, active_attempt="evt_000003")
        decision = event("verification_decided", 4, status="VERIFIED_COMPLETE")
        with self.assertRaises(LifecycleError):
            apply_event(state, decision)

    def test_recovery_after_security_rejection_is_illegal(self) -> None:
        state = LedgerState(last_decision="SECURITY_REJECTED", decided=True, terminal=True)
        with self.assertRaises(LifecycleError):
            apply_event(state, event("recovery_authorized", 9, remaining_attempts=1))
```

```python
# tests/test_schemas.py
import unittest

from agent_evidence_ledger.errors import SchemaError
from agent_evidence_ledger.schemas import validate_event_envelope


class SchemaTests(unittest.TestCase):
    def test_rejects_unknown_top_level_field(self) -> None:
        payload = {
            "schema_version": "1",
            "ledger_id": "led_demo",
            "sequence": 0,
            "event_id": "evt_000000",
            "event_type": "ledger_opened",
            "recorded_at": "2026-07-22T10:00:00Z",
            "actor": {"actor_id": "writer", "actor_type": "orchestrator"},
            "evidence_class": "context",
            "references": [],
            "payload": {},
            "previous_hash": "0" * 64,
            "event_hash": "1" * 64,
            "unexpected": True,
        }
        with self.assertRaises(SchemaError):
            validate_event_envelope(payload)
```

- [ ] **Step 2: Run and confirm missing schema/state modules**

```bash
PYTHONPATH=src python -m unittest tests.test_schemas tests.test_state_machine -v
```

Expected: import failures.

- [ ] **Step 3: Implement strict envelopes and explicit state**

Use these exact public shapes:

```python
# src/agent_evidence_ledger/state_machine.py
from __future__ import annotations

from dataclasses import dataclass, replace

from .errors import LifecycleError


@dataclass(frozen=True)
class LedgerState:
    opened: bool = False
    requested: bool = False
    contracted: bool = False
    active_attempt: str | None = None
    attempt_reported: bool = False
    attempt_observed: bool = False
    observation_matches: bool = False
    observation_partial: bool = False
    terminal: bool = False
    completion_claimed: bool = False
    decided: bool = False
    last_decision: str | None = None
    recovery_authorized: bool = False
    closed: bool = False


def apply_event(state: LedgerState, event: dict[str, object]) -> LedgerState:
    event_type = str(event["event_type"])
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        raise LifecycleError("event payload must be an object")
    if state.closed:
        raise LifecycleError("no event is legal after closure")
    if event_type == "ledger_opened":
        if state.opened or int(event["sequence"]) != 0:
            raise LifecycleError("ledger_opened must be the unique genesis event")
        return replace(state, opened=True)
    if event_type == "request_received":
        if not state.opened or state.requested:
            raise LifecycleError("request_received must occur once after opening")
        return replace(state, requested=True)
    if event_type == "contract_declared":
        if not state.requested or state.contracted or state.active_attempt:
            raise LifecycleError("contract_declared must precede attempts")
        return replace(state, contracted=True)
    if event_type == "tool_attempted":
        if not state.contracted or state.active_attempt is not None or state.decided:
            raise LifecycleError("attempt requires a contracted open attempt window")
        return replace(state, active_attempt=str(event["event_id"]))
    if event_type == "tool_reported":
        if state.active_attempt is None or state.decided or state.attempt_reported:
            raise LifecycleError("one source report is allowed per active attempt")
        return replace(state, attempt_reported=True)
    if event_type == "observation_recorded":
        if state.active_attempt is None or state.decided or state.attempt_observed:
            raise LifecycleError("one observation is allowed per active attempt")
        return replace(
            state,
            attempt_observed=True,
            observation_matches=bool(payload.get("matches_contract")),
            observation_partial=str(payload.get("outcome_class")) == "partial",
            terminal=bool(payload.get("terminal")),
        )
    if event_type == "completion_claimed":
        if state.active_attempt is None or state.decided or state.completion_claimed:
            raise LifecycleError("one completion claim is allowed per active attempt")
        return replace(state, completion_claimed=True)
    if event_type == "verification_decided":
        if state.active_attempt is None or state.decided:
            raise LifecycleError("one decision is required per active attempt")
        status = str(payload.get("status"))
        if status == "VERIFIED_COMPLETE" and not (state.attempt_observed and state.observation_matches):
            raise LifecycleError("verified completion requires a matching observation")
        if status == "PARTIAL" and not (state.attempt_observed and state.observation_partial):
            raise LifecycleError("partial requires a partial observation")
        if status == "SECURITY_REJECTED" and not (state.attempt_observed and state.terminal):
            raise LifecycleError("security rejection requires a terminal observation")
        if status not in {"VERIFIED_COMPLETE", "PARTIAL", "UNVERIFIED", "FAILED", "SECURITY_REJECTED"}:
            raise LifecycleError("unsupported decision status")
        return replace(state, decided=True, last_decision=status)
    if event_type == "recovery_authorized":
        if not state.decided or state.last_decision not in {"PARTIAL", "UNVERIFIED", "FAILED"} or state.terminal:
            raise LifecycleError("recovery is not legal after the final decision")
        return replace(
            state,
            active_attempt=None,
            attempt_reported=False,
            attempt_observed=False,
            observation_matches=False,
            observation_partial=False,
            completion_claimed=False,
            decided=False,
            last_decision=None,
            recovery_authorized=True,
        )
    if event_type == "ledger_closed":
        if not state.decided:
            raise LifecycleError("closure requires a final decision")
        return replace(state, closed=True)
    return state
```

`schemas.py` must define exact allowed envelope keys, actor types, evidence classes, RFC 3339 `Z` validation, reference count, lowercase hash validation and event-specific evidence-class constraints. `validate_reference_rules` must reject forward, self, missing and wrong-cardinality references.

- [ ] **Step 4: Expand tests to every event type and run**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_schemas tests.test_state_machine -v
```

Expected: all schema and transition tests pass, including one positive complete lifecycle and every invalid lifecycle fixture listed in the design.

- [ ] **Step 5: Commit the protocol state machine**

```bash
git add src/agent_evidence_ledger/schemas.py src/agent_evidence_ledger/state_machine.py tests/test_schemas.py tests/test_state_machine.py
git commit -m "feat: enforce evidence ledger lifecycle rules"
```

### Task 4: Implement open-ledger verification and deterministic mutation detection

**Files:**
- Create: `src/agent_evidence_ledger/verifier.py`
- Create: `tests/helpers.py`
- Create: `tests/test_verifier_open.py`
- Create: `tests/test_mutations.py`

**Interfaces:**
- Produces: `LedgerVerifier.verify(path, expected_root=None, expected_checkpoint=None, require_sealed=False) -> VerificationReport`.
- Consumes: canonical parser, hashing, schemas and state machine.

- [ ] **Step 1: Write an open-chain verification test**

```python
# tests/test_verifier_open.py
import tempfile
import unittest
from pathlib import Path

from agent_evidence_ledger.models import AssuranceLevel
from agent_evidence_ledger.verifier import LedgerVerifier
from tests.helpers import write_open_valid_ledger


class OpenVerifierTests(unittest.TestCase):
    def test_valid_open_chain_has_open_assurance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = write_open_valid_ledger(Path(directory))
            report = LedgerVerifier().verify(ledger)
            self.assertTrue(report.valid)
            self.assertEqual(report.assurance_level, AssuranceLevel.OPEN_CHAIN_VALID)

    def test_payload_mutation_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = write_open_valid_ledger(Path(directory))
            path = ledger / "ledger.jsonl"
            path.write_bytes(path.read_bytes().replace(b'"task":"write"', b'"task":"erase"'))
            report = LedgerVerifier().verify(ledger)
            self.assertFalse(report.valid)
            self.assertEqual(report.assurance_level, AssuranceLevel.INVALID)
```

- [ ] **Step 2: Run and confirm verifier import failure**

```bash
PYTHONPATH=src python -m unittest tests.test_verifier_open -v
```

Expected: `ModuleNotFoundError` for `verifier`.

- [ ] **Step 3: Implement read-only verification**

`LedgerVerifier.verify` must:

1. reject symlinks for ledger-controlled paths;
2. snapshot `ledger.jsonl` size and modification metadata;
3. read bytes without creating files;
4. split with preserved newlines and reject a partial final line;
5. parse each canonical event;
6. validate envelope, sequence, event ID, timestamp order and prior-only references;
7. recompute every event hash and previous hash;
8. replay the lifecycle state machine;
9. compare source metadata after reading and return `OperationalError` when changed;
10. return `OPEN_CHAIN_VALID` when no `ledger_closed` event exists and `require_sealed` is false.

The verifier records multiple independent schema problems when safe, but stops hash-chain-dependent checks after integrity is lost.

- [ ] **Step 4: Add deterministic mutation loops**

```python
# tests/test_mutations.py
import tempfile
import unittest
from pathlib import Path

from agent_evidence_ledger.verifier import LedgerVerifier
from tests.helpers import open_fixture_lines, write_lines


class MutationTests(unittest.TestCase):
    def test_every_single_event_deletion_is_invalid(self) -> None:
        original = open_fixture_lines()
        for index in range(len(original)):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                ledger = write_lines(Path(directory), original[:index] + original[index + 1 :])
                self.assertFalse(LedgerVerifier().verify(ledger).valid)

    def test_every_adjacent_swap_is_invalid(self) -> None:
        original = open_fixture_lines()
        for index in range(len(original) - 1):
            mutated = list(original)
            mutated[index], mutated[index + 1] = mutated[index + 1], mutated[index]
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                ledger = write_lines(Path(directory), mutated)
                self.assertFalse(LedgerVerifier().verify(ledger).valid)
```

Also add scalar mutation, hash-nibble mutation, boundary truncation and copied-event insertion loops.

- [ ] **Step 5: Run the full milestone-1 suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all protocol-core tests pass.

- [ ] **Step 6: Commit milestone 1**

```bash
git add src/agent_evidence_ledger/verifier.py tests/helpers.py tests/test_verifier_open.py tests/test_mutations.py
git commit -m "feat: verify open ledgers and detect trace mutations"
```

## Milestone 2 — Persistence and commands

### Task 5: Implement platform advisory locking and append writer

**Files:**
- Create: `src/agent_evidence_ledger/locking.py`
- Create: `src/agent_evidence_ledger/writer.py`
- Create: `tests/test_locking.py`
- Create: `tests/test_writer.py`

**Interfaces:**
- Produces: `AdvisoryLock(path, timeout_seconds)`, `LedgerWriter.init`, `LedgerWriter.append`, injectable clock and identifier factory.
- Consumes: open verifier, schemas, hashing and models.

- [ ] **Step 1: Write lock-contention and deterministic append tests**

```python
# tests/test_writer.py
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agent_evidence_ledger.writer import LedgerWriter


class WriterTests(unittest.TestCase):
    def test_init_creates_deterministic_genesis_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            writer = LedgerWriter(clock=lambda: datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc))
            ledger = writer.init(Path(directory) / "led_demo", ledger_id="led_demo", evidence_label="deterministic_fixture")
            line = (ledger / "ledger.jsonl").read_text(encoding="utf-8")
            self.assertIn('"event_id":"evt_000000"', line)
            self.assertTrue(line.endswith("\n"))

    def test_append_refuses_invalid_existing_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            writer = LedgerWriter()
            ledger = writer.init(Path(directory) / "led_demo", ledger_id="led_demo", evidence_label="fixture")
            path = ledger / "ledger.jsonl"
            path.write_bytes(path.read_bytes().replace(b"ledger_opened", b"ledger_broken"))
            with self.assertRaises(Exception):
                writer.append(ledger, event_type="request_received", actor_type="user", actor_id="user", payload={"task": "write"})
```

- [ ] **Step 2: Run and confirm missing writer**

```bash
PYTHONPATH=src python -m unittest tests.test_locking tests.test_writer -v
```

Expected: import errors.

- [ ] **Step 3: Implement advisory lock and append protocol**

`AdvisoryLock` opens `.ledger.lock` and uses `fcntl.flock(..., LOCK_EX | LOCK_NB)` on POSIX or `msvcrt.locking(..., LK_NBLCK, 1)` on Windows with monotonic timeout polling. It must always release in `__exit__` and raise `LockError` on timeout.

`LedgerWriter.append` must acquire the lock, verify the existing open chain, recursively reject secret-like keys, assign sequence/event ID/timestamp/previous hash, validate the event, append one canonical line, flush and `os.fsync`.

- [ ] **Step 4: Run persistence tests**

```bash
PYTHONPATH=src python -m unittest tests.test_locking tests.test_writer -v
```

Expected: lock contention, deterministic IDs, non-decreasing clock, secret rejection and invalid-history refusal pass on the current platform.

- [ ] **Step 5: Commit cooperative writer persistence**

```bash
git add src/agent_evidence_ledger/locking.py src/agent_evidence_ledger/writer.py tests/test_locking.py tests/test_writer.py
git commit -m "feat: add locked append-only ledger writer"
```

### Task 6: Implement atomic artifacts, sealing, manifest and expected checkpoints

**Files:**
- Create: `src/agent_evidence_ledger/artifacts.py`
- Create: `src/agent_evidence_ledger/seal.py`
- Modify: `src/agent_evidence_ledger/writer.py`
- Modify: `src/agent_evidence_ledger/verifier.py`
- Create: `tests/test_artifacts.py`
- Create: `tests/test_sealing.py`
- Create: `tests/test_expected_root.py`

**Interfaces:**
- Produces: `attach_artifact`, `close_ledger`, `build_seal`, `build_manifest`, `ExpectedCheckpoint` parsing.
- Adds sealed assurance to `LedgerVerifier`.

- [ ] **Step 1: Write crash-resume closure tests**

```python
# tests/test_sealing.py
import tempfile
import unittest
from pathlib import Path

from agent_evidence_ledger.models import AssuranceLevel
from agent_evidence_ledger.verifier import LedgerVerifier
from tests.helpers import build_decided_ledger


class SealingTests(unittest.TestCase):
    def test_close_is_idempotent_after_missing_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            writer, ledger = build_decided_ledger(Path(directory), status="VERIFIED_COMPLETE")
            writer.close(ledger, close_reason="complete")
            (ledger / "manifest.json").unlink()
            writer.close(ledger, close_reason="complete")
            report = LedgerVerifier().verify(ledger, require_sealed=True)
            self.assertTrue(report.valid)
            self.assertEqual(report.assurance_level, AssuranceLevel.INTERNAL_CHAIN_VALID)
```

- [ ] **Step 2: Run and confirm sealing/artifact failures**

```bash
PYTHONPATH=src python -m unittest tests.test_artifacts tests.test_sealing tests.test_expected_root -v
```

Expected: missing modules or methods.

- [ ] **Step 3: Implement atomic attachment and closure**

Use temporary siblings created with `tempfile.NamedTemporaryFile(delete=False, dir=...)`, stream hashing, `flush`, `os.fsync`, `os.replace` and best-effort directory `fsync`. Artifact paths are digest-only. Closure refuses unreferenced artifacts and unexpected retained files.

`close` must append `ledger_closed` once, then atomically reconstruct missing seal/manifest files. Existing disagreement is a hard error, never overwritten.

`ExpectedCheckpoint` contains `schema_version`, `ledger_id`, `event_count` and `final_event_hash`; all fields match before returning `EXPECTED_ROOT_MATCHED`.

- [ ] **Step 4: Run sealed-ledger tests**

```bash
PYTHONPATH=src python -m unittest tests.test_artifacts tests.test_sealing tests.test_expected_root -v
```

Expected: atomic attach, modified artifact, unreferenced artifact, seal mismatch, manifest mismatch, idempotent close and checkpoint mismatch cases pass.

- [ ] **Step 5: Commit sealed evidence persistence**

```bash
git add src/agent_evidence_ledger/artifacts.py src/agent_evidence_ledger/seal.py src/agent_evidence_ledger/writer.py src/agent_evidence_ledger/verifier.py tests/test_artifacts.py tests/test_sealing.py tests/test_expected_root.py
git commit -m "feat: seal ledgers with atomic artifacts and checkpoints"
```

### Task 7: Implement `ledger-record` and `ledger-verify`

**Files:**
- Create: `src/agent_evidence_ledger/record_cli.py`
- Create: `src/agent_evidence_ledger/verify_cli.py`
- Create: `tests/test_record_cli.py`
- Create: `tests/test_verify_cli.py`

**Interfaces:**
- Produces installed commands `ledger-record` and `ledger-verify`.
- JSON is default output; text mode is explicit.

- [ ] **Step 1: Write CLI exit-code tests**

```python
# tests/test_verify_cli.py
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import write_open_valid_ledger


class VerifyCliTests(unittest.TestCase):
    def test_valid_open_ledger_returns_zero_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = write_open_valid_ledger(Path(directory))
            result = subprocess.run(
                [sys.executable, "-m", "agent_evidence_ledger.verify_cli", "--ledger", str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["assurance_level"], "OPEN_CHAIN_VALID")
```

- [ ] **Step 2: Run and confirm missing CLI modules**

```bash
PYTHONPATH=src python -m unittest tests.test_record_cli tests.test_verify_cli -v
```

Expected: import failures.

- [ ] **Step 3: Implement exact subcommands and exit mapping**

`record_cli` subcommands:

```text
ledger-record init --output PATH [--ledger-id ID] --evidence-label LABEL
ledger-record append --ledger PATH --event-type TYPE --actor-type TYPE --actor-id ID --payload-file FILE [--reference EVENT_ID ...]
ledger-record attach --ledger PATH --file FILE --media-type TYPE [--description TEXT]
ledger-record close --ledger PATH --close-reason complete|security_rejected|aborted
```

`verify_cli` options:

```text
ledger-verify --ledger PATH [--require-sealed] [--expected-root HASH | --expected-root-file FILE] [--format json|text]
```

Map valid to `0`, invalid evidence to `2`, malformed input to `3`, unsupported schema to `4`, and operational failure to `5`. Never print unrestricted stack traces by default.

- [ ] **Step 4: Run CLI tests and module smoke commands**

```bash
PYTHONPATH=src python -m unittest tests.test_record_cli tests.test_verify_cli -v
PYTHONPATH=src python -m agent_evidence_ledger.verify_cli --help
PYTHONPATH=src python -m agent_evidence_ledger.record_cli --help
```

Expected: tests pass and both help commands return zero.

- [ ] **Step 5: Commit milestone 2 commands**

```bash
git add src/agent_evidence_ledger/record_cli.py src/agent_evidence_ledger/verify_cli.py tests/test_record_cli.py tests/test_verify_cli.py
git commit -m "feat: add ledger recording and verification commands"
```

## Milestone 3 — Disclosure and reproducible evidence

### Task 8: Generate valid, invalid and replacement-chain reference ledgers

**Files:**
- Create: `scripts/generate_reference_ledgers.py`
- Create: `fixtures/scenarios.json`
- Create: `reference_ledgers/`
- Create: `tests/test_reference_ledgers.py`
- Create: `tests/test_fixture_regeneration.py`

**Interfaces:**
- Produces deterministic reference directories and `reference_ledgers/expected_outcomes.json`.
- Consumes only package APIs and an injected fixed clock/IDs.

- [ ] **Step 1: Write exact outcome expectations**

```python
# tests/test_reference_ledgers.py
import json
import unittest
from pathlib import Path


class ReferenceLedgerTests(unittest.TestCase):
    def test_expected_outcomes_cover_all_required_classes(self) -> None:
        outcomes = json.loads(Path("reference_ledgers/expected_outcomes.json").read_text(encoding="utf-8"))
        self.assertEqual(outcomes["valid_verified"]["assurance_level"], "INTERNAL_CHAIN_VALID")
        self.assertEqual(outcomes["tampered_payload"]["assurance_level"], "INVALID")
        self.assertEqual(outcomes["replacement_chain_internal"]["assurance_level"], "INTERNAL_CHAIN_VALID")
        self.assertEqual(outcomes["replacement_chain_expected_root"]["error_code"], "EXPECTED_ROOT_MISMATCH")
```

- [ ] **Step 2: Run and confirm missing references**

```bash
PYTHONPATH=src python -m unittest tests.test_reference_ledgers tests.test_fixture_regeneration -v
```

Expected: missing files.

- [ ] **Step 3: Implement deterministic generator**

The generator must create the six valid, twelve invalid-integrity and ten invalid-lifecycle fixtures from the specification. It must first build valid source ledgers through `LedgerWriter`, then mutate copies as raw bytes or structured events. It writes a canonical expected-outcomes file and an external checkpoint outside the matching ledger directory.

- [ ] **Step 4: Verify byte-for-byte regeneration**

```bash
rm -rf /tmp/ael-reference
PYTHONPATH=src python scripts/generate_reference_ledgers.py --output /tmp/ael-reference
python - <<'PY'
from pathlib import Path
import filecmp
assert filecmp.dircmp("reference_ledgers", "/tmp/ael-reference").left_only == []
assert filecmp.dircmp("reference_ledgers", "/tmp/ael-reference").right_only == []
PY
```

The test implementation must recursively compare every relative file and byte digest, not only directory names.

- [ ] **Step 5: Commit reproducible evidence**

```bash
git add scripts/generate_reference_ledgers.py fixtures/scenarios.json reference_ledgers tests/test_reference_ledgers.py tests/test_fixture_regeneration.py
git commit -m "test: add deterministic ledger evidence fixtures"
```

### Task 9: Implement safe disclosure export and diagnostic-invalid bundles

**Files:**
- Create: `src/agent_evidence_ledger/export.py`
- Create: `src/agent_evidence_ledger/export_cli.py`
- Create: `tests/test_export.py`
- Create: `tests/test_export_cli.py`

**Interfaces:**
- Produces: `DisclosureExporter.export(source, output, diagnostic_invalid=False) -> Path` and `ledger-export`.
- Normal export requires `INTERNAL_CHAIN_VALID` or `EXPECTED_ROOT_MATCHED`.

- [ ] **Step 1: Write fail-closed and diagnostic tests**

```python
# tests/test_export.py
import json
import tempfile
import unittest
from pathlib import Path

from agent_evidence_ledger.export import DisclosureExporter
from agent_evidence_ledger.errors import ChainIntegrityError
from tests.helpers import copy_reference_ledger


class ExportTests(unittest.TestCase):
    def test_normal_export_refuses_invalid_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = copy_reference_ledger("tampered_payload", Path(directory) / "source")
            with self.assertRaises(ChainIntegrityError):
                DisclosureExporter().export(source, Path(directory) / "out")

    def test_diagnostic_export_contains_no_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = copy_reference_ledger("tampered_payload", Path(directory) / "source")
            output = DisclosureExporter().export(source, Path(directory) / "out", diagnostic_invalid=True)
            disclosure = json.loads((output / "disclosure.json").read_text(encoding="utf-8"))
            self.assertEqual(disclosure["bundle_type"], "INVALID_SOURCE_DIAGNOSTIC")
            self.assertNotIn("payload", json.dumps(disclosure))
```

- [ ] **Step 2: Run and confirm exporter absence**

```bash
PYTHONPATH=src python -m unittest tests.test_export tests.test_export_cli -v
```

Expected: import failures.

- [ ] **Step 3: Implement allowlisted disclosure**

Valid disclosure includes safe envelope fields, selected allowlisted payload fields, reference links, final assurance, root/checkpoint metadata, artifact digest metadata and omitted field paths. Artifact bytes are excluded unless an explicit future feature adds a separate allowlist.

Diagnostic invalid disclosure includes only error codes, safe positions/types and non-sensitive digest metadata. It must never copy source payloads or artifacts.

- [ ] **Step 4: Run export tests and command smoke test**

```bash
PYTHONPATH=src python -m unittest tests.test_export tests.test_export_cli -v
PYTHONPATH=src python -m agent_evidence_ledger.export_cli --help
```

Expected: all pass.

- [ ] **Step 5: Commit milestone 3 disclosure**

```bash
git add src/agent_evidence_ledger/export.py src/agent_evidence_ledger/export_cli.py tests/test_export.py tests/test_export_cli.py
git commit -m "feat: export safe evidence disclosure bundles"
```

## Milestone 4 — Employer-facing release

### Task 10: Build the dependency-free static viewer

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`
- Create: `web/data/valid.json`
- Create: `web/data/tampered.json`
- Create: `tests/test_web.py`

**Interfaces:**
- Viewer consumes only the disclosure JSON schema from Task 9.
- No network request may target outside the local `web/` directory.

- [ ] **Step 1: Write static claims and accessibility tests**

```python
# tests/test_web.py
import unittest
from pathlib import Path


class WebTests(unittest.TestCase):
    def test_viewer_has_required_claims_boundary(self) -> None:
        html = Path("web/index.html").read_text(encoding="utf-8")
        self.assertIn("Prove the trace, not the claim", html)
        self.assertIn("does not prove every recorded fact is true", html)
        self.assertNotIn("immutable", html.lower())
        self.assertNotIn("trusted agent", html.lower())

    def test_viewer_is_local_and_keyboard_addressable(self) -> None:
        combined = "\n".join(Path(path).read_text(encoding="utf-8") for path in ["web/index.html", "web/styles.css", "web/app.js"])
        self.assertNotIn("https://", combined)
        self.assertIn("aria-live", combined)
        self.assertIn(":focus-visible", combined)
```

- [ ] **Step 2: Run and confirm missing web surface**

```bash
PYTHONPATH=src python -m unittest tests.test_web -v
```

Expected: file-not-found failures.

- [ ] **Step 3: Implement the employer experience**

The page must show, above the fold:

- headline `Prove the trace, not the claim`;
- source bundle type;
- chain assurance and final decision;
- valid-versus-tampered switch;
- explicit distinction between source report, independent observation and decision;
- event timeline and hash ribbon;
- visible limitation that role independence is asserted by protocol labels, not signatures.

Use semantic landmarks, buttons for scenario selection, keyboard-operable event navigation, visible focus, reduced-motion CSS and a single-column layout at 390 CSS pixels. Provide meaningful static `<noscript>` and initial HTML content.

- [ ] **Step 4: Run static and local server review**

```bash
PYTHONPATH=src python -m unittest tests.test_web -v
python -m http.server 8000 --directory web
```

Review desktop and 390-pixel layouts. Confirm no horizontal overflow, missing labels, external requests or unsupported security wording.

- [ ] **Step 5: Commit the viewer**

```bash
git add web tests/test_web.py
git commit -m "feat: add evidence ledger inspection viewer"
```

### Task 11: Add documentation, release verifier and Python matrix

**Files:**
- Create: `README.md`
- Create: `RESULTS.md`
- Create: `THREAT_MODEL.md`
- Create: `docs/METHODOLOGY.md`
- Create: `docs/CONTRIBUTION.md`
- Create: `docs/DEMO_SCRIPT.md`
- Create: `scripts/verify_release.py`
- Create: `.github/workflows/tests.yml`
- Create: `.github/workflows/pages.yml`
- Create: `tests/test_documentation.py`
- Create: `LICENSE`

**Interfaces:**
- Release verifier becomes the single local and CI release gate.
- Pages deploys only the static `web/` directory.

- [ ] **Step 1: Write documentation-boundary tests**

```python
# tests/test_documentation.py
import unittest
from pathlib import Path


class DocumentationTests(unittest.TestCase):
    def test_readme_leads_with_problem_and_limit(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("Prove the trace, not the claim", readme)
        self.assertIn("deterministic software fixtures", readme)
        self.assertIn("does not prove who authored an event", readme)
        self.assertNotIn("legally immutable", readme.lower())
```

- [ ] **Step 2: Run and confirm documentation failures**

```bash
PYTHONPATH=src python -m unittest tests.test_documentation -v
```

Expected: missing README.

- [ ] **Step 3: Write the public narrative and release gate**

README order:

1. public question and one-line answer;
2. valid-versus-tampered preview;
3. assurance table;
4. two-minute local reproduction;
5. exact detected tamper classes;
6. architecture;
7. threat-model limits beside the claims;
8. commands and repository map;
9. deterministic-fixture disclaimer;
10. authorship and AI-assistance statement.

`scripts/verify_release.py` must compile source/tests/scripts, run all tests, regenerate references in a temporary directory, compare every byte, run the three module CLIs, verify valid/invalid/checkpoint outcomes, compare web data with fresh exports, scan for common credential patterns and reject forbidden public phrases such as `legally immutable` and unqualified `trusted`.

CI matrix: Python 3.10, 3.11, 3.12 and 3.13 with `fail-fast: false`. Each job upgrades packaging tools, installs editable, runs release verification, builds a wheel, creates a clean secondary venv, installs only the wheel, runs all tests from outside the source tree, runs all three installed commands and executes `pip check`.

- [ ] **Step 4: Run the complete source gate**

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .
python scripts/verify_release.py
```

Expected: all tests, reference regeneration, commands, scans and web comparisons pass.

- [ ] **Step 5: Commit release documentation and automation**

```bash
git add README.md RESULTS.md THREAT_MODEL.md docs scripts/verify_release.py .github/workflows tests/test_documentation.py LICENSE
git commit -m "docs: prepare evidence ledger employer release"
```

### Task 12: Perform source, wheel, archive and publication verification

**Files:**
- Modify only defects revealed by verification.
- Create release outputs outside the repository: `agent_evidence_ledger_v0.1.0.zip`, wheel and checksums.

**Interfaces:**
- Produces the exact independently tested public release.

- [ ] **Step 1: Run first complete source verification**

```bash
rm -rf build dist *.egg-info
python scripts/verify_release.py
python -m build --wheel
```

Expected: source gate passes and exactly one `agent_evidence_ledger-0.1.0-py3-none-any.whl` is built.

- [ ] **Step 2: Run the clean-wheel clarification pass**

```bash
python -m venv /tmp/ael-wheel-venv
/tmp/ael-wheel-venv/bin/python -m pip install --upgrade pip
/tmp/ael-wheel-venv/bin/python -m pip install dist/agent_evidence_ledger-0.1.0-py3-none-any.whl
cd /tmp
/tmp/ael-wheel-venv/bin/python -m unittest discover -s "$OLDPWD/tests" -p "test_*.py" -v
/tmp/ael-wheel-venv/bin/ledger-verify --help
/tmp/ael-wheel-venv/bin/ledger-record --help
/tmp/ael-wheel-venv/bin/ledger-export --help
/tmp/ael-wheel-venv/bin/python -m pip check
```

On Windows, use the equivalent `Scripts\python.exe` and console-script paths. Expected: every test and command passes without editable-source import fallback.

- [ ] **Step 3: Freeze and independently test the archive**

Create a clean archive from the release tree, excluding `.git`, venvs, caches, build directories and temporary runs. Extract it into a new directory, repeat the source verifier, rebuild a wheel from the extracted copy, install it into another clean environment and repeat the wheel tests.

Record SHA-256 for the ZIP and rebuilt wheel.

- [ ] **Step 4: Publish through a reviewed GitHub PR**

Create a standalone public repository `Luca-1304/agent-evidence-ledger`. Publish the exact verified tree on a release branch, open a PR, inspect every changed file, run Python 3.10–3.13 CI, correct any shared failure once, rerun the complete matrix, squash merge the verified head and deploy `web/` through GitHub Pages.

- [ ] **Step 5: Verify the public result**

Confirm:

- repository default branch contains the verified source;
- all four Python jobs passed from the merged code or a documentation-only verification PR based on the complete default branch;
- Pages loads without external assets;
- README links resolve;
- reference ledgers and expected checkpoint are present;
- no bootstrap or transfer workflow remains;
- public claims match the design boundary;
- issue #4 records design, implementation, CI and release evidence.

- [ ] **Step 6: Commit only verified fixes and tag the release**

```bash
git tag -a v0.1.0 -m "Agent Evidence Ledger v0.1.0"
git push origin v0.1.0
```

Do not tag before the final matrix and archive clarification pass are complete.

## Plan self-review

### Spec coverage

- Protocol core: Tasks 1–4.
- Cooperative persistence, artifact integrity and crash closure: Tasks 5–6.
- Recording and verification commands: Task 7.
- Deterministic valid, tampered and replacement fixtures: Task 8.
- Separate safe disclosure and invalid diagnostics: Task 9.
- Employer viewer and accessibility: Task 10.
- Claims boundary, threat model, authorship and release automation: Task 11.
- Source, wheel, archive, matrix, Pages and standalone publication: Task 12.

### Placeholder scan

The plan contains no `TBD`, `TODO`, “implement later”, generic “add validation” instruction or unnamed error-handling step. Code-changing steps provide concrete interfaces, commands and expected results.

### Type and naming consistency

- Assurance levels are consistently `OPEN_CHAIN_VALID`, `INTERNAL_CHAIN_VALID`, `EXPECTED_ROOT_MATCHED`, `INVALID`.
- Public types are consistently `Event`, `VerificationProblem`, `VerificationReport`.
- Public services are consistently `LedgerWriter`, `LedgerVerifier`, `DisclosureExporter`.
- Commands are consistently `ledger-record`, `ledger-verify`, `ledger-export`.
- Source ledger artifacts consistently use `artifacts/<sha256>` without extensions.
- Invalid viewer bundles consistently use `INVALID_SOURCE_DIAGNOSTIC`.

The plan is approved for execution in the stated order.