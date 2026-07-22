# Disclosure-safe evidence boundary

This document defines what may move from a private real-provider run into a public Agent Reliability Arena evidence bundle.

## Private by default

The following remain private unless deliberately reviewed and separately approved:

- complete prompts and role inputs;
- complete model outputs and refusals;
- raw provider response bodies;
- API credentials and authentication headers;
- provider request and response identifiers;
- local absolute paths, usernames, hostnames and machine identifiers;
- private operator notes;
- unredacted transport ledgers;
- provider account, billing or organisation identifiers;
- screenshots containing private console, browser or account information.

Private evidence must remain available long enough to verify public claims, but availability to the public is not required.

## Implemented derivation mechanism

The release candidate now provides:

- `write_private_evidence_index(...)`, which writes an immutable index of every private run directory;
- `build_disclosure_safe_empirical_export(...)`, which derives an allow-listed public bundle;
- `write_disclosure_safe_empirical_export(...)`, which writes the public bundle without overwriting an existing file;
- `verify_disclosure_safe_empirical_export(...)`, which verifies the public schema, digest, aggregate reconstruction and claims boundary;
- `arena-export-live-evidence`, the provider-free export command;
- `arena-verify-live-export`, the provider-free public replay command.

The private evidence-set index commits to:

- the exact completed and aborted run set;
- each run status;
- each private file-manifest digest and file count;
- each independently verified private-ledger digest;
- a per-run source commitment;
- one digest covering the complete index.

After the index is written, adding, deleting or changing a private run causes export to fail. This prevents favourable omission after the evidence set has been committed.

## Permitted public fields

A disclosure-safe export may include:

- experiment, configuration, contract and prompt-catalogue digests;
- provider name and exact model identifier recorded by the private ledger;
- scenario IDs, seeds and held-constant fairness fields;
- policy and preflight-manifest digests;
- absolute outcome, failure, recovery and security-rejection counts;
- completed-run and aborted-run counts;
- measured input, output, cached, reasoning and total tokens when returned;
- measured wall-clock and provider processing time;
- dated price-source metadata, kept separate from measured usage and provider billing;
- independently verified final status;
- public evidence references based on stable private commitments;
- private file-manifest and ledger digests;
- redaction record and limitations.

## Prohibited publication

The exporter and public verifier reject or exclude:

- API keys, bearer tokens or authentication material;
- complete prompts, role inputs or model outputs;
- raw provider payloads and provider request/response IDs;
- raw private ledger records;
- local absolute paths or environment dumps;
- private operator notes;
- selective omission of indexed failed or aborted runs;
- changes to measured outcomes during redaction;
- aggregate metrics that do not reconstruct from the public per-run records;
- metrics that cannot be traced to verified private evidence;
- unsupported causal, representative or universal claims;
- a dated price calculation presented as measured provider billing.

## Required derivation rule

Public evidence must be generated from independently verified private artifacts. It must not be assembled manually from memory, screenshots or favourable excerpts.

The implemented derivation process:

1. commits the complete private run set before export;
2. verifies current run membership against that index;
3. verifies each private file commitment and transport ledger;
4. derives public counts and measurements from verified records;
5. applies an explicit public field allow-list;
6. records every excluded category;
7. calculates a public bundle digest after redaction;
8. preserves stable private source commitments;
9. retains failed and aborted runs in public aggregate counts;
10. performs no provider request during export or replay.

## Provider-free adversarial verification

The permanent release reproduction uses one synthetic completed private run and one synthetic aborted private run. It inserts private markers, prompts, notes and machine paths into private-only files and provider-shaped outputs, then proves that:

- both runs remain represented publicly;
- source commitments and the public bundle digest verify;
- private markers and prohibited fields do not appear publicly;
- added, removed or changed private runs are rejected;
- changed public outcomes or aggregate counts are rejected;
- dated price metadata remains separate from usage;
- export and replay work without credentials or provider access;
- editable and clean-wheel verification pass on Python 3.10–3.13.

This validates the mechanism against representative synthetic private evidence. Validation against retained real-provider evidence remains blocked on Stage 7 or Stage 8.

## Claims boundary

Disclosure-safe evidence improves auditability and privacy. It does not make a small sample statistically representative, prove that hidden private prompts had no influence beyond the controlled experiment design, or authorise a comparative claim from one pilot. Public bundles therefore retain `comparative_claim_permitted: false` until a separately reviewed repeated experiment supports cautious analysis.
