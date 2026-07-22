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

## Current stage

### Stage 6 — v0.2.0rc1 release candidate

Status: **safeguards implemented; final matrix pending**  
Tracking: [#13 — Prepare Agent Reliability Arena v0.2 release candidate](https://github.com/Luca-1304/agent-reliability-arena/issues/13)

- [x] align package, README, changelog and release metadata;
- [x] provide a provider-free pilot preflight command;
- [x] define private run-directory and secret-handling rules;
- [x] define hard call, requested-output-token, reserved-total-token and monetary ceilings;
- [x] require an exact reviewed policy digest and separate execution approval;
- [x] ensure the real adapter network opener is disabled by default;
- [x] define abort conditions for provider, parser, ledger, contract and verifier failures;
- [x] define a disclosure-safe public/private evidence boundary;
- [x] verify the safeguard core on Python 3.10–3.13;
- [ ] run the full Python 3.10–3.13 matrix on the final candidate tree;
- [ ] merge the unchanged green candidate and close #13.

Exit condition: a reviewer can reproduce every non-paid path, understand every limitation and see exactly what a private pilot would do before credentials are supplied.

## Planned empirical stages

### Stage 7 — Minimal private provider pilot

Status: **not started; blocked by #13**  
Tracking: [#14 — Run a minimal private real-provider pilot](https://github.com/Luca-1304/agent-reliability-arena/issues/14)

Scope:

- one explicitly named provider and dated model snapshot;
- one controlled scenario first;
- both conditions use the same model, task, contract and seed;
- reviewed policy digest and two explicit execution approvals;
- strict token and monetary reservations;
- no automatic retries;
- private tamper-evident evidence only;
- immediate stop on parser, ledger, contract or verifier inconsistency.

Exit condition: one complete paired run with verified private evidence and no public performance claim.

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
