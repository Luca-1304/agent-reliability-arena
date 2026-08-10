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
- new ledgers use hash-chained record schema 2 while non-empty legacy schema-1 ledgers remain verifiable and continuable without migration;
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

### Reliability assurance architecture

Status: **implemented, exact-head verified and merged; required gates remain the evidence authority for subsequent changes**

The repository reliability system is intentionally layered rather than one oversized repeated job:

- **Fast** — rapid merge feedback across Python 3.10–3.13, including source tests, policy/privacy checks and wheel smoke verification;
- **Deep** — the repeated/adversarial 15-pass assurance engine on Python 3.10 and 3.13;
- **Specialist** — independent reproducible-build, explicit-determinism, clean-room, concurrency-isolation and diagnostic-security jobs;
- **Scheduled** — a weekly/manual ecosystem-drift advisory using latest compatible build tools, cold cache and dependency resolution without PR or push triggers;
- **Policy + evidence** — the governing layer that constrains permissions, trigger surfaces, artifact retention, diagnostic privacy, workflow roles and evidence interpretation.

Fast, Deep and Specialist are required reliability roles. Scheduled remains advisory by default. Each role emits a machine record and a non-authoritative human summary; missing, duplicate, failed or unknown required records cannot be interpreted as a pass. Diagnostic artifacts are scanned before publication.

Performance telemetry is **observational only**. Median/worst timing can be reported, but no performance threshold becomes merge-blocking from this architecture alone. A `slower-than-recent-median` observation requires at least ten explicit prior samples and still does not change the required-gate decision.

These controls verify repository, packaging, deterministic fixture, isolation and evidence behavior. They do **not** prove provider deletion, production deployment health, Git-to-Vercel provenance, absence of every possible flake, external immutability of local private evidence, or real-provider/model performance.

## Current empirical boundary

### Stage 7 — Minimal private provider pilot

Status: **runner and disabled execution packet implemented and provider-free rehearsed; real provider execution not yet performed**  
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
- [x] provider-reported model identity is checked at the recording boundary, preserved as a non-retryable independently verifiable mismatch error, and rejected before orchestration can use mismatched output;
- [x] provider-free paired rehearsal covering both conditions and five role calls;
- [x] local-only execution script refuses GitHub Actions, missing approvals and missing environment credentials;
- [x] disabled review packet pins candidate snapshot `gpt-5.5-2026-04-23`, one `success` scenario, exact config/policy/preflight commitments and a dated `2026-08-10` price-source digest;
- [x] disabled packet reserves 16,384 total tokens and 96 USD cents against a deliberately pessimistic 50-cent all-tokens-at-output-rate planning bound, under a proposed-not-approved $1.00 hard ceiling;
- [x] packet verification reconstructs every commitment provider-free and requires `external_execution_enabled: false`, `operator_approved: false` and `provider_called: false`;
- [x] complete Python 3.10–3.13 source, release, wheel and clean-wheel verification.

Still required to complete Stage 7:

- [ ] freshly re-confirm the exact dated model snapshot is available at the execution time;
- [ ] freshly re-confirm current provider pricing and review a new packet if the dated source is stale or changed;
- [ ] create and privately review an enabled one-scenario policy from the disabled candidate;
- [ ] explicitly approve the exact worst-case monetary ceiling after reading the final preflight;
- [ ] supply `OPENAI_API_KEY` through the local process environment only;
- [ ] execute one local paired pilot;
- [ ] verify the resulting private ledger and final manifest independently;
- [ ] retain failures and make no public comparative performance claim.

Exit condition: one real-provider paired run completes or aborts with preserved, independently verified private evidence. One pilot remains insufficient for a representative performance conclusion.

### Stage 8 — Repeated paired experiment

Status: **preregistered runner, safe continuation and descriptive analysis implemented; real repeated execution not performed**  
Tracking: [#21 — Add preregistered repeated paired experiment runner](https://github.com/Luca-1304/agent-reliability-arena/issues/21)

Completed implementation:

- [x] immutable exact trial schedule with canonical plan digest;
- [x] deterministic round-robin scenario schedule and counterbalanced first condition;
- [x] unique seed per planned trial, shared by both conditions within that trial;
- [x] exact experiment-level call, requested-output-token, reserved-total-token and monetary ceilings;
- [x] General-first and Specialist-first private paired execution without changing condition artifact names;
- [x] immutable experiment plan, preflight and start records;
- [x] independently verified trial ledger and summary before checkpoint advancement;
- [x] append-only hash-chained root witness commits each verified completed trial before the replaceable checkpoint advances;
- [x] continuation re-verifies the witnessed completed prefix and rejects retained-witness ledger truncation or evidence rewrite before any new provider-shaped call;
- [x] deterministic create-once detached receipts commit exact verified witness prefixes outside the experiment root without adding network or Git authority;
- [x] earlier detached receipts remain verifiable after later append-only witness growth and reject rewritten committed prefixes or different locally valid replacement histories;
- [x] optional HMAC-SHA256 authentication envelopes bind a verified detached receipt to an independently retained 256-bit operator secret without adding runtime dependencies or network authority;
- [x] replacing the local root and detached receipt is rejected by the authenticated envelope unless the HMAC key is also compromised;
- [x] atomic experiment checkpoint after each verified completed trial;
- [x] deliberate pause after a verified trial and continuation without replaying completed calls;
- [x] refusal of non-contiguous, partial, altered, unexpected or aborted evidence;
- [x] terminal experiment abort with preserved trial evidence;
- [x] absolute paired outcome counts and Specialist-minus-General difference;
- [x] Wilson 95% condition intervals;
- [x] explicitly labelled paired normal-approximation interval;
- [x] exact two-sided binomial sign test over discordant pairs;
- [x] measured call, token and latency totals reconstructed from verified ledgers;
- [x] permanent provider-free four-trial pause/resume release reproduction;
- [x] separate terminal-abort reproduction;
- [x] `comparative_claim_permitted: false` throughout.

The root witness is a local continuity control. A detached receipt can detect replacement of the exact witness prefix it committed when at least one receipt copy is retained outside the rewritten root. An optional HMAC authentication envelope can additionally detect replacement of the detached receipt while the independently retained 256-bit key remains uncompromised. HMAC is shared-secret authentication, not a public-key signature, trusted timestamp or external notarization; compromise of the key or of every independently retained trust artifact remains outside this guarantee.

Still required before Stage 8 becomes empirical evidence:

- [ ] complete Stage 7 or explicitly preregister a reviewed real repeated plan;
- [ ] approve the aggregate worst-case provider reservation;
- [ ] execute the complete schedule without changing its stopping rule;
- [ ] retain every completed, failed and aborted trial;
- [ ] independently verify all ledgers and experiment artifacts;
- [ ] interpret intervals and sign tests only within the recorded sample limitations.

Exit condition: a complete preregistered real-provider dataset suitable for cautious analysis, not a single-run anecdote. Provider-free infrastructure alone does not satisfy this exit condition.

### Stage 9 — Disclosure-safe evidence release

Status: **export, verifier and adversarial provider-free rehearsal implemented; validation against real private evidence pending**  
Tracking: [#15 — Design disclosure-safe empirical evidence export](https://github.com/Luca-1304/agent-reliability-arena/issues/15)

Completed implementation:

- [x] immutable private evidence-set index commits to every completed and aborted run;
- [x] added, removed or modified private runs are rejected before export;
- [x] private file manifests and transport ledgers are represented by stable SHA-256 commitments;
- [x] public output uses an explicit allow-list rather than field-by-field deletion;
- [x] prompts, role inputs, model outputs, provider identifiers, operator notes and machine paths are excluded;
- [x] completed and aborted runs remain visible in public counts;
- [x] token and latency totals are derived from independently verified private ledgers;
- [x] dated price-source metadata is kept separate from measured usage and billing claims;
- [x] public aggregate fields are reconstructed during replay and outcome mutation is rejected;
- [x] `arena-export-live-evidence` and `arena-verify-live-export` make no provider request;
- [x] synthetic completed-and-aborted evidence passes source, release, wheel and clean-wheel verification on Python 3.10–3.13.

Still required before a real public empirical release:

- [ ] validate the same export against retained private evidence from Stage 7 or Stage 8;
- [ ] review provider/model naming and any dated price source for public accuracy;
- [ ] confirm every published count maps to a retained private source commitment;
- [ ] publish limitations and negative outcomes alongside any empirical result;
- [ ] keep `comparative_claim_permitted: false` until the repeated experiment supports cautious comparison.

Exit condition: another reviewer can audit public counts, limitations and source commitments without receiving credentials, private prompts or raw provider payloads.

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
- treating an interval or p-value as proof of causality or representativeness;
- merging separate ACE projects into one oversized repository.
