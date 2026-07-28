# Five-minute demo — AI Operations Assurance

## Audience

Implementation consultant, solutions engineer, AI operations, evaluation or forward-deployed hiring panel.

## Opening — 0:00 to 0:35

> This is a synthetic protection-insurance operations case. The problem is not simply whether an AI can draft a useful response. The problem is whether the organisation can prove that the correct, authorised action happened—and distinguish that from a confident but unsupported success message.

Show `synthetic_case.json` and identify:

- two different annual-income values;
- recorded customer consent;
- the proposed information request;
- the requirement for human approval;
- the fact that the pilot may create a draft but must not send it.

## Discovery and requirements — 0:35 to 1:20

> I modelled the workflow around the people who must trust it: case handlers, team leaders, quality reviewers, customers, security owners and the implementation sponsor. The critical requirements are source-linked facts, preserved conflicts, explicit approval, idempotency, independent observation and retention of failed or aborted work.

Open `IMPLEMENTATION_CASE.md`, sections 2 to 5.

Emphasise that the design does not automate regulated advice or resolve the income conflict by itself.

## Architecture and authority — 1:20 to 2:15

Show the workflow diagram and authority table.

> Recommendation, mutation, observation and approval are separated. The Strategist may propose but cannot mutate. The Operator may mutate but cannot approve. The observer reads the resulting state independently. Only the Completion Verifier can derive the final outcome from the exact evidence contract.

Relate this to the underlying Agent Reliability Arena:

- same task and evidence rules across conditions;
- deterministic failure injection;
- independent postcondition checking;
- bounded recovery;
- replayable evidence.

## The acceptance contract — 2:15 to 3:10

Open `acceptance_contract.json`.

Walk through the six requirements:

1. preserve the income conflict;
2. record exact human approval;
3. create the approved draft exactly once;
4. observe the resulting draft independently;
5. prove it was not sent;
6. retain the complete audit record.

> A tool saying `success: true` does not satisfy this contract. A missing observation produces `UNVERIFIED`; a content mismatch or unauthorised send produces `FAILED`; a complete matching evidence set produces `VERIFIED_COMPLETE`.

## Testing and rollout — 3:10 to 4:05

Show the functional, adversarial and release-gate sections.

Mention:

- false success;
- partial creation;
- stale approval;
- duplicate retry;
- target substitution;
- public-evidence leakage;
- tampered aggregate metrics;
- rollback overriding earlier success.

> I would begin in shadow mode, move to a confined pilot with human approval, and only then consider a narrow production trial. The manual process remains available as rollback.

## Value and honest boundary — 4:05 to 4:40

> The value model is explicit and hypothetical: 500 eligible cases and eight minutes released per case would equal about 66.7 hours of monthly capacity. At an illustrative loaded cost of £25 per hour, that is roughly £1,667 of gross monthly capacity before AI, implementation, review and support costs. I would replace every assumption with observed pilot data before making a business case.

State clearly:

- no real customer data;
- no insurer deployment claim;
- no production savings claim;
- no claim that deterministic fixtures measure a hosted model.

## Close — 4:40 to 5:00

> The work demonstrates how I approach implementation: identify the operational failure, define exact evidence and authority boundaries, build a controlled path, test adversarially, retain negative evidence and communicate what remains unproven. The repository provides the inspectable technical foundation; this case translates it into a customer-facing implementation plan.

## Likely questions

### Why not let the same agent check its own work?

Because the actor can reproduce the same mistaken assumption or trust the same success-shaped receipt. Independent observation creates a different evidence source.

### Why is the income conflict not automatically resolved?

The documents disagree and there is no authorised rule proving which value is current. The correct operational output is a controlled information request, not invented certainty.

### Why create a draft instead of sending?

The pilot is designed to establish reliability and adoption without exposing customers to an unproven automated communication path.

### What would be built next?

A confined runnable adapter that maps the synthetic case into the Arena's existing mutation, observation and verification path, followed by a user-reviewed shadow-mode pilot.

### What did Luca personally contribute?

The failure selection, evidence standard, role-authority boundaries, recovery constraints, publication boundary, implementation framing and accountable review. Code and documentation are transparently identified as AI-assisted where applicable.