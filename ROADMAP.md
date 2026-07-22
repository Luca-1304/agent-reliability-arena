# Roadmap

This roadmap is evidence-gated. A stage is complete only when its implementation, tests, release checks and claims boundary all agree.

## Completed foundations

### Stage 0 — Deterministic fixture release

Status: **complete in v0.1.0**

- paired general-versus-specialist fixture;
- independently observed completion contract;
- replayable SHA-256-backed artifacts;
- deterministic metrics and static trace viewer;
- Python 3.10–3.13 source and clean-wheel verification.

### Stage 1 — Versioned provider boundary

Status: **complete**

- provider-neutral request/result protocol;
- OpenAI Responses adapter;
- exact request and response digests;
- usage, latency, request IDs, refusal, incomplete and provider-failure handling;
- credential, endpoint and explicit network-approval protections.

### Stage 2 — Private transport evidence

Status: **complete**

- append-only JSONL ledger;
- request, record and full-ledger digests;
- sequence and cross-field validation;
- tamper, malformed-data, symlink and unsafe-path rejection;
- provider-free read-only verification.

### Stage 3 — Deterministic live request planning

Status: **complete**

- six-role source-controlled prompt catalogue;
- strict condition/role/attempt grammar;
- deterministic call IDs and canonical input;
- held-constant fairness metadata;
- provider-free permission manifest;
- 64 permitted templates verified for the reference configuration.

### Stage 4 — Fail-closed role outputs

Status: **complete**

- exact JSON-object parsing;
- duplicate-key, unknown-field, oversized-output and unsafe-path rejection;
- typed outputs for General, Strategist, Operator, Auditor, Recovery and Synthesiser;
- raw-output and canonical-payload digests;
- verifier status remains authoritative.

### Stage 5 — Provider-free end-to-end integration

Status: **complete**

- general and specialist live orchestrators;
- exact contract checks before bounded mutation;
- independent observation and verification;
- evidence-derived audit and recovery;
- terminal security handling;
- scripted success, recovery and terminal-failure release fixtures;
- private ledger verification for every scripted run.

### Stage 6 — v0.2.0rc1 release candidate

Status: **complete and merged**  
Tracking: [#13 — Prepare Agent Reliability Arena v0.2 release candidate](https://github.com/Luca-1304/agent-reliability-arena/issues/13)

- package, installed distribution and documentation versions aligned;
- provider-free pilot preflight command;
- private run-directory and secret-handling rules;
- hard call, requested-output-token, reserved-total-token and monetary ceilings;
- exact reviewed-policy digest and separate execution approval;
- real adapter network opener disabled by default;
- explicit abort conditions;
- disclosure-safe public/private evidence boundary;
- complete Python 3.10–3.13 source, release, wheel and clean-wheel verification.

## Current stage

### Stage 7 — Minimal private provider pilot

Status: **runner implemented and provider-free rehearsed; real provider execution not yet performed**  
Tracking: [#14 — Run a minimal private real-provider pilot](https://github.com/Luca-1304/agent-reliability-arena/issues/14)

Completed preparation:

- [x] exactly one reviewed scenario per pilot;
- [x] both conditions use the same model, task, contract, seed and tool boundary;
- [x] exact preflight call-plan enforcement;
- [x] duplicate and unplanned calls rejected before provider invocation;
- [x] strict call, token and monetary reservations;
- [x] fresh private run directory required and reuse rejected;
- [x] preflight, policy, start, condition-result, ledger and verification artifacts;
- [x] abort evidence and partial ledger preserved on failure;
- [x] provider-free paired rehearsal covering both conditions and five role calls;
- [x] local-only execution script refuses GitHub Actions, missing approvals and missing environment credentials;
- [x] complete Python 3.10–3.13 source, release, wheel and clean-wheel verification.

Still required to complete Stage 7:

- [ ] choose one explicitly dated real model snapshot;
- [ ] create and privately review an enabled one-scenario policy;
- [ ] approve an exact worst-case monetary ceiling;
- [ ] supply `OPENAI_API_KEY` through the local process environment only;
- [ ] execute one local paired pilot;
- [ ] verify the resulting private ledger and final manifest independently;
- [ ] retain failures and make no public comparative performance claim.

Exit condition: one real-provider paired run completes or aborts with preserved, independently verified private evidence. One pilot remains insufficient for a representative performance conclusion.

## Planned empirical stages

### Stage 8 — Repeated paired experiment

Status: **not started**

- pre-register scenarios, repetition count and stopping rules;
- randomise or counterbalance condition order where applicable;
- measure tokens, wall-clock latency, provider processing time and dated cost;
- separate provider failures from orchestration failures;
- report absolute counts and uncertainty intervals;
- preserve all private raw evidence needed for replay.

Exit condition: a complete dataset suitable for cautious analysis, not a single-run anecdote.

### Stage 9 — Disclosure-safe evidence release

Status: **design tracked; validation requires private evidence**  
Tracking: [#15 — Design disclosure-safe empirical evidence export](https://github.com/Luca-1304/agent-reliability-arena/issues/15)

- derive public artifacts from verified private evidence;
- redact or omit prompts, secrets and sensitive provider payloads;
- retain hashes, configuration, model version, counts and methodology;
- publish limitations and negative outcomes;
- make every public metric traceable to a verified private source record.

Exit condition: another reviewer can audit the claims without receiving credentials or private prompts.

### Stage 10 — Broader task and tool coverage

Status: **deferred**

Only after the file-write experiment is empirically understood:

- add new tools one at a time;
- define a separate contract, threat model and verifier adapter for each tool;
- require deterministic adversarial fixtures before live use;
- integrate the Contract Compiler or Action Firewall only through separately reviewed interfaces.

## Explicit non-goals for v0.2

- unattended autonomous operation;
- arbitrary shell, browser, email or financial actions;
- claims of general AI safety;
- claims that specialist orchestration is universally superior;
- hiding failed runs or selecting only favourable examples;
- merging separate ACE projects into one oversized repository.
