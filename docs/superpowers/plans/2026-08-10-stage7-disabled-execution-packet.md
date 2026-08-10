# Stage 7 Disabled Execution Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify one deterministic, disabled, public-safe candidate packet for the first Stage 7 private pilot without granting provider execution or spend authority.

**Architecture:** Commit a one-scenario candidate config, disabled policy, dated price source and canonical packet manifest under `examples/stage7_candidate/`. Add a focused provider-free verifier module and repository-only script that reconstruct config/policy/preflight/price commitments, computes a conservative all-tokens-at-highest-rate monetary bound, and fails closed on any drift or enablement.

**Tech Stack:** Python 3.10–3.13 standard library; existing `ExperimentConfig`, `PromptCatalog`, `PilotPolicy`, `build_pilot_preflight`, `PriceSource`, and canonical SHA-256 helpers.

## Global Constraints

- Provider remains `openai-responses`.
- Exact candidate model ID and version marker are `gpt-5.5-2026-04-23`.
- Source date is `2026-08-10` and source reference is `https://developers.openai.com/api/docs/models/gpt-5.5`.
- Candidate scenario list is exactly `["success"]`.
- `external_execution_enabled`, `operator_approved`, and `provider_called` remain `false`.
- Candidate policy reserves 8 calls, 2068 requested output tokens, 2048 total tokens per call, 16384 total tokens, 12 USD cents per call, 96 USD cents aggregate, with a proposed hard ceiling of 100 USD cents.
- Price source records 500 USD cents per million input tokens and 3000 USD cents per million output tokens.
- No network request, API credential access, provider transport construction, runtime dependency, workflow permission change, publication authority, Git mutation authority, Vercel change, or comparative performance claim.

---

### Task 1: Commit the disabled candidate inputs

**Files:**
- Create: `examples/stage7_candidate/experiment.json`
- Create: `examples/stage7_candidate/policy.disabled.json`
- Create: `examples/stage7_candidate/price-source.json`
- Test: `tests/test_stage7_candidate.py`

**Interfaces:**
- Consumes: existing strict config/policy/price schemas.
- Produces: exact source-controlled inputs for packet verification.

- [ ] **Step 1: Write failing committed-input tests**

Tests must load the candidate files and assert the exact model snapshot, source date, one-scenario boundary, disabled execution state, call/token reservations, USD price source, and proposed $1 ceiling constants.

- [ ] **Step 2: Run the focused tests and confirm RED**

```bash
python -m unittest tests.test_stage7_candidate -v
```

Expected: FAIL because candidate files and verifier do not yet exist.

- [ ] **Step 3: Add exact candidate JSON**

`experiment.json` uses the existing fixture contract and prompt version but only scenario `success`, model ID/version `gpt-5.5-2026-04-23`, seed 1304 and two mutation attempts.

`policy.disabled.json` uses:

```json
{
  "provider": "openai-responses",
  "model_id": "gpt-5.5-2026-04-23",
  "model_version": "gpt-5.5-2026-04-23",
  "scenario_ids": ["success"],
  "max_calls": 8,
  "max_requested_output_tokens": 2068,
  "reserved_total_tokens_per_call": 2048,
  "max_reserved_total_tokens": 16384,
  "currency": "USD",
  "reserved_cost_per_call_minor_units": 12,
  "max_cost_minor_units": 100,
  "external_execution_enabled": false
}
```

`price-source.json` uses the existing `PriceSource` fields and 500/3000 USD cents per million input/output tokens.

---

### Task 2: Implement strict provider-free packet reconstruction

**Files:**
- Create: `src/agent_reliability_arena/stage7_candidate.py`
- Modify: `tests/test_stage7_candidate.py`

**Interfaces:**
- Produces: `build_stage7_candidate_packet(candidate_root: Path, catalog_path: Path) -> dict[str, object]`
- Produces: `verify_stage7_candidate(candidate_root: Path, catalog_path: Path) -> dict[str, object]`

- [ ] **Step 1: Write verifier failure tests**

Cover malformed/duplicate JSON, symlinks, policy enablement, model/provider/scenario drift, budget under-reservation, currency mismatch and digest drift.

- [ ] **Step 2: Run focused tests and confirm RED**

Expected: FAIL because `agent_reliability_arena.stage7_candidate` does not exist.

- [ ] **Step 3: Implement the minimal verifier**

The module must:

1. read strict non-symlink JSON objects;
2. parse `ExperimentConfig`, `PromptCatalog`, `PilotPolicy`, and `PriceSource`;
3. build `build_pilot_preflight(...)`;
4. require config/policy agreement and exact one-scenario `success` boundary;
5. require policy execution disabled;
6. calculate `price_source_digest = canonical_json_sha256(price_source.to_dict())`;
7. calculate the conservative bound as:

```python
numerator = policy.max_reserved_total_tokens * max(
    price_source.input_per_million_minor_units,
    price_source.output_per_million_minor_units,
)
conservative_price_bound_minor_units = (numerator + 999_999) // 1_000_000
```

8. require the bound <= preflight reserved cost <= policy hard ceiling;
9. build the exact packet fields from the spec;
10. set `external_execution_enabled=False`, `operator_approved=False`, `provider_called=False`;
11. compute `packet_digest = canonical_json_sha256(unsigned_packet)`.

`verify_stage7_candidate(...)` reads committed `packet.json`, requires an exact closed shape and compares it to the reconstructed packet.

---

### Task 3: Commit the canonical packet and repository verifier script

**Files:**
- Create: `examples/stage7_candidate/packet.json`
- Create: `scripts/verify_stage7_candidate.py`
- Modify: `tests/test_stage7_candidate.py`

**Interfaces:**
- Consumes: `verify_stage7_candidate(...)`.
- Produces: provider-free human/operator verification command.

- [ ] **Step 1: Generate the canonical packet from the reconstructed candidate**

Commit the exact deterministic JSON returned by `build_stage7_candidate_packet(...)` plus its `packet_digest`.

- [ ] **Step 2: Add the script**

The script imports only `Path`, `json`, `sys` and `verify_stage7_candidate`, points by default at `examples/stage7_candidate` and `examples/live_prompt_catalog.json`, and prints a compact summary. It must never import `OpenAIResponsesTransport` or inspect `OPENAI_API_KEY`.

- [ ] **Step 3: Test the script with a fake environment secret**

Set `OPENAI_API_KEY=SHOULD_NOT_BE_READ_OR_PRINTED`, run the script in a subprocess, assert zero exit, `provider_called` false, and assert the marker is absent from stdout/stderr.

---

### Task 4: Update Stage 7 status without overclaiming

**Files:**
- Modify: `docs/PRIVATE_PILOT_RUNBOOK.md`
- Modify: `ROADMAP.md`
- Modify: `README.md` only if needed for a concise provider-free reproduction pointer.

**Interfaces:**
- Produces: accurate operator-facing state.

- [ ] Document the disabled candidate packet, exact model snapshot, dated price source, proposed-not-approved $1 ceiling, and verification command.
- [ ] State explicitly that official model/price facts must be rechecked at execution time.
- [ ] Keep real-provider execution status unperformed and comparative claims prohibited.

---

### Task 5: Final verification and exact-head integration

**Files:** No additional functional files unless a substantive failure is found.

- [ ] Run focused Stage 7 tests.
- [ ] Run the complete provider-free suite.
- [ ] Compare branch to `main`; reject workflow/dependency/release/Vercel drift.
- [ ] Open a focused PR and freeze its exact head.
- [ ] Require all triggered tests, Fast, Specialist, Deep, CodeQL, History, Concurrent Evidence Ledger and Pages verification families to succeed.
- [ ] Confirm no review threads, mergeability and zero commits behind `main`.
- [ ] Guarded squash merge with `expected_head_sha`.
- [ ] Confirm merge SHA is identical to `main`.
- [ ] Preserve the feature branch.
- [ ] Perform the one-time post-merge Vercel boundary check.

The packet remains disabled after merge. A later live run requires a separate private enabled policy and explicit operator approval.