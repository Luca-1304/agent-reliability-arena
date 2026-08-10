# Private real-provider pilot runbook

Status: **runner implemented and provider-free rehearsed; real-provider pilot not yet executed**. This document governs the local pilot tracked in issue #14. It does not authorise spending or provider access by itself.

## Governing rule

No credential or provider request is used until the exact experiment configuration, prompt catalogue and pilot policy have been reviewed through the provider-free preflight command.

The system has three independent execution barriers:

1. `PilotExecutionGate` requires an enabled policy, the exact reviewed policy digest, exact preflight call membership and explicit external-execution approval.
2. `OpenAIResponsesTransport` refuses its real network opener unless `external_execution_approved=True` is supplied explicitly.
3. `scripts/run_private_pilot.py` refuses GitHub Actions and requires the exact operator confirmation phrase before policy loading, credential access, output creation or transport construction.

**External network execution is disabled by default.** Injected test transports remain available for provider-free tests and release rehearsals.

Provider-returned model identity is enforced again at the private recording boundary. A `ModelCallResult` whose `model_id` differs from the exact requested `ModelCallRequest.model_id` is never returned to orchestration as a successful result. Instead, `RecordingTransport` durably appends a non-retryable `model_identity_mismatch` error record containing the expected and observed model IDs, response ID and raw-response SHA-256, then raises. The ledger verifier independently checks those mismatch fields.

## Provider-free preflight

The committed example policy is disabled:

```bash
arena-preflight-pilot \
  --config examples/fixture_experiment.json \
  --catalog examples/live_prompt_catalog.json \
  --policy examples/pilot_policy.disabled.json
```

This command:

- reads local JSON files only;
- creates no run directory;
- reads no API key;
- constructs no provider transport;
- makes no network request;
- prints exact policy, configuration, contract and prompt-catalogue digests;
- lists every permitted call and the requested-output-token maximum;
- reports conservative total-token and monetary reservations;
- records `provider_called: false`.

Review the complete output, especially:

- provider and dated model identifier;
- model, prompt and configuration versions;
- scenario list;
- call ceiling and every permitted call ID;
- requested-output-token ceiling;
- reserved total-token ceiling;
- currency and reserved monetary ceiling;
- policy and manifest digests;
- `external_execution_enabled`.

## Disabled Stage 7 candidate packet

A source-controlled candidate packet now makes the intended first real-pilot boundary reviewable **without enabling execution**:

```bash
python scripts/verify_stage7_candidate.py
```

The candidate under `examples/stage7_candidate/` pins, for review only:

- provider `openai-responses`;
- exact dated model ID/version `gpt-5.5-2026-04-23`;
- one `success` scenario;
- the existing `fixture-prompts-v1` catalogue and exact file-write contract;
- eight permitted preflight calls;
- 2,068 maximum requested output tokens;
- 2,048 reserved total tokens per permitted call and 16,384 aggregate;
- a dated `2026-08-10` USD price source recording 500 minor units per million input tokens and 3,000 per million output tokens;
- a conservative 50-cent planning bound obtained by pricing **every** reserved token at the higher output-token rate;
- a 96-cent aggregate policy reservation;
- a **proposed, not approved** $1.00 hard monetary ceiling.

The committed packet must verify with all three authority flags false:

- `external_execution_enabled: false`;
- `operator_approved: false`;
- `provider_called: false`.

The verifier reconstructs the configuration, policy, preflight and price-source commitments instead of trusting the packet JSON. It makes no provider request, reads no API credential and creates no private run directory.

This candidate is a review artifact, not durable permission to spend. Before any later real execution, re-check that the exact model snapshot is still available and that the provider's current pricing still supports the reviewed reservation. If either changed, stop and create a new reviewed candidate rather than editing around the old commitments.

## Provider-free paired rehearsal

The release suite rehearses the private runner without a credential or network request. It executes one controlled success scenario through both conditions and verifies:

- one General call;
- Strategist, Operator, Auditor and Synthesiser calls;
- five unique calls from the reviewed preflight plan;
- five tamper-evident ledger records;
- seven private evidence artifacts;
- both independently verified condition outcomes;
- `comparative_claim_permitted: false`.

The tests also prove that malformed role output creates `abort.json`, preserves the partial ledger and prevents reuse of the dirty run directory. A separate provider-free regression returns a deliberately different provider-reported model ID and proves the first call becomes a verifiable `model_identity_mismatch` ledger error, the pilot aborts, and no second provider-shaped call begins.

## Private policy preparation

Use a **private copy** of the disabled Stage 7 candidate policy when preparing a real run. Do not commit an enabled pilot policy unless every value is deliberately suitable for public disclosure.

The policy schema contains no credential field. Unknown fields, including `api_key`, are rejected.

For the first real pilot:

- start from the reviewed `examples/stage7_candidate/experiment.json` and a private copy of `examples/stage7_candidate/policy.disabled.json`;
- freshly confirm the exact dated model snapshot and dated price source before enabling anything;
- use provider `openai-responses`;
- use exactly one scenario;
- permit exactly the preflight call ceiling;
- disable automatic retries;
- reserve total tokens conservatively before each call;
- reserve a worst-case minor-currency amount before each call;
- keep the total monetary ceiling low enough that the full reservation is acceptable;
- stop rather than expanding the policy during a run.

`reserved_cost_per_call_minor_units` is an operator-supplied conservative reservation. It is not measured provider cost or a built-in price estimate. Actual usage and a separately dated price table belong in later empirical evidence.

## Private run-directory rules

Every real-provider run must use a new private directory outside the public reference bundle.

Required properties:

- owned by the operator account;
- readable and writable only by the operator unless a named reviewer is deliberately granted access;
- not inside `web/`, `web/data/` or another public-export directory;
- not synchronised to a public repository;
- not reused after success, failure or abort;
- never a symlink;
- empty before execution;
- retained until its ledger and evidence have been independently verified.

On Unix-like systems, create the directory under a restrictive mask such as `umask 077` and verify mode `0700`. On Windows, remove inherited broad access and confirm that only the operator and explicitly approved reviewers have access before use.

The runner creates:

```text
private_runs/<run-id>/
  preflight.json
  policy.json
  run-start.json
  transport-calls.jsonl
  general/
    result.json
    sandbox/
  specialist/
    result.json
    sandbox/
  verification-summary.json   # completed run only
  abort.json                  # aborted run only
```

Never place credentials, shell history, complete environment dumps or raw authentication headers in this directory.

## Credential handling

- Supply `OPENAI_API_KEY` through the local process environment only.
- Do not write the key into JSON, source files, notebooks, command arguments, logs, screenshots, issue comments or ledger metadata.
- Do not paste it into GitHub Actions variables for this private local pilot.
- Clear the environment variable when the process ends.
- Rotate the credential immediately if it appears in output or an unexpected file.
- Stop before retrying if any error message contains authentication material.

The transport stores neither the API key nor raw HTTP authorisation headers in `ModelCallResult`, `TransportError` or the transport ledger.

## Local execution procedure

The paid path is a repository script, not a public installed command. It is never invoked by CI or the release verifier.

1. Verify the committed disabled packet with `python scripts/verify_stage7_candidate.py`.
2. Freshly re-check exact model availability and current provider pricing. If either differs from the committed candidate, stop and review a new packet.
3. Copy `examples/stage7_candidate/policy.disabled.json` to a private location.
4. Change only the privately reviewed policy fields needed for execution, including `external_execution_enabled: true`; do not change the committed candidate.
5. Run provider-free preflight against `examples/stage7_candidate/experiment.json`, the existing prompt catalogue and that private enabled policy.
6. Review the complete output and record the exact `policy_digest`.
7. Explicitly approve the full worst-case monetary reservation only if it remains acceptable.
8. Set `OPENAI_API_KEY` in the local process environment.
9. Run:

```bash
python scripts/run_private_pilot.py \
  --config examples/stage7_candidate/experiment.json \
  --catalog examples/live_prompt_catalog.json \
  --policy /private/path/pilot-policy.json \
  --output /private/path/private_runs/<run-id> \
  --reviewed-policy-digest <exact-64-character-digest> \
  --approve-external-execution \
  --operator-confirmation I_APPROVE_ONE_PRIVATE_PILOT
```

The script has no API-key argument. It refuses execution when:

- either approval is missing or the confirmation phrase differs;
- `GITHUB_ACTIONS=true`;
- the policy provider is not `openai-responses`;
- the reviewed digest differs from the policy or preflight;
- external execution remains disabled;
- `OPENAI_API_KEY` is absent from the local environment;
- the output directory is dirty, unsafe or reused.

## Required approvals before a real call

A real-provider caller must possess all of the following:

1. a freshly re-verified Stage 7 candidate whose model availability and dated price assumptions have been checked for the execution date;
2. the exact reviewed private enabled policy JSON;
3. the exact `PilotPolicy.digest` printed by preflight;
4. a policy with `external_execution_enabled: true`;
5. explicit approval of the full monetary and token reservation;
6. `--approve-external-execution`;
7. `--operator-confirmation I_APPROVE_ONE_PRIVATE_PILOT`;
8. `OpenAIResponsesTransport(..., external_execution_approved=True)` as constructed by the script;
9. a private, empty, non-symlink run directory;
10. `OPENAI_API_KEY` supplied through the local environment only;
11. a deliberate operator decision after reading the exact preflight.

Missing any item means no external call.

## Immediate abort conditions

Stop the pilot immediately and make no further paid request when any of these occurs:

- policy, configuration, contract or prompt-catalogue digest mismatch;
- a request not listed in the reviewed preflight plan;
- duplicate call ID or attempt drift;
- provider identity or provider-reported model ID drift from the exact requested model snapshot;
- API-key or authentication-header exposure;
- ledger write or ledger verification failure;
- non-empty, unsafe, symlinked or unexpectedly shared run directory;
- strict role-output parse failure;
- proposed path or content differing from the configured contract;
- sandbox security rejection;
- independent observation or verifier inconsistency;
- audit, recovery or synthesis text conflicting with authoritative evidence;
- call, requested-output-token, reserved-total-token or monetary ceiling exhaustion;
- provider response that cannot be classified and persisted safely;
- unexpected retry, parallel writer or second process touching the ledger.

On abort, `abort.json` and any verifiable partial ledger are retained. Repair and reproduce the defect provider-free before considering another paid attempt.

## Post-run procedure

1. Stop external execution and clear the API key.
2. Verify the transport ledger read-only.
3. Confirm call counts and reservations match the reviewed policy.
4. Preserve failed and aborted calls; do not remove unfavourable evidence.
5. Record the provider, exact model identifier, timestamps and operator notes.
6. Keep private evidence private.
7. Generate no public comparison until disclosure-safe export and repeated-experiment stages are complete.

## Claims boundary

The disabled candidate packet establishes only that one proposed configuration is internally consistent and budget-bounded against a dated public price source while execution remains disabled. Completing one later private pilot can establish that the real-provider path executed and produced preserved evidence for that controlled run. Neither establishes representative model performance, universal superiority of specialist orchestration, production readiness or general tool safety.
