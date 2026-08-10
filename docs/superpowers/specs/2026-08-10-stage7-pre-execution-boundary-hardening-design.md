# Stage 7 pre-execution boundary hardening design

Date: 2026-08-10
Status: approved for implementation by operator continuation after self-audit

## Purpose

Close the final provider-free gaps found in the Stage 7 self-audit before any real OpenAI request, credential use, or spend approval. This change must not make a provider request, enable external execution, change provider credentials, add dependencies, alter workflow/release authority, or close the historical privacy incident.

## Audit findings being addressed

1. The historical hosting/privacy incident is still open, but the paid CLI does not machine-enforce that hold.
2. The paid CLI accepts any internally valid enabled policy whose new digest is supplied; it does not prove that the enabled policy differs from the reviewed disabled Stage 7 candidate only by `external_execution_enabled: false -> true`.
3. The paid CLI uses ordinary `json.loads`, so duplicate keys and symlinked JSON inputs can be accepted even though the candidate verifier rejects them.
4. `OpenAIResponsesTransport` currently substitutes the requested model ID when a provider response omits the `model` field, turning missing provenance into apparent identity agreement.
5. Existing private-pilot CLI tests use generic fixture inputs rather than the actual Stage 7 candidate path.
6. Documentation uses “hard ceiling” language for local reservations in places where the code provides a pre-call reservation/accounting guard rather than an instantaneous provider billing cap.
7. Final design review found that the documented execution order requires output-path safety before API-key lookup, while the prior paid script deferred that check to the runner after the key was read.

## Considered approaches

### A. Documentation-only closure checklist

Keep the current CLI unchanged and rely on the runbook/operator to verify privacy closure and policy equivalence manually.

Rejected: this leaves the exact audit failure intact — review rules would remain stronger than the paid execution boundary.

### B. User-supplied privacy attestation and arbitrary enabled policy

Add another CLI argument pointing at a private closure attestation and continue accepting any reviewed enabled policy digest.

Rejected: a caller could create a fresh local “closed” attestation or materially altered policy without changing reviewed repository state. It adds ceremony without a meaningful authority boundary.

### C. Source-controlled machine gate plus exact candidate-delta verification — selected

Add a fixed source-controlled privacy gate that remains closed until a separately reviewed repository change records verified closure. The paid Stage 7 path reads that gate from the repository with no CLI override. It also reconstructs the committed disabled candidate and requires the private enabled policy to be semantically identical except for the single execution-enable Boolean.

Selected because it makes the code path match the governance already documented and minimizes new authority.

## Architecture

### 1. Machine-readable privacy execution gate

Add `examples/stage7_candidate/privacy-execution-gate.json` with an exact schema including:

- schema version;
- issue number (`14`);
- incident status (`open` or `closed`);
- last verified date;
- `execution_permitted` Boolean;
- concise non-sensitive rationale.

The committed state in this change remains:

- `incident_status: "open"`;
- `execution_permitted: false`.

The live Stage 7 path reads this fixed repository file. It has no command-line option to replace it. Execution refuses before API-key access or output-directory creation while the gate is open.

Closing the gate later requires a separately reviewed source change after the external closure criteria in `docs/HOSTING_PRIVACY_BOUNDARY.md` have actually been verified.

### 2. Exact enabled-policy delta

Extend the Stage 7 candidate module with an execution-policy verifier that:

1. verifies the committed disabled packet first;
2. binds the supplied execution config to the exact committed candidate config digest;
3. strictly loads the private enabled policy;
4. compares its normalized `PilotPolicy.to_dict()` against the committed disabled policy;
5. requires every field to match exactly except `external_execution_enabled`;
6. requires the candidate value to be `false` and private value to be `true`;
7. rebuilds the enabled preflight against the committed candidate experiment and prompt catalogue;
8. confirms call membership, scenario, model, prompt version, token reservations, currency, per-call reservation and maximum reservation are unchanged;
9. returns the candidate packet digest, enabled policy digest and preflight manifest digest for operator review.

No enabled policy is committed.

### 3. Strict paid-path JSON handling

Promote/reuse the candidate verifier’s strict JSON boundary for Stage 7 inputs:

- UTF-8 only;
- JSON object only;
- duplicate-key rejection;
- regular file required;
- symlink rejected;
- exact schema validation remains delegated to `ExperimentConfig`, `PromptCatalog` and `PilotPolicy`.

The paid script must no longer call plain `json.loads(path.read_text(...))` for execution inputs.

### 4. Missing provider model identity fails closed

`OpenAIResponsesTransport` must require a non-empty provider-returned `model` string. Missing, null, blank or non-string model identity becomes non-retryable `TransportError(category="invalid_response")`.

The transport must never synthesize provider identity from `request.model_id`.

The existing `RecordingTransport` equality check remains the second boundary for a present-but-different model ID.

### 5. Prepared private output before credential lookup

The paid Stage 7 command must require its output directory to be deliberately prepared **before** the API key is read.

Before credential lookup, the script requires:

- the output path already exists;
- it is a directory;
- it is not a symlink;
- it is empty;
- on non-Windows platforms, its permission bits are exactly operator-only mode `0700`.

The paid script performs this provider-free precheck. `run_private_paired_pilot(...)` then retains its existing independent root checks when execution begins. A bad, absent, dirty or over-broad output directory therefore fails before credential lookup and is checked again by the runner rather than relying on one layer.

### 6. Actual Stage 7 end-to-end provider-free regression

Add permanent tests using `examples/stage7_candidate/` rather than only generic fixtures. They must prove:

- committed privacy gate blocks the real CLI before secret access/output creation even with all operator flags supplied;
- an enabled private policy with only `external_execution_enabled` changed is accepted by the provider-free execution-policy verifier;
- any change to model, scenario, call ceiling, requested-output ceiling, total-token reservation, currency, per-call cost reservation or maximum monetary reservation is rejected;
- duplicate-key and symlinked private policy inputs are rejected;
- provider response missing `model` is rejected as invalid response;
- present-but-different model identity remains rejected by the recording boundary;
- after an injected test-only closed privacy result, an absent/unsafe output directory fails before the API-key gate;
- a valid prepared output directory reaches the missing-key refusal only after the output precheck passes;
- no test makes a real provider request.

Tests that need to exercise post-privacy-gate logic call isolated functions or patch the in-process privacy verifier with a test-only closed result. The production CLI exposes no privacy-gate override.

## Execution ordering

The paid Stage 7 script should fail closed in this order:

1. explicit operator flags;
2. GitHub Actions refusal;
3. fixed source-controlled privacy gate;
4. committed Stage 7 packet verification;
5. strict config/catalog/private-policy loading and exact candidate binding;
6. reviewed enabled-policy digest/preflight digest checks;
7. prepared private output-path safety checks;
8. API-key lookup;
9. transport construction;
10. runner recheck and provider execution.

The key must not be read and the output directory must not be created when any earlier gate fails. The output directory is deliberately created by the operator before invoking the paid command and is required to be empty/private before the key can be read.

## Budget semantics

Retain the existing numeric candidate:

- 8 planned calls;
- 2,068 maximum requested output tokens;
- 16,384 aggregate reserved tokens;
- 12 USD cents reserved per call;
- 96 USD cents aggregate local reservation;
- proposed-not-approved 100 USD cents maximum local reservation.

Clarify documentation that these are local pre-call reservation/accounting guards, not proof of an instantaneous provider billing cutoff. Before real execution, the operator should additionally use a dedicated restricted provider project/key and a suitably low provider-side spend limit when available.

No provider-side billing setting is changed by this PR.

## Privacy/governance reconciliation

Update:

- `docs/HOSTING_PRIVACY_BOUNDARY.md` to name the machine gate and state that it intentionally remains closed;
- `docs/PRIVATE_PILOT_RUNBOOK.md` so privacy closure is Step 0 before model/pricing or policy enablement;
- `ROADMAP.md` so Stage 7 remaining work includes verified privacy closure before all real-provider steps.

After merge, update issue #14 to replace the stale gpt-5-mini/GBP candidate description with the current GPT-5.5/USD disabled candidate while preserving the `privacy-hold` state and historical closure requirements.

## Non-goals

- no real provider call;
- no API-key creation/read during CI;
- no spend approval;
- no privacy-incident closure claim;
- no Vercel deletion or hosting mutation;
- no GitHub history deletion;
- no new runtime dependency;
- no workflow/permission/release-authority change;
- no automatic retry;
- no comparative performance claim;
- no branch deletion.

## Acceptance

The change is acceptable only if:

1. tests demonstrate the audited failures and the final implementation closes them;
2. the committed privacy gate remains closed;
3. the live Stage 7 path cannot read `OPENAI_API_KEY` or create output while the privacy gate is closed;
4. the private enabled policy can differ from the committed candidate only in the execution-enable Boolean;
5. missing provider model identity fails closed;
6. the paid path validates an already prepared private output directory before credential lookup and the runner retains its own recheck;
7. the actual Stage 7 candidate path has provider-free end-to-end boundary regressions;
8. no workflow, dependency, provider execution, release authority or Vercel path changes;
9. the exact final PR head passes all triggered required repository workflow families before merge.
