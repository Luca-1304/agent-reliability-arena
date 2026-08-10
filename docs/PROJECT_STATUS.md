# Project status

Last verified: 10 August 2026

## Current state

Agent Reliability Arena is at **v0.2.0rc2**, with additional provider-free Stage 7 pre-execution hardening merged after that prerelease.

`v0.2.0rc2` is a published prerelease. Its checksum-verified assets are attested with SLSA provenance and CycloneDX statements tied to the release workflow and source commit. This records build and artifact identity; it is not a security certification, production-readiness claim or real-model benchmark.

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
28. a permanent four-trial provider-free pause/resume and terminal-abort reproduction;
29. a source-controlled Stage 7 privacy execution gate tied to issue #14, committed open and non-overridable at runtime;
30. a disabled Stage 7 candidate packet pinning the exact dated model snapshot, scenario, policy, preflight, price-source and reservation commitments without permitting execution;
31. strict private execution-policy verification that binds the execution config and permits only `external_execution_enabled: false -> true` relative to the committed candidate;
32. fail-closed provider model provenance requiring an explicit non-empty provider-returned model identity before orchestration can consume a result;
33. a prepared private output-directory check that runs before API-key lookup and is independently rechecked by the runner.

## Verification evidence

The current provider-free boundary passes the repository's layered authority set, including the complete Python 3.10, 3.11, 3.12 and 3.13 package matrix.

The final Stage 7 pre-execution hardening head merged through PR #115 after fresh success from:

- Tests;
- Reliability Fast Gate;
- Reliability Specialist Gates;
- Auditable policy-driven Deep Gate, including the repeated 15-pass engines on Python 3.10 and 3.13;
- CodeQL;
- Repository history boundary;
- Concurrent Evidence Ledger;
- GitHub Pages/privacy verification.

Every supported package version passes:

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
- proof that disabled policy and the open privacy gate block before provider invocation;
- one complete private-pilot rehearsal with both conditions, five role calls, five verified ledger records and seven private artifacts;
- refusal of the local execution script inside GitHub Actions or without the required approvals and later environment credential;
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
- exact Stage 7 candidate verification and execution-policy drift rejection;
- duplicate-key and symlink rejection for Stage 7 execution JSON inputs;
- rejection of missing or mismatched provider model provenance;
- proof that the paid Stage 7 script hits the privacy gate and prepared-output checks before API-key lookup;
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
- real network execution remains disabled unless the privacy, local-script, pilot and adapter boundaries are all satisfied;
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
- Wilson, paired normal-approximation and sign-test outputs can be labelled with their actual methods and limitations;
- the reviewed disabled Stage 7 candidate cannot become executable through silent model, scenario, call, token, currency or monetary drift;
- missing provider model identity cannot be silently replaced with the requested model ID;
- unresolved historical privacy state can machine-block the paid script before credential lookup.

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
- production readiness or unattended operation;
- provider-side deletion of the historical Vercel projects/deployments;
- provider-side removal of the affected historical GitHub objects and caches.

No real provider request has been used as benchmark evidence.

## Current limitations

- The validated mutation surface is one confined file-write action.
- Private ledgers may contain prompts and model outputs.
- Automatic retry and built-in price estimation are excluded.
- There is no public installed live-execution command.
- The real-provider script is local-only and remains machine-blocked while `examples/stage7_candidate/privacy-execution-gate.json` is open.
- The current Stage 7 packet proposes, but does not approve, a USD 1.00 maximum local monetary reservation.
- Local monetary limits are conservative operator reservations, not measured billing or an instantaneous provider-side cutoff.
- A single pilot cannot justify a public comparative conclusion.
- The disclosure exporter is validated against synthetic completed and aborted private evidence; real-evidence validation remains pending.
- The repeated runner is validated with scripted provider-shaped evidence only.
- A terminal repeated root must not be reused after a partial or aborted trial.
- The paired normal interval is explicitly an approximation and may be unreliable for small or sparse samples.
- The historical privacy incident remains open: the two retired Vercel projects and affected retained deployments still exist, and GitHub/Vercel have not yet provided verified removal confirmation.

## Current priority

**Historical privacy closure pending. Do not execute issue #14 while the source-controlled privacy gate remains open.**

The repository-owner cleanup and provider-free Stage 7 hardening are complete. As re-verified on 10 August 2026, the remaining blocker is platform-side historical removal under `docs/HOSTING_PRIVACY_BOUNDARY.md`. The affected historical Vercel URLs currently redirect through Vercel authentication rather than satisfying the required `404`/`410` erasure condition; this is mitigation, not closure.

After all historical closure criteria are independently satisfied, the next sequence is:

1. merge a focused exact-head-reviewed change closing the machine privacy gate;
2. freshly re-confirm the exact dated model snapshot and provider pricing;
3. prepare a dedicated restricted provider project/key and low provider-side spend backstop where practical;
4. prepare and provider-free verify a private enabled policy differing from the committed candidate only by `external_execution_enabled: true`;
5. explicitly approve the complete local token and monetary reservation;
6. prepare the private output directory, then supply `OPENAI_API_KEY` through the local environment and execute exactly once with no automatic retry;
7. clear the credential and independently verify/preserve success, failure or abort evidence.

Until Step 0 is closed, provider-free tests, documentation maintenance and GitHub Pages/privacy verification may continue, but no real-provider request or spend is authorised.

## Related but separate projects

The Agent Contract Compiler and Agent Action Firewall remain separate projects. They may integrate later through reviewed interfaces but are outside the v0.2.0rc2 scope.