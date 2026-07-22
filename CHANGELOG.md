# Changelog

All notable changes to Agent Reliability Arena are recorded here.

The project distinguishes deterministic fixture evidence, provider-free integration evidence and real-provider empirical evidence. A feature appearing in this changelog does not imply that a real-model benchmark has been run.

## Unreleased — v0.2.0 development

### Added

- provider-neutral `ModelTransport` request and result contracts;
- HTTPS OpenAI Responses adapter with `store: false`;
- deterministic client request IDs and provider request provenance;
- token, latency and provider-processing-time capture;
- refusal, incomplete-response and provider-failure handling;
- exact request and response SHA-256 evidence;
- explicit custom-endpoint opt-in and API-key non-disclosure protections;
- append-only tamper-evident private transport ledger;
- provider-free ledger verification and sequence continuation;
- source-controlled six-role live prompt catalogue;
- deterministic live request factory and preflight manifest;
- strict fail-closed JSON output contracts for all six roles;
- exact-byte and canonical role-output digests;
- provider-neutral live general and specialist orchestrators;
- exact contract checks before bounded file mutation;
- evidence-derived audit, one-attempt recovery and final synthesis checks;
- permanent provider-free release scenarios for success, recovery and terminal security failure;
- project status and evidence-gated roadmap documentation.

### Verified

- Python 3.10, 3.11, 3.12 and 3.13;
- complete source suite;
- release verifier;
- installed commands;
- wheel build and clean-wheel tests;
- deterministic reference equality;
- dependency checks;
- three complete provider-free end-to-end scenarios;
- 12 validated role calls and three independently verified private ledgers in the latest release fixture.

### Not yet included

- a public live-provider execution command;
- benchmark results from any hosted or local model;
- automatic retry or price estimation;
- concurrent ledger writers;
- prompt-redacted public ledger publication;
- arbitrary tool execution.

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
