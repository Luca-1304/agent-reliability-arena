# Agent Reliability Arena — technical summary

**Author and project lead:** Luca Panayiotou  
**Implementation:** AI-assisted implementation, documentation and testing under Luca's problem framing, acceptance standard and review direction.

## Engineering question

Agent Reliability Arena asks a narrow, testable question:

> When the model, task, tools and evidence rules stay fixed, can role-specialised orchestration improve independently verified completion enough to justify its added calls and complexity?

The comparison is between one general agent and one unified specialist system with bounded Strategist, Operator, Auditor, Recovery and Synthesiser roles. Completion is determined by independently observed state, not by a success-shaped model or tool report.

## System design

The repository implements:

- deterministic experiment configuration and held-constant fairness metadata;
- exact tool and completion contracts;
- confined file mutation followed by independent observation;
- a verifier that remains authoritative over agent text;
- strict role-output schemas and canonical digests;
- provider-neutral request and result contracts;
- append-only, tamper-evident private transport evidence;
- explicit call, token and monetary reservations before external execution;
- preregistered repeated trials with counterbalanced condition order;
- safe pause and continuation through a verified completed prefix;
- disclosure-safe public export derived from verified evidence.

## What is verified

The public deterministic fixture contains eight paired scenarios. In that fixture:

- the general condition completed **2 of 8** scenarios;
- the specialist condition completed **6 of 8** scenarios;
- **3** unsupported completion claims were removed;
- the specialist path used **36 additional logical role calls**.

These numbers validate the software, evidence separation and demonstration path. They are not hosted-model measurements.

Provider-free release reproductions also verify:

- strict parsing for all six role-output types;
- success, recovery and terminal security paths;
- private paired-run success and abort evidence;
- duplicate and unplanned call rejection;
- four counterbalanced repeated trials with safe pause and continuation;
- independent reconstruction of repeated-trial usage and latency;
- disclosure export retaining completed and aborted outcomes while excluding private material;
- source and clean-wheel verification on Python 3.10, 3.11, 3.12 and 3.13.

## Engineering value

The project demonstrates practical work in evaluation design, agent architecture, security boundaries, deterministic testing, evidence integrity, packaging, CI, release discipline and honest claims management.

It is designed to be reviewable: each stage has a narrow contract, adversarial tests, a reproducible release fixture and a written boundary describing what the evidence does and does not support.

## What is not claimed

The current showcase does not claim:

- measured performance of a real hosted or local model;
- a representative comparison across tasks, providers or populations;
- that specialist orchestration is always preferable;
- measured provider billing or real-world cost efficiency;
- safety for unrestricted tools or unattended production operation;
- that a real paid-provider pilot has already run.

No real-provider benchmark request or provider spend has been executed.

## Review route

1. Open `web/index.html` through a local static server.
2. Inspect the false-success trace and the independent evidence panel.
3. Run the provider-free reproduction commands from `README.md`.
4. Run `arena-verify-showcase` to verify the compact public package.
5. Review `docs/PUBLICATION_BOUNDARY.md` for the disclosure rules.
