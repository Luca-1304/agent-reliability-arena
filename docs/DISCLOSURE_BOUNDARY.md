# Disclosure-safe evidence boundary

This document defines what may move from a private real-provider run into a public Agent Reliability Arena evidence bundle.

## Private by default

The following remain private unless deliberately reviewed and redacted:

- complete prompts and role inputs;
- complete model outputs and refusals;
- raw provider response bodies;
- API credentials and authentication headers;
- local absolute paths, usernames, hostnames and machine identifiers;
- private operator notes;
- unredacted transport ledgers;
- provider account, billing or organisation identifiers;
- screenshots containing private console, browser or account information.

Private evidence must remain available long enough to verify public claims, but availability to the public is not required.

## Permitted public fields

A disclosure-safe export may include:

- experiment, configuration, contract and prompt-catalogue digests;
- provider name and exact dated model identifier;
- scenario IDs, seeds and held-constant fairness fields;
- policy and preflight-manifest digests;
- absolute outcome, failure and recovery counts;
- measured input, output, cached, reasoning and total tokens when returned;
- measured wall-clock and provider processing time;
- dated price-source metadata, kept separate from measured usage;
- independently verified final status;
- public evidence references;
- private ledger digest or another stable commitment to the private source evidence;
- redaction record, limitations and aborted-run counts.

## Prohibited publication

A public export must reject:

- any API key, bearer token or authentication material;
- unapproved full prompts or model outputs;
- raw private ledger records;
- local absolute paths or environment dumps;
- selective omission of failed or aborted runs;
- changes to measured outcomes during redaction;
- metrics that cannot be traced to verified private evidence;
- unsupported causal, representative or universal claims;
- a dated price calculation presented as measured provider billing.

## Required derivation rule

Public evidence must be generated from independently verified private artifacts. It must not be assembled manually from memory, screenshots or favourable excerpts.

The derivation process must:

1. verify the private ledger and source manifests;
2. derive public counts and measurements from those verified records;
3. apply explicit field allow-lists;
4. record every redaction or omission category;
5. calculate public artifact digests after redaction;
6. preserve a stable link to the private source digest;
7. retain failed and aborted runs in aggregate counts;
8. perform no provider request during export or replay.

## Current release-candidate status

`0.2.0rc1` defines this boundary but does not yet publish real-provider evidence. The current static viewer continues to use the deterministic v0.1.0 fixture export.

Issue #15 tracks implementation and adversarial validation of the live disclosure-safe export.

## Claims boundary

Disclosure-safe evidence improves auditability and privacy. It does not make a small sample statistically representative and does not prove that hidden private prompts had no influence beyond what the controlled experiment design can establish.
