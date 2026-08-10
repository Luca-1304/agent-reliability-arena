# Provider Model Identity Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject and preserve auditable evidence for any provider result whose reported model ID differs from the exact requested model ID before orchestration can consume the result.

**Architecture:** Extend the existing provider-neutral `RecordingTransport` boundary. Matching results retain current behaviour; mismatches become durable schema-2 error records carrying minimal identity evidence and raise a non-retryable `TransportError`. Extend ledger verification with semantic checks for this error category and add a private-pilot regression proving the mismatch aborts before the next provider-shaped call.

**Tech Stack:** Python standard library, pytest, existing transport ledger schema 2 and private-pilot infrastructure.

## Global Constraints

- No real provider request or external execution.
- No new runtime dependency.
- No workflow, permission, release, Git mutation or Vercel authority change.
- Do not copy mismatched provider output text into the error record.
- Keep existing schema-1/schema-2 ledger compatibility.
- Exact model-ID equality is intentional.
- Merge only the unchanged exact PR head after all triggered required workflow families succeed.

---

### Task 1: Lock the model-identity transport contract

**Files:**
- Create: `tests/test_recording_model_identity.py`
- Modify: `src/agent_reliability_arena/transports/recording.py`

**Interfaces:**
- Consumes: `ModelCallRequest`, `ModelCallResult`, `ModelUsage`, `TransportError`, `RecordingTransport`, `verify_transport_ledger`.
- Produces: `RecordingTransport.complete()` rejects `result.model_id != request.model_id` with category `model_identity_mismatch` after writing one valid error record.

- [ ] **Step 1: Write failing tests**

Create tests that build a minimal scripted transport returning a caller-selected model ID. Assert matching identity remains a normal result. Assert mismatched identity raises `TransportError` with `category == "model_identity_mismatch"`, `retryable is False`, and produces one ledger error record containing `expected_model_id`, `observed_model_id`, `response_id`, and `raw_response_sha256` while excluding the response `output_text`.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
python -m pytest tests/test_recording_model_identity.py -q
```

Expected: the mismatch test fails because current `RecordingTransport.complete()` returns the mismatched result instead of rejecting it.

- [ ] **Step 3: Implement minimal recorder rejection**

In `RecordingTransport.complete()` after existing call/request/provider checks and before the normal result commit:

```python
if result.model_id != request.model_id:
    error = TransportError(
        "Provider-reported model_id does not match the requested model_id.",
        category="model_identity_mismatch",
        retryable=False,
        client_request_id=result.client_request_id,
        provider_request_id=result.provider_request_id,
    )
    evidence = {
        **error.to_dict(),
        "expected_model_id": request.model_id,
        "observed_model_id": result.model_id,
        "response_id": result.response_id,
        "raw_response_sha256": result.raw_response_sha256,
    }
    self._commit_record(
        request,
        outcome_type="error",
        result=None,
        error=evidence,
    )
    raise error
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused pytest command. Expected: PASS.

---

### Task 2: Make mismatch evidence independently verifiable

**Files:**
- Modify: `src/agent_reliability_arena/transports/recording.py`
- Modify: `tests/test_recording_model_identity.py`

**Interfaces:**
- Consumes: schema-1/schema-2 ledger rows and error-category data.
- Produces: `verify_transport_ledger()` semantically validates `model_identity_mismatch` evidence.

- [ ] **Step 1: Add failing semantic-tamper tests**

After generating a valid mismatch record, rewrite the JSON row, change one of `expected_model_id`, `observed_model_id`, `response_id`, or `raw_response_sha256`, recompute `record_digest` using `canonical_json_sha256`, and assert verification still fails. Include cases where expected model no longer equals request model, observed equals expected, response ID is empty, digest is malformed, or retryable is changed to true.

- [ ] **Step 2: Run focused tests and verify RED**

Expected: at least one recomputed semantic tamper currently passes because the generic error verifier does not interpret model-identity fields.

- [ ] **Step 3: Add category-specific verifier**

Add a focused helper in `recording.py` that validates only `error.category == "model_identity_mismatch"` and enforces:

```text
expected_model_id == request.model_id
observed_model_id != expected_model_id
response_id is non-empty
raw_response_sha256 is lowercase 64-hex
retryable is false
```

Call it from the existing error-record branch without changing other error categories.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the focused tests. Expected: PASS.

---

### Task 3: Prove private-pilot terminal behaviour

**Files:**
- Modify or create focused test under `tests/` using existing private-pilot fixtures/helpers.
- Modify: `docs/PRIVATE_PILOT_RUNBOOK.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: `run_private_paired_pilot(...)` and a scripted provider-neutral transport.
- Produces: provider-model drift aborts after the first mismatched call with a verifiable one-error ledger and no subsequent condition/provider call.

- [ ] **Step 1: Write failing private-pilot regression**

Use the existing one-scenario enabled policy/test setup. Return a mismatched `ModelCallResult.model_id` on the first call. Assert:

```text
run raises TransportError(category="model_identity_mismatch")
transport call count == 1
abort.json exists
transport-calls.jsonl verifies
ledger records == 1
ledger errors == 1
no second condition/provider call occurs
```

- [ ] **Step 2: Run focused private-pilot test and confirm current failure where applicable**

The test should fail on the pre-change recorder because the mismatched result can reach orchestration rather than becoming the terminal model-identity error.

- [ ] **Step 3: Update runbook/roadmap**

Document that model identity is enforced from provider response to evidence boundary before orchestration trusts output. Keep Stage 7 explicitly unexecuted and provider-free.

- [ ] **Step 4: Run focused and complete provider-free suite**

Run:

```bash
python -m pytest tests/test_recording_model_identity.py -q
python -m pytest -q
```

Expected: PASS.

---

### Task 4: Exact-head review and repository authority

**Files:** No additional production changes unless a substantive issue is found.

- [ ] Review branch diff against `main`; reject workflow/dependency/provider/release/Vercel drift.
- [ ] Open focused PR from `reliability/provider-model-identity-2026-08-10`.
- [ ] Freeze exact PR head.
- [ ] Require all triggered tests, Fast, Specialist, Deep, CodeQL, History, Concurrent Evidence Ledger and Pages verification families to succeed.
- [ ] Confirm no unresolved review threads and branch is zero behind `main`.
- [ ] Squash merge with `expected_head_sha` guard.
- [ ] Confirm merge SHA is identical to `main`.
- [ ] Preserve feature branch.
- [ ] Perform one-time Vercel boundary check only.