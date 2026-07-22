# Agent Evidence Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a standalone, local-first, tamper-evident evidence ledger for one tool-using agent execution, with canonical events, explicit approval and attempt boundaries, crash-resumable sealing, deterministic tamper fixtures, three CLIs and an employer-facing static viewer.

**Architecture:** A ledger directory contains one canonical JSONL event stream, content-addressed artifacts, a final seal and a deterministic manifest. The supported writer validates the complete prior stream before each append. A separate read-only verifier checks canonical bytes, hashes, prior-only references, lifecycle legality, artifacts, closure metadata and optional external checkpoints. Disclosure is generated outside the source ledger.

**Tech Stack:** Python 3.10–3.13 standard library, `unittest`, `dataclasses`, `argparse`, SHA-256, platform advisory locks (`fcntl` and `msvcrt`), HTML5, CSS and vanilla JavaScript. Setuptools builds the package; `build` is a release-only dependency. Runtime dependencies remain empty.

## Global Constraints

- One ledger represents one execution trace and one completion contract.
- “Append-only” describes the supported writer protocol, not physical filesystem immutability.
- Actor identifiers and `independent_observation` are protocol labels, not signatures or proof of organisational independence.
- Canonical JSON uses NFC-normalised strings, post-normalisation duplicate rejection, JSON-safe integers and byte-exact verification.
- Event lines are limited to 1 MiB, nesting depth to 32 and references to 128.
- References always point to strictly earlier events in the same ledger.
- Every attempt must follow `action_proposed → action_authorized → tool_attempted → verification_decided`.
- Artifacts use `artifacts/<sha256>`, reject symbolic links and default to a 64 MiB limit.
- `ledger-verify` is read-only and distinguishes open, sealed, expected-root and invalid assurance states.
- Normal export requires a valid sealed ledger. Invalid demonstration uses a payload-free diagnostic bundle.
- Public wording must not claim legal non-repudiation, authenticated identity, trusted time, observation truth, blockchain properties, compliance certification or external-model performance.
- No tests or release checks make network or paid-model calls.
- Every milestone ends with a complete source test pass and an independently reviewable commit.

---

## Milestone 1 — Protocol core

### Task 1: Establish the package, models and typed errors

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_evidence_ledger/__init__.py`
- Create: `src/agent_evidence_ledger/models.py`
- Create: `src/agent_evidence_ledger/errors.py`
- Create: `tests/test_public_api.py`
- Create: `tests/test_errors.py`

**Interfaces:**
- Produces: `AssuranceLevel`, `Event`, `VerificationProblem`, `VerificationReport`, `ExpectedCheckpoint` and the error classes named in the specification.
- Later tasks import those names from `agent_evidence_ledger`.

- [ ] **Step 1: Write the failing import and error-code tests**

```python
# tests/test_public_api.py
import unittest


class PublicApiTests(unittest.TestCase):
    def test_public_types_import(self) -> None:
        from agent_evidence_ledger import AssuranceLevel, Event, ExpectedCheckpoint, VerificationReport

        self.assertEqual(AssuranceLevel.OPEN_CHAIN_VALID.value, "OPEN_CHAIN_VALID")
        self.assertEqual(Event.__name__, "Event")
        self.assertEqual(ExpectedCheckpoint.__name__, "ExpectedCheckpoint")
        self.assertEqual(VerificationReport.__name__, "VerificationReport")
```

```python
# tests/test_errors.py
import unittest


class ErrorTests(unittest.TestCase):
    def test_chain_error_code_is_stable(self) -> None:
        from agent_evidence_ledger.errors import ChainIntegrityError

        error = ChainIntegrityError("broken chain")
        self.assertEqual(error.code, "CHAIN_INTEGRITY_ERROR")
        self.assertEqual(str(error), "broken chain")
```

- [ ] **Step 2: Run the tests and verify the expected import failure**

```bash
python -m unittest tests.test_public_api tests.test_errors -v
```

Expected: `ModuleNotFoundError: No module named 'agent_evidence_ledger'`.

- [ ] **Step 3: Create package metadata and exact model shapes**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=77", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-evidence-ledger"
version = "0.1.0"
description = "A tamper-evident evidence ledger for tool-using agents"
requires-python = ">=3.10"
license = "MIT"
license-files = ["LICENSE"]
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
class ExpectedCheckpoint:
    schema_version: str
    ledger_id: str
    event_count: int
    final_event_hash: str


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

Create `errors.py` with `LedgerError` and these exact subclasses/codes: `CanonicalizationError`, `SchemaError`, `ChainIntegrityError`, `LifecycleError`, `ReferenceError`, `ArtifactIntegrityError`, `SealError`, `ExpectedRootMismatch`, `LockError`, `OperationalError`.

- [ ] **Step 4: Run the focused tests**

```bash
PYTHONPATH=src python -m unittest tests.test_public_api tests.test_errors -v
```

Expected: `Ran 2 tests ... OK`.

- [ ] **Step 5: Commit the package boundary**

```bash
git add pyproject.toml src/agent_evidence_ledger tests/test_public_api.py tests/test_errors.py
git commit -m "feat: establish evidence ledger package boundary"
```

### Task 2: Implement canonical JSON and domain-separated hashing

**Files:**
- Create: `src/agent_evidence_ledger/canonical.py`
- Create: `src/agent_evidence_ledger/hashing.py`
- Create: `tests/test_canonical.py`
- Create: `tests/test_hashing.py`

**Interfaces:**
- Produces: `canonicalize(value: object) -> bytes`, `parse_canonical_line(line: bytes) -> dict[str, object]`, `calculate_event_hash(event_without_hash: dict[str, object]) -> str`.

- [ ] **Step 1: Write failing canonical edge-case tests**

```python
# tests/test_canonical.py
import unittest

from agent_evidence_ledger.canonical import canonicalize, parse_canonical_line
from agent_evidence_ledger.errors import CanonicalizationError


class CanonicalTests(unittest.TestCase):
    def test_sorts_keys_and_normalises_nfc(self) -> None:
        self.assertEqual(canonicalize({"b": 1, "a": "e\u0301"}), b'{"a":"\\u00e9","b":1}')

    def test_rejects_float_and_unsafe_integer(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonicalize({"value": 1.5})
        with self.assertRaises(CanonicalizationError):
            canonicalize({"value": 1 << 53})

    def test_rejects_duplicate_after_nfc(self) -> None:
        with self.assertRaises(CanonicalizationError):
            parse_canonical_line(b'{"\\u00e9":1,"e\\u0301":2}\n')

    def test_rejects_noncanonical_line(self) -> None:
        with self.assertRaises(CanonicalizationError):
            parse_canonical_line(b'{"b":1,"a":2}\n')
```

```python
# tests/test_hashing.py
import unittest

from agent_evidence_ledger.hashing import calculate_event_hash


class HashingTests(unittest.TestCase):
    def test_hash_is_order_independent_and_lowercase(self) -> None:
        event = {"schema_version": "1", "sequence": 0, "payload": {}}
        self.assertEqual(calculate_event_hash(event), calculate_event_hash(dict(reversed(tuple(event.items())))))
        self.assertRegex(calculate_event_hash(event), r"^[0-9a-f]{64}$")
```

- [ ] **Step 2: Run tests and confirm missing modules**

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_hashing -v
```

Expected: import failures.

- [ ] **Step 3: Implement the canonical profile**

Use `json.dumps(..., ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))`. Recursively NFC-normalise keys and string values, reject lone surrogates, floats, unsafe integers, depth above 32 and encoded bodies above 1 MiB. Parse with `object_pairs_hook` so raw duplicates and post-NFC duplicates are both rejected. `parse_canonical_line` requires a final newline and compares the body byte-for-byte with reconstructed canonical bytes.

```python
# src/agent_evidence_ledger/hashing.py
import hashlib

from .canonical import canonicalize

EVENT_DOMAIN = b"agent-evidence-ledger:event:v1\n"


def calculate_event_hash(event_without_hash: dict[str, object]) -> str:
    return hashlib.sha256(EVENT_DOMAIN + canonicalize(event_without_hash)).hexdigest()
```

- [ ] **Step 4: Run focused tests**

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_hashing -v
```

Expected: all pass.

- [ ] **Step 5: Commit canonicalisation and hashing**

```bash
git add src/agent_evidence_ledger/canonical.py src/agent_evidence_ledger/hashing.py tests/test_canonical.py tests/test_hashing.py
git commit -m "feat: add canonical event encoding and hashing"
```

### Task 3: Implement strict schemas, references and the full approval state machine

**Files:**
- Create: `src/agent_evidence_ledger/schemas.py`
- Create: `src/agent_evidence_ledger/state_machine.py`
- Create: `tests/test_schemas.py`
- Create: `tests/test_references.py`
- Create: `tests/test_state_machine.py`

**Interfaces:**
- Produces: `validate_event_envelope`, `validate_event_references`, `LifecycleSnapshot`, `apply_event`.
- Every transition consumes an already schema-valid event.

- [ ] **Step 1: Write tests that prove the complete approval chain is mandatory**

```python
# tests/test_state_machine.py
import unittest

from agent_evidence_ledger.errors import LifecycleError
from agent_evidence_ledger.state_machine import LifecyclePhase, LifecycleSnapshot, apply_event


def e(event_type: str, sequence: int, references: list[str] | None = None, payload: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "event_type": event_type,
        "sequence": sequence,
        "event_id": f"evt_{sequence:06d}",
        "references": references or [],
        "payload": payload or {},
    }


class StateMachineTests(unittest.TestCase):
    def test_attempt_without_proposal_and_authorisation_is_illegal(self) -> None:
        state = LifecycleSnapshot(phase=LifecyclePhase.CONTRACTED, contract_event_id="evt_000002")
        with self.assertRaises(LifecycleError):
            apply_event(state, e("tool_attempted", 3, ["evt_000002"]))

    def test_authorisation_must_reference_active_proposal(self) -> None:
        state = LifecycleSnapshot(
            phase=LifecyclePhase.PROPOSED,
            contract_event_id="evt_000002",
            proposal_event_id="evt_000003",
        )
        with self.assertRaises(LifecycleError):
            apply_event(state, e("action_authorized", 4, ["evt_000001"]))

    def test_verified_complete_requires_matching_observation(self) -> None:
        state = LifecycleSnapshot(
            phase=LifecyclePhase.ATTEMPTED,
            contract_event_id="evt_000002",
            attempt_event_id="evt_000005",
        )
        with self.assertRaises(LifecycleError):
            apply_event(state, e("verification_decided", 6, ["evt_000002"], {"status": "VERIFIED_COMPLETE"}))
```

- [ ] **Step 2: Run and confirm missing schema/state modules**

```bash
PYTHONPATH=src python -m unittest tests.test_schemas tests.test_references tests.test_state_machine -v
```

Expected: import failures.

- [ ] **Step 3: Implement exact lifecycle phases and attempt context**

```python
# src/agent_evidence_ledger/state_machine.py
from dataclasses import dataclass, replace
from enum import Enum

from .errors import LifecycleError


class LifecyclePhase(str, Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    REQUESTED = "REQUESTED"
    CONTRACTED = "CONTRACTED"
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    ATTEMPTED = "ATTEMPTED"
    DECIDED = "DECIDED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class LifecycleSnapshot:
    phase: LifecyclePhase = LifecyclePhase.NEW
    contract_event_id: str | None = None
    proposal_event_id: str | None = None
    authorization_event_id: str | None = None
    attempt_event_id: str | None = None
    report_event_id: str | None = None
    observation_event_id: str | None = None
    claim_event_id: str | None = None
    observation_matches: bool = False
    observation_partial: bool = False
    observation_terminal: bool = False
    persisted_attempt_error: bool = False
    decision_event_id: str | None = None
    decision_status: str | None = None
    remaining_attempts: int = 0


def apply_event(state: LifecycleSnapshot, event: dict[str, object]) -> LifecycleSnapshot:
    event_type = str(event["event_type"])
    event_id = str(event["event_id"])
    references = tuple(str(item) for item in event.get("references", []))
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        raise LifecycleError("payload must be an object")

    if state.phase is LifecyclePhase.CLOSED:
        raise LifecycleError("no event is legal after closure")
    if event_type == "ledger_opened":
        if state.phase is not LifecyclePhase.NEW or int(event["sequence"]) != 0:
            raise LifecycleError("ledger_opened must be the unique genesis event")
        return replace(state, phase=LifecyclePhase.OPEN)
    if event_type == "request_received":
        if state.phase is not LifecyclePhase.OPEN:
            raise LifecycleError("request_received must follow opening")
        return replace(state, phase=LifecyclePhase.REQUESTED)
    if event_type == "contract_declared":
        if state.phase is not LifecyclePhase.REQUESTED:
            raise LifecycleError("contract_declared must follow the request")
        return replace(state, phase=LifecyclePhase.CONTRACTED, contract_event_id=event_id)
    if event_type == "action_proposed":
        if state.phase is not LifecyclePhase.CONTRACTED or references != (state.contract_event_id,):
            raise LifecycleError("proposal must reference the active contract")
        return replace(state, phase=LifecyclePhase.PROPOSED, proposal_event_id=event_id)
    if event_type == "action_authorized":
        if state.phase is not LifecyclePhase.PROPOSED or references != (state.proposal_event_id,):
            raise LifecycleError("authorisation must reference the active proposal")
        return replace(state, phase=LifecyclePhase.AUTHORIZED, authorization_event_id=event_id)
    if event_type == "tool_attempted":
        if state.phase is not LifecyclePhase.AUTHORIZED or references != (state.authorization_event_id,):
            raise LifecycleError("attempt must reference the active authorisation")
        return replace(state, phase=LifecyclePhase.ATTEMPTED, attempt_event_id=event_id)
    if event_type == "tool_reported":
        if state.phase is not LifecyclePhase.ATTEMPTED or state.report_event_id is not None or references != (state.attempt_event_id,):
            raise LifecycleError("one source report is allowed for the active attempt")
        return replace(state, report_event_id=event_id)
    if event_type == "observation_recorded":
        if state.phase is not LifecyclePhase.ATTEMPTED or state.observation_event_id is not None or references != (state.attempt_event_id,):
            raise LifecycleError("one observation is allowed for the active attempt")
        return replace(
            state,
            observation_event_id=event_id,
            observation_matches=bool(payload.get("matches_contract")),
            observation_partial=str(payload.get("outcome_class")) == "partial",
            observation_terminal=bool(payload.get("terminal")),
        )
    if event_type == "completion_claimed":
        if state.phase is not LifecyclePhase.ATTEMPTED or state.claim_event_id is not None or state.attempt_event_id not in references:
            raise LifecycleError("one claim may reference the active attempt")
        return replace(state, claim_event_id=event_id)
    if event_type == "error_recorded":
        if state.phase in {LifecyclePhase.NEW, LifecyclePhase.OPEN, LifecyclePhase.CLOSED}:
            raise LifecycleError("persisted errors require a received request")
        return replace(state, persisted_attempt_error=state.phase is LifecyclePhase.ATTEMPTED)
    if event_type == "verification_decided":
        if state.phase is not LifecyclePhase.ATTEMPTED:
            raise LifecycleError("decision requires an active attempt")
        status = str(payload.get("status"))
        if status == "VERIFIED_COMPLETE" and not (state.observation_event_id and state.observation_matches):
            raise LifecycleError("verified completion requires a matching observation")
        if status == "PARTIAL" and not (state.observation_event_id and state.observation_partial):
            raise LifecycleError("partial requires a partial observation")
        if status == "SECURITY_REJECTED" and not (state.observation_event_id and state.observation_terminal):
            raise LifecycleError("security rejection requires a terminal observation")
        if status == "FAILED" and not (state.observation_event_id or state.persisted_attempt_error):
            raise LifecycleError("failed requires a failing observation or persisted attempt error")
        if status not in {"VERIFIED_COMPLETE", "PARTIAL", "UNVERIFIED", "FAILED", "SECURITY_REJECTED"}:
            raise LifecycleError("unsupported decision status")
        return replace(state, phase=LifecyclePhase.DECIDED, decision_event_id=event_id, decision_status=status)
    if event_type == "recovery_authorized":
        remaining = int(payload.get("remaining_attempts", 0))
        if state.phase is not LifecyclePhase.DECIDED or state.decision_status not in {"PARTIAL", "UNVERIFIED", "FAILED"}:
            raise LifecycleError("recovery requires a recoverable decision")
        if state.observation_terminal or remaining < 1:
            raise LifecycleError("recovery requires a positive bounded allowance")
        return LifecycleSnapshot(
            phase=LifecyclePhase.CONTRACTED,
            contract_event_id=state.contract_event_id,
            remaining_attempts=remaining,
        )
    if event_type == "ledger_closed":
        if state.phase is not LifecyclePhase.DECIDED or references != (state.decision_event_id,):
            raise LifecycleError("closure must reference the final decision")
        return replace(state, phase=LifecyclePhase.CLOSED)
    raise LifecycleError(f"unsupported event type: {event_type}")
```

`schemas.py` must enforce exact envelope keys, event types, actor labels, evidence classes, RFC 3339 UTC timestamps, lower-case hashes and event-specific evidence-class requirements. `validate_event_references` must reject missing, self, forward and cross-ledger references and enforce the exact cardinalities above.

- [ ] **Step 4: Expand tests to every valid and invalid transition**

```bash
PYTHONPATH=src python -m unittest tests.test_schemas tests.test_references tests.test_state_machine -v
```

Expected: all tests pass, including proposal, authorisation, attempt, report, observation, claim, decision, recovery, abort and closure cases.

- [ ] **Step 5: Commit the protocol rules**

```bash
git add src/agent_evidence_ledger/schemas.py src/agent_evidence_ledger/state_machine.py tests/test_schemas.py tests/test_references.py tests/test_state_machine.py
git commit -m "feat: enforce ledger approval and evidence lifecycle"
```

### Task 4: Implement read-only open-ledger verification and mutation generators

**Files:**
- Create: `src/agent_evidence_ledger/verifier.py`
- Create: `tests/helpers.py`
- Create: `tests/test_verifier_open.py`
- Create: `tests/test_mutations.py`

**Interfaces:**
- Produces: `LedgerVerifier.verify(path, expected_root=None, expected_checkpoint=None, require_sealed=False) -> VerificationReport`.
- Consumes canonical parser, schemas, references, hashing and lifecycle replay.

- [ ] **Step 1: Write open-chain and mutation tests**

```python
# tests/test_verifier_open.py
import tempfile
import unittest
from pathlib import Path

from agent_evidence_ledger.models import AssuranceLevel
from agent_evidence_ledger.verifier import LedgerVerifier
from tests.helpers import write_open_valid_ledger


class OpenVerifierTests(unittest.TestCase):
    def test_valid_open_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = LedgerVerifier().verify(write_open_valid_ledger(Path(directory)))
            self.assertTrue(report.valid)
            self.assertEqual(report.assurance_level, AssuranceLevel.OPEN_CHAIN_VALID)

    def test_payload_edit_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = write_open_valid_ledger(Path(directory))
            path = ledger / "ledger.jsonl"
            path.write_bytes(path.read_bytes().replace(b'"task":"write"', b'"task":"erase"'))
            self.assertFalse(LedgerVerifier().verify(ledger).valid)
```

- [ ] **Step 2: Run and verify the missing verifier failure**

```bash
PYTHONPATH=src python -m unittest tests.test_verifier_open tests.test_mutations -v
```

Expected: import failures.

- [ ] **Step 3: Implement read-only verification**

The verifier must reject symbolic links for ledger-controlled paths, read `ledger.jsonl` without creating files, reject partial lines, parse canonical events, validate sequence/event IDs/timestamp order/prior-only references, recompute every hash, replay lifecycle state and return `OPEN_CHAIN_VALID` when the stream is valid but not closed. It must compare file metadata before and after reading and return an operational concurrency problem if the source changes during verification.

Mutation tests must remove every event, swap every adjacent pair, alter one scalar, change one hash nibble, truncate at every event boundary and insert a copied event at every position. Every mutation must fail parsing or verification.

- [ ] **Step 4: Run the milestone-1 suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all protocol-core tests pass.

- [ ] **Step 5: Commit milestone 1**

```bash
git add src/agent_evidence_ledger/verifier.py tests/helpers.py tests/test_verifier_open.py tests/test_mutations.py
git commit -m "feat: verify open ledgers and detect trace mutation"
```

## Milestone 2 — Persistence and commands

### Task 5: Implement advisory locking and the validated writer

**Files:**
- Create: `src/agent_evidence_ledger/locking.py`
- Create: `src/agent_evidence_ledger/writer.py`
- Create: `tests/test_locking.py`
- Create: `tests/test_writer.py`

**Interfaces:**
- Produces: `AdvisoryLock`, `LedgerWriter.init`, `LedgerWriter.append`, injectable clock and ID factory.

- [ ] **Step 1: Write deterministic init, append and contention tests**

The tests must prove:

- genesis event is deterministic with an injected clock and ID;
- append refuses an altered prior stream;
- secret-like nested keys are rejected case-insensitively after separator removal;
- timestamps cannot regress;
- a second writer times out while the first process holds the advisory lock.

- [ ] **Step 2: Run and confirm missing writer modules**

```bash
PYTHONPATH=src python -m unittest tests.test_locking tests.test_writer -v
```

Expected: import failures.

- [ ] **Step 3: Implement platform locks and append semantics**

`AdvisoryLock` opens `.ledger.lock` and uses `fcntl.flock(..., LOCK_EX | LOCK_NB)` on POSIX or `msvcrt.locking(..., LK_NBLCK, 1)` on Windows, polling with `time.monotonic()` until the explicit timeout. The operating system releases the lock on process exit.

`LedgerWriter.append` acquires the lock, verifies the complete open stream, recursively filters secret-like keys, assigns sequence/event ID/time/previous hash, validates schema/references/lifecycle, appends exactly one canonical line, flushes and calls `os.fsync`.

- [ ] **Step 4: Run writer tests**

```bash
PYTHONPATH=src python -m unittest tests.test_locking tests.test_writer -v
```

Expected: all pass on the current operating system.

- [ ] **Step 5: Commit writer persistence**

```bash
git add src/agent_evidence_ledger/locking.py src/agent_evidence_ledger/writer.py tests/test_locking.py tests/test_writer.py
git commit -m "feat: add locked append-only ledger writer"
```

### Task 6: Implement atomic artifacts, crash-resumable sealing and checkpoints

**Files:**
- Create: `src/agent_evidence_ledger/artifacts.py`
- Create: `src/agent_evidence_ledger/seal.py`
- Modify: `src/agent_evidence_ledger/writer.py`
- Modify: `src/agent_evidence_ledger/verifier.py`
- Create: `tests/test_artifacts.py`
- Create: `tests/test_sealing.py`
- Create: `tests/test_expected_root.py`

**Interfaces:**
- Produces: `attach_artifact`, `LedgerWriter.close`, `build_seal`, `build_manifest`, checkpoint parsing and sealed verification.

- [ ] **Step 1: Write failing atomicity and resume tests**

Tests must prove:

- digest-only artifact paths and 64 MiB limit;
- symlink rejection;
- same-byte attachment is idempotent;
- changed artifact bytes invalidate verification;
- closure refuses unreferenced artifacts;
- deleting only `manifest.json` after a completed close and rerunning `close` reconstructs it without appending another event;
- an existing disagreeing seal is never overwritten;
- raw expected-root mismatch and structured checkpoint mismatch are distinct failures.

- [ ] **Step 2: Run and verify expected failures**

```bash
PYTHONPATH=src python -m unittest tests.test_artifacts tests.test_sealing tests.test_expected_root -v
```

Expected: missing methods/modules.

- [ ] **Step 3: Implement atomic files and deterministic manifest rules**

Stream artifacts into a temporary sibling while hashing, then `flush`, `fsync`, `os.replace` and best-effort directory `fsync`. Closure appends `ledger_closed` once, writes seal and manifest through temporary siblings and resumes missing metadata after a crash. The manifest includes sorted entries only for `ledger.jsonl`, `seal.json` and referenced artifacts; `.ledger.lock`, temporary files and disclosure outputs are excluded. Unexpected retained files invalidate a sealed ledger.

- [ ] **Step 4: Run sealed evidence tests**

```bash
PYTHONPATH=src python -m unittest tests.test_artifacts tests.test_sealing tests.test_expected_root -v
```

Expected: all pass.

- [ ] **Step 5: Commit sealed persistence**

```bash
git add src/agent_evidence_ledger/artifacts.py src/agent_evidence_ledger/seal.py src/agent_evidence_ledger/writer.py src/agent_evidence_ledger/verifier.py tests/test_artifacts.py tests/test_sealing.py tests/test_expected_root.py
git commit -m "feat: seal ledgers with atomic evidence and checkpoints"
```

### Task 7: Implement `ledger-record` and `ledger-verify`

**Files:**
- Create: `src/agent_evidence_ledger/record_cli.py`
- Create: `src/agent_evidence_ledger/verify_cli.py`
- Create: `tests/test_record_cli.py`
- Create: `tests/test_verify_cli.py`

**Interfaces:**
- Produces installed commands `ledger-record` and `ledger-verify`.
- JSON output is default; text is opt-in.

- [ ] **Step 1: Write subprocess tests for output and exit codes**

Test valid open/sealed ledgers, invalid chain exit `2`, malformed input `3`, unsupported schema `4` and operational failure `5`. Test that default stderr contains no stack trace.

- [ ] **Step 2: Run and confirm missing CLI modules**

```bash
PYTHONPATH=src python -m unittest tests.test_record_cli tests.test_verify_cli -v
```

Expected: import failures.

- [ ] **Step 3: Implement exact command surfaces**

```text
ledger-record init --output PATH [--ledger-id ID] --evidence-label LABEL
ledger-record append --ledger PATH --event-type TYPE --actor-type TYPE --actor-id ID --payload-file FILE [--reference EVENT_ID ...]
ledger-record attach --ledger PATH --file FILE --media-type TYPE [--description TEXT]
ledger-record close --ledger PATH --close-reason complete|security_rejected|aborted

ledger-verify --ledger PATH [--require-sealed] [--expected-root HASH | --expected-root-file FILE] [--format json|text]
```

- [ ] **Step 4: Run tests and help commands**

```bash
PYTHONPATH=src python -m unittest tests.test_record_cli tests.test_verify_cli -v
PYTHONPATH=src python -m agent_evidence_ledger.record_cli --help
PYTHONPATH=src python -m agent_evidence_ledger.verify_cli --help
```

Expected: tests and help commands pass.

- [ ] **Step 5: Commit milestone 2**

```bash
git add src/agent_evidence_ledger/record_cli.py src/agent_evidence_ledger/verify_cli.py tests/test_record_cli.py tests/test_verify_cli.py
git commit -m "feat: add ledger record and verification commands"
```

## Milestone 3 — Disclosure and reproducible evidence

### Task 8: Generate deterministic valid, tampered and replacement ledgers

**Files:**
- Create: `fixtures/scenarios.json`
- Create: `scripts/generate_reference_ledgers.py`
- Create: `reference_ledgers/`
- Create: `tests/test_reference_ledgers.py`
- Create: `tests/test_fixture_regeneration.py`

**Interfaces:**
- Produces every valid and invalid fixture named in the design plus `reference_ledgers/expected_outcomes.json` and an external checkpoint file.

- [ ] **Step 1: Write exact fixture expectation tests**

Assert at minimum:

```python
self.assertEqual(outcomes["valid_verified"]["assurance_level"], "INTERNAL_CHAIN_VALID")
self.assertEqual(outcomes["tampered_payload"]["assurance_level"], "INVALID")
self.assertEqual(outcomes["replacement_chain_internal"]["assurance_level"], "INTERNAL_CHAIN_VALID")
self.assertEqual(outcomes["replacement_chain_checkpoint"]["error_code"], "EXPECTED_ROOT_MISMATCH")
```

- [ ] **Step 2: Run and confirm missing evidence files**

```bash
PYTHONPATH=src python -m unittest tests.test_reference_ledgers tests.test_fixture_regeneration -v
```

Expected: file-not-found failures.

- [ ] **Step 3: Implement the deterministic generator**

Build valid ledgers only through public writer APIs with fixed IDs and clocks. Create invalid integrity fixtures by mutating copied bytes or structured copies. Create invalid lifecycle fixtures with a test-only raw fixture builder, never by weakening the public writer. Record expected assurance/error outcomes canonically.

- [ ] **Step 4: Regenerate and compare every byte**

```bash
rm -rf /tmp/ael-reference
PYTHONPATH=src python scripts/generate_reference_ledgers.py --output /tmp/ael-reference
PYTHONPATH=src python -m unittest tests.test_fixture_regeneration -v
```

Expected: recursive path sets, byte lengths and SHA-256 digests match the source-controlled references.

- [ ] **Step 5: Commit deterministic evidence**

```bash
git add fixtures scripts/generate_reference_ledgers.py reference_ledgers tests/test_reference_ledgers.py tests/test_fixture_regeneration.py
git commit -m "test: add deterministic evidence ledger fixtures"
```

### Task 9: Implement safe disclosure and invalid diagnostics

**Files:**
- Create: `src/agent_evidence_ledger/export.py`
- Create: `src/agent_evidence_ledger/export_cli.py`
- Create: `tests/test_export.py`
- Create: `tests/test_export_cli.py`

**Interfaces:**
- Produces: `DisclosureExporter.export(source, output, diagnostic_invalid=False) -> Path` and `ledger-export`.

- [ ] **Step 1: Write fail-closed and payload-free diagnostic tests**

Normal export of `tampered_payload` must raise `ChainIntegrityError`. Diagnostic export must set `bundle_type` to `INVALID_SOURCE_DIAGNOSTIC`, include error metadata and contain no key named `payload` and no artifact bytes.

- [ ] **Step 2: Run and confirm missing exporter**

```bash
PYTHONPATH=src python -m unittest tests.test_export tests.test_export_cli -v
```

Expected: import failures.

- [ ] **Step 3: Implement allowlisted bundles**

Valid disclosure includes safe envelope fields, reference links, selected safe payload fields, assurance/root/checkpoint metadata, artifact digest metadata and omitted field paths. Diagnostic invalid disclosure contains only error codes, safe positions/types, non-sensitive digest metadata and the claims warning.

Command:

```text
ledger-export --ledger PATH --output PATH [--diagnostic-invalid] [--format json|text]
```

- [ ] **Step 4: Run export tests and CLI help**

```bash
PYTHONPATH=src python -m unittest tests.test_export tests.test_export_cli -v
PYTHONPATH=src python -m agent_evidence_ledger.export_cli --help
```

Expected: all pass.

- [ ] **Step 5: Commit milestone 3**

```bash
git add src/agent_evidence_ledger/export.py src/agent_evidence_ledger/export_cli.py tests/test_export.py tests/test_export_cli.py
git commit -m "feat: export safe ledger disclosure bundles"
```

## Milestone 4 — Employer-facing release

### Task 10: Build the dependency-free evidence viewer

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`
- Create: `web/data/valid.json`
- Create: `web/data/tampered.json`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes only Task 9 disclosure bundles.
- Makes no external request.

- [ ] **Step 1: Write static claims and accessibility tests**

Tests require `Prove the trace, not the claim`, an explicit statement that a valid chain does not prove every fact true, semantic landmarks, `aria-live`, `:focus-visible`, reduced-motion CSS, no `https://` references and no unqualified `immutable` or `trusted agent` language.

- [ ] **Step 2: Run and confirm missing web files**

```bash
PYTHONPATH=src python -m unittest tests.test_web -v
```

Expected: file-not-found failures.

- [ ] **Step 3: Implement the viewer**

Above the fold show bundle type, assurance, final decision, valid-versus-tampered selection and the distinction between source report, independent observation and verification decision. Add keyboard-operable timeline navigation, reference links, a hash ribbon, artifact metadata, invalid-fixture explanations and the observer-label limitation. Provide useful static and `<noscript>` content.

- [ ] **Step 4: Run static tests and visually review desktop and 390 px layouts**

```bash
PYTHONPATH=src python -m unittest tests.test_web -v
python -m http.server 8000 --directory web
```

Expected: no horizontal overflow, external assets, missing labels or unsupported claims.

- [ ] **Step 5: Commit the viewer**

```bash
git add web tests/test_web.py
git commit -m "feat: add evidence ledger inspection viewer"
```

### Task 11: Add public documentation, release verification and CI

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
- `scripts/verify_release.py` is the single local and CI release gate.
- Pages publishes only `web/`.

- [ ] **Step 1: Write documentation boundary tests**

Require the headline, deterministic-fixture label, cryptographic limitations, two-minute reproduction, detected tamper table and authorship statement. Reject `legally immutable`, generic `trusted`, compliance claims and external-model claims.

- [ ] **Step 2: Run and confirm missing documentation**

```bash
PYTHONPATH=src python -m unittest tests.test_documentation -v
```

Expected: missing README.

- [ ] **Step 3: Implement the release gate and workflows**

`verify_release.py` compiles source/tests/scripts, runs all tests, regenerates references into a temporary directory, compares every byte, executes all three module CLIs, checks exact valid/invalid/checkpoint outcomes, compares web data with fresh exports, scans for common credential patterns and checks forbidden public wording.

CI uses Python 3.10, 3.11, 3.12 and 3.13 with `fail-fast: false`. Each job:

```bash
python -m pip install --upgrade pip setuptools wheel build
python -m pip install --editable .
python scripts/verify_release.py
python -m build --wheel
```

Then it creates a clean secondary environment, installs only the wheel, runs the full tests from outside the source tree, invokes all three installed commands and runs `pip check`.

- [ ] **Step 4: Run the complete source gate**

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel build
python -m pip install --editable .
python scripts/verify_release.py
```

Expected: all checks pass.

- [ ] **Step 5: Commit release documentation and automation**

```bash
git add README.md RESULTS.md THREAT_MODEL.md docs scripts/verify_release.py .github/workflows tests/test_documentation.py LICENSE
git commit -m "docs: prepare evidence ledger employer release"
```

### Task 12: Verify source, wheel, archive and public release

**Files:**
- Modify only defects revealed by verification.
- Produce release ZIP, wheel and checksum records outside the repository.

- [ ] **Step 1: Run the first complete source and wheel build**

```bash
rm -rf build dist src/*.egg-info
python scripts/verify_release.py
python -m build --wheel
```

Expected: source gate passes and exactly one `agent_evidence_ledger-0.1.0-py3-none-any.whl` exists.

- [ ] **Step 2: Run a clean-wheel clarification pass**

Create a new environment, install only the wheel, change the working directory outside the repository, run every test against the installed package, run `ledger-record --help`, `ledger-verify --help`, `ledger-export --help` and `pip check`. Confirm no editable-source fallback.

- [ ] **Step 3: Freeze and independently retest the downloadable archive**

Create a clean ZIP excluding `.git`, environments, caches, build output and temporary ledgers. Extract it elsewhere, repeat source verification, rebuild a wheel from the extracted copy, install into another clean environment and repeat the wheel pass. Record ZIP and rebuilt-wheel SHA-256 values.

- [ ] **Step 4: Publish through a reviewed standalone GitHub PR**

Create `Luca-1304/agent-evidence-ledger`, publish the exact verified tree on a release branch, open a PR, inspect the complete diff, run the Python 3.10–3.13 matrix, repair any shared failure once, rerun the whole matrix and squash-merge the verified head. Deploy only `web/` through Pages.

- [ ] **Step 5: Verify the public result**

Confirm the default branch contains source, reference ledgers and external checkpoint; all four jobs passed; Pages loads without external assets; no bootstrap/transfer workflow remains; README links resolve; public claims match the specification; and issue #4 records the design, review, implementation, CI and release evidence.

- [ ] **Step 6: Tag only after final proof**

```bash
git tag -a v0.1.0 -m "Agent Evidence Ledger v0.1.0"
git push origin v0.1.0
```

## Plan self-review

### Spec coverage

- Canonical data, hashes, schema, references, approval chain and lifecycle: Tasks 1–4.
- Locking, append persistence, artifacts, closure, manifest and checkpoint: Tasks 5–6.
- Recording and verification commands: Task 7.
- Valid, tampered, lifecycle-invalid and replacement fixtures: Task 8.
- Separate disclosure and invalid diagnostic mode: Task 9.
- Employer viewer and accessibility: Task 10.
- Claims boundary, authorship, methodology, CI and Pages: Task 11.
- Source, wheel, archive, matrix and standalone publication: Task 12.

### Placeholder scan

No `TBD`, `TODO`, “implement later”, unnamed validation step or generic error-handling instruction remains.

### Type and transition consistency

- Assurance values are consistently `OPEN_CHAIN_VALID`, `INTERNAL_CHAIN_VALID`, `EXPECTED_ROOT_MATCHED`, `INVALID`.
- Public services are consistently `LedgerWriter`, `LedgerVerifier`, `DisclosureExporter`.
- The state machine explicitly requires proposal, authorisation, attempt and one decision; no tool attempt can bypass approval.
- Recoverable decisions return to `CONTRACTED` only through `recovery_authorized` and require a fresh proposal/authorisation.
- Sealed artifacts consistently use digest-only paths.
- Invalid viewer bundles consistently use `INVALID_SOURCE_DIAGNOSTIC`.
- Release commands install `build` before `python -m build`.

The corrected plan is approved for execution in this order.