# Provider Model Identity Enforcement Design

## Goal

Make the recorded provider boundary fail closed when a provider returns a different `model_id` from the exact model requested, while preserving auditable, hash-chained mismatch evidence and preventing the mismatched output from reaching orchestration.

## Why this stage exists

The private-pilot runbook already treats provider/model drift as an immediate abort condition. The OpenAI Responses transport sends `ModelCallRequest.model_id` directly to the provider, but `RecordingTransport` currently validates only call ID, request digest and provider before returning a successful `ModelCallResult`. A provider-reported model mismatch can therefore pass through the evidence boundary today.

This change closes that gap before any real-provider pilot.

## Architecture

`RecordingTransport` is the enforcement point because it is the first provider-neutral boundary that simultaneously sees the exact request, the provider result and the private tamper-evident ledger.

For an ordinary matching result, behaviour remains unchanged.

For `result.model_id != request.model_id`:

1. the mismatched `ModelCallResult` is not returned to the caller;
2. `RecordingTransport` constructs a non-retryable `model_identity_mismatch` error record;
3. the error record is appended through the existing locked, fsynced, schema-2 hash-chain path;
4. the error evidence contains only the fields needed to audit model identity without copying provider output text:
   - `expected_model_id`;
   - `observed_model_id`;
   - `response_id`;
   - `raw_response_sha256`;
   - existing client/provider request identifiers when available;
5. a `TransportError(category="model_identity_mismatch", retryable=False)` is raised after durable evidence append;
6. the private pilot catches that terminal error, preserves `abort.json` and the independently verifiable partial ledger, and makes no further provider-shaped call.

The output text from the mismatched provider response is never forwarded to orchestration and is not duplicated into the mismatch error payload.

## Ledger verification

The existing error-record shape remains compatible: `outcome_type="error"`, `result=null`, `error` is an object. No ledger schema-version bump is required.

The verifier gains category-specific validation for `model_identity_mismatch` records:

- `expected_model_id` must be a non-empty string equal to the recorded request's `model_id`;
- `observed_model_id` must be a non-empty string and must differ from `expected_model_id`;
- `response_id` must be a non-empty string;
- `raw_response_sha256` must be exactly 64 lowercase hexadecimal characters;
- `retryable` must be `false`;
- provider and request-digest invariants continue to be enforced by the existing record validation.

This makes the mismatch evidence independently verifiable rather than relying only on the recorder having behaved correctly.

## Error and authority boundary

This change does not:

- call a provider;
- enable external execution;
- alter provider credentials;
- change model selection or pricing;
- add a dependency;
- change GitHub workflow permissions;
- add release/publication authority;
- add Git or Vercel mutation authority;
- expose provider output in the mismatch error payload;
- make any comparative model-performance claim.

The feature remains provider-neutral and applies to every `RecordingTransport` consumer. Exact equality is intentional: callers that want reproducible model identity must request the exact provider identifier they are willing to accept.

## Tests

Provider-free regression tests must prove:

1. a matching result is returned and recorded as a normal result;
2. a mismatched result is never returned and raises non-retryable `model_identity_mismatch`;
3. the mismatch ledger contains one hash-chained error record with expected/observed model IDs, response ID and raw-response SHA-256 but no copied output text;
4. `verify_transport_ledger` accepts correctly formed mismatch evidence and counts it as an error;
5. tampering any mismatch identity field without recomputing the record digest is rejected by the existing digest check;
6. recomputing a record digest after changing category-specific mismatch fields is still rejected by the new semantic verifier;
7. a private paired pilot aborts immediately on first model mismatch, preserves a valid partial ledger, and does not begin the next condition/provider call.

## Acceptance

Merge only the unchanged exact PR head after every triggered required workflow family succeeds. Preserve the feature branch and perform only the existing one-time Vercel boundary check after merge.