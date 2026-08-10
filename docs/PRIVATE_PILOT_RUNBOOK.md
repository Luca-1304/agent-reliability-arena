# Private real-provider pilot runbook

Status: **runner, disabled execution packet and pre-execution boundary implemented provider-free; historical privacy hold remains open; real-provider pilot not yet executed**. This document governs the local pilot tracked in issue #14. It does not authorise spending or provider access by itself.

## Governing rule

No credential or provider request is used until the historical privacy incident is independently closed, the source-controlled execution gate is reviewed closed, and the exact experiment configuration, prompt catalogue and private enabled policy have passed the provider-free Stage 7 checks.

The system has independent execution barriers:

1. `examples/stage7_candidate/privacy-execution-gate.json` is a fixed source-controlled gate. While `execution_permitted: false`, the paid script stops before API-key lookup, output creation or transport construction. There is no CLI override.
2. The committed disabled Stage 7 packet reconstructs and verifies the exact candidate configuration, prompt catalogue, disabled policy, preflight and dated price-source commitments.
3. `verify_stage7_execution_policy(...)` requires the private enabled policy to match the committed disabled candidate in every policy field except the single `external_execution_enabled: false -> true` transition. It also binds the execution config and preflight back to the reviewed candidate.
4. `PilotExecutionGate` requires the exact reviewed enabled-policy digest, exact preflight call membership and explicit external-execution approval.
5. `OpenAIResponsesTransport` refuses its real network opener unless `external_execution_approved=True` is supplied explicitly.
6. `scripts/run_private_pilot.py` refuses GitHub Actions and requires the exact operator confirmation phrase before the later execution boundary can be crossed.

**External network execution remains disabled while the privacy gate is open.** Injected test transports remain available for provider-free tests and release rehearsals.

Provider model provenance is fail-closed at two layers. `OpenAIResponsesTransport` requires the provider response to include a non-empty model identity; it does not synthesize a missing model from the request. `RecordingTransport` then requires that returned model identity to equal the exact requested `ModelCallRequest.model_id`. A present-but-different model is durably recorded as a non-retryable `model_identity_mismatch` error before orchestration can consume it, and the ledger verifier independently checks that evidence.

## Step 0 — Historical privacy closure

Do **not** begin the live steps below while `examples/stage7_candidate/privacy-execution-gate.json` remains open.

The closure criteria are governed by `docs/HOSTING_PRIVACY_BOUNDARY.md` and require all of the following:

1. affected immutable Vercel deployment URLs return `404` or `410`;
2. both redundant Vercel projects are deleted or confirmed removed by Vercel;
3. GitHub confirms removal of affected historical blobs, pull-request references and cached views;
4. the canonical GitHub Pages CV still passes source, staged and live privacy verification;
5. no tracked public file contains a Vercel deployment URL or private contact value.

After those conditions are independently verified, close the machine gate only through a focused reviewed repository change. That gate-closing change must pass the normal exact-head repository authority before merge. Absence of new Vercel deployments does not satisfy the closure criteria by itself.

## Provider-free preflight

The general provider-free preflight command remains available for reviewing a policy without a key or network request. For Stage 7 execution preparation, use the pinned candidate configuration and the private enabled-policy copy only after Step 0 is complete:

```bash
arena-preflight-pilot \
  --config examples/stage7_candidate/experiment.json \
  --catalog examples/live_prompt_catalog.json \
  --policy /private/path/pilot-policy.json
```

This command:

- reads local JSON files only;
- creates no run directory;
- reads no API key;
- constructs no provider transport;
- makes no network request;
- prints exact policy, configuration, contract and prompt-catalogue digests;
- lists every permitted call and the requested-output-token maximum;
- reports local total-token and monetary reservations;
- records `provider_called: false`.

Review the complete output, especially:

- provider and dated model identifier;
- model, prompt and configuration versions;
- scenario list;
- call ceiling and every permitted call ID;
- requested-output-token ceiling;
- reserved total-token amount;
- currency and monetary reservation;
- policy and manifest digests;
- `external_execution_enabled`.

## Disabled Stage 7 candidate packet

The source-controlled candidate packet makes the intended first real-pilot boundary reviewable **without enabling execution**:

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
- a 96-cent aggregate local policy reservation;
- a **proposed, not approved** $1.00 maximum local monetary reservation;
- an open source-controlled privacy execution gate.

The committed packet must verify with all three authority flags false:

- `external_execution_enabled: false`;
- `operator_approved: false`;
- `provider_called: false`.

The verifier reconstructs the configuration, policy, preflight and price-source commitments instead of trusting the packet JSON. It makes no provider request, reads no API credential and creates no private run directory.

This candidate is a review artifact, not durable permission to spend. Before any later real execution, re-check that the exact model snapshot is still available and that current provider pricing still supports the reviewed reservation. If either changed materially, stop and create a new reviewed candidate rather than editing around the old commitments.

## Provider-free paired rehearsal

The release suite rehearses the private runner without a credential or network request. It executes one controlled success scenario through both conditions and verifies:

- one General call;
- Strategist, Operator, Auditor and Synthesiser calls;
- five unique calls from the reviewed preflight plan;
- five tamper-evident ledger records;
- seven private evidence artifacts;
- both independently verified condition outcomes;
- `comparative_claim_permitted: false`.

The tests also prove that malformed role output creates `abort.json`, preserves the partial ledger and prevents reuse of the dirty run directory. Separate provider-free regressions prove that a missing provider model identity is invalid, a different provider-reported model becomes a verifiable `model_identity_mismatch`, the pilot aborts, and no later provider-shaped call begins.

The actual Stage 7 candidate path is also exercised provider-free: the committed open privacy gate stops the paid script before credential lookup or output creation, and the execution-policy verifier accepts only the single reviewed enablement delta while rejecting model, scenario, call, token, currency and monetary drift plus duplicate-key or symlinked execution inputs.

## Private policy preparation

Only after Step 0, use a **private copy** of `examples/stage7_candidate/policy.disabled.json`. Do not commit the enabled policy.

For the first real pilot the only permitted semantic difference from the committed disabled candidate policy is:

```text
external_execution_enabled: false -> true
```

Do not alter the model, model version, prompt version, scenario list, call ceiling, requested-output reservation, per-call total-token reservation, aggregate total-token reservation, currency, per-call monetary reservation or maximum monetary reservation. `verify_stage7_execution_policy(...)` rejects any such drift even if the altered policy has a newly reviewed digest.

The policy schema contains no credential field. Unknown fields, including `api_key`, are rejected. Stage 7 execution inputs are read as regular non-symlink UTF-8 JSON objects with duplicate-key rejection.

## Reservation and provider-side spend controls

The committed candidate values are deliberately conservative local controls:

- eight planned calls;
- 2,068 maximum requested output tokens;
- 16,384 aggregate reserved total tokens;
- 12 USD cents reserved per call;
- 96 USD cents aggregate local reservation;
- proposed-not-approved 100 USD cents maximum local reservation;
- 50 USD cents conservative planning estimate when every reserved token is priced at the recorded output-token rate.

These values are **pre-call reservation/accounting guards**. They are not proof of an instantaneous provider billing cutoff and they do not replace provider-side spend controls.

Before a real run, use a dedicated OpenAI API project where practical, create a restricted key for that project, and configure a suitably low provider-side spend limit or budget control if the provider offers one. Treat that provider-side control as an independent backstop rather than a replacement for the Arena policy. Do not weaken the Arena reservation because a provider-side limit exists.

`reserved_cost_per_call_minor_units` is an operator-supplied conservative reservation. It is not measured provider cost or a billing statement. Actual usage and a separately dated price source belong in post-run empirical evidence.

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

- Use a dedicated restricted project key when practical.
- Supply `OPENAI_API_KEY` through the local process environment only.
- Do not write the key into JSON, source files, notebooks, command arguments, logs, screenshots, issue comments or ledger metadata.
- Do not paste it into GitHub Actions variables for this private local pilot.
- Set the key only after every provider-free boundary has passed.
- Clear the environment variable when the process ends.
- Rotate the credential immediately if it appears in output or an unexpected file.
- Stop before retrying if any error message contains authentication material.

The transport stores neither the API key nor raw HTTP authorisation headers in `ModelCallResult`, `TransportError` or the transport ledger.

## Local execution procedure

The paid path is a repository script, not a public installed command. It is never invoked by CI or the release verifier.

0. Complete the historical privacy closure criteria and merge a separately reviewed change that closes `examples/stage7_candidate/privacy-execution-gate.json`.
1. Re-verify the committed disabled packet with `python scripts/verify_stage7_candidate.py`.
2. Freshly re-check exact model availability and current provider pricing. If either materially differs from the committed candidate, stop and review a new packet.
3. Prepare a dedicated restricted provider project/key and a suitably low provider-side spend backstop where available, but do not put the key in the environment yet.
4. Copy `examples/stage7_candidate/policy.disabled.json` to a private location and change **only** `external_execution_enabled` to `true`.
5. Verify the private execution policy against the committed candidate, then run the provider-free preflight using `examples/stage7_candidate/experiment.json`, the existing prompt catalogue and that private policy.
6. Review the complete output and record the exact enabled `policy_digest` and preflight manifest digest.
7. Explicitly approve the full local token and monetary reservation only if it remains acceptable.
8. Create/verify the fresh private run directory and then set `OPENAI_API_KEY` in the local process environment.
9. Run exactly once:

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

The script has no API-key argument and no privacy-gate override. It refuses execution when:

- either operator approval is missing or the confirmation phrase differs;
- `GITHUB_ACTIONS=true`;
- the fixed source-controlled privacy gate is still open or malformed;
- the committed Stage 7 packet does not reconstruct exactly;
- execution config/catalog drift from the reviewed candidate;
- the private enabled policy differs from the candidate by anything except the single execution-enable Boolean;
- the reviewed digest differs from the exact enabled policy or rebuilt preflight;
- provider/model/prompt/scenario/call/token/currency/monetary commitments drift;
- `OPENAI_API_KEY` is absent after all earlier checks pass;
- the output directory is dirty, unsafe or reused.

## Required approvals before a real call

A real-provider caller must possess all of the following:

1. independently verified historical privacy closure and a reviewed source-controlled gate with `execution_permitted: true`;
2. a freshly re-verified Stage 7 candidate whose exact model availability and dated price assumptions have been checked for the execution date;
3. a private enabled policy differing from the committed candidate only by `external_execution_enabled: true`;
4. the exact enabled `PilotPolicy.digest` and exact rebuilt preflight manifest digest;
5. explicit approval of the full local monetary and token reservation;
6. a dedicated restricted provider project/key and low provider-side spend backstop where practical;
7. `--approve-external-execution`;
8. `--operator-confirmation I_APPROVE_ONE_PRIVATE_PILOT`;
9. `OpenAIResponsesTransport(..., external_execution_approved=True)` as constructed by the script;
10. a private, empty, non-symlink run directory;
11. `OPENAI_API_KEY` supplied through the local environment only after all earlier gates pass;
12. a deliberate operator decision after reading the exact preflight.

Missing any item means no external call.

## Immediate abort conditions

Stop the pilot immediately and make no further paid request when any of these occurs:

- privacy-gate or candidate commitment inconsistency;
- policy, configuration, contract or prompt-catalogue digest mismatch;
- a request not listed in the reviewed preflight plan;
- duplicate call ID or attempt drift;
- missing provider-returned model identity;
- provider identity or provider-reported model ID drift from the exact requested model snapshot;
- API-key or authentication-header exposure;
- ledger write or ledger verification failure;
- non-empty, unsafe, symlinked or unexpectedly shared run directory;
- strict role-output parse failure;
- proposed path or content differing from the configured contract;
- sandbox security rejection;
- independent observation or verifier inconsistency;
- audit, recovery or synthesis text conflicting with authoritative evidence;
- call, requested-output-token, reserved-total-token or local monetary reservation exhaustion;
- provider response that cannot be classified and persisted safely;
- unexpected retry, parallel writer or second process touching the ledger.

On abort, `abort.json` and any verifiable partial ledger are retained. Repair and reproduce the defect provider-free before considering another paid attempt. Do not automatically retry the first real pilot.

## Post-run procedure

1. Stop external execution and clear the API key.
2. Verify the transport ledger read-only.
3. Confirm call counts and local reservations match the reviewed policy.
4. Compare measured provider usage/billing evidence with the recorded reservation and dated price source; do not describe a reservation as measured cost.
5. Preserve failed and aborted calls; do not remove unfavourable evidence.
6. Record the provider, exact model identifier, timestamps and operator notes.
7. Keep private evidence private.
8. Generate no public comparison until disclosure-safe export and repeated-experiment stages are complete.

## Claims boundary

The disabled candidate packet establishes only that one proposed configuration is internally consistent and locally reservation-bounded against a dated public price source while execution remains disabled. A closed privacy gate would establish only that the repository's documented external closure evidence was reviewed; it would not prove provider deletion beyond that evidence. Completing one later private pilot can establish that the real-provider path executed and produced preserved evidence for that controlled run. None of these establishes representative model performance, universal superiority of specialist orchestration, production readiness or general tool safety.
