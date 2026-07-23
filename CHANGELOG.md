# Changelog

All notable changes to Agent Reliability Arena are recorded here.

The project distinguishes deterministic fixture evidence, provider-free integration evidence and real-provider empirical evidence. A feature appearing here does not imply that a real-model benchmark has been run.

## v0.2.0rc2 — 23 July 2026

### Added

- deterministic CycloneDX SBOM as a first-class release asset;
- supply-chain manifest and citation provenance in the immutable release bundle;
- GitHub SLSA provenance attestations for the wheel and source distribution;
- CycloneDX SBOM attestations for both executable package artifacts;
- online `gh attestation verify` gates before release publication;
- job-scoped OIDC, attestation and artifact-metadata permissions;
- rc2 citation, package, security and release metadata alignment.

### Preserved

- immutable `v0.2.0rc1` tag, notes and assets;
- deterministic fixture and provider-free evidence boundaries;
- `provider_called: false` and `comparative_claim_permitted: false`;
- no claim of production readiness, vulnerability absence or representative real-model performance.

## v0.2.0rc1 — 22 July 2026

### Added

- provider-neutral `ModelTransport` request and result contracts;
- HTTPS OpenAI Responses adapter with `store: false`;
- deterministic client request IDs and provider request provenance;
- token, latency and provider-processing-time capture;
- refusal, incomplete-response and provider-failure handling;
- exact request and response SHA-256 evidence;
- explicit custom-endpoint opt-in and API-key non-disclosure protections;
- explicit adapter approval before the real network opener may run;
- append-only tamper-evident private transport ledger;
- provider-free ledger verification and sequence continuation;
- source-controlled six-role live prompt catalogue;
- deterministic live request factory and permission manifest;
- strict fail-closed JSON output contracts for all six roles;
- exact-byte and canonical role-output digests;
- provider-neutral live general and specialist orchestrators;
- exact contract checks before bounded file mutation;
- evidence-derived audit, one-attempt recovery and final synthesis checks;
- permanent provider-free release scenarios for success, recovery and terminal security failure;
- exact, secret-free `PilotPolicy` schema;
- provider-free `arena-preflight-pilot` command;
- hard call, requested-output-token, reserved-total-token and monetary-reservation ceilings;
- reviewed-policy-digest and separate external-execution approval gates;
- disabled committed pilot policy example;
- private pilot, repeated experiment and disclosure runbooks;
- exact preflight call-plan enforcement and duplicate-call rejection;
- a secure private paired runner that writes preflight, policy, start, condition-result, ledger and final-verification artifacts;
- preserved `abort.json` and partial ledger verification when a private run fails;
- provider-free private-pilot release rehearsal covering one scenario, both conditions and five role calls;
- a local-only `scripts/run_private_pilot.py` entry point that refuses GitHub Actions, missing approvals, disabled policy, digest drift and missing environment credentials;
- an immutable private evidence-set index covering every completed and aborted run;
- a disclosure-safe allow-list exporter with per-run private source commitments;
- provider-free `arena-export-live-evidence` and `arena-verify-live-export` commands;
- public reconstruction of outcome, token and latency aggregates from verified private ledgers;
- optional dated price-source metadata kept separate from measured usage and provider billing;
- immutable `TrialPlan` and `RepeatedExperimentPlan` preregistration schemas;
- deterministic round-robin, counterbalanced repeated-trial planning with unique seeds;
- exact experiment-level call, token and monetary reservation preflight;
- explicit General-first or Specialist-first paired-pilot execution;
- a private repeated runner with immutable plan/preflight/start records and atomic checkpoints;
- safe deliberate pause and continuation through a verified completed trial prefix;
- terminal refusal after partial, non-contiguous, altered, unexpected or aborted trial evidence;
- descriptive repeated analysis with absolute paired counts, Wilson intervals, a labelled paired normal approximation and an exact discordant-pair sign test;
- measured repeated-trial calls, tokens and latency reconstructed from independently verified ledgers;
- project status and evidence-gated roadmap documentation.

### Verified

- Python 3.10, 3.11, 3.12 and 3.13;
- complete source suite;
- release verifier, disclosure reproduction and repeated-experiment reproduction;
- installed commands;
- wheel build and clean-wheel tests;
- deterministic reference equality;
- dependency checks;
- three complete provider-free end-to-end scenarios;
- 12 validated role calls and three independently verified private ledgers;
- disabled pilot policy blocks before provider invocation;
- injected test transports remain provider-free;
- an API key alone is insufficient to enable real network execution;
- unplanned and duplicate pilot calls are rejected before provider invocation;
- one provider-free private paired rehearsal creates seven private artifacts and five verified ledger records;
- parser failure preserves abort evidence and prevents dirty-directory reuse;
- the local script help and refusal paths require no provider credential and leak no test secret;
- a script-argument handling failure found during CI was corrected and the complete matrix rerun successfully;
- one synthetic completed and one synthetic aborted private run remain represented in the public export;
- private prompts, outputs, notes, provider identifiers and machine paths are excluded;
- added, removed or modified private runs are rejected after the evidence index is committed;
- public bundle and aggregate mutation is detected during replay;
- disclosure export and replay make no provider request;
- deterministic repeated schedules reject duplicate trial IDs, duplicate seeds, unknown scenarios, template drift and order imbalance;
- four provider-free repeated trials include two General-first and two Specialist-first orders;
- the repeated release fixture pauses after five calls and resumes the remaining 15 without replaying the first trial;
- 20 repeated-trial ledger records reconstruct 400 scripted total tokens and 20 ms scripted latency;
- a separate invalid-output trial preserves both trial and experiment abort evidence;
- the aborted repeated root refuses continuation;
- all repeated release behavior passes editable and clean-wheel verification on every supported Python version.

### Not included

- an executed real-provider pilot;
- a real repeated provider experiment;
- benchmark results from any hosted or local model;
- validation of the disclosure export against retained real-provider evidence;
- a public installed live-provider command;
- automatic retry or built-in price estimation;
- concurrent ledger writers;
- a representative public live-model comparison;
- claims that statistical intervals or p-values establish causality or generality;
- arbitrary tool execution.

### Evidence boundary

`v0.2.0rc1` is a reviewable release candidate with provider-free rehearsed private-pilot, repeated-experiment and disclosure mechanisms. It does not establish real-model performance, cost efficiency, statistical significance, production readiness or safety for arbitrary tools.

## v0.1.0 — 21 July 2026

### Added

- deterministic paired comparison between one general policy and a unified specialist policy;
- Strategist, Operator, Auditor, Recovery and Synthesiser role boundaries;
- confined exact file-write sandbox;
- independently observed acceptance contract;
- Agent Completion Verifier v0.6.0 vendored with digest-pinned source manifest;
- deterministic scenario fixtures and paired metrics;
- replayable SHA-256-backed evidence bundle;
- static dependency-free trace viewer;
- `arena-run`, `arena-replay` and `arena-export-web` commands;
- methodology, threat model, contribution and vendored-source documentation.

### Evidence boundary

The v0.1.0 results are deterministic software fixtures. They validate the system and demonstration path but are not measurements of OpenAI, Anthropic, Gemini, local models or people.
