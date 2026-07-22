# Project status

Last verified: 22 July 2026

## Current state

Agent Reliability Arena is in **v0.2.0 development** on `main`.

The public v0.1.0 evidence remains a deterministic fixture. It validates the experiment plumbing, evidence separation, replay, metrics and trace viewer; it is not a claim about external model performance.

The v0.2 development tree now adds a complete provider-free live-model path:

1. versioned model request and result contracts;
2. an HTTPS OpenAI Responses transport with credential and endpoint protections;
3. client/provider request provenance, latency, usage and incomplete/failure handling;
4. an append-only, tamper-evident private transport ledger;
5. a source-controlled six-role prompt catalogue and deterministic request factory;
6. a provider-free preflight manifest covering every permitted request template;
7. strict fail-closed JSON output contracts for all six roles;
8. provider-neutral general and specialist orchestrators;
9. exact contract checks before bounded file mutation;
10. independent observation, verification, audit, recovery and synthesis.

## Latest verification evidence

GitHub Actions run **#59** completed successfully on Python 3.10, 3.11, 3.12 and 3.13.

Every matrix job passed:

- source compilation;
- the complete source test suite;
- release verification;
- installed command checks;
- wheel build;
- clean-wheel installation and tests;
- deterministic reference checks;
- dependency validation.

The permanent release verifier reproduces three complete provider-free scenarios:

- general success;
- specialist recovery after false success;
- specialist terminal rejection of path traversal.

Across those scenarios it validates 12 role calls and independently verifies three private transport ledgers.

## What is proven

The current repository proves, for the controlled exact file-write fixture, that:

- requests can be versioned and pre-authorised deterministically;
- model-shaped outputs can be parsed fail-closed into bounded role schemas;
- proposed writes can be checked against the exact task contract before mutation;
- source-reported success can be separated from independently observed state;
- false success can trigger one evidence-backed recovery attempt;
- security failures remain terminal;
- Auditor, Recovery and Synthesiser text cannot override authoritative evidence;
- every provider-shaped call can be recorded and later verified without re-execution.

## What is not yet proven

The repository does **not** yet prove:

- performance of any real hosted or local model;
- comparative reliability from a statistically meaningful live sample;
- monetary cost or price efficiency;
- safe execution of arbitrary tools;
- concurrent ledger writing;
- prompt-redacted public ledger publication;
- production readiness or unattended operation.

No real provider request has been used as benchmark evidence.

## Current limitations

- The validated mutation surface is one confined file-write action.
- The transport ledger is deliberately single-writer.
- Private ledgers may contain prompts and model outputs.
- Automatic retry and price estimation are excluded.
- There is no public live-execution CLI.
- The OpenAI adapter exists, but real-provider execution remains a separate controlled experiment.

## Current priority

**Prepare a reviewable v0.2 release candidate before any paid empirical run.**

The release-candidate gate should confirm:

- package and documentation version consistency;
- a documented private pilot procedure;
- explicit budget and call ceilings;
- secret handling and evidence-directory rules;
- preflight-only and scripted-provider demonstrations;
- a disclosure-safe export plan;
- a fresh Python 3.10–3.13 matrix on the complete release tree.

## Related but separate projects

The Agent Contract Compiler and Agent Action Firewall are tracked as separate repository issues. They may integrate with the Arena later, but they should not be folded into the v0.2 release scope.
