# Private real-provider pilot runbook

Status: **runner implemented and provider-free rehearsed; real-provider pilot not yet executed**. This document governs the local pilot tracked in issue #14. It does not authorise spending or provider access by itself.

## Governing rule

No credential or provider request is used until the exact experiment configuration, prompt catalogue and pilot policy have been reviewed through the provider-free preflight command.

The system has three independent execution barriers:

1. `PilotExecutionGate` requires an enabled policy, the exact reviewed policy digest, exact preflight call membership and explicit external-execution approval.
2. `OpenAIResponsesTransport` refuses its real network opener unless `external_execution_approved=True` is supplied explicitly.
3. `scripts/run_private_pilot.py` refuses GitHub Actions and requires the exact operator confirmation phrase before policy loading, credential access, output creation or transport construction.

**External network execution is disabled by default.** Injected test transports remain available for provider-free tests and release rehearsals.

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

## Provider-free paired rehearsal

The release suite rehearses the private runner without a credential or network request. It executes one controlled success scenario through both conditions and verifies:

- one General call;
- Strategist, Operator, Auditor and Synthesiser calls;
- five unique calls from the reviewed preflight plan;
- five tamper-evident ledger records;
- seven private evidence artifacts;
- both independently verified condition outcomes;
- `comparative_claim_permitted: false`.

The tests also prove that malformed role output creates `abort.json`, preserves the partial ledger and prevents reuse of the dirty run directory.

## Private policy preparation

Use a private copy of the policy file. Do not commit an enabled pilot policy unless every value is deliberately suitable for public disclosure.

The policy schema contains no credential field. Unknown fields, including `api_key`, are rejected.

For the first real pilot:

- use provider `openai-responses`;
- use one explicitly dated model snapshot;
- use one scenario;
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

1. Copy the disabled policy to a private location.
2. Set the exact dated model ID/version, one scenario, conservative reservations and `external_execution_enabled: true`.
3. Run provider-free preflight against that private policy.
4. Review the complete output and record the exact `policy_digest`.
5. Confirm the full worst-case monetary reservation is acceptable.
6. Set `OPENAI_API_KEY` in the local process environment.
7. Run:

```bash
python scripts/run_private_pilot.py \
  --config examples/fixture_experiment.json \
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

1. the exact reviewed private policy JSON;
2. the exact `PilotPolicy.digest` printed by preflight;
3. a policy with `external_execution_enabled: true`;
4. an acceptable full monetary and token reservation;
5. `--approve-external-execution`;
6. `--operator-confirmation I_APPROVE_ONE_PRIVATE_PILOT`;
7. `OpenAIResponsesTransport(..., external_execution_approved=True)` as constructed by the script;
8. a private, empty, non-symlink run directory;
9. `OPENAI_API_KEY` supplied through the local environment only;
10. a deliberate operator decision after reading the preflight.

Missing any item means no external call.

## Immediate abort conditions

Stop the pilot immediately and make no further paid request when any of these occurs:

- policy, configuration, contract or prompt-catalogue digest mismatch;
- a request not listed in the reviewed preflight plan;
- duplicate call ID or attempt drift;
- provider or model-version drift;
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

Completing one private pilot can establish that the real-provider path executed and produced preserved evidence for that controlled run. It cannot establish representative model performance, universal superiority of specialist orchestration, production readiness or general tool safety.
