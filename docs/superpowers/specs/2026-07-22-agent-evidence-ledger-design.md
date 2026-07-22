# Agent Evidence Ledger — Standalone v0.1.0 Design

Date: 2026-07-22  
Tracking issue: #4  
Status: Approved direction; implementation planning gated on written-spec review

## Purpose

Build a separate employer-facing project that records the evidence history of one tool-using agent execution in a portable, append-only and tamper-evident ledger.

The public question is deliberately narrow:

> Can another person determine what an agent was asked to do, what it attempted, what its tools reported, what an independent observer actually found, and whether completion was justified—without trusting the agent's own success claim?

Agent Evidence Ledger does not execute arbitrary agents and does not decide whether an agent is intelligent. It provides a durable evidence format, legal event transitions, integrity verification, deterministic tamper fixtures and a read-only viewer.

The project is complementary to, but technically distinct from:

- **Agent Completion Verifier**, which evaluates whether evidence satisfies a completion contract;
- **Agent Reliability Arena**, which compares orchestration strategies under identical evidence rules;
- **Agent Evidence Ledger**, which preserves ordered audit history and exposes whether that history has been altered or is logically impossible.

Primary public line:

> **Prove the trace, not the claim.**

Supporting line:

> A tamper-evident evidence ledger for tool-using agents, with independently classified observations and verifiable state transitions.

## Employer-facing value

The project should demonstrate:

- a stable evidence protocol rather than prose logs;
- explicit separation of claims, source reports, independent observations and decisions;
- deterministic canonical representation before hashing;
- append persistence with crash and cooperative-concurrency handling;
- detection of deletion, insertion, reordering, mutation and truncation;
- legal lifecycle transitions encoded as executable invariants;
- honest explanation of cryptographic limits;
- reproducible command-line and browser inspection;
- untrusted handling of model and tool output.

## Approaches considered

### Hosted audit service

A central service offers convenient team access and potentially stronger identity and timestamp controls, but hosting, authentication, billing and operational security would dominate the first release. It would also make the result harder to reproduce offline.

### Signed SQLite ledger

SQLite provides transactions and efficient queries, and signatures could later support stronger identity assertions. The first release would nevertheless become entangled with key generation, custody, rotation and revocation. A binary database is also less transparent for a compact public demonstration.

### Portable hash-chained event ledger — selected

Use canonical newline-delimited JSON events in a local ledger directory. Each event includes the previous event hash and its own SHA-256 digest. A final seal records the root and event count. Verification can optionally require an expected root retained outside the ledger directory.

This route is readable, deterministic, dependency-light and easy to inspect. It can later gain signatures or external anchoring without changing event semantics.

Its limitations are explicit:

- chaining does not prove who authored an event;
- an attacker controlling the complete ledger and all local seals can recompute a valid replacement chain;
- detecting complete replacement requires an independently retained expected root;
- local timestamps do not prove trusted wall-clock time.

## v0.1.0 scope

One ledger directory represents one agent execution trace for one completion contract.

Included:

- a versioned event schema;
- a deterministic canonical JSON subset;
- SHA-256 event chaining with domain separation;
- typed actors and evidence classes;
- legal transition validation;
- exclusive append locking, flush and filesystem synchronisation;
- content-addressed artifact references;
- a final seal and optional expected-root verification;
- `ledger-record`, `ledger-verify` and `ledger-export`;
- deterministic valid and tampered fixtures;
- a dependency-free static viewer;
- Python 3.10–3.13 source and clean-wheel verification.

Deferred:

- multiple tasks in one stream;
- network replication or hosted storage;
- user accounts;
- public-key signatures;
- trusted timestamp authorities;
- hardware-backed keys;
- Merkle-tree transparency services;
- legal non-repudiation;
- arbitrary tool execution.

“Append-only” in v0.1.0 means the supported writer only appends and refuses altered histories. It does not mean the underlying filesystem is physically immutable.

## Threat model

### Protected properties

The verifier should detect, within the supplied ledger directory:

- event content mutation;
- event deletion, insertion or reordering;
- duplicate or skipped sequence numbers;
- duplicate event identifiers;
- broken previous-hash references;
- truncated or partially written events;
- malformed or non-canonical encoding;
- artifact byte changes;
- seal or event-count disagreement;
- impossible lifecycle transitions;
- a final root differing from an externally supplied expected root.

### Adversaries considered

- accidental edits;
- broken logging integrations;
- misleading success-shaped tool or model output;
- selective removal or rearrangement before sharing;
- incomplete transfer;
- process interruption during append;
- cooperative concurrent writers;
- a malicious local editor who does not control an external checkpoint.

### Adversaries not defeated by v0.1.0 alone

- complete replacement of the ledger, seal and every locally stored checkpoint;
- host compromise before observation;
- forged actor labels without signatures;
- a dishonest independent observer;
- inaccurate system time;
- operating-system compromise below the writer;
- deletion of the entire directory.

A valid chain proves consistency of the supplied history under this threat model. It does not prove that every reported fact is true.

## Ledger and disclosure layout

The sealed source ledger is self-contained:

```text
<ledger-id>/
  ledger.jsonl
  seal.json
  manifest.json
  artifacts/
    <sha256>.<extension>
```

`ledger.jsonl` is the canonical event stream.

`seal.json` records the final event hash, count, ledger identifier, schema and writer versions, and close status. It is useful for transport and checkpointing but is not independently trustworthy when stored only beside the ledger.

`manifest.json` records the SHA-256 digest and byte length of every retained source-ledger file except itself. It is generated only after closure.

A disclosure bundle is always written to a separate output directory:

```text
<disclosure-output>/
  disclosure.json
  disclosure-manifest.json
  viewer/
```

`ledger-export` never writes inside the sealed source ledger. This prevents a public export from invalidating or mutating the source manifest.

## Canonical data profile

The first release defines a narrow canonical JSON subset rather than claiming full RFC 8785 compatibility.

Rules:

- UTF-8 without a byte-order mark;
- object keys sorted lexicographically by Unicode code point;
- compact separators and no insignificant whitespace;
- strings normalized to Unicode NFC;
- integers only; floats, NaN and Infinity rejected;
- booleans and `null` permitted;
- duplicate keys rejected during parsing;
- arrays preserve source order;
- unknown top-level fields rejected for schema version `1`;
- each ledger line must exactly equal the canonical serialization of its decoded event;
- the ledger line ends in `\n`, which is not part of the event hash.

The standard library can implement this profile consistently across Python 3.10–3.13 with explicit parsing and validation.

## Hash construction

Each event is hashed after all fields except `event_hash` are populated.

```text
canonical_event = canonical_json(event_without_event_hash)

event_hash = SHA256(
  UTF8("agent-evidence-ledger:event:v1\n")
  || UTF8(canonical_event)
)
```

The genesis event uses sixty-four zeroes as `previous_hash`. Every later event must reference the immediately preceding event hash.

Artifact bytes use raw SHA-256. Other structured hash objects use separate documented domain prefixes.

## Event envelope

Every event contains:

```json
{
  "schema_version": "1",
  "ledger_id": "led_...",
  "sequence": 0,
  "event_id": "evt_000000",
  "event_type": "ledger_opened",
  "recorded_at": "2026-07-22T10:00:00Z",
  "actor": {
    "actor_id": "writer",
    "actor_type": "orchestrator"
  },
  "evidence_class": "context",
  "references": [],
  "payload": {},
  "previous_hash": "0000...0000",
  "event_hash": "abcd..."
}
```

### Identifiers

- `ledger_id` is caller-supplied or generated from UUIDv4 with prefix `led_`;
- deterministic fixtures inject fixed identifiers;
- `event_id` is `evt_` followed by the zero-padded sequence;
- sequence starts at zero and increments by exactly one;
- identifiers cannot be reused within a ledger.

### Timestamps

- RFC 3339 UTC with `Z` suffix;
- non-decreasing;
- generated through an injectable clock;
- informational unless provided by an independently trusted time source;
- clock regression is invalid, but a valid timestamp is not proof of real-world time.

### Actor types

Allowed actor labels:

- `user`;
- `agent`;
- `orchestrator`;
- `operator`;
- `tool`;
- `observer`;
- `verifier`;
- `system`.

Actor identifiers are labels, not cryptographic identities.

### Evidence classes

- `context` — request, contract or configuration;
- `intent` — proposal, authorisation or recovery plan;
- `source_report` — what an agent or tool says happened;
- `independent_observation` — state measured outside the reporting source;
- `decision` — verification, policy or closure decision;
- `error` — normalized operational failure.

Source reports can never be silently reclassified as independent observations.

## Event types and invariants

### `ledger_opened`

Sequence zero; exactly once. Declares writer version, schema version, canonical profile, hash algorithm and evidence label.

### `request_received`

Exactly once after opening. Records the user-visible task or a digest-backed artifact reference.

### `contract_declared`

Exactly once after the request and before mutation attempts. Records completion requirements and the independent observation method.

### `action_proposed`

References the contract and records one bounded proposed action.

### `action_authorized`

References exactly one proposal. Authorisation is intent evidence, not proof of execution.

### `tool_attempted`

References a valid authorisation. One authorisation cannot be consumed more times than its declared bounded attempt allowance.

### `tool_reported`

References one attempt and always has evidence class `source_report`.

### `observation_recorded`

References the relevant attempt and always has evidence class `independent_observation`.

Required payload fields:

- observer identifier;
- observation method;
- outcome class;
- observed contract fields;
- artifact references when applicable;
- `matches_contract`;
- `terminal` when security or policy rejection prevents recovery.

### `completion_claimed`

Records whether an agent or synthesiser claims completion and which events it cites. It is legal after an attempt and may precede observation so premature claims can be represented. A claim never changes completion state by itself.

### `verification_decided`

Allowed statuses:

- `VERIFIED_COMPLETE`;
- `PARTIAL`;
- `UNVERIFIED`;
- `FAILED`;
- `SECURITY_REJECTED`.

`VERIFIED_COMPLETE` is legal only when:

- a contract exists;
- a relevant independent observation exists after the latest mutation attempt;
- the latest relevant observation matches the contract;
- no later observation contradicts it;
- referenced artifacts verify;
- the decision references the contract and observation.

A completion claim is not required for independently verified completion, allowing silent success to be represented.

### `recovery_authorized`

References a non-terminal `PARTIAL`, `UNVERIFIED` or `FAILED` decision and states the remaining retry allowance.

Illegal after `VERIFIED_COMPLETE`, `SECURITY_REJECTED` or a terminal observation.

### `error_recorded`

Stores a normalized error class and redacted message. Raw exception objects, secrets and authorization headers are forbidden.

### `ledger_closed`

Exactly once and final. References the final verification decision and repeats the final status plus close reason. No event is legal afterward.

## Lifecycle state machine

```text
NEW
  ↓ ledger_opened
OPEN
  ↓ request_received
REQUESTED
  ↓ contract_declared
CONTRACTED
  ↓ action_proposed → action_authorized → tool_attempted
ATTEMPTED
  ├─ tool_reported
  ├─ completion_claimed
  └─ observation_recorded
OBSERVED
  ↓ verification_decided
DECIDED
  ├─ verified or terminal → ledger_closed
  └─ recoverable → recovery_authorized → action_proposed
CLOSED
```

Non-state-changing events remain legal only inside their attempt window. Event-specific validators should be separate rather than implemented as one monolithic conditional.

## Append semantics

`ledger-record` is the sole supported writer in v0.1.0.

Append procedure:

1. acquire an exclusive lock inside the ledger directory;
2. parse and verify the complete existing stream;
3. validate the proposed event against current lifecycle state;
4. assign sequence, event identifier, previous hash and timestamp;
5. canonicalize and hash;
6. append one UTF-8 line;
7. flush;
8. `fsync` the ledger file;
9. release the lock.

The writer refuses:

- malformed or missing final newline;
- partial final line;
- an already-invalid chain;
- an event after closure;
- lock acquisition timeout;
- forbidden secret-like fields.

The lock coordinates compliant writers. It is not protection against a malicious process that ignores it.

## Artifact handling

Artifacts are content-addressed beneath `artifacts/`.

```json
{
  "sha256": "...",
  "byte_length": 1234,
  "media_type": "application/json",
  "relative_path": "artifacts/<sha256>.json",
  "description": "Independent filesystem observation"
}
```

Verification requires path confinement, regular files only, no symbolic links, correct byte length and matching SHA-256. Duplicate digest references must resolve to identical bytes.

## Seal, manifest and expected root

On closure, `ledger-record close` creates the seal and manifest.

The seal records:

- ledger identifier;
- schema version;
- final event hash;
- event count;
- final status;
- close timestamp;
- writer version;
- canonical profile;
- hash algorithm.

Verification modes:

```bash
ledger-verify --ledger path/to/ledger
ledger-verify --ledger path/to/ledger --expected-root <sha256>
ledger-verify --ledger path/to/ledger --expected-root-file checkpoint.txt
```

Assurance levels:

- `INTERNAL_CHAIN_VALID` — the supplied directory is internally consistent;
- `EXPECTED_ROOT_MATCHED` — internal consistency plus match to an independently retained root;
- `INVALID`.

The CLI must never output a generic “trusted” status.

## Command-line applications

### `ledger-record`

```text
ledger-record init
ledger-record append
ledger-record attach
ledger-record close
```

Machine-readable JSON is the default. `--format text` provides a concise summary.

### `ledger-verify`

Validates parsing, canonical form, sequence, identifiers, chain, lifecycle, references, artifact integrity, seal, manifest and optional expected root.

Exit codes:

- `0` valid;
- `2` invalid chain or evidence;
- `3` malformed input;
- `4` unsupported schema;
- `5` operational error.

### `ledger-export`

Verifies the source ledger and writes a separate reduced disclosure bundle. It uses an explicit allowlist, records omitted field paths and never modifies the source.

Export fails when the source ledger is invalid.

## Python API and package boundaries

Public API:

```python
from agent_evidence_ledger import (
    LedgerWriter,
    LedgerVerifier,
    DisclosureExporter,
    Event,
    VerificationReport,
)
```

Suggested modules:

```text
src/agent_evidence_ledger/
  canonical.py
  events.py
  schemas.py
  state_machine.py
  hashing.py
  artifacts.py
  writer.py
  verifier.py
  seal.py
  export.py
  errors.py
  record_cli.py
  verify_cli.py
  export_cli.py
```

Persistence, lifecycle validation and presentation must remain separate.

## Static viewer

A dependency-free HTML/CSS/JavaScript application reads only `ledger-export` disclosure bundles.

It shows:

- headline and limitations;
- chain status and assurance level;
- final completion status;
- ordered event timeline;
- evidence-class filters;
- reference links between proposals, attempts, reports, observations and decisions;
- a chain ribbon with event and previous hashes;
- explanations for invalid fixtures;
- artifact digest metadata.

The viewer does not verify arbitrary local ledgers in-browser in v0.1.0.

Accessibility requirements:

- semantic structure;
- keyboard-operable navigation;
- visible focus;
- labels in addition to colour;
- sufficient contrast;
- reduced-motion support;
- responsive down to 390 CSS pixels;
- useful static content without JavaScript.

## Deterministic fixtures

### Valid

1. verified completion with matching observation;
2. silent verified completion;
3. recoverable failure followed by one authorised successful retry;
4. terminal security rejection without retry;
5. artifact-backed observation;
6. valid ledger matching an external expected root.

### Invalid integrity

1. edited payload;
2. deleted event;
3. inserted event;
4. reordered events;
5. broken previous hash;
6. duplicate sequence;
7. duplicate event ID;
8. truncated final line;
9. non-canonical line;
10. modified artifact bytes;
11. seal count mismatch;
12. recomputed replacement chain with expected-root mismatch.

### Invalid lifecycle

1. request before opening;
2. attempt without authorisation;
3. source report labelled as independent observation;
4. verified completion without observation;
5. verified completion after later contradiction;
6. recovery after terminal security rejection;
7. retry after verified completion;
8. closure without final decision;
9. event after closure;
10. decision referencing an unrelated attempt.

Fixture labels must distinguish software validation from real agent evidence.

## Error model

Structured errors:

- `CanonicalizationError`;
- `SchemaError`;
- `ChainIntegrityError`;
- `LifecycleError`;
- `ReferenceError`;
- `ArtifactIntegrityError`;
- `SealError`;
- `ExpectedRootMismatch`;
- `LockError`;
- `OperationalError`.

A report includes validity, assurance level, error code, event location where available, non-sensitive expected and actual values, and safe remediation guidance. Stack traces are hidden by default.

Independent problems may be aggregated when safe, but chain-dependent validation stops after integrity can no longer be established.

## Privacy and secret handling

Append-only storage requires filtering before ingestion.

Rules:

- secret-like payload keys rejected by default;
- raw API keys, authorization headers, cookies and passwords forbidden;
- disclosure export uses an allowlist;
- redaction occurs before append or in a separate disclosure bundle, never by rewriting a sealed ledger;
- omitted paths recorded;
- artifact disclosure opt-in;
- fixtures use synthetic data;
- CI scans for common secret patterns.

No GDPR, HIPAA, SOC 2 or legal-record compliance claim is made.

## Claims boundary

v0.1.0 may claim:

- alterations to a supplied chain are detectable under the documented threat model;
- lifecycle-invalid histories are rejected;
- source reports and independent observations remain structurally distinct;
- expected-root comparison detects complete local replacement;
- deterministic fixtures reproduce documented integrity failures.

v0.1.0 may not claim:

- legal non-repudiation;
- authenticated identity;
- trusted time;
- truth of the underlying observation;
- protection against a fully compromised host;
- filesystem immutability;
- protection when every copy and checkpoint is attacker-controlled;
- blockchain or distributed-consensus properties;
- compliance certification;
- external-model performance.

## Repository presentation

The standalone repository should open with:

- the public question;
- a valid-versus-tampered viewer preview;
- a two-minute reproduction;
- exact assurance terminology;
- detected tamper classes;
- architecture and threat model;
- fixture and CI evidence;
- visible limitations;
- authorship and AI-assistance disclosure.

Suggested map:

```text
agent-evidence-ledger/
  .github/workflows/
  docs/
  examples/
  fixtures/
  reference_ledgers/
  scripts/
  src/agent_evidence_ledger/
  tests/
  web/
  LICENSE
  README.md
  RESULTS.md
  THREAT_MODEL.md
  pyproject.toml
```

## Testing strategy

### Unit tests

- canonical JSON and NFC normalization;
- integer-only numeric validation;
- deterministic hashes;
- schema and transition validation;
- actor and evidence-class restrictions;
- references;
- artifact confinement and digest checks;
- seal construction;
- expected-root comparison;
- secret rejection;
- exit-code mapping.

### Integration tests

- complete valid lifecycle;
- recovery lifecycle;
- terminal security lifecycle;
- partial final line after interruption;
- lock contention;
- artifact attachment and closure;
- disclosure export;
- read-only verification;
- fixture regeneration;
- source and wheel command execution.

### Deterministic mutation tests

Generate ledgers with each event removed, adjacent events swapped, one scalar changed, one hash nibble altered, each event boundary truncated and copied events inserted. Every mutation must fail parsing or verification.

### Viewer tests

- local data only;
- no network dependency;
- evidence-class labels;
- integrity and lifecycle explanations;
- keyboard navigation;
- semantic structure;
- 390-pixel layout;
- no unsupported “trusted” or “immutable” claims;
- useful no-JavaScript content.

### Release gate

- Python 3.10–3.13;
- source compilation and full tests;
- deterministic reference-ledger regeneration;
- exact fixture outcomes;
- wheel build and clean installation;
- full tests against installed wheel outside source;
- all three commands from the installed wheel;
- secret and dependency checks;
- source/wheel fixture equality;
- viewer checks;
- independently tested downloadable archive.

Tests and CI require no network or paid model call.

## Demonstration narrative

Ninety seconds:

1. an agent reports success;
2. the timeline labels it as a source report rather than proof;
3. an independent observation contradicts it and verification records failure;
4. one event is manually edited;
5. `ledger-verify` identifies the broken sequence and digest;
6. a completely recomputed replacement chain passes internal consistency but fails the independently retained expected root;
7. the viewer explains that chain validity, lifecycle validity and evidence truth are separate questions.

## Authorship framing

The contribution statement should distinguish:

- Luca Panayiotou's repeated identification of unsupported agent completion as a practical failure mode;
- the requirement that source claims remain separate from independent observations;
- the approved product and employer-facing direction;
- AI-assisted specification, implementation, documentation and testing;
- reproducible fixtures, hashes and CI as primary evidence;
- later external contributors when they exist.

## Success criteria

The first release succeeds when:

- an employer understands the problem in under two minutes;
- valid and tampered ledgers reproduce offline;
- every event is canonical, typed, chained and lifecycle-validated;
- source reports cannot satisfy observation requirements;
- deletion, insertion, reordering, mutation, truncation and artifact tampering are detected;
- complete replacement is detected with an external root;
- assurance terminology is precise;
- package, CLIs and viewer pass source, wheel, matrix and archive verification;
- the project remains distinct from the Verifier and Arena.

## Implementation milestones

The implementation plan should divide work into four independently reviewable releases:

1. **Protocol core** — canonicalization, event schema, hash chain, state machine and deterministic invalid fixtures.
2. **Persistence and commands** — locking, artifact handling, seal, `ledger-record` and `ledger-verify`.
3. **Disclosure and evidence** — `ledger-export`, reference ledgers, expected-root workflow, mutation generators and release verification.
4. **Employer-facing release** — static viewer, documentation, accessibility, clean-wheel matrix, archive verification and standalone publication.

Implementation must not begin until this written specification has been reviewed and approved.