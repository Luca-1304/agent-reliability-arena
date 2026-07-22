# Tamper-Evident Transport Ledger Design

## Decision

Add a provider-neutral `RecordingTransport` wrapper that writes one append-only JSON object per model call to a private JSONL ledger. Add `verify_transport_ledger(path)` to validate every record before replay, analysis or export.

This design is approved under the standing instruction to expand Agent Reliability Arena incrementally, with each layer proven before the next.

## Context

The Arena now has a verified provider-neutral model transport and an OpenAI Responses adapter that records request digests, result or refusal state, incomplete outcomes, token usage, latency and request identifiers. Those objects currently exist only in process memory unless a later orchestrator persists them.

A real-model experiment needs a durable record that does not trust an agent summary or a provider success shape. The ledger must remain independent of any one provider and must not execute a model by itself.

## Approaches considered

### 1. Append-only JSONL ledger — selected

Each call becomes one canonical JSON line with a line-level SHA-256 digest. It uses only the Python standard library, is easy to inspect, stream and version, and works with the repository's existing JSON artifact style.

Trade-off: concurrent writers are deliberately unsupported in this increment.

### 2. SQLite ledger

SQLite would provide transactions, indexing and concurrency control. It would also introduce schema migrations, binary artifacts and more operational surface before the experiment needs query-scale storage.

### 3. One artifact directory per call

Per-call directories would align with the existing experiment bundle, but would create many small files and make ordered replay and aggregate verification harder.

## Architecture

### `RecordingTransport`

`RecordingTransport` implements `ModelTransport` and wraps another `ModelTransport`.

For each `complete(request)` call it:

1. invokes the wrapped transport exactly once;
2. records the complete `ModelCallRequest` and either the `ModelCallResult` or structured `TransportError`;
3. assigns a strictly increasing sequence number;
4. computes a canonical SHA-256 `record_digest` over the record excluding that digest field;
5. appends one UTF-8 JSON line and flushes it to disk;
6. returns the original result or re-raises the original `TransportError`.

It does not retry, mutate provider output, redact prompts or execute tools.

### Ledger record schema

Every line contains:

- `schema_version`: `"1"`;
- `sequence`: positive integer starting at `1`;
- `recorded_at`: caller-supplied or clock-generated UTC timestamp;
- `provider`: wrapped transport provider identifier;
- `request`: full `ModelCallRequest.to_dict()` payload;
- `request_digest`: canonical request SHA-256;
- `outcome_type`: `"result"` or `"error"`;
- `result`: `ModelCallResult.to_dict()` or `null`;
- `error`: `TransportError.to_dict()` or `null`;
- `record_digest`: canonical SHA-256 of all preceding fields.

A result record must have `result.request_digest == request_digest` and matching call IDs. An error record must contain a structured `TransportError` and no result.

### Verification

`verify_transport_ledger(path)` reads the file without modifying it and rejects:

- missing, empty, symlinked or non-regular ledger paths;
- invalid UTF-8 or JSON;
- blank lines;
- unsupported schema versions;
- non-contiguous sequences;
- mismatched request digests;
- mismatched result request digests or call IDs;
- invalid result/error exclusivity;
- line-level digest changes.

It returns a summary with record, result and error counts plus the SHA-256 of the exact ledger bytes.

## File safety

- The ledger parent directory must already exist and be a real directory.
- A ledger path may be new or an existing verified regular file.
- Symlink ledger paths are rejected.
- Existing non-empty ledgers are verified before appending.
- This release supports one writer per ledger. Concurrent writers are explicitly outside scope.
- The ledger is private evidence and may contain prompts. Public export remains a separate later step.

## Error handling

Only structured `TransportError` failures are persisted and re-raised. Unexpected programming exceptions are not converted into apparently valid provider evidence.

If persistence fails after a provider call, `RecordingTransport` raises a ledger persistence error rather than returning an unrecorded success. The underlying result is not silently treated as durable evidence.

## Testing

Tests use fake transports and temporary directories. They cover:

- successful result recording and return identity;
- structured error recording and re-raising;
- reopening and continuing a verified ledger sequence;
- request, result, sequence and record digest validation;
- byte-level ledger summary digest;
- tampered-line rejection;
- symlink and missing-parent rejection;
- no provider execution during verification.

The complete repository matrix must continue to pass on Python 3.10–3.13 from source and clean wheels.

## Explicit exclusions

This increment does not add live orchestrator calls, automatic retries, concurrent writing, prompt redaction, pricing, public export or model-performance claims.
