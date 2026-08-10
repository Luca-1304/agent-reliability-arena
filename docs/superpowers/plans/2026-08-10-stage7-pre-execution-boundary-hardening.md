# Stage 7 Pre-Execution Boundary Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the first real Stage 7 execution path enforce the unresolved privacy hold, exact reviewed candidate policy, strict JSON boundary and explicit provider model identity before any key access, output creation or provider call.

**Architecture:** Keep the existing disabled Stage 7 packet as the source of truth. Add a source-controlled privacy execution gate that remains closed, extend `stage7_candidate.py` with strict reusable input and exact enabled-policy-delta verification, harden the real CLI to call those gates before secret access, and make the OpenAI transport reject missing model provenance rather than synthesizing it.

**Tech Stack:** Python standard library only; existing `unittest` suite; existing GitHub Actions reliability gates; no new dependency.

## Global Constraints

- No real provider call or API-key use during development, tests or CI.
- `examples/stage7_candidate/privacy-execution-gate.json` must remain `execution_permitted: false` in this change.
- The private enabled policy may differ from the committed disabled candidate only by `external_execution_enabled: false -> true`.
- Missing provider-returned model identity must fail closed as non-retryable `invalid_response`.
- No workflow, dependency, release/publication authority, Git mutation authority or Vercel deployment change.
- No privacy-incident closure claim, spend approval, automatic retry or comparative model-performance claim.
- Preserve feature branch after merge.

---

### Task 1: Machine-readable privacy gate

**Files:**
- Create: `examples/stage7_candidate/privacy-execution-gate.json`
- Modify: `src/agent_reliability_arena/stage7_candidate.py`
- Test: `tests/test_stage7_execution_boundary.py`

**Interfaces:**
- Produces: `verify_stage7_privacy_gate(path: Path) -> dict[str, object]`
- Committed gate fields: `schema_version`, `issue_number`, `incident_status`, `last_verified_date`, `execution_permitted`, `rationale`

- [x] Write tests requiring exact gate shape, duplicate-key rejection, symlink rejection, inconsistent `closed/false` or `open/true` rejection, and the committed gate to verify as open with execution refused.
- [x] Run the focused source suite and confirm RED because the gate/verifier did not exist and the old CLI reached the API-key check.
- [x] Add the committed gate with issue 14, `incident_status: "open"`, `execution_permitted: false`, date `2026-08-10`, and non-sensitive rationale that Vercel projects still exist and platform-level historical removal is unconfirmed.
- [x] Implement `verify_stage7_privacy_gate` using strict regular non-symlink JSON object parsing and exact-field validation.
- [x] Confirm the new privacy-gate tests pass on the implementation head.

### Task 2: Exact private enabled-policy delta

**Files:**
- Modify: `src/agent_reliability_arena/stage7_candidate.py`
- Test: `tests/test_stage7_execution_boundary.py`

**Interfaces:**
- Produces: `verify_stage7_execution_policy(candidate_root: Path, config_path: Path, catalog_path: Path, enabled_policy_path: Path) -> dict[str, object]`
- Reuses: `verify_stage7_candidate(...)`, strict JSON reader, `PilotPolicy`, `build_pilot_preflight(...)`

- [x] Write tests where a private copy changing only `external_execution_enabled` to `true` is accepted.
- [x] Add regressions that independently change model ID, model version, prompt version, scenario, `max_calls`, requested-output ceiling, per-call total-token reservation, aggregate total-token reservation, currency, per-call monetary reservation and maximum monetary reservation; every mutation fails.
- [x] Add config-drift, duplicate-key and symlinked private-policy tests.
- [x] Confirm RED before implementation.
- [x] Implement the execution-policy verifier: verify the committed packet first, bind the supplied execution config to the candidate digest, compare normalized policy dictionaries with only the Boolean delta allowed, rebuild enabled preflight and return candidate packet digest, enabled policy digest and enabled preflight manifest digest.
- [x] Confirm the new execution-policy tests pass on the implementation head.

### Task 3: Provider model provenance must be explicit

**Files:**
- Modify: `src/agent_reliability_arena/transports/openai_responses.py`
- Create: `tests/test_openai_model_provenance.py`

**Interfaces:**
- Existing: `OpenAIResponsesTransport.complete(request: ModelCallRequest) -> ModelCallResult`
- New invariant: successful/processable provider response requires a non-empty returned `model` string.

- [x] Add tests for missing `model`, `model: null`, blank model and non-string model; each must raise `TransportError` with category `invalid_response` and `retryable == false`.
- [x] Confirm RED under the previous fallback behavior.
- [x] Remove the fallback to `request.model_id`; reject absent/invalid provider model before constructing `ModelCallResult`.
- [x] Confirm the focused model-provenance regression passes while existing valid-model transport tests remain green.

### Task 4: Harden the real Stage 7 CLI boundary

**Files:**
- Modify: `scripts/run_private_pilot.py`
- Modify: `tests/test_private_pilot_script.py`
- Create: `tests/test_stage7_private_script_boundary.py`

**Interfaces:**
- The CLI uses fixed repository paths for `examples/stage7_candidate/` and its privacy gate; there is no privacy-gate override argument.
- Reuses: `verify_stage7_privacy_gate`, `verify_stage7_candidate`, `verify_stage7_execution_policy`, strict Stage 7 JSON reader.

- [x] Add subprocess regressions using the actual Stage 7 candidate. With all operator flags present, the committed open privacy gate refuses before output creation or API-key lookup.
- [x] Add regression proving a materially altered enabled policy cannot become a valid Stage 7 execution policy even when it has its own internally valid digest.
- [x] Add duplicate-key and symlinked execution-policy regressions.
- [x] Confirm RED because the old paid CLI reached the API-key check and used the generic fixture boundary.
- [x] Change script order to: approvals -> GitHub Actions refusal -> fixed privacy gate -> committed packet verification -> strict candidate/config/catalog/policy binding -> reviewed enabled policy digest/preflight validation -> API-key lookup -> transport -> runner.
- [x] Replace plain JSON execution-input loading with the strict Stage 7 reader.
- [x] Keep output creation in the existing runner, after every pre-secret gate.
- [x] Align the legacy private-pilot script tests with the actual Stage 7 candidate and privacy-first ordering.
- [ ] Confirm the complete source suite is green on the post-alignment head.

### Task 5: Governance and budget semantics reconciliation

**Files:**
- Modify: `docs/HOSTING_PRIVACY_BOUNDARY.md`
- Modify: `docs/PRIVATE_PILOT_RUNBOOK.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Documentation must match executable state: privacy gate open, provider execution disabled, candidate GPT-5.5/USD values unchanged.

- [x] Update hosting/privacy docs to name the machine gate and state that a future reviewed source change is required after external closure evidence.
- [x] Make privacy closure Step 0 in the private pilot runbook before model/pricing refresh or policy enablement.
- [x] Clarify that 16,384 tokens / 96 cents / proposed $1 maximum are local pre-call reservation/accounting controls, not an instantaneous provider billing cutoff; recommend a dedicated restricted provider project/key and a low provider-side spend backstop before execution.
- [x] Update Stage 7 ROADMAP remaining work so privacy closure is explicitly first.
- [x] Preserve the current GPT-5.5/USD candidate and remove stale current-path assumptions rather than rewriting historical records.

### Task 6: Full verification and integration

**Files:**
- No new implementation scope; verify all changed files.

- [ ] Compare branch to `main`; confirm only expected Stage 7 boundary/tests/docs files changed and branch is not behind.
- [ ] Update PR #115 with exact final head and explicit no-provider/no-spend scope, then mark ready for review.
- [ ] Require the full final-head repository workflow family set: Tests, Reliability Fast Gate, Reliability Specialist Gates, Auditable policy-driven Deep reliability gate, CodeQL, Repository history boundary, Concurrent Evidence Ledger and GitHub Pages verification.
- [ ] Confirm no review threads, mergeability, 0 behind `main`, unchanged exact head and all required workflow families successful.
- [ ] Squash-merge only the tested exact head; preserve the feature branch.
- [ ] Confirm merge SHA is identical to `main`.
- [ ] Perform one-time post-merge Vercel boundary check only; do not start monitoring.
- [ ] Update issue #14 to the current GPT-5.5/USD candidate while retaining `privacy-hold` and the unresolved external closure criteria.
