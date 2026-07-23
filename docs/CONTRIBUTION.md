# Contribution and authorship

## Problem framing and acceptance standard

Luca Panayiotou identified false completion as the practical agent failure mode worth isolating: a consequential task is not complete merely because an agent or tool reports success. Completion must correspond to independently observed state satisfying an exact acceptance contract.

For Agent Reliability Arena, Luca chose the held-constant engineering question: whether General and role-specialised orchestration behave differently when the task, model configuration, tools, sandbox, failure schedule, mutation limit and evidence rules remain the same.

He required deterministic fixture evidence to remain visibly separate from empirical real-model evidence. He also required extra calls, failures, aborts and limitations to remain reportable rather than being hidden behind a favourable aggregate.

## Architecture and authority constraints

Luca required the system to separate functions that are often collapsed in agent demonstrations:

- Strategist and Auditor roles cannot mutate state;
- the Operator cannot approve its own completion;
- proposed actions must match the exact authorised path and content before mutation;
- independent observation and the completion verifier remain authoritative over agent text;
- Recovery is evidence-triggered and bounded rather than an unlimited retry loop;
- external execution requires explicit policy, preflight, approval and credential boundaries;
- failed and aborted runs must preserve verifiable evidence;
- public export must exclude private prompts, raw provider payloads, identifiers, operator notes and machine-local paths.

These constraints define the project's architecture and claims boundary, not merely its presentation.

## Review and defect correction

Luca directed iterative review rather than treating generated output as complete by default. He approved publication only after source tests, installed-command checks, clean-wheel verification and evidence-package checks passed.

During development, release, fixture, checksum, attestation, schema and Python-version defects were surfaced. Luca's standing requirement was that defects be fixed at their source, rerun through the exact verification gates and recorded honestly rather than hidden or reframed as success.

He also approved the removal of unnecessary verifier and workflow proposals when repository review showed they would add maintenance without adding meaningful evidence.

## AI-assisted implementation

The repository's architecture refinement, Python implementation, tests, documentation and static viewer were developed through **AI-assisted implementation** under Luca's direction, constraints and review.

This record does not present generated implementation as unaided authorship. It distinguishes Luca's problem selection, acceptance standard, architectural constraints, publication decisions and review responsibility from AI-assisted drafting and coding.

## Evidence over authorship claims

Neither Luca's statement nor an AI-generated success report determines correctness. The repository evidence does:

- deterministic fixtures and independently reconstructed metrics;
- adversarial source tests;
- Python 3.10–3.13 matrices;
- installed-package and clean-wheel verification;
- checksum-locked public manifests;
- release records and attestations;
- explicit limitations and prohibited-claim checks.

Reviewers should evaluate the work through those artifacts and the linked source/tests.

## What the project does not claim

The project does not claim that deterministic role policies are external-model results, that the Specialist condition is always preferable, that the current prerelease is production readiness, or that role-conditioned components are independent conscious beings.

Future real-model work must preserve exact versions, prompts, usage, repeated paired runs, retained failures and uncertainty before comparative conclusions are published.