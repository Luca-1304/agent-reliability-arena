# Chained Transport Ledger Schema v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every new transport ledger use cryptographically chained record schema `"2"` while preserving complete verification and continuation of non-empty legacy schema-1 ledgers without rewriting historical bytes.

**Architecture:** Keep all schema logic inside `transports/recording.py`. Add a private verified-ledger state object so one parse yields schema, counts and final digest. The existing concurrent commit lock remains authoritative for sequence and predecessor selection, while the existing Windows/Linux workflow proves the new chain under threads and spawned processes.

**Tech Stack:** Python 3.10–3.13 standard library, SHA-256 via existing canonical digest helper, JSONL, `unittest`, existing GitHub Actions.

## Global Constraints

- New or empty ledgers default to schema `"2"`.
- Non-empty schema-1 ledgers remain schema `"1"` and are never rewritten or silently upgraded.
- Non-empty schema-2 ledgers remain schema `"2"`.
- A ledger may never mix schema versions.
- Schema 2 adds exactly `previous_record_digest`.
- Sequence 1 uses `previous_record_digest: null`; every later schema-2 record points to the immediately prior `record_digest`.
- Provider/model calls remain outside the ledger lock.
- No migration command, runtime dependency, provider change, publication authority, Git mutation authority, branch deletion or empirical claim is added.
- Public verifier summary keeps the existing fields and reports the actual schema version.
- Merge requires the exact PR head to finish every existing required workflow with zero genuine failures/cancellations.

---

### Task 1: Establish schema-2 and legacy-v1 test contracts

**Files:**
- Modify: `tests/test_transport_ledger.py`
- Create: `tests/test_transport_ledger_schema_v2.py`

**Interfaces:**
- Consumes: `RecordingTransport`, `verify_transport_ledger`, `canonical_json_sha256`.
- Produces: explicit default-v2, chain-integrity, mixed-schema and legacy-v1 compatibility tests.

- [ ] **Step 1: Change the default-ledger expectation to schema 2**

Update the existing success test so a new ledger must contain:

```python
self.assertEqual(row["schema_version"], "2")
self.assertIsNone(row["previous_record_digest"])
```

Keep the existing record-digest assertion so `previous_record_digest` is covered by the digest.

- [ ] **Step 2: Add a two-record chain test**

Write two records, parse both rows and require:

```python
self.assertEqual(rows[1]["previous_record_digest"], rows[0]["record_digest"])
self.assertEqual(verify_transport_ledger(ledger)["schema_version"], "2")
```

- [ ] **Step 3: Add an independent legacy schema-1 fixture builder**

In `tests/test_transport_ledger_schema_v2.py`, build schema-1 rows directly from the documented old field set and `canonical_json_sha256`, rather than using new production record-building code.

- [ ] **Step 4: Prove unchanged v1 verification and continuation**

Write a valid one-record v1 fixture, preserve its original bytes, open `RecordingTransport` on it, append one call, then require:

```python
self.assertTrue(ledger.read_bytes().startswith(original_bytes))
self.assertEqual([row["schema_version"] for row in rows], ["1", "1"])
self.assertNotIn("previous_record_digest", rows[1])
```

- [ ] **Step 5: Add fail-closed schema tests**

Cover unknown schema, mixed v1/v2 rows, non-null schema-2 genesis, wrong previous digest, middle deletion and record reordering.

- [ ] **Step 6: Keep RED evidence off PR**

Before production changes, these tests describe behavior the current schema-1-only writer cannot satisfy. No PR is opened until the implementation is expected green.

---

### Task 2: Add one internal verified-ledger state and dual-schema verification

**Files:**
- Modify: `src/agent_reliability_arena/transports/recording.py`
- Test: `tests/test_transport_ledger.py`
- Test: `tests/test_transport_ledger_schema_v2.py`

**Interfaces:**
- Produces private `_LedgerState` containing `schema_version`, `records`, `results`, `errors`, `ledger_sha256`, `last_record_digest`.
- Public `verify_transport_ledger(...)` return shape remains unchanged.

- [ ] **Step 1: Define schema constants and exact key sets**

Use:

```python
LEGACY_SCHEMA_VERSION = "1"
SCHEMA_VERSION = "2"
_SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}
_RECORD_KEYS_V1 = {...existing keys...}
_RECORD_KEYS_V2 = _RECORD_KEYS_V1 | {"previous_record_digest"}
```

- [ ] **Step 2: Add private immutable ledger state**

```python
@dataclass(frozen=True)
class _LedgerState:
    schema_version: str
    records: int
    results: int
    errors: int
    ledger_sha256: str
    last_record_digest: str

    def to_summary(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "records": self.records,
            "results": self.results,
            "errors": self.errors,
            "ledger_sha256": self.ledger_sha256,
        }
```

- [ ] **Step 3: Make record validation schema-aware**

`_validate_record(...)` must receive the expected ledger schema and expected predecessor digest. It must enforce exact field shape and current semantic checks for both formats.

For schema 2:

```python
if line_number == 1:
    if row.get("previous_record_digest") is not None:
        raise ValueError(...)
elif row.get("previous_record_digest") != expected_previous_digest:
    raise ValueError(...)
```

- [ ] **Step 4: Parse once into `_LedgerState`**

Create `_inspect_transport_ledger_unlocked(path)` that reads the file, determines schema from line 1, rejects unsupported/mixed versions, validates every row, tracks the previous record digest and returns `_LedgerState`.

- [ ] **Step 5: Preserve public verifier shape**

Make `_verify_transport_ledger_unlocked(path)` return `_inspect_transport_ledger_unlocked(path).to_summary()` and keep public locking unchanged.

- [ ] **Step 6: Run focused schema tests**

Expected: dual-schema verification, mixed-schema rejection and chain-tamper tests pass.

---

### Task 3: Default new commits to schema 2 without upgrading historical v1 ledgers

**Files:**
- Modify: `src/agent_reliability_arena/transports/recording.py`
- Test: `tests/test_transport_ledger.py`
- Test: `tests/test_transport_ledger_schema_v2.py`

**Interfaces:**
- `_record(..., schema_version: str, previous_record_digest: str | None, ...) -> dict[str, object]`
- `_commit_record(...)` selects schema under the existing exclusive ledger lock.

- [ ] **Step 1: Make record construction conditional on schema**

Build all common fields once. Add `previous_record_digest` only when `schema_version == "2"`.

- [ ] **Step 2: Select schema under the transaction lock**

Inside `_commit_record`:

```python
if ledger missing/empty:
    schema_version = "2"
    sequence = 1
    previous_record_digest = None
else:
    state = _inspect_transport_ledger_unlocked(self.ledger_path)
    schema_version = state.schema_version
    sequence = state.records + 1
    previous_record_digest = (
        state.last_record_digest if schema_version == "2" else None
    )
```

- [ ] **Step 3: Never put the new field on v1 rows**

Legacy continuation must preserve the exact old record shape.

- [ ] **Step 4: Preserve constructor fail-closed verification**

A non-empty existing ledger must still fully verify before the recorder is accepted.

- [ ] **Step 5: Run old + new ledger tests**

Expected: all `test_transport_ledger*.py` tests pass.

---

### Task 4: Extend concurrency proof to chain continuity

**Files:**
- Modify: `tests/test_transport_ledger_concurrency.py`

**Interfaces:**
- Consumes default schema-2 `RecordingTransport`.

- [ ] **Step 1: Add reusable chain assertion**

```python
def assert_schema2_chain(testcase, rows):
    testcase.assertTrue(rows)
    testcase.assertIsNone(rows[0]["previous_record_digest"])
    for previous, current in zip(rows, rows[1:]):
        testcase.assertEqual(current["previous_record_digest"], previous["record_digest"])
```

- [ ] **Step 2: Apply it to threaded writers**

After exact `1..N` sequence checks, require all rows are schema 2 and the chain is continuous.

- [ ] **Step 3: Apply it to spawned-process mixed outcomes**

Require the same chain across result/error records and after the `N+1` continuation write.

- [ ] **Step 4: Preserve provider parallelism, lock timeout, malformed-tail and symlink tests**

Do not weaken or replace any existing concurrency safety assertion.

- [ ] **Step 5: Rely on the existing cross-platform workflow**

The already-reviewed `Concurrent Evidence Ledger` workflow will run the expanded `test_transport_ledger*.py` suite on Ubuntu and Windows, Python 3.10 and 3.13. No second workflow is added.

---

### Task 5: Align status documentation without overclaiming

**Files:**
- Modify: `ROADMAP.md`
- Modify only if useful: `README.md`

**Interfaces:**
- Documentation must distinguish concurrent-ledger capability from record schema 2.

- [ ] **Step 1: Update Stage 2 wording**

State that new private transport ledgers use chained schema 2 while legacy schema-1 ledgers remain verifiable/continuable without migration.

- [ ] **Step 2: State claim limitation**

Document that chain continuity does not replace externally committed whole-ledger SHA/evidence indexes and does not alone detect a consistently rewritten ledger or valid-looking suffix truncation.

- [ ] **Step 3: Avoid release/version confusion**

Do not rename package version or Concurrent Evidence Ledger v2.

---

### Task 6: Pre-PR and full exact-head verification

**Files:**
- No new production files expected.

- [ ] **Step 1: Review diff scope**

Expected scope: recording implementation, ledger tests, schema-compatibility tests, concurrency assertions, approved spec/plan and minimal status documentation only.

- [ ] **Step 2: Run the strongest available off-PR checks**

Canonical full-checkout command remains:

```bash
python scripts/ci/pre_pr_green_gate.py --root . --output <report-path>
```

If this chat cannot materialize the complete checkout, do not invent a local pass; use focused executable evidence where available and treat the full PR matrix as repository-level authority.

- [ ] **Step 3: Open one PR only when candidate is expected green**

No intentional RED PR history.

- [ ] **Step 4: Require every PR workflow family to complete successfully**

This includes the focused Windows/Linux ledger matrix, tests, Fast, Specialist, Deep, CodeQL, history and Pages verification. Intentional failure-only/publication skips remain acceptable.

- [ ] **Step 5: Inspect required jobs, branch freshness and review threads**

Require exact head unchanged, branch behind `main` = 0, no unresolved review threads and no unexplained failed/cancelled required job.

- [ ] **Step 6: Squash merge with expected-head guard**

Verify resulting `main` equals the merge SHA. Preserve the feature/evidence branch unless separately authorized for destructive cleanup.