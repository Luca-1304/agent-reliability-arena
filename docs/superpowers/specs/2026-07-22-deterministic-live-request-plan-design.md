# Deterministic Live Request Plan Design

## Decision

Add a source-controlled prompt catalogue, a strict `LiveRequestFactory`, and a provider-free preflight manifest. This layer defines exactly which model calls may exist before any live transport is allowed to execute.

The design is approved under the standing instruction to expand Agent Reliability Arena in small, fully verified layers.

## Purpose

The transport and ledger layers can faithfully execute and record a request, but they do not yet define who may issue one, which prompt version applies, or whether a general and specialist condition still share the same model, task, seed and contract.

This layer closes that gap without making an API call.

## Components

### `RolePrompt`

A frozen value containing:

- non-empty `instructions`;
- positive `max_output_tokens`.

### `PromptCatalog`

A frozen, schema-versioned catalogue containing exactly these roles:

- `general`;
- `strategist`;
- `operator`;
- `auditor`;
- `recovery`;
- `synthesiser`.

The catalogue records `prompt_version`, supports strict JSON parsing, and has a canonical SHA-256 digest. Unknown, missing or duplicate role entries fail closed.

### `LiveRequestFactory`

The factory is constructed from one `ExperimentConfig` and one matching `PromptCatalog`. It rejects prompt-version drift immediately.

It builds `ModelCallRequest` objects only for the allowed call grammar:

- general condition: `general`, attempt 1;
- specialist condition: `strategist` attempt 1;
- specialist condition: `operator` attempts 1 or 2;
- specialist condition: `auditor` attempts 1 or 2;
- specialist condition: `recovery` attempt 1;
- specialist condition: `synthesiser` attempt 1.

Every request receives:

- a deterministic call ID;
- model ID, model version, prompt version and seed copied from `ExperimentConfig`;
- role-specific instructions and output limit from `PromptCatalog`;
- canonical JSON input containing the task, exact contract, scenario, attempt and caller-supplied role payload;
- string metadata linking the experiment, configuration digest, contract digest, prompt catalogue digest and scenario.

The factory rejects unknown scenarios, condition-role mismatches, invalid attempts, non-object role payloads and non-JSON-compatible payload values.

### Preflight manifest

`build_live_request_preflight(config, catalog)` enumerates the maximum permitted call graph for every scenario without constructing fake provider outputs.

Each scenario contains:

- one required general call;
- required strategist, first operator, first auditor and synthesiser calls;
- conditional recovery, second operator and second auditor calls.

The manifest includes the configuration digest, contract digest, prompt catalogue digest, held-constant fairness fingerprint, model identifiers and a canonical manifest digest. It contains no API key and executes no provider.

## Data and trust boundaries

- Prompt text and output limits are source-controlled evidence.
- `ExperimentConfig` remains authoritative for model/task/seed/contract fairness.
- The preflight manifest describes permission, not execution or success.
- Runtime evidence still comes from `RecordingTransport` and the completion verifier.
- A later orchestrator integration must use this factory rather than constructing ad-hoc requests.

## Testing

Tests cover:

- catalogue round-trip and deterministic digest;
- missing, unknown and invalid role definitions;
- prompt-version mismatch rejection;
- exact general and specialist request construction;
- deterministic call IDs and canonical input;
- invalid role, condition, scenario, attempt and payload rejection;
- manifest required/conditional call graph;
- held-constant model/task/seed/contract evidence across both conditions;
- deterministic manifest digest;
- proof that planning performs no transport call.

The complete Python 3.10–3.13 source, release, CLI, wheel and clean-wheel matrix must remain green.

## Explicit exclusions

This increment does not call a provider, execute tools, parse model output, retry, price calls, alter deterministic fixture metrics or claim real-model performance.
