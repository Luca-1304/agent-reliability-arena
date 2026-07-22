# Project status

Last verified: 22 July 2026

## Current state

Agent Reliability Arena is at **v0.2.0rc1**.

The public v0.1.0 evidence remains a deterministic fixture. It validates experiment plumbing, evidence separation, replay, metrics and the trace viewer; it is not a claim about external model performance.

The release candidate and current empirical preparation provide:

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
18. a local-only real-provider script that refuses GitHub Actions, missing approvals and missing environment credentials;
19. an immutable private evidence-set index covering completed and aborted runs;
20. a disclosure-safe public allow-list exporter and digest-verifying replay command;
21. public aggregate reconstruction from independently verified private ledgers;
22. adversarial secret, path, omission and outcome-mutation tests;
23. immutable repeated-experiment trial schedules and aggregate preflights;
24. deterministic counterbalanced condition order and unique trial seeds;
25. safe pause and continuation through a verified completed prefix without replay;
26. terminal refusal after partial or aborted repeated-trial evidence;
27. descriptive paired analysis with explicitly labelled uncertainty methods;
28. a permanent four-trial provider-free pause/resume and terminal-abort reproduction.

## Verification evidence

The private runner, disclosure exporter, repeated runner, release reproductions and guarded local script pass the complete matrix on Python 3.10, 3.11, 3.12 and 3.13.

Every supported version passes:

- source compilation;
- the complete source test suite;
- the existing release verifier;
- the disclosure release reproduction;
- the repeated-experiment release reproduction;
- installed command checks;
- wheel build;
- clean-wheel installation and tests;
- deterministic reference checks;
- dependency validation.

The permanent provider-free evidence includes:

- the deterministic v0.1.0 reference metrics;
- 64 permitted live request templates;
- all six strict role-output contracts;
- tamper-evident ledger verification;
- three complete orchestration scenarios covering success, recovery and terminal security rejection;
- the disabled pilot preflight with eight permitted calls;
- proof that the disabled policy blocks before provider invocation;
- one complete private-pilot rehearsal with both conditions, five role calls, five verified ledger records and seven private artifacts;
- refusal of the local execution script inside GitHub Actions or without both explicit approvals and an environment credential;
- a synthetic disclosure evidence set containing one completed and one aborted private run;
- verification that private prompts, provider payloads, notes and machine paths do not enter the public bundle;
- rejection of added, removed or altered private runs and changed public outcomes;
- provider-free public export and replay commands;
- one four-trial repeated experiment with two General-first and two Specialist-first orders;
- a one-trial pause followed by completion with no replay of the first five calls;
- 20 independently verified repeated-trial ledger records;
- reconstruction of 400 scripted measured tokens and 20 ms scripted wall-clock latency;
- a separate invalid-output trial with both trial and experiment abort evidence;
- proof that an aborted repeated root is terminal;
- package, installed-distribution and documentation consistency.

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
- real network execution remains disabled unless approved at the local script, pilot and adapter boundaries;
- conservative call, token and monetary reservations can be enforced before calls;
- a paired private run can preserve complete success evidence or partial abort evidence without persisting credentials;
- unplanned, duplicate or drifted calls can be rejected before provider invocation;
- a committed private run set cannot silently lose failed or aborted runs during export;
- public token, latency and outcome counts can be derived from verified private evidence;
- public bundles can exclude private prompts, outputs, notes, identifiers and machine paths;
- public aggregate mutation can be detected without provider access;
- a repeated schedule can be fixed by digest before any trial begins;
- order imbalance, duplicate seeds and source drift can be rejected before execution;
- a verified completed prefix can be continued without replaying its provider-shaped calls;
- partial, unexpected, altered or aborted trial evidence prevents unsafe continuation;
- absolute paired outcomes and measured usage can be reconstructed from verified trial ledgers;
- Wilson, paired normal-approximation and sign-test outputs can be labelled with their actual methods and limitations.

## What is not yet proven

The repository does **not** yet prove:

- performance of any real hosted or local model;
- that the local paid pilot path has executed successfully against a provider;
- that a real repeated experiment has been executed;
- comparative reliability from a statistically meaningful live sample;
- measured monetary cost or price efficiency;
- that the disclosure exporter has processed retained real-provider evidence;
- that any interval or p-value generalises beyond the recorded sample;
- safe execution of arbitrary tools;
- concurrent ledger writing;
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
- The disclosure exporter is validated against synthetic completed and aborted private evidence; real-evidence validation remains pending.
- The repeated runner is validated with scripted provider-shaped evidence only.
- A terminal repeated root must not be reused after a partial or aborted trial.
- The paired normal interval is explicitly an approximation and may be unreliable for small or sparse samples.

## Current priority

**Execute issue #14 only after the operator selects an exact dated model snapshot and approves the complete worst-case monetary reservation.**

The first-pilot, repeated-runner and disclosure mechanisms are ready at their provider-free boundaries. The next genuine evidence step remains the deliberate local provider call, independent verification of its private evidence, then either validation of issue #15 against that evidence or a separately reviewed repeated plan under issue #21.

## Related but separate projects

The Agent Contract Compiler and Agent Action Firewall remain separate projects. They may integrate later through reviewed interfaces but are outside the v0.2.0rc1 scope.
