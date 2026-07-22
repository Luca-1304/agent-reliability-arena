# Private real-provider pilot runbook

Status: **release-candidate operating procedure**. The repository does not ship a public live-provider execution command. This document prepares a later private pilot tracked in issue #14; it does not authorise one by itself.

## Governing rule

No credential or provider request is used until the exact experiment configuration, prompt catalogue and pilot policy have been reviewed through the provider-free preflight command.

The release candidate has two independent execution barriers:

1. `PilotExecutionGate` requires an enabled policy, the exact reviewed policy digest and explicit external-execution approval.
2. `OpenAIResponsesTransport` refuses its real network opener unless `external_execution_approved=True` is supplied explicitly.

Injected test openers remain available for provider-free tests and release fixtures.

## Preflight-only procedure

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
- prints the exact policy, configuration, contract and prompt-catalogue digests;
- lists every permitted call and the maximum requested-output-token total;
- reports conservative total-token and monetary reservations;
- records `provider_called: false`.

Review the entire output, especially:

- provider and dated model identifier;
- model, prompt and configuration versions;
- scenario list;
- maximum call count;
- requested output-token ceiling;
- reserved total-token ceiling;
- currency and reserved monetary ceiling;
- policy and manifest digests;
- `external_execution_enabled`, which must remain `false` during release-candidate verification.

## Private policy preparation

A later pilot must use a private copy of the policy file. Do not commit an enabled pilot policy unless every value is deliberately suitable for public disclosure.

The policy schema contains no credential field. Unknown fields, including `api_key`, are rejected.

For the first pilot:

- use one provider;
- use one explicitly dated model snapshot;
- use one scenario;
- permit exactly the preflight call ceiling;
- disable automatic retries;
- reserve total tokens conservatively before each call;
- reserve a worst-case minor-currency amount before each call;
- keep the total monetary ceiling low enough that the full reservation is acceptable;
- stop rather than expanding the policy during a run.

`reserved_cost_per_call_minor_units` is an operator-supplied conservative reservation. It is not measured provider cost and is not presented as a price estimate. Actual measured usage and a separately dated price table belong in later empirical evidence.

## Private run-directory rules

Every real-provider run must use a new private directory outside the public reference bundle.

Required properties:

- owned by the operator account;
- readable and writable only by the operator unless a named reviewer is deliberately granted access;
- not inside `web/`, `web/data/` or another public-export directory;
- not synchronised to a public repository;
- not reused after a failed or aborted run;
- never a symlink;
- empty before execution;
- retained until its ledger and manifest have been independently verified.

On Unix-like systems, create the directory under a restrictive mask such as `umask 077` and verify mode `0700`. On Windows, remove inherited broad access and confirm that only the operator and explicitly approved reviewers have access before use.

Recommended private structure:

```text
private_runs/<run-id>/
  preflight.json
  policy.json
  transport-calls.jsonl
  general/
  specialist/
  verification-summary.json
  operator-notes.md
```

Never place credentials, shell history, complete environment dumps or raw authentication headers in this directory.

## Credential handling

- Supply `OPENAI_API_KEY` through the process environment only.
- Do not write the key into JSON, source files, notebooks, command arguments, logs, screenshots, issue comments or ledger metadata.
- Do not paste it into GitHub Actions variables for this private local pilot.
- Clear the environment variable when the process ends.
- Rotate the credential immediately if it appears in output or an unexpected file.
- Stop before retrying if any error message contains authentication material.

The transport stores neither the API key nor raw HTTP authorisation headers in `ModelCallResult`, `TransportError` or the transport ledger.

## Required approvals before a real call

A real-provider caller must possess all of the following:

1. the exact reviewed policy JSON;
2. the exact `PilotPolicy.digest` printed by preflight;
3. a policy with `external_execution_enabled: true`;
4. `PilotExecutionGate(..., reviewed_policy_digest=<exact digest>, external_execution_approved=True)`;
5. `OpenAIResponsesTransport(..., external_execution_approved=True)`;
6. a private empty run directory;
7. an acceptable worst-case token and monetary reservation;
8. an operator decision to proceed after reading the preflight.

Missing any item means no external call.

## Immediate abort conditions

Stop the pilot immediately and make no further paid request when any of these occurs:

- policy, configuration, contract or prompt-catalogue digest mismatch;
- a request not listed in the preflight permission manifest;
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

After an abort, repair and reproduce the defect provider-free before considering another paid attempt.

## Post-run procedure

1. Stop external execution and clear the API key.
2. Verify the transport ledger read-only.
3. Confirm call counts and reservations match the reviewed policy.
4. Preserve failed and aborted calls; do not remove unfavourable evidence.
5. Record the provider, exact model identifier, timestamps and operator notes.
6. Keep private evidence private.
7. Generate no public comparison until the disclosure-safe export and repeated-experiment stages are complete.

## Claims boundary

Completing one private pilot can establish that the real-provider path executed and produced preserved evidence for that controlled run. It cannot establish representative model performance, universal superiority of specialist orchestration, production readiness or general tool safety.
