# Hiring manager brief — AI Operations Assurance

**Candidate:** Luca Panayiotou  
**Target work:** AI implementation, solutions, AI operations, evaluation and selective forward-deployed roles  
**Review time:** three to five minutes

## What this proves

Luca can take an ambiguous operational AI problem and turn it into a controlled implementation plan with:

- stakeholder and workflow discovery;
- precise functional and safety requirements;
- explicit role and authority boundaries;
- a source-linked data and evidence model;
- an acceptance contract that distinguishes completion from self-report;
- migration, shadow-mode, pilot and rollback planning;
- functional and adversarial test design;
- measurement and value logic;
- honest publication and claims boundaries.

The underlying Agent Reliability Arena provides inspectable Python, tests, CI, CodeQL, release evidence, tamper checks, independent postcondition verification and deterministic benchmark fixtures.

## The business case

The simulated client handles protection-insurance cases containing documents, evidence requirements and customer communications. The selected case includes conflicting income values. The proposed system does **not** guess which value is correct. It prepares a controlled request for clarification, requires human approval, creates a draft only, independently observes the resulting state and accepts completion only when the full evidence contract is satisfied.

This demonstrates a practical implementation principle:

> The valuable AI system is not the one that sounds most certain; it is the one whose authorised outcomes can be proved, reviewed and recovered.

## Evidence to inspect

1. `IMPLEMENTATION_CASE.md` — discovery, requirements, architecture, migration, tests, rollout and value model.
2. `synthetic_case.json` — public-safe input containing an intentional evidence conflict.
3. `acceptance_contract.json` — exact conditions for verified completion and terminal failure.
4. `DEMO_SCRIPT.md` — five-minute client or interview walkthrough.
5. repository root `EMPLOYER_REVIEW.md` — technical evidence and honest limitations.
6. `web/index.html` — deterministic trace viewer.
7. source and test files listed in the employer review.

## Role relevance

### Implementation Consultant

- converts customer workflow into configuration and acceptance requirements;
- plans migration, shadow mode, launch, adoption and rollback;
- communicates implementation trade-offs to technical and non-technical stakeholders.

### AI Operations / Transformation

- identifies a repeatable operational bottleneck;
- distinguishes safe assistance from autonomous regulated action;
- defines measurable reliability, throughput, rework and adoption metrics.

### Solutions / Forward-Deployed

- starts from the client's system of record and operational constraints;
- defines exact tool authority, evidence, idempotency and integration boundaries;
- connects technical architecture to a staged business deployment.

### AI Evaluation / Assurance

- tests false success, partial execution, stale approvals, duplicate retries, rollback and tampered summaries;
- uses independent observation and explicit acceptance contracts;
- preserves negative evidence and states what the experiment cannot prove.

## What remains to be demonstrated in employment

- delivery against a real customer's systems and data;
- independent production coding at sustained commercial scale;
- live integration ownership and on-call responsibility;
- measured real-world adoption, reliability and financial outcomes;
- domain-specific regulatory approval.

Those limitations are stated because the project is intended as auditable evidence, not inflated positioning.

## Suggested interview prompt

> Give Luca a small workflow with two conflicting inputs, one external action and a strict evidence requirement. Ask him to map the stakeholders, define the acceptance contract, identify authority boundaries, propose a pilot and explain what evidence would justify rollout.

That exercise directly tests the capabilities represented here.