# Detached Witness Receipts Design

## Purpose

The repeated-experiment root now contains an append-only hash-chained `experiment-evidence-witness.jsonl` that commits each independently verified completed trial before the replaceable checkpoint advances. That closes the local suffix-truncation/consistent-rewrite window while the witness itself remains trustworthy.

The next remaining continuity boundary is wholesale replacement of both the local evidence and the local witness. This change introduces a deliberately smaller control: a deterministic, create-once **detached witness receipt** that can be retained outside the experiment root and later used to prove that a previously accepted witness prefix has not been replaced.

This is not external notarization. If an actor can rewrite both the experiment root and every retained detached receipt, this mechanism can still be defeated. It creates a separately retainable checkpoint without adding network services, credentials, signatures, Git writes, publication authority or provider calls.

## Chosen approach

Three approaches were considered:

1. **External timestamp/signature service.** Stronger trust separation, but it adds network availability, external trust, operational secrets/identity and new authority before the private provider experiment exists.
2. **Git-committed receipts.** Durable and reviewable, but it creates Git mutation authority and risks moving private experiment metadata into a public or source-controlled surface.
3. **Deterministic create-once receipt outside the experiment root.** No network or Git mutation, portable, provider-free, and strong enough to detect root-only wholesale witness replacement. This is the selected approach.

## Artifact

A detached receipt is one UTF-8 JSON object with schema:

`arena-repeated-experiment-detached-witness-receipt-v1`

Exact fields:

- `schema_version`
- `plan_digest`
- `preflight_manifest_digest`
- `witness_records`
- `witness_prefix_bytes`
- `witness_prefix_sha256`
- `witness_head_digest`
- `last_trial_id`
- `receipt_digest`

`receipt_digest` is canonical JSON SHA-256 over every other receipt field.

No prompt, model output, provider payload, credential, path, machine identifier, operator note, billing value or timestamp is included.

## Why prefix bytes instead of whole-file SHA only

The witness is append-only. A receipt generated after trial 1 should remain useful after trials 2–4 are appended. Therefore the receipt commits the **exact byte prefix** that existed when the receipt was created:

- `witness_prefix_bytes` records its byte length;
- `witness_prefix_sha256` commits exactly those bytes;
- `witness_records` records how many complete witness records are covered;
- `witness_head_digest` commits the final witness record in that prefix;
- `last_trial_id` makes the checkpoint human-auditable without exposing experiment content.

Later appends do not invalidate an earlier receipt as long as the committed prefix is byte-for-byte unchanged.

## Production interfaces

Create a focused module:

`src/agent_reliability_arena/repeated_receipt.py`

Public functions:

```python
write_detached_witness_receipt(
    experiment_root: Path,
    receipt_path: Path,
) -> dict[str, object]

verify_detached_witness_receipt(
    experiment_root: Path,
    receipt_path: Path,
) -> dict[str, object]
```

Add one public inspection helper to the existing witness module:

```python
inspect_completed_trial_witnesses(
    experiment_root: Path,
    plan_digest: str,
    preflight_manifest_digest: str,
) -> list[dict[str, object]]
```

The helper verifies the witness structure and every witnessed trial commitment, using the witness's own ordered trial IDs. It does not weaken `verify_completed_trial_witnesses(...)`, which remains the runner's stricter expected-prefix API.

`repeated_receipt.py` may provide `python -m agent_reliability_arena.repeated_receipt create|verify ...` for operator use. No `pyproject.toml` console-script entry is added, avoiding release metadata churn and new command-surface authority.

## Context derivation

Receipt creation and verification read only these existing root artifacts:

- `experiment-plan.json` → `plan_digest`
- `experiment-preflight.json` → `manifest_digest`
- `experiment-evidence-witness.jsonl`

The plan/preflight JSON readers reject symlinks, non-files, invalid UTF-8, duplicate keys, non-object roots, missing digests and malformed lowercase SHA-256 values.

Before creating a receipt, the complete current witness history is independently reverified against its referenced completed trial ledgers and verification summaries.

A receipt cannot be created for an empty/missing witness.

## Detached-path boundary

Creation requires the receipt output to be outside the resolved experiment root.

Rules:

- experiment root must be a regular non-symlink directory;
- receipt parent must already exist and resolve to a directory;
- the resolved receipt parent must not be the experiment root or any descendant of it;
- receipt output must not already exist or be a symlink;
- receipt is created with exclusive-create semantics, restrictive permissions where supported, flush and `fsync`;
- no directory is auto-created by the receipt writer.

Verification applies the same outside-root path check. Moving a receipt back into the experiment root therefore removes the claimed detached boundary and is rejected.

The resolved-parent check prevents a simple parent symlink from disguising an inside-root destination. It does not claim to solve hostile concurrent filesystem namespace mutation; the existing single-operator/local evidence assumptions remain.

## Verification algorithm

1. Validate the experiment root and detached receipt path boundary.
2. Parse the receipt with duplicate-key and exact-field rejection.
3. Recompute and verify `receipt_digest`.
4. Read and validate current plan/preflight digests; require exact equality with the receipt.
5. Reverify the complete current witness history against the current referenced trial evidence.
6. Require the current witness to contain at least `witness_records` records and at least `witness_prefix_bytes` bytes.
7. Hash exactly the first `witness_prefix_bytes` bytes of the current witness and require equality with `witness_prefix_sha256`.
8. Require current witness record `witness_records` to have the recorded `witness_head_digest` and `last_trial_id`.
9. Return a compact verified summary. No provider/network call occurs.

A receipt made at trial N remains valid after later appended trials because only the committed prefix is compared.

## Fail-closed cases

Reject:

- receipt inside the experiment root;
- receipt output already existing or symlinked;
- missing/empty witness;
- malformed plan/preflight/witness/receipt JSON;
- duplicate or unknown receipt fields;
- malformed digest/count fields;
- receipt digest mismatch;
- plan or preflight drift;
- current witness shorter than the committed record count or byte prefix;
- any changed byte inside the committed prefix;
- mismatched witness head digest or last trial ID;
- a current witness that no longer independently verifies against its trial evidence.

Do not silently update or overwrite an old receipt. A later checkpoint uses a new receipt file chosen by the operator.

## Testing

Provider-free tests cover:

- deterministic receipt creation after one witnessed trial;
- exact field shape and digest recomputation;
- creation rejected inside the experiment root;
- exclusive-create/no-overwrite behavior;
- symlink and malformed-path rejection;
- verification immediately after creation;
- old receipt remains valid after witness records are appended;
- committed-prefix byte rewrite rejected;
- wholesale locally consistent witness/evidence replacement rejected by a retained old receipt;
- receipt field/digest tampering rejected;
- plan/preflight drift rejected;
- current witness shorter than the receipt rejected;
- no provider call during receipt creation or verification;
- module CLI create/verify smoke behavior without adding a packaged console entry point.

Existing witness, repeated-runner, Fast, Deep, Specialist, history, CodeQL, Pages and concurrency gates remain authoritative.

## Documentation

Update `docs/REPEATED_EXPERIMENT_RUNBOOK.md` to describe optional detached receipts after a verified/witnessed checkpoint and the external-retention claim boundary.

Update `ROADMAP.md` Stage 8 completed infrastructure to record detached prefix receipts without implying external notarization or real-provider evidence.

## Scope and authority

This change adds no:

- real provider execution;
- credential handling;
- network request;
- runtime dependency;
- Git mutation authority;
- Vercel integration;
- release/publication authority;
- automatic external storage;
- signature/timestamp authority;
- model-performance claim.

The receipt is useful only if at least one copy is retained outside the experiment root and outside the adversary/failure domain that may rewrite that root.
