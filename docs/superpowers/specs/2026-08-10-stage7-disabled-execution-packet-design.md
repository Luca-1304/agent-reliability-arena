# Stage 7 Disabled Execution Packet Design

## Goal

Create one source-controlled, provider-free, reviewable candidate packet for the first private Stage 7 pilot without granting provider execution authority, handling credentials, or making any empirical model claim.

## Chosen approach

Use a deterministic **disabled execution packet** rather than either:

1. loose operator notes that can drift independently; or
2. an enabled committed policy that could be mistaken for spend approval.

The packet is a concrete pre-execution commitment that CI can verify. It remains incapable of authorising a provider request because its policy has `external_execution_enabled: false` and its packet manifest has `operator_approved: false`.

## Candidate boundary

The committed candidate uses:

- provider: `openai-responses`;
- exact model ID: `gpt-5.5-2026-04-23`;
- model version marker: `gpt-5.5-2026-04-23`;
- source date: `2026-08-10`;
- one scenario: `success`;
- existing prompt catalogue: `examples/live_prompt_catalog.json` / `fixture-prompts-v1`;
- existing exact file-write contract;
- seed: `1304`;
- mutation attempts: `2`;
- maximum permitted call graph: `8` calls;
- maximum requested output tokens: `2068`;
- conservative total-token reservation: `2048` tokens per permitted call / `16384` aggregate;
- policy currency: `USD` so the hard reservation is directly comparable to the provider's USD price source;
- reserved cost: `12` cents per permitted call / `96` cents aggregate;
- proposed hard monetary ceiling: `100` cents (`$1.00`);
- external execution: disabled;
- operator approval: false.

The dated price source records OpenAI's GPT-5.5 standard API rates as observed on `2026-08-10`:

- input: `$5.00` / 1M tokens = `500` USD minor units;
- output: `$30.00` / 1M tokens = `3000` USD minor units;
- source reference: `https://developers.openai.com/api/docs/models/gpt-5.5`.

The packet does not assert that these rates will remain current after the source date. A live run requires a fresh operator review of the price source and exact model availability.

## Files

`examples/stage7_candidate/` contains:

- `experiment.json` — exact one-scenario `ExperimentConfig` candidate;
- `policy.disabled.json` — exact disabled `PilotPolicy` candidate;
- `price-source.json` — dated pricing metadata using the existing `PriceSource` schema;
- `packet.json` — canonical commitments and readiness/approval state.

A focused provider-free module validates the packet. A small repository script exposes verification without becoming a public installed live-provider command.

## Packet manifest

`packet.json` contains exactly:

- `schema_version`;
- `prepared_date`;
- `provider`;
- `model_id`;
- `model_version`;
- `scenario_ids`;
- `config_digest`;
- `prompt_catalog_digest`;
- `policy_digest`;
- `preflight_manifest_digest`;
- `price_source_digest`;
- `planned_call_ceiling`;
- `max_requested_output_tokens`;
- `max_reserved_total_tokens`;
- `reserved_cost_minor_units`;
- `proposed_hard_ceiling_minor_units`;
- `conservative_price_bound_minor_units`;
- `currency`;
- `external_execution_enabled`;
- `operator_approved`;
- `provider_called`;
- `packet_digest`.

The packet digest is canonical SHA-256 of every preceding field.

## Conservative price bound

The verifier does not guess the actual input/output mix. It computes a deliberately pessimistic bound by pricing **every token in `max_reserved_total_tokens` at the more expensive of the input and output rates**, then rounding up to the nearest minor unit.

For this candidate:

`ceil(16384 × 3000 / 1,000,000) = 50 cents`.

The candidate's 96-cent aggregate reservation is therefore above the calculated 50-cent conservative token-price bound and below the proposed $1.00 hard ceiling.

This is still a planning bound, not provider billing evidence.

## Verification rules

`verify_stage7_candidate(...)` must fail closed unless all of the following hold:

1. all four packet files are regular non-symlink files and contain strict JSON objects with no duplicate keys;
2. `ExperimentConfig`, `PromptCatalog`, `PilotPolicy` and `PriceSource` all parse using their existing strict schemas;
3. config, policy and packet agree exactly on provider/model/version/scenario;
4. the candidate contains exactly one `success` scenario;
5. the policy remains disabled;
6. `operator_approved`, `external_execution_enabled`, and `provider_called` are all false;
7. `build_pilot_preflight(...)` reconstructs the exact committed preflight digest and ceilings;
8. the policy reserves every permitted call and token ceiling exactly as committed;
9. price-source currency equals policy currency;
10. the conservative all-tokens-at-highest-rate bound is no greater than the aggregate reserved cost;
11. aggregate reserved cost is no greater than the proposed hard ceiling;
12. every component digest and final packet digest recomputes exactly.

## CLI boundary

`scripts/verify_stage7_candidate.py` only calls the provider-free verifier and prints a compact JSON summary:

- status;
- model ID;
- scenario;
- planned call ceiling;
- token reservation;
- reserved cost;
- proposed hard ceiling;
- conservative price bound;
- provider_called false;
- external_execution_enabled false;
- operator_approved false;
- packet digest.

It must not read `OPENAI_API_KEY`, instantiate `OpenAIResponsesTransport`, import network clients, create a private run directory, or mutate the candidate packet.

## Tests

Provider-free tests cover:

- the committed candidate verifies exactly;
- expected current snapshot/source date/rates/ceilings are locked by tests;
- policy enablement or operator approval causes rejection;
- model/provider/scenario drift causes rejection;
- config/policy/preflight/price/packet digest drift causes rejection;
- a below-bound monetary reservation is rejected;
- a hard ceiling below the aggregate reservation is rejected;
- duplicate-key, symlink and malformed-file inputs fail closed;
- the script works with an `OPENAI_API_KEY` marker present in the environment without reading or echoing it;
- verification makes no provider request and returns `provider_called: false`.

## Claims and authority boundary

This packet proves only that a specific proposed Stage 7 configuration is internally consistent and budget-bounded against a dated public price source.

It does **not**:

- approve $1.00 of spend;
- enable a provider call;
- prove the model is currently available at later execution time;
- prove the dated price remains current later;
- create or use an API credential;
- create a live run;
- establish model performance;
- permit a comparative claim.

A real run still requires a fresh review, a private enabled copy of the policy, the exact reviewed policy digest, explicit operator spend/execution approval, a local `OPENAI_API_KEY`, and the existing local-only confirmation gates.