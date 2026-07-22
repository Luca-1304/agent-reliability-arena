# Project status

Last verified: 22 July 2026

## Current state

Agent Reliability Arena is at **v0.2.0rc1**.

The public v0.1.0 evidence remains a deterministic fixture. It validates experiment plumbing, evidence separation, replay, metrics and the trace viewer; it is not a claim about external model performance.

The release candidate adds a complete provider-free live-model path and private-pilot safeguards:

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
14. a private pilot runbook and disclosure-safe evidence boundary.

## Verification evidence

The safeguard core passed GitHub Actions run **#67** on Python 3.10, 3.11, 3.12 and 3.13, including source tests, release verification, installed commands, wheel build, clean-wheel tests and dependency checks.

The complete release-candidate tree must pass a fresh final matrix before issue #13 is closed or the PR is merged.

The permanent release verifier reproduces:

- the deterministic v0.1.0 reference metrics;
- 64 permitted live request templates;
- all six strict role-output contracts;
- one tamper-evident transport ledger;
- three complete provider-free orchestration scenarios;
- 12 validated role calls and three verified private ledgers;
- the disabled pilot preflight with eight permitted calls;
- proof that the disabled policy blocks before provider invocation;
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
- conservative call, token and monetary reservations can be enforced before calls.

## What is not yet proven

The repository does **not** yet prove:

- performance of any real hosted or local model;
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
- There is no public live-execution CLI.
- A future private caller must deliberately enable both execution barriers.
- Monetary limits are conservative operator reservations, not measured billing.

## Current priority

**Finish the final v0.2.0rc1 verification matrix, then close issue #13.**

After that, issue #14 permits one bounded private provider pilot. It must use one provider, one dated model snapshot, one scenario, strict reservations, no automatic retries and immediate abort on evidence inconsistency.

Issue #15 separately tracks the disclosure-safe public export.

## Related but separate projects

The Agent Contract Compiler and Agent Action Firewall remain separate projects. They may integrate later through reviewed interfaces but are outside the v0.2.0rc1 scope.
