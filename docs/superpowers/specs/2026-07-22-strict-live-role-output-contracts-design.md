# Strict Live Role Output Contracts Design

## Decision

Add a provider-neutral, fail-closed parser that converts model output text into strict typed role objects before any orchestrator may inspect or act on it.

This design is approved under the standing instruction to expand Agent Reliability Arena in small, fully verified layers.

## Purpose

The Arena now proves which requests are permitted, transports and records provider responses, and preserves tamper-evident evidence. It does not yet distinguish valid bounded role output from arbitrary text, markdown, duplicate-key JSON or unsafe action proposals.

This layer performs that validation without executing a provider or tool.

## Input boundary

`parse_live_role_output(role, output_text, *, expected_attempt_number=None)` accepts:

- one of the six exact role names;
- a UTF-8 Python string no larger than 65,536 encoded bytes;
- one top-level JSON object only.

It rejects:

- empty text;
- markdown fences or prose around JSON;
- arrays, scalars or trailing JSON values;
- duplicate object keys at any nesting level;
- `NaN`, positive infinity or negative infinity;
- unknown or missing fields;
- unsupported roles;
- invalid role-specific values;
- absolute, backslash-containing, dot, empty-segment or traversal paths.

The parser never repairs, guesses or extracts a JSON substring from malformed output.

## Typed outputs

### GeneralProposal

Exact fields:

- `action`: `write_file` or `none`;
- `path`: safe relative POSIX path or `null`;
- `content`: string or `null`;
- `completion_claimed`: boolean;
- `rationale`: non-empty string.

`write_file` requires path and content. `none` requires both to be `null`. A completion claim remains observable but is not accepted as proof.

### StrategyPlan

Uses the existing `StrategyPlan` schema with exact fields and existing role-permission constraints.

### OperatorProposal

Exact fields:

- `approved_action`: exactly `write_file`;
- `path`: safe relative POSIX path;
- `content`: string;
- `attempt_number`: `1` or `2`;
- `rationale`: non-empty string.

When `expected_attempt_number` is supplied, it must match exactly.

### AuditRecord

Uses the existing `AuditRecord` schema with exact fields. Lists are converted to tuples only after type and duplicate validation.

### RecoveryRecord

Uses the existing `RecoveryRecord` schema with exact fields and existing retry/refusal invariants.

### SynthesisRecord

Uses the existing `SynthesisRecord` schema. It therefore cannot claim completion unless `verified_status` is `VERIFIED_COMPLETE`.

## Evidence envelope

`ParsedRoleOutput` records:

- role;
- typed value;
- canonical parsed payload;
- SHA-256 of the exact UTF-8 output bytes;
- SHA-256 of the canonical JSON payload.

The exact-byte digest distinguishes provider formatting changes; the canonical digest identifies semantically identical validated payloads.

## Security and trust boundary

- Parsing proves schema validity, not truth.
- Safe relative paths prevent direct absolute or traversal proposals but do not authorise mutation.
- General completion claims remain untrusted until independent verification.
- Operator proposals remain proposals; a later execution layer must enforce approved action and sandbox confinement.
- Audit, recovery and synthesis output cannot override verifier evidence.
- No parser call contacts a provider, writes a ledger or executes a tool.

## Testing

Tests cover:

- all six valid role outputs;
- deterministic exact-byte and canonical digests;
- duplicate-key rejection at top level and nested objects;
- markdown, trailing text, array and scalar rejection;
- output-size and non-finite-number rejection;
- exact-field enforcement;
- unsafe path rejection;
- action/path/content consistency;
- expected attempt matching;
- existing strategist, auditor, recovery and synthesis invariants;
- proof that a completion claim remains data rather than accepted evidence.

The complete Python 3.10–3.13 source, release, CLI, wheel and clean-wheel matrix must remain green.

## Explicit exclusions

This increment does not call a provider, execute tools, compare proposals with the task contract, retry, price calls, integrate live orchestrators or claim model performance.
