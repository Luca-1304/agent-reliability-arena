# Live-model transport boundary

Status: provider-free integration scaffold for the next empirical phase. It does not change the published deterministic fixture results and it does not claim external-model performance.

## Purpose

The live-model boundary separates request planning, provider communication, strict output parsing, bounded orchestration, durable evidence, independent verification, metrics and public export. The system can now prove what was permitted, what was sent, what returned, what was structurally valid, which controlled action occurred and what independently satisfied the task contract—without contacting a provider.

## Deterministic request planning

`PromptCatalog` is a source-controlled, schema-versioned catalogue containing exactly six bounded roles: general, strategist, operator, auditor, recovery and synthesiser. Each role has exact instructions and a positive maximum output-token limit.

`LiveRequestFactory` enforces the condition, role and attempt grammar, scenario membership, JSON-compatible payloads, deterministic call IDs, canonical input and provenance metadata. Model ID, model version, prompt version, seed, task and contract come only from `ExperimentConfig`.

`build_live_request_preflight(config, catalog)` performs no provider call. It creates a digest-backed permission manifest with one general and seven maximum specialist templates per scenario. Recovery, second operator and second auditor are conditional. It proves request permission and held-constant inputs—not execution or model quality.

## Strict live role output contracts

`parse_live_role_output(...)` fails closed unless one provider output is exactly one valid JSON object for the requested role. It rejects markdown, trailing text, duplicate keys, non-finite numbers, oversized output, wrong fields, unsafe paths and invalid role invariants.

General and operator output become frozen `GeneralProposal` and `OperatorProposal` objects. Strategist, auditor, recovery and synthesiser output reuse `StrategyPlan`, `AuditRecord`, `RecoveryRecord` and `SynthesisRecord`. `ParsedRoleOutput` records exact-byte and canonical-payload SHA-256 values.

Parsing proves structure—not truth, authorisation, completion or successful mutation.

## Provider-free live orchestration

`LiveGeneralOrchestrator` and `LiveSpecialistOrchestrator` integrate the request factory, any `ModelTransport`, strict role parsing, the existing controlled sandbox and the independent completion verifier.

The general path performs one permitted role call, requires an exact-contract `write_file` proposal, runs one controlled scenario and preserves the model completion claim as measured but untrusted data.

The specialist path performs bounded strategist, operator, auditor, recovery and synthesiser calls. Every consequential decision is cross-checked against locally derived evidence:

- operator path and content must equal the configured contract before execution;
- independent observation outranks source reports and role text;
- audit decisions and conflict markers must equal the evidence-derived result;
- security rejection is terminal and cannot trigger recovery;
- recovery must match the active retryable scenario and one-attempt policy;
- second operator output must still match the exact contract;
- synthesis status and completion claim must equal the final verifier status.

`LiveScenarioExecution` records ordered validated role calls, sandbox attempts, final verifier status, completion claim, recovery and security flags. `LiveRoleCallRecord` links each request digest, provider response, exact response digest and validated output digests.

The permanent release fixture uses scripted in-memory responses to prove three complete paths:

1. general exact success: one role call, one verified attempt;
2. specialist false-success recovery: seven role calls, two attempts, verified recovery;
3. specialist path-traversal failure: four role calls, terminal security rejection, no recovery.

All three use `RecordingTransport`; their private ledgers are independently verified. No network or paid request is involved.

## Transport and provider adapter

`ModelCallRequest`, `ModelCallResult`, `TransportError` and `ModelTransport` form the provider-neutral execution boundary.

`OpenAIResponsesTransport` uses HTTPS with `store: false`, deterministic client request IDs, provider request-ID and processing-time capture, token accounting, output/refusal/incomplete preservation, structured failure classification and exact response-byte SHA-256. Credentials default only to `api.openai.com`; another HTTPS host requires explicit opt-in. Tests inject network and clock functions.

## Tamper-evident transport ledger

`RecordingTransport` persists each result or structured error to append-only UTF-8 JSONL. Records include the canonical request, one outcome, sequence, timestamp, provider, cross-linked identifiers and a record digest.

`verify_transport_ledger(path)` is read-only and provider-free. It rejects malformed JSON, invalid UTF-8, broken sequences, changed digests, inconsistent result links, invalid outcome shapes, symlinks and non-regular files. Existing non-empty ledgers must verify before append.

Ledgers are **private evidence** and may contain full prompts and outputs. They are excluded from public export and never contain API credentials or raw provider response bytes.

## Deliberate exclusions

This work does not yet:

- use a real model provider in an Arena experiment;
- expose a live-execution CLI;
- generalise execution beyond the controlled exact file-write contract;
- estimate dated prices or retry provider failures automatically;
- support concurrent ledger writers or prompt redaction;
- publish raw provider responses or private ledgers;
- produce comparative external-model results.

Those steps require explicit provider configuration, controlled spending, repeated paired runs, uncertainty reporting and disclosure-safe export.

## Verification

The tests and release gate cover:

- exact prompt catalogue, request grammar, provenance and 64 provider-free templates;
- strict outputs and digests for all six roles;
- malformed JSON, duplicate keys, number, size, field and path rejection;
- general success and preserved false-completion behavior;
- specialist recovery, timeout-after-write and terminal security behavior;
- contract, audit and synthesis override rejection;
- response, refusal, incomplete and provider-error handling;
- request IDs, usage, latency, endpoint and credential protections;
- result/error ledger recording, continuation, digest and tamper checks;
- three release-level end-to-end scenarios and three verified private ledgers;
- source, release, CLI, wheel and clean-wheel verification on Python 3.10–3.13.
