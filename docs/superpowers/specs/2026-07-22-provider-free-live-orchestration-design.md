# Provider-Free Live Orchestration Integration Design

## Decision

Add provider-neutral live general and specialist orchestrators, then prove them end-to-end with scripted model responses, the real request factory, strict role parser, tamper-evident transport ledger, controlled sandbox and independent completion verifier.

This is the final safe integration layer before any real provider or paid execution.

## Purpose

The repository now verifies request permission, transport behavior, durable call evidence and strict role-output structure independently. The missing proof is that these boundaries compose correctly and that model output cannot override tool, sandbox or verifier evidence.

The integration executes only the existing controlled file-write fixture scenarios. Tests and release verification use a scripted in-memory transport and perform no network request.

## Public interfaces

### `LiveRoleCallRecord`

Records one validated role call:

- call ID, role and attempt number;
- request digest;
- provider response ID and status;
- exact response-byte digest;
- exact role-output-byte digest;
- canonical role-output digest;
- canonical parsed payload.

### `LiveScenarioExecution`

Records one condition/scenario execution:

- experiment, condition and scenario identifiers;
- configuration and contract digests;
- ordered validated role-call records;
- independently observed sandbox attempts;
- final verifier status;
- completion claim;
- recovery and security-rejection flags.

Derived properties expose verified completion, false completion and silent verified completion. The object has a deterministic `to_dict()` representation but is not added to the published deterministic v0.1 artifacts.

### `LiveGeneralOrchestrator`

Execution flow:

1. build the permitted general request through `LiveRequestFactory`;
2. call the supplied `ModelTransport` once;
3. require a completed, non-refusal, non-incomplete response;
4. parse one `GeneralProposal`;
5. require `write_file` proposals to match the exact configured path and content before tool execution;
6. invoke the existing controlled sandbox scenario once;
7. use the independent verifier status as authoritative;
8. preserve the model completion claim as untrusted measured data.

A `none` proposal is not executed in this increment and fails closed as an orchestration error rather than being converted into fabricated evidence.

### `LiveSpecialistOrchestrator`

Execution flow:

1. Strategist request and strict `StrategyPlan` parse;
2. first Operator request and exact-contract proposal validation;
3. first controlled sandbox execution and independent observation;
4. Auditor request with source report, observation and evaluation in the role payload;
5. compare the parsed audit decision and conflict set with the authoritative evidence-derived decision;
6. when and only when evidence allows recovery, require a matching Recovery output, second exact-contract Operator output, successful controlled retry and second matching Auditor output;
7. request Synthesis with final verifier evidence;
8. require synthesis status and completion claim to equal the authoritative final verifier status.

Security rejections are terminal. Model audit or recovery output cannot authorise a retry for path traversal or symlink escape. Synthesis cannot claim completion over a failed verifier status.

## Authoritative evidence rules

- Independent observation outranks source reports and role text.
- Expected audit decision is derived locally:
  - `accept` when the observed state satisfies the contract;
  - `fail` for security rejection;
  - `recover` only for configured retryable scenarios with an attempt remaining;
  - otherwise `fail`.
- Expected conflict markers are derived locally from source-report/observation disagreement.
- Auditors must reference exactly `source_report.json`, `observation.json` and `evaluation.json`.
- Operator path and content must equal the configured contract exactly before any sandbox call.
- Recovery must match the scenario and one-attempt policy.
- Final synthesis must match the final verifier status exactly.

## Error boundary

`LiveOrchestrationError` is raised for request/result mismatch, refusal, incomplete response, invalid output, contract mismatch, incorrect audit/recovery/synthesis decisions or unsupported `none` action. It never converts those failures into verified completion.

Provider `TransportError` remains distinct and propagates unchanged after any enclosing `RecordingTransport` records it.

## Test scenarios

The integration suite covers:

- general exact success with one role call and one verified attempt;
- general false-success claim preserved as a false completion;
- specialist false-success recovery with seven recorded role calls and two attempts;
- specialist timeout-after-write acceptance without retry;
- specialist path-traversal terminal failure with no recovery call;
- wrong operator contract rejected before sandbox mutation;
- auditor attempt to accept unmatched state rejected;
- recovery attempt on a security rejection never requested;
- synthesis status mismatch rejected;
- ledger record counts equal actual role-call counts;
- verification and replay paths perform no provider calls beyond scripted calls.

## Release proof

The release verifier runs scripted general success, specialist false-success recovery and specialist path-traversal failure in temporary directories. It verifies:

- expected call and attempt counts;
- verified/failed status and recovery flags;
- terminal security behavior;
- all resulting private transport ledgers;
- no network or paid request.

## Explicit exclusions

This increment does not use a real provider, expose a CLI for live execution, estimate price, retry provider failures, publish private ledgers, generalise beyond the controlled file-write contract or claim external-model performance.
