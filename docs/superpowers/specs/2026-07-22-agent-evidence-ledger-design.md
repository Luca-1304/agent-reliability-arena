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
- **Agent Evidence Ledger**, which preserves the ordered audit history and exposes whether that history has been altered or is logically impossible.

## Employer-facing value

The project should demonstrate capabilities relevant to agent infrastructure, evals, reliability, security and applied-AI engineering:

- designing a stable evidence protocol rather than relying on prose logs;
- separating claims, reports, observations and decisions by trust class;
- defining a deterministic canonical representation before hashing;
- building append-only local persistence with crash and concurrency handling;
- detecting deletion, insertion, reordering, mutation and truncation;
- encoding legal lifecycle transitions as testable invariants;
- explaining cryptographic limits rather than overstating them;
- providing reproducible command-line and browser-based inspection;
- treating model and tool output as untrusted input.

Primary public line:

> **Prove the trace, not the claim.**

Supporting line:

> A tamper-evident evidence ledger for tool-using agents, with independently classified observations and verifiable state transitions.

## Approaches considered

### 1. Hosted audit service

Send every agent event to a central web service and expose a dashboard.

Advantages:

- easy team access;
- central retention and search;
- an external service can provide stronger timestamping and identity controls.

Risks:

- hosting, authentication, billing and operational security dominate the first release;
- users must trust the service operator;
- difficult to reproduce offline;
- less suitable as a compact public engineering project.

### 2. Signed SQLite ledger

Store normalized events in SQLite and sign database checkpoints with a user-managed key.

Advantages:

- efficient queries;
- transactions and concurrency are mature;
- signatures can support stronger actor identity and non-repudiation claims.

Risks:

- binary database format is less transparent in code review;
- key generation, storage, rotation and revocation substantially expand the threat model;
- a database file alone is awkward for a static employer-facing evidence viewer;
- signatures can create misleading confidence when key custody is weak.

### 3. Portable hash-chained event ledger — selected

Use canonical newline-delimited JSON events in an append-only ledger directory. Each event includes the previous event hash and its own SHA-256 digest. A seal records the final root, event count and software version. Verification can optionally require an expected root retained outside the ledger directory.

Advantages:

- readable with ordinary tools;
- deterministic and dependency-light;
- portable between systems;
- easy to test with exact fixtures;
- clear integrity model;
- well suited to a read-only static viewer;
- can later be checkpointed, signed or anchored externally without changing event semantics.

Limitations:

- SHA-256 chaining alone does not prove who authored an event;
- an attacker who can replace the complete ledger and all local seals can recompute a valid chain;
- trustworthy detection of a complete rewrite requires an expected root stored elsewhere;
- local timestamps do not prove trusted wall-clock time.

This limitation is part of the public product story, not hidden in fine print.

## v0.1.0 scope

One ledger directory represents one agent execution trace for one declared completion contract.

Included:

- a versioned event schema;
- a deterministic canonical JSON subset;
- SHA-256 event chaining with domain separation;
- typed actors and evidence classes;
- legal event-transition validation;
- append locking, flush and filesystem synchronisation;
- artifact references with independent digests;
- a final seal and optional expected-root verification;
- three command-line applications;
- deterministic valid and tampered fixtures;
- a dependency-free static viewer;
- Python 3.10–3.13 source and clean-wheel verification.

Deferred:

- multiple tasks in one ledger stream;
- network replication;
- user accounts or hosted storage;
- public-key signatures;
- trusted timestamp authorities;
- hardware-backed keys;
- transparency-log gossip or Merkle-tree inclusion proofs;
- arbitrary database import;
- legal non-repudiation claims;
- shell, browser, email, payment or repository execution.

## Threat model

### Protected properties

The verifier should detect, within the supplied ledger directory:

- event content mutation;
- event deletion;
- event insertion;
- event reordering;
- duplicate sequence numbers or event identifiers;
- a broken previous-hash reference;
- truncated or partially written events;
- non-canonical or malformed event encoding;
- artifact byte changes;
- seal/event-count disagreement;
- impossible lifecycle transitions;
- a final root that differs from an externally supplied expected root.

### Adversaries considered

- accidental file edits;
- broken logging integrations;
- a tool or model that emits misleading success-shaped data;
- a user who rearranges or removes events before sharing a trace;
- incomplete file transfer;
- a process crash during append;
- concurrent writers attempting to append to the same ledger;
- a malicious local editor who changes some ledger files but does not control an external expected-root checkpoint.

### Adversaries not defeated by v0.1.0 alone

- an attacker who replaces the entire ledger, seal and any locally stored expected root;
- compromise of the machine before evidence is observed;
- forged actor identity when no cryptographic signing key exists;
- falsified independent-observer software;
- inaccurate system time;
- operating-system or filesystem compromise beneath the writer;
- denial of service or deletion of the entire directory.

The viewer must never translate “hash chain valid” into “all facts are true.” Chain integrity and evidence truth are separate properties.

## Ledger directory

```text
<ledger-id>/
  ledger.jsonl
  seal.json
  manifest.json
  artifacts/
    <sha256>.<extension>
  public/
    disclosure.json        # created only by explicit export
```

`ledger.jsonl` is the canonical ordered event stream.

`seal.json` records the final event hash, event count, ledger identifier, schema version, writer version and close status. It is useful for transport and external checkpointing but is not independently trustworthy when stored only beside the ledger.

`manifest.json` records the SHA-256 digest and byte length of every retained file except itself. The manifest is generated only when the ledger is sealed.

Artifacts are content-addressed by SHA-256. Event payloads reference artifacts rather than embedding large or binary data.

## Canonical data rules

The first release uses a deliberately narrow canonical JSON subset rather than claiming full RFC 8785 compatibility.

Before hashing, an event must satisfy all of these rules:

- UTF-8 encoding without a byte-order mark;
- object keys sorted lexicographically by Unicode code point;
- compact separators with no insignificant whitespace;
- strings normalized to Unicode NFC;
- integers only; floating-point numbers are rejected;
- booleans and `null` permitted;
- duplicate object keys rejected during parsing;
- NaN and Infinity rejected;
- arrays preserve source order;
- a trailing newline exists in `ledger.jsonl`, but the newline is not part of the event hash;
- unknown top-level fields rejected for the declared schema version.

This subset is simple enough to implement with the Python standard library plus explicit validation and is stable across supported Python versions.

## Hash construction

Each event is hashed after all fields except `event_hash` have been populated.

```text
canonical_event = canonical_json(event_without_event_hash)

event_hash = SHA256(
  UTF8("agent-evidence-ledger:event:v1\n")
  || UTF8(canonical_event)
)
```

The first event uses:

```text
previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
```

Every later event's `previous_hash` must equal the immediately preceding event's `event_hash`.

Domain separation prevents the same canonical bytes from being silently reused as another hash object type. Artifact hashes and manifest hashes use separate domains or raw byte hashing as explicitly documented.

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

### Identifier rules

- `ledger_id` is an opaque caller-supplied identifier or a generated UUIDv7-style value with the prefix `led_`.
- `event_id` is deterministic within a ledger: `evt_` followed by the zero-padded sequence number.
- `sequence` begins at zero and increments by exactly one.
- identifiers are never reused within a ledger.

### Timestamp rules

- `recorded_at` is RFC 3339 UTC with a `Z` suffix;
- timestamps must be non-decreasing;
- timestamps are informational unless supplied by an independently trusted time source;
- deterministic fixtures use an injected fixed clock;
- clock regression is a verification failure because it breaks deterministic ordering assumptions, but a valid timestamp is not treated as proof of real-world time.

### Actor types

Allowed actor types in v0.1.0:

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

- `context` — task, contract or configuration;
- `intent` — proposal, authorisation or recovery plan;
- `source_report` — what an agent or tool says happened;
- `independent_observation` — state measured outside the reporting source;
- `decision` — verification, policy or closure decision;
- `error` — normalized execution, persistence or validation failure.

A source report can never be silently reclassified as an independent observation.

## Event types

### `ledger_opened`

Must be sequence zero and occur exactly once.

Payload includes:

- writer version;
- schema version;
- canonicalization profile;
- hash algorithm;
- fixture or live evidence label.

### `request_received`

Records the user-visible task or a digest-backed artifact reference to it.

Must occur exactly once after `ledger_opened`.

### `contract_declared`

Records the completion requirements and independent observation method.

Must occur exactly once after `request_received` and before mutation events.

### `action_proposed`

Records a proposed bounded action and its contract relationship.

Must reference `contract_declared`.

### `action_authorized`

Records permission for one proposed action.

Must reference exactly one prior `action_proposed` event. Authorisation is intent evidence, not proof that the action occurred.

### `tool_attempted`

Records that an authorised action was submitted to a tool boundary.

Must reference a valid `action_authorized` event. A single authorisation cannot be consumed by more than one attempt unless the authorisation payload explicitly permits a bounded retry count.

### `tool_reported`

Records the source-reported result of a tool attempt.

Must reference one `tool_attempted` event. Its evidence class is always `source_report`.

### `observation_recorded`

Records independently measured state after an attempt.

Must reference the relevant `tool_attempted` event and include:

- observer identifier;
- observation method;
- outcome class;
- observed contract fields;
- artifact references when applicable;
- `matches_contract` boolean;
- `terminal` boolean when security or policy rejection prevents recovery.

Its evidence class is always `independent_observation`.

### `completion_claimed`

Records whether an agent or synthesiser claims completion and the event identifiers it cites as support.

It may occur before an observation so false or premature claims can be represented faithfully. The ledger state machine does not convert the claim into completion.

### `verification_decided`

Records the verifier's status and supporting references.

Allowed statuses:

- `VERIFIED_COMPLETE`;
- `PARTIAL`;
- `UNVERIFIED`;
- `FAILED`;
- `SECURITY_REJECTED`.

`VERIFIED_COMPLETE` is legal only when:

- a contract exists;
- at least one relevant independent observation exists after the latest mutation attempt;
- the latest relevant observation has `matches_contract: true`;
- no later observation contradicts that state;
- every referenced artifact digest verifies;
- the decision references the contract and observation events.

A completion claim is not required for independently verified completion. This allows silent successful completion to be represented.

### `recovery_authorized`

Records one bounded recovery decision after a non-terminal failed, partial or unverified decision.

Must reference the prior `verification_decided` event and specify the remaining retry allowance.

It is illegal after `SECURITY_REJECTED`, after a terminal observation, or after `VERIFIED_COMPLETE`.

### `error_recorded`

Records normalized persistence, tool, observer or verification errors.

Secrets and authorization headers must be removed before append. Error payloads include error class and redacted message, not unrestricted exception objects.

### `ledger_closed`

Must occur exactly once and be the final event.

Must reference the final `verification_decided` event. The payload repeats the final status and indicates whether the ledger is complete, aborted or invalidated.

No event can be appended after closure.

## Lifecycle state machine

Conceptual states:

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
  ├─ VERIFIED_COMPLETE / terminal failure → ledger_closed
  └─ recoverable failure → recovery_authorized → action_proposed
CLOSED
```

Events that do not change state, such as `tool_reported`, remain legal only within their relevant attempt window.

The implementation uses explicit validators per event type rather than one monolithic conditional function.

## Append semantics

`ledger-record` is the only supported writer in v0.1.0.

Append procedure:

1. acquire an exclusive lock file inside the ledger directory;
2. parse and verify the complete existing chain;
3. validate the proposed event against the current lifecycle state;
4. assign sequence, event identifier, previous hash and timestamp;
5. canonicalize and hash the event;
6. append exactly one UTF-8 line;
7. flush the file buffer;
8. call `fsync` on the ledger file;
9. update writer metadata when required;
10. release the lock.

The writer refuses:

- a missing or malformed final newline;
- a partial existing line;
- a chain that already fails verification;
- an event after closure;
- a concurrent lock that cannot be acquired within the configured timeout;
- a payload containing secret-like field names such as `api_key`, `authorization`, `password`, `secret` or `token` unless explicitly allowlisted as a digest-only metadata field.

The lock prevents cooperative concurrent writers. It is not claimed as protection against a malicious process that ignores the lock.

## Artifact handling

Large or binary evidence is stored under `artifacts/` by digest.

Artifact reference fields:

```json
{
  "sha256": "...",
  "byte_length": 1234,
  "media_type": "application/json",
  "relative_path": "artifacts/<sha256>.json",
  "description": "Independent filesystem observation"
}
```

Verification requires:

- path remains within the ledger directory;
- file exists;
- byte length matches;
- SHA-256 matches;
- duplicate digest references resolve to identical bytes;
- symbolic links are rejected in retained artifacts.

The ledger hashes the artifact reference; the artifact file is verified independently.

## Seal and expected-root verification

On closure, `ledger-record close` creates `seal.json` and `manifest.json`.

`seal.json` includes:

- ledger identifier;
- schema version;
- final event hash;
- event count;
- final status;
- closed timestamp;
- writer version;
- canonicalization profile;
- hash algorithm.

`ledger-verify` supports:

```bash
ledger-verify --ledger path/to/ledger
ledger-verify --ledger path/to/ledger --expected-root <sha256>
ledger-verify --ledger path/to/ledger --expected-root-file checkpoint.txt
```

Without an expected root, verification proves internal consistency of the supplied directory.

With an independently retained expected root, verification also detects complete local replacement of the chain.

The CLI output must state which assurance level was achieved:

- `INTERNAL_CHAIN_VALID`;
- `EXPECTED_ROOT_MATCHED`;
- `INVALID`.

It must never output a generic “trusted” status.

## Command-line applications

### `ledger-record`

Subcommands:

```text
ledger-record init
ledger-record append
ledger-record attach
ledger-record close
```

Examples:

```bash
ledger-record init \
  --output ledgers/demo \
  --ledger-id led_demo \
  --evidence-label deterministic_fixture

ledger-record append \
  --ledger ledgers/demo \
  --event-type request_received \
  --actor-type user \
  --actor-id user \
  --payload-file fixtures/request.json

ledger-record attach \
  --ledger ledgers/demo \
  --file fixtures/observation.json \
  --media-type application/json

ledger-record close \
  --ledger ledgers/demo
```

Machine-readable JSON output is the default. A concise human summary is available through `--format text`.

### `ledger-verify`

Validates:

- parsing and canonical form;
- sequence and identifiers;
- hash chain;
- lifecycle transitions;
- references;
- artifact integrity;
- closure and seal;
- manifest;
- optional expected root.

Exit codes:

- `0` valid;
- `2` invalid evidence or chain;
- `3` malformed input;
- `4` unsupported schema;
- `5` operational error.

### `ledger-export`

Produces a reduced disclosure bundle for the static viewer.

It never modifies the source ledger.

Export includes:

- event timeline with selected safe payload fields;
- actor and evidence-class labels;
- chain and lifecycle verification results;
- root hash and assurance level;
- artifact metadata without private bytes unless explicitly approved;
- disclosure manifest recording removed fields.

Export fails when the source ledger is invalid.

## Python API

The package exposes focused interfaces:

```python
from agent_evidence_ledger import (
    LedgerWriter,
    LedgerVerifier,
    DisclosureExporter,
    Event,
    VerificationReport,
)
```

Internal modules remain small and independently testable:

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

No module should combine persistence, lifecycle validation and presentation logic.

## Static evidence viewer

A dependency-free HTML/CSS/JavaScript application reads only the reduced disclosure bundle.

Primary employer experience:

1. a clear headline: “Prove the trace, not the claim”;
2. chain status and assurance level;
3. final completion status;
4. an ordered timeline of typed events;
5. evidence-class filtering;
6. visible links between proposals, attempts, reports, observations and decisions;
7. a chain ribbon showing each event hash and previous-hash relationship;
8. an explanation panel for invalid fixtures;
9. artifact digest and byte-length details;
10. explicit cryptographic limitations.

The viewer does not verify arbitrary local files in the browser in v0.1.0. It displays a bundle created by `ledger-export` and includes the export's verification report. Native browser verification can be considered later.

Accessibility requirements:

- semantic headings and landmarks;
- keyboard-operable timeline navigation;
- visible focus states;
- text labels in addition to colour;
- sufficient contrast;
- reduced-motion support;
- responsive layout down to 390 CSS pixels;
- meaningful static content when JavaScript fails.

## Deterministic fixtures

### Valid fixtures

1. verified completion with matching independent observation;
2. silent verified completion with no agent completion claim;
3. recoverable failure followed by one authorised successful retry;
4. terminal security rejection closed without retry;
5. valid artifact-backed observation;
6. valid ledger checked against an externally supplied expected root.

### Invalid integrity fixtures

1. edited payload without recomputed hash;
2. deleted middle event;
3. inserted event;
4. reordered events;
5. broken `previous_hash`;
6. duplicate sequence number;
7. duplicate event identifier;
8. truncated final JSON line;
9. non-canonical whitespace or key ordering;
10. modified artifact bytes;
11. seal event-count mismatch;
12. expected-root mismatch after a completely recomputed replacement chain.

### Invalid lifecycle fixtures

1. request before `ledger_opened`;
2. tool attempt without authorisation;
3. source report classified as independent observation;
4. `VERIFIED_COMPLETE` without an observation;
5. `VERIFIED_COMPLETE` after a contradicting later observation;
6. recovery after terminal security rejection;
7. retry after verified completion;
8. closure without a final verification decision;
9. event appended after closure;
10. completion decision referencing an unrelated attempt.

Fixture labels must distinguish software validation from real agent evidence.

## Error handling

Errors are structured by layer:

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

A verification report includes:

- validity;
- assurance level;
- error code;
- event sequence and identifier when available;
- expected and actual values for non-sensitive digest mismatches;
- safe remediation guidance;
- no unrestricted stack trace by default.

Verification continues far enough to report multiple independent problems when safe, but chain-dependent checks stop after the first event whose integrity cannot be established.

## Privacy and secret handling

Append-only storage makes pre-ingestion filtering essential.

Rules:

- known secret-like payload keys are rejected by default;
- raw API keys, authorization headers, cookies and passwords are forbidden;
- public export uses an explicit allowlist, not a denylist;
- redaction occurs before append or during disclosure export, never by rewriting a sealed ledger;
- a disclosure bundle records which field paths were omitted;
- artifact export is opt-in;
- example fixtures contain synthetic values only;
- CI scans retained files for common secret patterns.

The project does not claim GDPR, HIPAA, SOC 2 or legal-record compliance.

## Claims boundary

v0.1.0 may claim:

- alteration of a supplied chain is detectable under the documented threat model;
- lifecycle-invalid histories are rejected;
- source reports and independent observations remain structurally distinct;
- externally retained root comparison detects a complete local chain replacement;
- deterministic fixtures reproduce the documented integrity failures.

v0.1.0 may not claim:

- legal non-repudiation;
- authenticated actor identity;
- trusted time;
- truth of the underlying observation;
- protection against a fully compromised host;
- immutability when every copy and checkpoint is controlled by the same attacker;
- blockchain or distributed-consensus properties;
- compliance certification;
- external-model performance.

## Repository presentation

The future standalone repository should open with:

- the public question;
- a concise valid-versus-tampered viewer image;
- a two-minute local reproduction;
- exact assurance terminology;
- a table of detected tamper classes;
- architecture and threat-model diagrams;
- deterministic fixtures and test evidence;
- limitations visible near the headline;
- authorship and AI-assistance disclosure.

Suggested repository map:

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

- canonical JSON rules;
- Unicode normalization;
- integer-only numeric validation;
- deterministic event hashing;
- schema validation;
- each legal and illegal state transition;
- actor and evidence-class restrictions;
- reference resolution;
- artifact path confinement and digest checking;
- seal construction;
- expected-root comparison;
- secret-key rejection;
- exit-code mapping.

### Integration tests

- complete valid ledger lifecycle;
- recoverable retry lifecycle;
- security-terminal lifecycle;
- crash leaving a partial final line;
- lock contention;
- artifact attachment and closure;
- disclosure export;
- read-only verification;
- deterministic fixture regeneration;
- source and wheel command execution.

### Property-style tests

Without adding a heavy dependency, deterministic mutation generators should:

- remove each event in turn;
- swap adjacent events;
- mutate one payload scalar;
- alter one hash nibble;
- truncate every event boundary;
- insert a copied event at each position.

Every generated mutation must either fail parsing or produce an invalid verification report.

### Viewer tests

- local data only;
- no network dependency;
- evidence-class labels;
- chain and lifecycle error explanations;
- keyboard navigation;
- semantic structure;
- 390-pixel responsive layout;
- no unsupported “trusted” or “immutable” claims;
- graceful no-JavaScript content.

### Release gate

- Python 3.10, 3.11, 3.12 and 3.13;
- source compilation;
- full source test suite;
- deterministic reference-ledger regeneration;
- exact expected fixture outcomes;
- wheel build;
- clean-wheel installation;
- full tests against installed wheel outside the source tree;
- all three commands from the installed wheel;
- secret scan;
- dependency check;
- source/wheel fixture equivalence;
- static viewer checks;
- independently tested downloadable archive.

No network or paid model call is required by tests or CI.

## Demonstration narrative

Ninety-second employer demonstration:

1. **0–15 seconds:** An agent receives a task and reports success.
2. **15–30 seconds:** The timeline shows that success as a source report, not proof.
3. **30–45 seconds:** An independent observation contradicts the claim; verification records `FAILED`.
4. **45–60 seconds:** One event is edited manually.
5. **60–70 seconds:** `ledger-verify` identifies the exact broken sequence and digest mismatch.
6. **70–80 seconds:** A completely recomputed replacement chain passes internal consistency but fails against the externally retained expected root.
7. **80–90 seconds:** The viewer summarises the distinction: valid chain, valid lifecycle and truthful evidence are three separate questions.

The demonstration illustrates the system; aggregate performance claims are out of scope.

## Authorship framing

The contribution statement should distinguish:

- Luca Panayiotou's repeated identification of unsupported agent completion as a practical failure mode;
- the requirement that source claims remain separate from independently observed evidence;
- the approved product direction and public-employer framing;
- AI-assisted specification, implementation, documentation and testing;
- reproducible fixtures, hashes and CI as the primary technical evidence;
- later external review or contributions when they exist.

## Success criteria

The first release succeeds when:

- an employer understands the problem in under two minutes;
- valid and tampered ledgers are reproducible without private infrastructure;
- every event is canonical, typed, chained and lifecycle-validated;
- source reports cannot satisfy independent-observation requirements;
- deletion, insertion, reordering, mutation, truncation and artifact tampering are detected;
- complete replacement is detected when an external expected root is supplied;
- assurance terminology is precise and visible;
- the package, CLIs and viewer pass source, wheel, matrix and archive verification;
- the project remains clearly distinct from the Verifier and Arena.

## Implementation milestones

The implementation plan should divide work into four independently reviewable releases:

1. **Protocol core** — canonicalization, event schema, hash chain, state machine and deterministic invalid fixtures.
2. **Persistence and commands** — append locking, artifact handling, seal, `ledger-record` and `ledger-verify`.
3. **Disclosure and evidence** — `ledger-export`, reference ledgers, expected-root workflow, mutation generators and release verification.
4. **Employer-facing release** — static viewer, documentation, accessibility, clean-wheel matrix, archive verification and public repository publication.

Implementation must not begin until this written specification has been reviewed and approved.