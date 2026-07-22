# Live-model transport boundary

Status: development scaffold for the next empirical phase. It does not change the published deterministic fixture results and it does not claim external-model performance.

## Purpose

The live-model boundary separates request planning, provider communication, durable evidence, independent verification, metrics and public export. A later experiment can therefore prove what was permitted, what was sent, what returned and what independently satisfied the task contract.

## Deterministic request planning

`PromptCatalog` is a source-controlled, schema-versioned catalogue containing exactly six bounded roles: general, strategist, operator, auditor, recovery and synthesiser. Each role has exact instructions and a positive maximum output-token limit. Its canonical SHA-256 digest changes whenever wording, limits or versioning changes.

`LiveRequestFactory` accepts one `ExperimentConfig` and one prompt catalogue with the matching `prompt_version`. It is the only planned construction path for live `ModelCallRequest` objects. It enforces:

- general condition: general role, attempt 1 only;
- specialist strategist, recovery and synthesiser: attempt 1 only;
- specialist operator and auditor: attempts 1 or 2 only;
- scenario membership in the experiment configuration;
- JSON-compatible role payloads with string object keys and finite numbers;
- deterministic call IDs, canonical JSON input and provenance metadata;
- model ID, model version, prompt version, seed, task and contract copied from `ExperimentConfig` rather than caller overrides.

`build_live_request_preflight(config, catalog)` performs no provider call. It produces a digest-backed permission manifest containing one general template and seven maximum specialist templates per scenario. Recovery, second operator and second auditor calls are marked conditional. The manifest records the held-constant fairness fingerprint, configuration, contract and catalogue digests. It proves request permission and experiment consistency—not execution, completion or model quality.

The source-controlled example catalogue is `examples/live_prompt_catalog.json`. Its role instructions explicitly prohibit tool execution, state mutation and unsupported completion claims.

## Included transport contracts

- `ModelCallRequest` records the condition, role, model identifier and version, prompt version, exact instructions and input, output limit, seed and local metadata.
- Prompt whitespace is preserved, and each request has a canonical SHA-256 digest so paired conditions can prove exactly which versioned request was issued.
- `ModelCallResult` records normal output, a valid refusal or an incomplete outcome, together with the provider response identifier, returned model identifier, status, measured wall-clock latency, provider processing time, token usage, client and provider request IDs, and the SHA-256 digest of the exact response bytes.
- `TransportError` separates retryable network, HTTP and provider-side generation failures from terminal invalid responses while preserving safe request provenance.
- `ModelTransport` is the provider-neutral execution protocol.

## OpenAI Responses adapter

`OpenAIResponsesTransport` uses the HTTPS Responses endpoint with:

- the model, instructions, input and maximum output-token limit from the versioned request;
- `store: false`;
- local Arena identifiers in request metadata;
- a deterministic `X-Client-Request-Id` derived from the request digest;
- `OPENAI_API_KEY` read from the environment unless explicitly supplied by a caller;
- no SDK dependency and no automatic retries;
- provider request-ID capture from the `x-request-id` response header;
- provider processing-time capture from `openai-processing-ms` when available;
- input, output, total, cached-input and reasoning-token accounting when returned;
- output, refusal and incomplete-outcome preservation;
- structured provider-failure errors with retry classification;
- SHA-256 recording of the exact provider response bytes without persisting the API key.

The adapter accepts HTTPS only and sends credentials to `api.openai.com` by default. A different host requires `allow_custom_endpoint=True` explicitly. Tests use injected openers and clocks, so the source suite never performs a paid or external request.

## Tamper-evident transport ledger

`RecordingTransport` wraps any `ModelTransport` and persists every completed call or structured `TransportError` to an append-only UTF-8 JSONL ledger.

Each record contains the complete canonical request, exactly one result or structured error, a strictly increasing sequence, evidence timestamp, provider identifier, cross-linked call IDs and request digests, and a SHA-256 digest covering the complete record except its own digest field.

`verify_transport_ledger(path)` reads the ledger without executing a provider or changing the file. It rejects malformed JSON, invalid UTF-8, blank lines, unsupported schemas, broken sequences, changed request or record digests, inconsistent result links, invalid outcome shapes, symlink paths and non-regular files. A valid summary reports result and error counts plus the SHA-256 of the exact ledger bytes.

Existing non-empty ledgers must verify before append. Successful results are not returned as durable evidence if persistence fails. The current ledger supports one writer only.

Transport ledgers are **private evidence**. They may contain full prompts and model output. They are not included in the static public export, and they store response digests rather than raw provider response bytes or API credentials.

## Deliberate exclusions

This work does not yet:

- connect live requests to the general or specialist orchestrators;
- execute tools proposed by a model;
- parse role JSON into bounded action schemas;
- estimate prices or retry automatically;
- support concurrent ledger writers or prompt redaction;
- publish raw provider responses or private ledger records;
- produce comparative model results.

Those behaviours require separate reviewed integrations with bounded schemas, repeated paired runs, dated price tables, uncertainty reporting and disclosure-safe export.

## Verification

The tests and release gate cover:

- exact role catalogue coverage, parsing, versioning and digest stability;
- prompt-version drift and request-grammar rejection;
- deterministic general and specialist requests;
- canonical input, call IDs and fairness provenance;
- provider-free preflight generation and 64 permitted templates for the reference fixture;
- transport response, refusal, incomplete and error handling;
- request IDs, token usage, latency and exact response-byte hashing;
- credential and endpoint protections;
- successful and failed-call ledger recording;
- sequence continuation, record/request/ledger digests and tamper rejection;
- unsafe path rejection and provider-free read-only verification;
- source and clean-wheel verification on Python 3.10–3.13.
