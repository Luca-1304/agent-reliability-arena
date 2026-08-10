# Monotonic Trial Evidence Witness — Design

Date: 2026-08-10
Status: approved continuation design
Scope: provider-free repeated-experiment evidence continuity
Base: `main` after PR #109 (`5745a0eb08bb802746963e27d8c2e520da443870`)

## Purpose

Close the evidence-continuity window that exists between completed repeated-experiment trials and the later immutable private evidence-set index.

Transport ledger schema 2 already links records internally. The disclosure-safe private evidence index already commits finalized run files and whole-ledger SHA-256 values. The remaining useful gap is during a repeated experiment: `experiment-checkpoint.json` is intentionally replaceable, so a previously completed trial's ledger and verification summary could be rewritten consistently before the final immutable evidence set is created.

This design adds a root-level, append-only, hash-chained witness for each verified completed trial. Continuation must reproduce the exact witnessed completed prefix before another provider-shaped trial may begin.

## Non-goals and claim boundary

This is not an external transparency log, hardware-backed monotonic counter, timestamp authority, signature service or remote notarization system.

It detects later modification, valid-looking suffix truncation, or consistent rewrite of an already-witnessed trial **when the witness file itself is retained**. An actor able to rewrite both all experiment evidence and the witness can still construct a different internally consistent local history. Preventing that requires an independently controlled external anchor and is outside this repository's current authority.

The change adds no provider calls, credentials, runtime dependency, publication authority, Git mutation authority, Vercel behavior, branch cleanup or comparative performance claim.

## Why this layer rather than another final hash

A new final hash file would duplicate existing controls:

- each transport ledger already has a whole-file SHA-256 summary;
- schema 2 already chains individual transport records;
- the private evidence-set index already immutably commits finalized run manifests and ledger SHA-256 values.

The missing property is monotonic continuity *during* a repeated experiment. Therefore the new control sits at the experiment root and advances once per independently verified completed trial, before the replaceable checkpoint advances.

## Artifact

New private root artifact:

`experiment-evidence-witness.jsonl`

Schema name:

`arena-repeated-experiment-evidence-witness-v1`

Each line contains exactly:

- `schema_version`
- `sequence`
- `trial_id`
- `plan_digest`
- `preflight_manifest_digest`
- `ledger_schema_version`
- `ledger_records`
- `ledger_sha256`
- `verification_summary_sha256`
- `previous_witness_digest`
- `witness_digest`

`witness_digest` is SHA-256 over canonical JSON of the record without `witness_digest`. Sequence 1 has `previous_witness_digest: null`; every later witness points to the previous line's `witness_digest`.

The witness contains digests and counts only. It does not duplicate prompts, model outputs, provider payloads, credentials or operator notes.

## Write ordering

For every newly completed trial:

1. the paired pilot persists its ordinary trial evidence;
2. `verify_completed_trial(...)` independently re-verifies the persisted summary and full transport ledger;
3. the runner appends and fsyncs one witness record for that exact verified trial;
4. the runner re-verifies the complete witness prefix against the completed trial prefix;
5. only then may `experiment-checkpoint.json` advance;
6. only then may execution proceed to the next planned trial or return a deliberate pause.

This ordering makes the append-only witness the stronger continuity boundary and keeps the replaceable checkpoint a convenience/progress artifact.

## Continuation rules

On reopening an experiment root, the runner first discovers and independently verifies the contiguous completed trial prefix. It then verifies the witness before replacing the checkpoint or making another provider-shaped call.

For a non-empty completed prefix:

- the witness file must exist;
- witness line count must exactly equal completed-trial count;
- witness trial IDs must exactly equal the preregistered completed prefix;
- plan and preflight digests must match;
- sequence and witness-chain links must be exact;
- every witnessed `ledger_schema_version`, `ledger_records` and `ledger_sha256` must equal fresh transport-ledger verification;
- every `verification_summary_sha256` must equal the current persisted summary bytes;
- every witness digest must recompute exactly.

For an empty completed prefix, an existing non-empty witness is invalid.

A missing or shorter witness for already-completed trial evidence fails closed rather than silently backfilling history. This deliberately favours evidence integrity over automatic recovery after a process crash in the narrow interval between trial completion and witness append.

## Append safety

Witness records use create-or-append private file handling with:

- regular-file / non-symlink checks;
- restrictive permissions where supported;
- one encoded JSON record per write;
- flush + `fsync` before the checkpoint advances;
- full witness verification before and after append;
- refusal of blank lines, malformed JSON, duplicate/unknown fields, unsupported schema, invalid digest format, sequence gaps, wrong predecessor, wrong trial prefix or mismatched evidence commitments.

The repeated experiment runner is not made multi-writer by this change. Existing single-execution assumptions remain.

## Failure behavior

Any witness inconsistency is terminal for that continuation attempt and occurs before a new provider-shaped trial starts. Existing experiment abort behavior remains authoritative for failures during active execution.

A crash that leaves completed trial evidence without its witness is intentionally not auto-repaired. The root must be treated as incomplete evidence rather than allowing an unwitnessed history to be accepted later.

## Compatibility

- Existing completed experiment fixtures created before this feature do not automatically acquire witnesses.
- New experiment roots created by the updated runner require the witness contract once a trial completes.
- Transport ledger schema 1 remains verifiable/continuable under its existing compatibility rules; a witness records the actual ledger schema reported by verification.
- Transport ledger schema 2 remains unchanged.
- Public transport-ledger verifier return shape remains unchanged.
- The disclosure-safe evidence index remains unchanged; if a repeated-experiment root or its trial evidence is later indexed/exported under an appropriate workflow, the witness is an additional private artifact rather than a replacement for the immutable final index.

## Tests

Provider-free regression tests must prove:

1. a completed trial produces one valid witness record before checkpoint advancement;
2. pause/resume preserves the first witness and appends later records without replaying completed calls;
3. a normal three-trial run produces sequences `1..3` and a continuous witness chain;
4. mutating or suffix-truncating an already-witnessed trial ledger is rejected on resume even if local trial metadata is made otherwise self-consistent;
5. mutating a witnessed verification summary is rejected;
6. witness line deletion, reordering, digest mutation, predecessor mutation, unknown fields and malformed JSON are rejected;
7. a completed trial prefix with a missing/shorter witness fails closed;
8. a witness ahead of the verified completed prefix fails closed;
9. no provider-shaped calls are made after witness validation fails;
10. existing abort, non-contiguous evidence, drift, release reproduction and cross-version test behavior remain green.

## Documentation

The repeated-experiment runbook will describe the witness artifact, ordering and claim limit.

`ROADMAP.md` will be updated in the same substantive PR to:

- mark the reliability assurance architecture as merged/operational rather than still awaiting rollout evidence;
- record witnessed completed-trial continuity under Stage 8 without claiming external immutability or real-provider evidence.

## Acceptance

Merge only an unchanged exact PR head after all existing required workflow families complete successfully. Publication-only/write-capable release steps may remain intentionally skipped on a pull request. No Vercel deployment path is re-enabled.