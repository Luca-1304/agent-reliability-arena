# Agent Reliability Arena: Technical Report

**Author:** Luca Panayiotou  
**Public version:** `0.2.0rc1`  
**Release date:** 23 July 2026  
**Evidence status:** deterministic fixture and provider-free integration evidence

## Abstract

Agent Reliability Arena is a controlled software evaluation system for comparing a single general agent with a bounded specialist orchestration under the same task, model configuration, tools, sandbox, failure scenario and independently observed acceptance contract. The project is designed around a simple question: does role-specialised orchestration improve reliable completion enough to justify its additional calls and complexity?

The current public evidence validates the experiment plumbing, role boundaries, evidence preservation, replay, private-run safeguards, repeated-experiment planning and disclosure controls. It does not measure a hosted or local model. **No real-provider benchmark has been executed.** The current prerelease is not production readiness, a safety certification, or evidence of universal model superiority.

## Research question

The primary comparison holds the task and operational boundary constant while changing orchestration:

- **General condition:** one policy plans, acts, checks and reports.
- **Specialist condition:** Strategist, Operator, Auditor, Recovery and Synthesiser roles operate through explicit authority boundaries.

The intended dependent variable is independently verified task completion, not the agent's own completion claim. Secondary observations include false-completion claims, recovery outcomes and logical call overhead.

## System architecture

The Arena separates responsibilities that are often collapsed in ordinary agent demos:

1. deterministic experiment configuration and permission preflight;
2. exact request construction and bounded role contracts;
3. confined mutation through an Operator-only path;
4. independent state observation after execution;
5. completion verification from observed evidence;
6. evidence-derived audit, bounded recovery and final synthesis;
7. append-only transport records for provider-shaped calls;
8. immutable trial scheduling and verified-prefix continuation;
9. disclosure-safe export from an indexed private evidence set;
10. provider-free public replay and aggregate reconstruction.

Strategist and Auditor roles cannot mutate state. The Operator cannot approve completion. Recovery is permitted only after a verified mismatch and is bounded to one attempt in the reference design. A Synthesiser cannot report success unless the independent verifier reports `VERIFIED_COMPLETE`.

## Evidence taxonomy

### 1. Deterministic fixture evidence

The public reference fixture is a software-validation dataset. Under fixed policies it records:

| Metric | General | Unified specialists |
|---|---:|---:|
| Independently verified outcomes | 2/8 | 6/8 |
| False completion claims | 3 | 0 |
| Recovered scenarios | 0 | 4 |
| Logical role calls | 8 | 44 |

The fixture therefore contains four paired outcome improvements and three fewer false-completion cases at an additional 36 logical calls. These values validate the deterministic evaluation and demonstration path. They are not measurements of OpenAI, Anthropic, Gemini, local models, people or production systems.

### 2. Provider-free integration evidence

Scripted provider-shaped responses exercise:

- provider-neutral request and result contracts;
- strict role-output parsing;
- request, result and ledger digests;
- success, recovery and terminal-failure paths;
- disabled-by-default network execution;
- hard call, token-reservation and monetary-reservation ceilings;
- one private paired rehearsal;
- a counterbalanced repeated experiment with pause and replay-free continuation;
- completed and aborted evidence retention;
- disclosure export and public replay without provider access.

This class proves software behavior around an external-provider boundary. It does not prove the behavior of a real model.

### 3. Real-provider empirical evidence

This class remains uncollected. A future pilot would require a dated model snapshot, a reviewed policy digest, exact call-plan approval, a local environment credential, a hard spend ceiling, private evidence retention and independent verification before any public export.

`provider_called: false`  
`comparative_claim_permitted: false`

## Reliability controls

The release candidate includes:

- exact permission and budget preflight;
- three independent approvals before a real network opener can execute;
- rejection of unplanned or duplicate calls;
- credential exclusion from source, policy, logs and public exports;
- tamper-evident private ledgers;
- fresh-directory and path-confinement requirements;
- preserved abort evidence;
- immutable repeated-trial schedules;
- terminal refusal after partial or altered trial evidence;
- public aggregates reconstructed during replay rather than trusted as supplied.

## Threats to validity

The deterministic fixture is intentionally small and constructed. It does not estimate representative effect size. Scripted provider responses do not model latency, cost, refusal patterns or output variance of a live service. More role calls can create additional cost and failure surface. The current descriptive intervals and sign tests, when used, apply only to the recorded sample and do not establish causality or generality.

The architecture reduces specific classes of false completion and evidence drift; it does not establish unrestricted-tool safety. The prerelease is research and engineering infrastructure, not production readiness.

## Reproducibility

The public fixture, preflight, release verifiers, showcase verifier, launch-package verifier and citation-package verifier require no provider credential and make no external model request. Exact commands are recorded in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Public provenance

This report is linked to:

- release tag `v0.2.0rc1`;
- the public prerelease URL;
- showcase manifest digest `30061fec34ed199b6dcec650b78a7ee320166d11f08c74302871015fb4ca12e7`;
- launch-package manifest digest `620c658240e4b05571de47dd66be13fbde72a6540ba06ba977d8056caf17427e`;
- the machine-readable record in `citation/provenance.json`.

## Conclusion

Agent Reliability Arena demonstrates an evidence-first pattern for evaluating orchestration changes without treating an agent's own report as proof. The current contribution is a reproducible software system, deterministic fixture, provider-free integration rehearsal and disclosure boundary. A real-provider comparison remains a separate, explicitly gated empirical stage.
