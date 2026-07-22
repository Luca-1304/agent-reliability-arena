# Live-model transport boundary

Status: development scaffold for the next empirical phase. It does not change the published deterministic fixture results and it does not claim external-model performance.

## Purpose

The live-model boundary separates request planning, provider communication, strict output parsing, durable evidence, independent verification, metrics and public export. A later experiment can therefore prove what was permitted, what was sent, what returned, what was structurally valid and what independently satisfied the task contract.

## Deterministic request planning

`PromptCatalog` is a source-controlled, schema-versioned catalogue containing exactly six bounded roles: general, strategist, operator, auditor, recovery and synthesiser. Each role has exact instructions and a positive maximum output-token limit. Its canonical SHA-256 digest changes whenever wording, limits or versioning changes.

`LiveRequestFactory` accepts one `ExperimentConfig` and one catalogue with the matching `prompt_version`. It enforces the exact condition, role and attempt grammar, scenario membership, JSON-compatible payloads, deterministic call IDs, canonical input and provenance metadata. Model ID, model version, prompt version, seed, task and contract come only from `ExperimentConfig`.

`build_live_request_preflight(config, catalog)` performs no provider call. It produces a digest-backed permission manifest with one general and seven maximum specialist templates per scenario. Recovery, second operator and second auditor calls are conditional. The manifest proves request permission and held-constant experiment inputs—not execution, completion or model quality.

The source-controlled example catalogue is `examples/live_prompt_catalog.json`. Its role instructions explicitly prohibit tool execution, state mutation and unsupported completion claims.

## Strict live role output contracts

`parse_live_role_output(role, output_text, expected_attempt_number=...)` accepts one bounded provider output and fails closed unless it is exactly one valid JSON object for the requested role.

The parser rejects:

- empty, non-UTF-8-encodable or over-65,536-byte text;
- markdown fences, prose, trailing values, arrays and scalar roots;
- duplicate keys at any nesting level;
- non-finite JSON numbers;
- unknown or missing fields;
- unsafe absolute, drive-qualified, backslash, empty-segment, dot or traversal paths;
- invalid role, action, attempt, audit, recovery or synthesis invariants.

General and operator output become frozen `GeneralProposal` and `OperatorProposal` objects. Strategist, auditor, recovery and synthesiser output reuse the existing `StrategyPlan`, `AuditRecord`, `RecoveryRecord` and `SynthesisRecord` schemas. An operator attempt may be matched against the expected request attempt.

`ParsedRoleOutput` stores the typed value, canonical payload, SHA-256 of the exact provider-output bytes and SHA-256 of the canonical validated payload. Parsing proves structure—not truth, authorisation, completion or successful mutation. A general completion claim remains untrusted data, and synthesis still cannot claim completion unless verifier status is `VERIFIED_COMPLETE`.

## Included transport contracts

- `ModelCallRequest` records condition, role, versioned model and prompt data, exact instructions and input, output limit, seed and metadata.
- `ModelCallResult` records output, refusal or incomplete outcome, provider identifiers, status, latency, processing time, token usage and exact response-byte digest.
- `TransportError` separates retryable network, HTTP and provider failures from terminal invalid responses.
- `ModelTransport` is the provider-neutral execution protocol.

## OpenAI Responses adapter

`OpenAIResponsesTransport` uses HTTPS with `store: false`, deterministic client request IDs, provider request-ID and processing-time capture, token accounting, output/refusal/incomplete preservation, structured failure classification and exact response-byte SHA-256. Credentials default only to `api.openai.com`; a different HTTPS host requires explicit opt-in. Tests use injected network and clock functions, so the suite performs no paid request.

## Tamper-evident transport ledger

`RecordingTransport` wraps any `ModelTransport` and persists each result or structured error to an append-only UTF-8 JSONL ledger. Records include the canonical request, one outcome, sequence, timestamp, provider, cross-linked identifiers and a record SHA-256.

`verify_transport_ledger(path)` is read-only and provider-free. It rejects malformed JSON, invalid UTF-8, blank lines, unsupported schemas, broken sequences, changed request or record digests, inconsistent result links, invalid outcome shapes, symlink paths and non-regular files. Valid summaries report result/error counts and the exact ledger-byte SHA-256.

Existing non-empty ledgers must verify before append. The current ledger supports one writer only. Ledgers are **private evidence** and may contain full prompts and model output; they are excluded from public export and never contain API credentials or raw provider response bytes.

## Deliberate exclusions

This work does not yet:

- connect validated live requests and outputs to the general or specialist orchestrators;
- authorise or execute proposed tool actions;
- compare proposals with the exact task contract before execution;
- estimate prices or retry automatically;
- support concurrent ledger writers or prompt redaction;
- publish raw provider responses or private ledger records;
- produce comparative model results.

Those behaviours require separate reviewed integrations with bounded execution policies, repeated paired runs, dated price tables, uncertainty reporting and disclosure-safe export.

## Verification

The tests and release gate cover:

- exact prompt catalogue, request grammar, provenance and 64 provider-free templates;
- strict valid output for all six roles;
- malformed JSON, duplicate keys, non-finite numbers, size, field and unsafe-path rejection;
- exact-byte and canonical role-output digests;
- existing strategist, auditor, recovery and synthesis invariants;
- response, refusal, incomplete and provider-error handling;
- request IDs, usage, latency, endpoint and credential protections;
- result/error ledger recording, continuation, digest and tamper checks;
- source, release, CLI, wheel and clean-wheel verification on Python 3.10–3.13.
