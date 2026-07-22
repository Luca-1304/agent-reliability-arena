# Live-model transport boundary

Status: development scaffold for the next empirical phase. It does not change the published deterministic fixture results and it does not claim external-model performance.

## Purpose

The transport boundary separates provider communication from orchestration, independent verification, metrics and public export. A live experiment can therefore keep the general and specialist conditions on the same versioned model request while recording the cost side of the comparison.

## Included contracts

- `ModelCallRequest` records the condition, role, model identifier and version, prompt version, exact instructions and input, output limit, seed and local metadata.
- Prompt whitespace is preserved, and each request has a canonical SHA-256 digest so paired conditions can prove exactly which versioned request was issued.
- `ModelCallResult` records normal output, a valid refusal or an incomplete outcome, together with the provider response identifier, returned model identifier, status, measured wall-clock latency, provider processing time, token usage, client and provider request IDs, and the SHA-256 digest of the exact response bytes.
- `TransportError` separates retryable network, HTTP and provider-side generation failures from terminal invalid responses while preserving safe request provenance.
- `ModelTransport` is the provider-neutral protocol used by later orchestration work.

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
- output extraction from all `output_text` message blocks;
- refusal extraction from `refusal` content blocks without misclassifying a valid refusal as a transport failure;
- incomplete-outcome preservation through `incomplete_details.reason`, even when no output text was produced;
- structured provider-failure errors with retry classification based on the provider error code;
- SHA-256 recording of the exact provider response bytes without persisting the API key.

The adapter accepts HTTPS only and sends credentials to `api.openai.com` by default. A different host requires the caller to set `allow_custom_endpoint=True` explicitly. Tests use injected openers and clocks, so the source test suite never performs a paid or external request.

## Deliberate exclusions

This increment does not yet:

- connect live model calls to the general or specialist orchestrators;
- execute tools proposed by a model;
- estimate prices;
- retry requests automatically;
- publish raw provider responses;
- produce comparative model results.

Those behaviours require a separate, reviewed integration with bounded tool schemas, repeated paired runs, dated price tables, uncertainty reporting and disclosure-safe artifact export.

## Verification

The transport tests cover:

- deterministic request digests, prompt-version sensitivity and exact prompt-whitespace preservation;
- normal response text, valid refusal and incomplete-outcome parsing;
- wall-clock latency, provider processing time, client request ID and provider request-ID capture;
- structured provider-side failed-response classification;
- exact response-byte hashing;
- `store: false` and version metadata in the request payload;
- API-key exclusion from persisted result records and raised errors;
- HTTP 429 retry classification;
- insecure endpoint rejection and explicit custom-host opt-in;
- missing-output, refusal and incomplete-detail rejection.
