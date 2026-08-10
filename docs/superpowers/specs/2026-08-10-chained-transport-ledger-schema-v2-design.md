# Chained Transport Ledger Schema v2 — Design

Date: 2026-08-10
Status: approved for implementation
Scope: provider-free private transport evidence
Base: Concurrent Evidence Ledger capability already merged in PR #104

## Naming boundary

Two different uses of “v2” now exist and must not be conflated:

- **Concurrent Evidence Ledger v2** is the already-merged Windows/Linux concurrency capability.
- **Transport ledger record schema `"2"`** is the new record format designed here.

Documentation, tests and code should use “schema 1 / schema 2” when discussing record format and “concurrent ledger” when discussing locking/concurrency.

## Purpose

Strengthen continuity of newly recorded private transport evidence by cryptographically linking each schema-2 record to the immediately preceding record while preserving all historical schema-1 ledgers exactly as schema 1.

This change does not migrate, rewrite, re-sign, truncate or otherwise alter historical ledger bytes.

## Core compatibility rule

1. A missing or zero-length ledger is treated as new and begins with schema `"2"`.
2. A non-empty existing schema-1 ledger remains schema `"1"` for all subsequent appends to that ledger.
3. A non-empty existing schema-2 ledger remains schema `"2"` for all subsequent appends.
4. One ledger may never mix schema versions.
5. Public verification supports complete schema-1 and complete schema-2 ledgers.
6. No automatic or in-place migration from schema 1 to schema 2 exists.
7. No public option is added merely to create new schema-1 ledgers.

The practical result is: **old evidence stays old; new evidence gets the stronger format.**

## Schema 1

Schema 1 remains byte-compatible with the current record contract:

- `schema_version`
- `sequence`
- `recorded_at`
- `provider`
- `request`
- `request_digest`
- `outcome_type`
- `result`
- `error`
- `record_digest`

Its existing digest, semantic validation, sequence validation, concurrency locking and fail-closed behavior remain supported.

## Schema 2

Schema 2 adds exactly one record field:

- `previous_record_digest`

All existing schema-1 fields remain otherwise unchanged.

### Genesis record

For sequence `1`:

- `schema_version == "2"`
- `previous_record_digest is null`

The null genesis marker is part of the unsigned record and therefore covered by `record_digest`.

### Later records

For sequence `N > 1`:

- `previous_record_digest` must be a non-empty string;
- it must exactly equal the `record_digest` stored on sequence `N - 1`.

The link is part of record `N` before its own `record_digest` is calculated.

Thus:

`digest(N) = SHA256(canonical_json(unsigned_record_N including previous_record_digest))`

and:

`previous_record_digest(N) = digest(N-1)`.

## Verification model

The verifier reads the complete ledger under the existing cooperative ledger lock.

1. Parse line 1 and determine its schema version.
2. Require the first schema to be supported (`"1"` or `"2"`).
3. Require every later row to use exactly the same schema.
4. Apply the existing exact sequence, timestamp, request digest, record digest and result/error semantic checks.
5. For schema 2 only, validate genesis/null and every previous-record link.
6. Reject any mixed, malformed, unknown-schema, reordered or broken-chain ledger.

The summary preserves the existing stable fields:

- `schema_version`
- `records`
- `results`
- `errors`
- `ledger_sha256`

`schema_version` reports the actual ledger schema. No extra summary field is required for the chain head in this change because the final record already contains its digest and the complete ledger SHA remains the external whole-file commitment.

## Recording model

`RecordingTransport` does not expose schema selection as a normal caller choice.

At construction/commit time:

- if the ledger is missing or empty, the recorder selects schema 2;
- if the ledger is non-empty, full verification determines and fixes that ledger's existing schema;
- commit re-verifies while holding the existing transaction lock before deriving sequence and previous digest.

### New schema-2 commit

Inside the existing exclusive ledger lock:

1. validate ledger and lock paths;
2. if empty/missing, choose schema 2, sequence 1, previous digest `null`;
3. if non-empty, fully verify the existing ledger;
4. derive the existing ledger schema and sequence `records + 1`;
5. for schema 2, read the immediately previous row's validated `record_digest` and use it as `previous_record_digest`;
6. construct the unsigned record;
7. compute `record_digest`;
8. append one canonical JSON line;
9. `fsync` before releasing the lock.

Provider/model calls remain outside the lock exactly as in the concurrent-ledger design.

## Historical schema-1 continuation

A recorder opened on a valid non-empty schema-1 ledger may append another schema-1 record. This is necessary for safe continuation of an already-started historical run and avoids mixing or silently upgrading its evidence contract.

The old rows are never rewritten. The new continuation row follows the original schema-1 shape and digest rules.

An empty file has no historical schema and therefore starts schema 2.

## Security and evidence claims

Schema 2 improves detection of:

- record reordering;
- middle-record deletion;
- substitution of one record without re-signing the dependent suffix;
- recomputation of an isolated modified record digest without updating the chain that follows it;
- accidental discontinuity between adjacent records.

Schema 2 does **not** by itself prove immutability against an attacker able to rewrite and re-digest the entire ledger consistently.

The repository's existing whole-ledger SHA-256 commitments and immutable evidence-set/index mechanisms remain necessary external anchors. A valid internal chain plus an externally committed ledger digest is stronger than either mechanism alone.

Suffix truncation can also remain internally well-formed; external expected counts/digests are required to detect that class of loss. Do not claim otherwise.

## Failure behavior

All existing fail-closed rules remain:

- unknown schema: reject;
- mixed schemas: reject;
- invalid record shape: reject;
- incorrect genesis marker: reject;
- previous digest mismatch: reject;
- sequence mismatch: reject;
- record/request digest mismatch: reject;
- semantic result/error mismatch: reject;
- malformed/partial tail: reject;
- lock timeout: reject without appending;
- symlink or unsafe path: reject.

No automatic repair, truncation, migration or chain reconstruction is permitted.

## Concurrency interaction

Schema 2 reuses the already-merged cross-platform commit lock.

The sequence decision and previous-digest decision are made together inside the same transaction lock. Therefore concurrent writers cannot legitimately select the same predecessor or sequence.

The focused Concurrent Evidence Ledger workflow remains the cross-platform proof surface:

- Ubuntu / Python 3.10
- Ubuntu / Python 3.13
- Windows / Python 3.10
- Windows / Python 3.13

No new GitHub workflow is needed unless implementation evidence shows the existing focused workflow cannot express the schema-2 contract.

## Test contract

The implementation is incomplete until tests prove at least:

1. a new ledger defaults to schema 2;
2. schema-2 record 1 has `previous_record_digest: null`;
3. record 2 points exactly to record 1's digest;
4. a multi-record schema-2 chain verifies;
5. modifying one prior record and recomputing only that record's digest breaks the next link;
6. reordering schema-2 records is rejected;
7. middle-record deletion is rejected;
8. mixed schema-1/schema-2 rows are rejected;
9. unsupported schema is rejected;
10. an existing schema-1 fixture still verifies unchanged;
11. a recorder continuing a non-empty schema-1 ledger appends schema 1 without rewriting prior bytes;
12. an existing schema-2 ledger reopens and continues its chain correctly;
13. concurrent thread writers produce exact sequence and chain continuity;
14. spawned-process writers produce exact sequence and chain continuity;
15. mixed successful results and `TransportError` records remain chained correctly;
16. malformed tails and lock timeouts remain fail-closed;
17. all pre-existing transport-ledger tests remain meaningful, with legacy-v1 expectations moved into explicit legacy fixtures rather than silently deleted;
18. source, packaging, release, Fast, Specialist, Deep, CodeQL, history, Pages verification and focused Windows/Linux ledger CI finish with zero genuine failures on the exact PR head before merge.

## Repository/documentation effects

Expected implementation scope:

- modify `src/agent_reliability_arena/transports/recording.py`;
- modify `tests/test_transport_ledger.py`;
- modify `tests/test_transport_ledger_concurrency.py`;
- add focused schema compatibility tests if separation improves clarity;
- update `ROADMAP.md` / README status text only after verified behavior exists and only enough to state the stronger evidence format accurately.

No runtime dependency, provider adapter, publication workflow, Git authority, branch policy, API credential handling or public empirical claim changes are in scope.

## Acceptance rule

Use the established process:

`implement off-PR → pre-PR evidence expected green → one PR → exact-head full matrix → zero genuine failures/cancellations → squash merge with expected-head guard`.

Do not merge merely because schema-specific tests pass. The normal repository matrix remains final integration authority.