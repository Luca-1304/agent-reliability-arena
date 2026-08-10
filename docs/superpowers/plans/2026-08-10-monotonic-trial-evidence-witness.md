# Monotonic Trial Evidence Witness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-free, append-only, hash-chained root witness that commits each independently verified completed repeated-experiment trial before the replaceable experiment checkpoint advances.

**Architecture:** Put witness parsing, validation, digesting and durable append behavior in a new focused `repeated_witness.py` module. Keep `repeated_runner.py` responsible only for ordering: verify the completed prefix, verify its witness, append the newly completed trial witness, reverify, then advance the ordinary checkpoint. The witness commits exact ledger and verification-summary bytes but explicitly does not claim protection if an actor can rewrite both evidence and witness history.

**Tech Stack:** Python 3.10–3.13 standard library, SHA-256, canonical JSON helper, JSONL, existing transport-ledger verifier, `unittest`, existing GitHub Actions reliability gates.

## Global Constraints

- No provider call, credential, network dependency or paid action is added.
- No runtime dependency is added.
- No publication, Git mutation, Vercel deployment or branch-cleanup authority is added.
- `experiment-evidence-witness.jsonl` is private evidence and contains digests/counts only, never prompts, outputs, provider payloads, credentials or operator notes.
- The witness must advance only after `verify_completed_trial(...)` succeeds and before `experiment-checkpoint.json` advances.
- A completed prefix with a missing/short witness fails closed; history is never silently backfilled.
- An existing witness ahead of the verified completed prefix fails closed.
- Schema-1 and schema-2 transport ledgers remain supported through the existing verifier; transport ledger formats are not changed.
- Existing single-runner assumptions remain; this change does not advertise multi-writer repeated-experiment execution.
- The claim boundary must state that rewriting both local evidence and the local witness can defeat the scheme; external notarization is out of scope.
- Merge requires the unchanged exact PR head to pass every existing required workflow family.

---

### Task 1: Lock the witness contract with RED tests

**Files:**
- Create: `tests/test_repeated_witness.py`

**Interfaces:**
- Consumes later API: `WITNESS_FILENAME`, `append_completed_trial_witness(...)`, `verify_completed_trial_witnesses(...)`.
- Produces provider-free contract tests for exact shape, chaining, evidence binding and fail-closed behavior.

- [ ] **Step 1: Add fixture helpers that create real schema-2 transport ledgers without provider/network use**

Reuse `RecordingTransport`, `ModelCallRequest`, `ModelCallResult` and a tiny scripted transport. Persist `verification-summary.json` bytes separately so the witness can commit both artifacts.

- [ ] **Step 2: Add a first-witness test**

Require one appended record to contain schema `arena-repeated-experiment-evidence-witness-v1`, sequence `1`, the expected trial/plan/preflight identifiers, fresh `ledger_schema_version`, `ledger_records`, `ledger_sha256`, the exact raw-byte SHA-256 of `verification-summary.json`, `previous_witness_digest: null`, and a recomputable `witness_digest`.

- [ ] **Step 3: Add a three-record chain test**

Create `trial-0001` through `trial-0003`, append each witness, and require sequences `[1, 2, 3]` and each later `previous_witness_digest` to equal the immediately prior `witness_digest`.

- [ ] **Step 4: Add fail-closed evidence mutation tests**

After witnessing a trial, mutate its ledger bytes and separately mutate its verification-summary bytes. `verify_completed_trial_witnesses(...)` must reject both before any caller can continue.

- [ ] **Step 5: Add fail-closed witness mutation tests**

Cover missing/short witness, witness ahead of completed prefix, deleted middle line, reordered lines, unknown field, malformed JSON, invalid digest, wrong predecessor and changed trial ID.

- [ ] **Step 6: Verify RED off-PR**

The new test module imports a production module/API that does not yet exist. If a complete local checkout is unavailable in chat, preserve this as structural RED evidence and do not open the PR until implementation is expected green.

---

### Task 2: Implement the focused witness module

**Files:**
- Create: `src/agent_reliability_arena/repeated_witness.py`
- Test: `tests/test_repeated_witness.py`

**Interfaces:**
- Produces: `WITNESS_FILENAME = "experiment-evidence-witness.jsonl"`.
- Produces: `append_completed_trial_witness(experiment_root: Path, trial_id: str, plan_digest: str, preflight_manifest_digest: str) -> dict[str, object]`.
- Produces: `verify_completed_trial_witnesses(experiment_root: Path, completed_trial_ids: list[str], plan_digest: str, preflight_manifest_digest: str) -> list[dict[str, object]]`.
- Consumes: `verify_transport_ledger(...)`, `canonical_json_sha256(...)`.

- [ ] **Step 1: Define exact schema, key set and digest validators**

Use schema `arena-repeated-experiment-evidence-witness-v1`, lowercase 64-hex SHA-256 validation, positive 1-based sequence values, safe non-empty trial IDs and an exact key set.

- [ ] **Step 2: Build current trial commitments from persisted evidence**

For `<experiment_root>/<trial_id>/transport-calls.jsonl`, call `verify_transport_ledger(...)` and capture its actual `schema_version`, `records` and `ledger_sha256`. Read raw bytes of `verification-summary.json` only after rejecting symlinks/non-regular files and calculate `hashlib.sha256(raw).hexdigest()`.

- [ ] **Step 3: Parse and verify the complete witness chain**

Reject empty existing files, blank lines, invalid UTF-8/JSON, non-object rows, duplicate/unknown fields, schema drift, sequence drift, plan/preflight drift, invalid digests, wrong predecessor links and duplicate/unexpected trial IDs. Recompute every `witness_digest` from the unsigned record.

- [ ] **Step 4: Reconcile witness rows to the exact completed prefix**

`verify_completed_trial_witnesses(...)` must require exact length and ordered trial IDs, then regenerate each trial's current ledger/summary commitment and compare every committed field.

- [ ] **Step 5: Append one durable witness record**

Before append, validate any existing witness chain. Refuse duplicate trial IDs. Construct sequence `N+1` with the previous witness digest, canonical-digest it, append exactly one newline-terminated JSON object through `O_APPEND | O_CREAT | O_WRONLY` plus `O_NOFOLLOW` when supported, `flush()` and `os.fsync()`, and set mode `0o600` where supported.

- [ ] **Step 6: Re-run the focused witness tests**

Expected: every `tests/test_repeated_witness.py` case passes provider-free.

---

### Task 3: Integrate witness ordering into the repeated runner

**Files:**
- Modify: `src/agent_reliability_arena/repeated_runner.py`
- Modify: `tests/test_repeated_runner.py`

**Interfaces:**
- Consumes: `WITNESS_FILENAME`, `append_completed_trial_witness(...)`, `verify_completed_trial_witnesses(...)`.
- Preserves: `run_private_repeated_experiment(...)` public signature and existing return shapes.

- [ ] **Step 1: Add runner integration tests before production edits**

Extend the four-trial success test to require the witness file and four chained rows. Extend pause/resume to record the first line bytes after the pause and require resumed execution to preserve that exact prefix while adding two new lines and only ten new provider-shaped calls.

- [ ] **Step 2: Add a resume-rewrite rejection test**

Run one trial and pause. Rewrite the witnessed trial's `verification-summary.json` in a semantically harmless way that changes bytes, then resume with a fresh scripted transport. Require a witness mismatch before the new transport receives any call.

- [ ] **Step 3: Treat the witness as a fixed experiment-root artifact**

Add `WITNESS_FILENAME` to `_FIXED_ROOT_NAMES` so root discovery accepts only the canonical witness filename and still rejects unrelated evidence.

- [ ] **Step 4: Verify existing witness before checkpoint replacement**

After `_discover_trial_prefix(...)`, call `verify_completed_trial_witnesses(...)` with the exact completed trial IDs, plan digest and preflight manifest digest. This must happen before `_replace_checkpoint(...)` and before the new-trial loop.

- [ ] **Step 5: Witness each newly verified trial before checkpoint advancement**

Immediately after `trial_summary == verified`, call `append_completed_trial_witness(...)`, append the trial to the in-memory completed prefix, re-run `verify_completed_trial_witnesses(...)`, and only then replace the ordinary checkpoint.

- [ ] **Step 6: Re-run repeated-runner and witness tests**

Expected: successful completion, pause/resume, abort, drift and new rewrite-rejection behavior all pass without network/provider access.

---

### Task 4: Align release reproduction and documentation

**Files:**
- Modify: `scripts/verify_repeated_release.py` only if its exact artifact expectations require witness awareness.
- Modify: `tests/test_repeated_release.py` only if necessary to assert the permanent witness proof.
- Modify: `docs/REPEATED_EXPERIMENT_RUNBOOK.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Documentation must distinguish transport record chaining, trial witness continuity and final immutable evidence indexing.

- [ ] **Step 1: Extend permanent provider-free reproduction if needed**

Require the four-trial synthetic reproduction to leave a four-record valid witness and the one-trial pause/resume boundary to preserve its first witness record. Keep `provider_called: false` and `comparative_claim_permitted: false`.

- [ ] **Step 2: Update the runbook artifact layout and ordering**

Document `experiment-evidence-witness.jsonl`, its append-only chained role, its precedence over the replaceable checkpoint for continuity, and the fail-closed missing-witness behavior.

- [ ] **Step 3: Document the exact claim limitation**

State plainly that the witness detects changes only while the witness itself remains trustworthy; an actor able to rewrite both local histories requires an external independently controlled anchor to defeat.

- [ ] **Step 4: Fix the stale reliability status in `ROADMAP.md`**

Replace `implemented; exact-head rollout evidence required before treating the current branch as merged` with wording that reflects the already-verified merged architecture. Add Stage 8 completion text for provider-free witnessed completed-trial continuity without implying real-provider execution.

---

### Task 5: Review, exact-head CI and guarded merge

**Files:**
- No additional production files expected.

**Interfaces:**
- Uses existing GitHub PR and Actions gates; no workflow permission changes expected.

- [ ] **Step 1: Review branch diff and freshness**

Require the branch to be `0` behind `main` before merge. Confirm changes are limited to the witness module/tests, repeated-runner integration, permanent reproduction if needed, spec/plan and documentation.

- [ ] **Step 2: Check authority/privacy impact**

Confirm no workflow permission widening, provider configuration change, secret handling change, Vercel deployment change, public raw evidence publication or destructive cleanup.

- [ ] **Step 3: Open one PR when the candidate is expected green**

Describe the exact gap closed, the retained-witness claim boundary and the fact that no real provider call is involved.

- [ ] **Step 4: Require every existing PR workflow family to complete on the unchanged exact head**

This includes tests, Fast, Deep, Specialist, CodeQL, Repository History, Concurrent Evidence Ledger, Pages verification and prerelease verification. Intentional PR-only publication/attestation skips remain acceptable.

- [ ] **Step 5: Inspect review threads and exact head**

Require no unresolved review thread, no unexplained failed/cancelled required job and no head movement after verification.

- [ ] **Step 6: Squash merge with `expected_head_sha` guard**

Verify the resulting `main` SHA. Preserve the feature branch unless separately authorized for destructive cleanup.

- [ ] **Step 7: Perform one reactive Vercel boundary check after merge**

Confirm the GitHub reliability merge did not reactivate retired `agent-reliability-arena` or `ytop-rho` Vercel Git deployments. Do not create ongoing monitoring.