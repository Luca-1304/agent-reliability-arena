# Project status

Last verified: 22 July 2026

## Current state

Agent Reliability Arena is at **v0.2.0rc1**.

The public v0.1.0 evidence remains a deterministic fixture. It validates experiment plumbing, evidence separation, replay, metrics and the trace viewer; it is not a claim about external model performance.

The release candidate and current private-pilot preparation provide:

1. versioned model request and result contracts;
2. an HTTPS OpenAI Responses transport with credential, endpoint and explicit network-approval protections;
3. client/provider request provenance, latency, usage and incomplete/failure handling;
4. an append-only, tamper-evident private transport ledger;
5. a source-controlled six-role prompt catalogue and deterministic request factory;
6. a provider-free permission manifest covering every permitted request template;
7. strict fail-closed JSON output contracts for all six roles;
8. provider-neutral general and specialist orchestrators;
9. exact contract checks before bounded file mutation;
10. independent observation, verification, audit, recovery and synthesis;
11. a secret-free pilot policy with reviewed-digest approval;
12. hard call, requested-output-token, reserved-total-token and monetary-reservation ceilings;
13. a provider-free pilot preflight command;
14. a private pilot runbook and disclosure-safe evidence boundary;
15. exact preflight call-plan and duplicate-call enforcement;
16. a private paired runner with secure artifacts and preserved abort evidence;
17. a provider-free release rehearsal of one paired scenario;
18. a local-only real-provider script that refuses GitHub Actions, missing approvals and missing environment credentials.

## Verification evidence

The private runner, release rehearsal and guarded local script have passed the complete matrix on Python 3.10, 3.11, 3.12 and 3.13.

Every supported version passed:

- source compilation;
- the complete source test suite;
- release verification;
- installed command checks;
- wheel build;
- clean-wheel installation and tests;
- deterministic reference checks;
- dependency validation.

The permanent provider-free evidence now includes:

- the deterministic v0.1.0 reference metrics;
- 64 permitted live request templates;
- all six strict role-output contracts;
- tamper-evident ledger verification;
- three complete orchestration scenarios covering success, recovery and terminal security rejection;
- the disabled pilot preflight with eight permitted calls;
- proof that the disabled policy blocks before provider invocation;
- one complete private-pilot rehearsal with both conditions, five role calls, five verified ledger records and seven private artifacts;
- refusal of the local execution script inside GitHub Actions or without both explicit approvals and an environment credential;
- package, installed-distribution and documentation version consistency.

## What is proven

For the controlled exact file-write fixture, the repository proves that:

- requests can be versioned and pre-authorised deterministically;
- model-shaped outputs can be parsed fail-closed into bounded role schemas;
- proposed writes can be checked against the exact contract before mutation;
- source-reported success can be separated from independently observed state;
- false success can trigger one evidence-backed recovery attempt;
- security failures remain terminal;
- Auditor, Recovery and Synthesiser text cannot override authoritative evidence;
- provider-shaped calls can be recorded and verified without re-execution;
- real network execution remains disabled unless approved at both the pilot and adapter boundaries;
- conservative call, token and monetary reservations can be enforced before calls;
- a paired private run can preserve complete success evidence or partial abort evidence without leaking an environment API key;
- unplanned, duplicate or drifted calls can be rejected before provider invocation.

## What is not yet proven

The repository does **not** yet prove:

- performance of any real hosted or local model;
- that the local paid pilot path has executed successfully against a provider;
- comparative reliability from a statistically meaningful live sample;
- measured monetary cost or price efficiency;
- safe execution of arbitrary tools;
- concurrent ledger writing;
- prompt-redacted public live-evidence publication;
- production readiness or unattended operation.

No real provider request has been used as benchmark evidence.

## Current limitations

- The validated mutation surface is one confined file-write action.
- The transport ledger is deliberately single-writer.
- Private ledgers may contain prompts and model outputs.
- Automatic retry and built-in price estimation are excluded.
- There is no public installed live-execution command.
- The real-provider script is local-only and requires an enabled private policy, an exact reviewed digest, two explicit approvals and `OPENAI_API_KEY` from the process environment.
- Monetary limits are conservative operator reservations, not measured billing.
- A single pilot cannot justify a public comparative conclusion.

## Current priority

**Execute issue #14 only after the operator selects an exact dated model snapshot and approves the complete worst-case monetary reservation.**

The runner and provider-free rehearsal are ready. The remaining Stage 7 work is the deliberate local provider call, independent verification of its private ledger and retention of all success, failure or abort evidence.

Issue #15 separately tracks the disclosure-safe public export. Repeated trials and public comparative analysis remain later stages.

## Related but separate projects

The Agent Contract Compiler and Agent Action Firewall remain separate projects. They may integrate later through reviewed interfaces but are outside the v0.2.0rc1 scope.
