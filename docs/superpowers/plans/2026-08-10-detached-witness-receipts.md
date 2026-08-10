# Detached Witness Receipts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic create-once detached receipts that commit a verified repeated-experiment witness prefix and remain verifiable after later witness appends.

**Architecture:** Extend the existing witness module with one read-only inspection API that revalidates the entire witnessed history against trial evidence. Add a focused `repeated_receipt.py` module that derives plan/preflight context, creates an exclusive receipt outside the experiment root, and verifies the committed witness prefix without changing the repeated runner. Keep the receipt deterministic and provider-free; no packaged console-script entry point is added.

**Tech Stack:** Python 3.10–3.13 standard library, JSON, SHA-256, existing canonical JSON helper, `unittest`, existing GitHub Actions reliability gates.

## Global Constraints

- No provider call, credential, network request or paid action.
- No runtime dependency.
- No Git mutation, Vercel integration, publication or release authority.
- Receipt output must resolve outside the experiment root and must be exclusive-create/no-overwrite.
- Receipt contains digests/counts/trial ID only: no prompt, output, provider payload, credential, path, machine identifier, operator note, price or timestamp.
- Earlier receipts remain valid after later append-only witness growth by committing exact witness prefix bytes rather than the whole future file.
- Existing `verify_completed_trial_witnesses(...)` remains the repeated runner's strict expected-prefix authority.
- A detached receipt is not external notarization; rewriting both the experiment root and every retained receipt remains outside the guarantee.
- Merge only an unchanged exact PR head after all triggered reliability workflow families succeed.

---

### Task 1: Add RED receipt contract tests

**Files:**
- Create: `tests/test_repeated_receipt.py`

**Interfaces:**
- Consumes planned APIs: `write_detached_witness_receipt(Path, Path) -> dict[str, object]`, `verify_detached_witness_receipt(Path, Path) -> dict[str, object]`.
- Reuses: `make_trial`, `witness_rows`, `PLAN_DIGEST`, `PREFLIGHT_DIGEST` from `tests/test_repeated_witness.py`.
- Produces: contract coverage for deterministic creation, prefix semantics, detached path enforcement and tamper detection.

- [ ] **Step 1: Create a real repeated-experiment root fixture**

Write `experiment-plan.json` with `plan_digest`, write `experiment-preflight.json` with `manifest_digest`, create one or more real schema-2 trial ledgers using existing witness test helpers, and append real witness records with `append_completed_trial_witness(...)`.

- [ ] **Step 2: Test deterministic one-record receipt creation**

Require exact fields:

```python
{
    "schema_version",
    "plan_digest",
    "preflight_manifest_digest",
    "witness_records",
    "witness_prefix_bytes",
    "witness_prefix_sha256",
    "witness_head_digest",
    "last_trial_id",
    "receipt_digest",
}
```

Require `witness_records == 1`, prefix byte length/hash to match exact witness bytes, head/trial fields to match row 1, and `receipt_digest == canonical_json_sha256(unsigned_receipt)`.

- [ ] **Step 3: Test immediate verification and later append compatibility**

Create receipt after trial 1, append trials 2 and 3, then require the original receipt still verifies because the first committed byte prefix remains unchanged.

- [ ] **Step 4: Test detached-path/exclusive-create failures**

Reject a receipt path inside the experiment root, an already-existing output, a receipt symlink and a resolved parent that points inside the experiment root.

- [ ] **Step 5: Test retained-receipt tamper detection**

After receipt creation, rewrite a byte inside the committed witness prefix and require verification failure. Separately replace the local witness/evidence with a different internally valid history and require the retained old receipt to fail against the changed prefix/head.

- [ ] **Step 6: Test receipt and context tampering**

Reject unknown fields, duplicate keys, malformed JSON, changed `receipt_digest`, changed plan/preflight context and a current witness shorter than the committed receipt.

- [ ] **Step 7: Preserve RED evidence before implementation**

Before `repeated_receipt.py` exists, the test module imports production APIs that are absent. With no local checkout execution surface in this chat, keep this structural RED boundary off the PR until implementation is present; PR CI will provide the full executable green evidence.

---

### Task 2: Add read-only witness-history inspection

**Files:**
- Modify: `src/agent_reliability_arena/repeated_witness.py`
- Modify: `tests/test_repeated_witness.py`

**Interfaces:**
- Produces:

```python
inspect_completed_trial_witnesses(
    experiment_root: Path,
    plan_digest: str,
    preflight_manifest_digest: str,
) -> list[dict[str, object]]
```

- Consumes existing private `_read_witness_rows(...)` and `_reconcile(...)`.

- [ ] **Step 1: Add an inspection test**

Create two witnessed trials and require inspection to return the two verified rows in order without needing a separately supplied expected completed-ID list.

- [ ] **Step 2: Implement the minimal helper**

Validate root/digests exactly as the current public verifier does, read rows, reject an empty witness, derive ordered IDs from the rows, call `_reconcile(...)`, return rows.

- [ ] **Step 3: Keep strict runner API unchanged**

Do not alter the semantics of `verify_completed_trial_witnesses(...)`; receipt inspection is additive only.

---

### Task 3: Implement detached receipt creation and verification

**Files:**
- Create: `src/agent_reliability_arena/repeated_receipt.py`
- Test: `tests/test_repeated_receipt.py`

**Interfaces:**
- Produces `RECEIPT_SCHEMA = "arena-repeated-experiment-detached-witness-receipt-v1"`.
- Produces `write_detached_witness_receipt(experiment_root: Path, receipt_path: Path) -> dict[str, object]`.
- Produces `verify_detached_witness_receipt(experiment_root: Path, receipt_path: Path) -> dict[str, object]`.
- Consumes `WITNESS_FILENAME`, `inspect_completed_trial_witnesses(...)`, `canonical_json_sha256(...)`.

- [ ] **Step 1: Implement strict JSON/digest helpers**

Reject symlink/non-file context artifacts, invalid UTF-8/JSON, duplicate keys, non-object roots and malformed lowercase 64-hex digests.

- [ ] **Step 2: Derive current context**

Read `experiment-plan.json["plan_digest"]` and `experiment-preflight.json["manifest_digest"]`, verify both digests, call `inspect_completed_trial_witnesses(...)`, reject no witness rows, and read exact witness bytes.

- [ ] **Step 3: Implement detached-path validation**

Resolve the existing receipt parent. Require it to be a directory whose resolved location is neither the experiment root nor a descendant. Reject existing/symlink receipt targets. Do not create parent directories.

- [ ] **Step 4: Build deterministic receipt**

Use the complete current witness bytes as the committed prefix at creation time and emit:

```python
unsigned = {
    "schema_version": RECEIPT_SCHEMA,
    "plan_digest": plan_digest,
    "preflight_manifest_digest": preflight_digest,
    "witness_records": len(rows),
    "witness_prefix_bytes": len(witness_bytes),
    "witness_prefix_sha256": hashlib.sha256(witness_bytes).hexdigest(),
    "witness_head_digest": rows[-1]["witness_digest"],
    "last_trial_id": rows[-1]["trial_id"],
}
receipt = {**unsigned, "receipt_digest": canonical_json_sha256(unsigned)}
```

- [ ] **Step 5: Persist with exclusive-create durability**

Write pretty sorted JSON plus newline using `O_WRONLY | O_CREAT | O_EXCL`, add `O_NOFOLLOW` where available, mode `0o600`, flush and `fsync`, chmod on non-Windows, then reread and verify the persisted receipt before returning it.

- [ ] **Step 6: Implement receipt verification**

Parse exact fields and recompute receipt digest; require current plan/preflight equality; independently reverify the current witness; require current record count/byte count at least the receipt checkpoint; hash exactly the first recorded byte count and compare; require row `witness_records - 1` to match receipt head/trial ID. Return a compact summary with `status: "verified"`, receipt record count, current witness record count, and whether later records exist.

- [ ] **Step 7: Add module CLI without packaging metadata changes**

Use `argparse` with subcommands:

```text
python -m agent_reliability_arena.repeated_receipt create --experiment-root ROOT --receipt PATH
python -m agent_reliability_arena.repeated_receipt verify --experiment-root ROOT --receipt PATH
```

Print JSON result to stdout. Do not add a `[project.scripts]` entry.

---

### Task 4: Document the new continuity layer

**Files:**
- Modify: `docs/REPEATED_EXPERIMENT_RUNBOOK.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Documents operator usage and exact claims boundary only; no runtime interface changes.

- [ ] **Step 1: Update the runbook**

Add a `Detached continuity receipt` section after the local witness section. Explain create-once outside-root storage, exact prefix semantics, the two `python -m` commands, why an older receipt remains valid after append-only growth, and why the guarantee depends on retaining the receipt outside the root's failure/adversary domain.

- [ ] **Step 2: Update Stage 8**

Record provider-free detached receipt infrastructure as completed while explicitly retaining `real repeated execution not performed` and `comparative_claim_permitted: false` boundaries.

---

### Task 5: Full verification and guarded integration

**Files:**
- Review all changed files.

**Interfaces:**
- Uses existing GitHub PR workflow families as final authority.

- [ ] **Step 1: Compare branch to `main`**

Require branch behind count `0`, no workflow/permission/dependency/Vercel/release metadata changes, and only expected files.

- [ ] **Step 2: Open one focused PR**

Document the exact root-only threat closed, the remaining both-root-and-receipt rewrite boundary, and absence of new authority.

- [ ] **Step 3: Verify every triggered workflow family on the unchanged exact head**

Require all real jobs green across Tests, Fast, Deep, Specialist, History, CodeQL, Concurrent Evidence Ledger, Pages verification and any other path-triggered required workflow. Expected PR-only publish/deploy steps may be skipped only where workflow policy explicitly requires it.

- [ ] **Step 4: Check reviews and freshness**

Require no unresolved review threads, PR mergeable, and branch `0` behind `main`.

- [ ] **Step 5: Guarded squash merge**

Merge with `expected_head_sha` equal to the exact verified head. Preserve the feature branch unless separately authorized to delete it.

- [ ] **Step 6: Verify merged `main` and Vercel boundary once**

Confirm merge SHA is identical to `main`, no open PR remains, and no Vercel deployment was triggered for the retired Arena/ytop projects. Do not create an ongoing monitor.
