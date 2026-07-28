# AI Operations Assurance — implementation case

**Project lead:** Luca Panayiotou  
**Evidence basis:** Agent Reliability Arena and Agent Completion Verifier  
**Case status:** public-safe implementation simulation using synthetic data  
**Purpose:** demonstrate requirements discovery, solution design, controlled AI workflow implementation, testing, rollout planning and value measurement for implementation, solutions, AI operations and forward-deployed roles.

## 1. Executive summary

A protection-insurance operations team receives customer documents, checks whether information is complete, prepares a recommended next action and communicates with customers and advisers. The process is slow, repetitive and vulnerable to a specific AI failure: an assistant can confidently report that a task is complete even when the required external state was never created.

This case designs a controlled AI-assisted workflow in which:

1. documents are ingested and classified;
2. proposed facts retain source references;
3. missing or conflicting information is surfaced;
4. the system proposes an authorised next action;
5. high-risk actions require human approval;
6. every mutation is independently observed;
7. completion is accepted only when the exact evidence contract is satisfied;
8. failed, partial and rolled-back actions remain visible in the audit trail.

The design reuses the repository's existing authority separation, independent observation and completion-verification principles. It does **not** claim deployment into a real insurer, measured customer outcomes or production readiness.

## 2. Client problem

### Current-state workflow

A case handler typically:

- opens several documents and emails;
- identifies customer, policy and underwriting facts;
- checks whether required evidence is present;
- decides whether to request information, prepare a recommendation or escalate;
- drafts a communication;
- records an action in a case-management system;
- confirms whether the action actually occurred.

### Failure modes

| Failure | Operational consequence |
|---|---|
| Missing evidence treated as present | unsuitable recommendation or avoidable delay |
| Conflicting document values silently merged | incorrect case state |
| Draft mistaken for sent communication | customer is not informed |
| Tool success receipt trusted without checking state | false completion |
| Agent both acts and approves its own work | weak accountability |
| Retried action creates duplicates | duplicated contact or records |
| Failed or rolled-back action disappears from reporting | misleading performance data |
| Sensitive data leaks into logs or public evidence | privacy and reputational harm |

## 3. Users and stakeholders

| Stakeholder | Need | Main risk |
|---|---|---|
| Case handler | faster review with clear evidence | automation hides uncertainty |
| Team leader | consistent decisions and exceptions | incorrect throughput metrics |
| Compliance or quality reviewer | traceable source-to-action chain | unverifiable reasoning |
| Customer or adviser | accurate and timely communication | wrong or duplicate message |
| Security and data owner | controlled access and retention | excessive data exposure |
| Implementation sponsor | measurable operational value | impressive demo without adoption |

## 4. Scope

### In scope

- synthetic case intake;
- deterministic document metadata and extracted facts;
- source-linked evidence records;
- conflict and missing-field detection;
- proposed next-action generation;
- authority and approval checks;
- confined simulated mutations;
- independent post-action observation;
- completion verification;
- audit, rollback and duplicate prevention;
- pilot metrics and rollout plan.

### Out of scope

- real customer data;
- regulated advice;
- automatic underwriting decisions;
- autonomous external communication;
- production identity, SSO or role provisioning;
- certification of legal or regulatory compliance;
- claims about real-provider model accuracy.

## 5. Requirements

### Must have

- Every extracted fact must identify its source document and source field.
- Conflicting values must remain unresolved until an authorised person selects or corrects one.
- Missing mandatory evidence must block a completion claim.
- The role that proposes an action must not approve final completion.
- External or customer-facing actions must require explicit approval in the pilot.
- A successful tool report must not count as completion without independent observation.
- A retry must use an idempotency key and must not silently duplicate an earlier action.
- Rollback or later failure must override an earlier successful state.
- Audit records must preserve attempted, failed, recovered and aborted work.
- Public evidence must exclude customer content, credentials, provider payloads and local machine paths.

### Should have

- Human-readable explanation of why a case is blocked.
- Replayable test cases for ordinary and adversarial paths.
- Measured latency, call count and cost fields when a real pilot is approved.
- Exportable management summary reconstructed from raw evidence rather than supplied totals.

### Could have later

- integration with a real CRM or case-management sandbox;
- document OCR and classification models;
- policy-specific rule packs;
- queue prioritisation;
- reviewer sampling and drift monitoring.

## 6. Proposed workflow

```text
Synthetic case bundle
        │
        ▼
Intake validation ───────► reject malformed or unauthorised input
        │
        ▼
Evidence extraction ─────► facts retain source references
        │
        ▼
Conflict / completeness gate
        │
        ├── blocked ─────► human resolution queue
        │
        ▼
Strategist proposes bounded next action
        │
        ▼
Authorisation + human approval gate
        │
        ▼
Operator performs confined mutation
        │
        ▼
Independent observer reads resulting state
        │
        ▼
Completion Verifier checks exact contract
        │
        ├── VERIFIED_COMPLETE
        ├── PARTIAL
        ├── UNVERIFIED
        └── FAILED
        │
        ▼
Auditor records outcome; Recovery may attempt one justified correction
```

## 7. Authority model

| Function | May read evidence | May propose | May mutate | May approve | May declare completion |
|---|---:|---:|---:|---:|---:|
| Intake validator | yes | no | no | no | no |
| Strategist | yes | yes | no | no | no |
| Human case handler | yes | yes | no | yes | no |
| Operator | minimum required | no | yes | no | no |
| Independent observer | resulting state only | no | no | no | no |
| Auditor | evidence and trace | no | no | no | no |
| Recovery | mismatch evidence | bounded correction | one authorised retry | no | no |
| Completion Verifier | contract and observation | no | no | no | yes, evidence-derived only |

The system separates recommendation, mutation, observation and acceptance. No role can create the evidence that it alone uses to approve itself.

## 8. Data and evidence model

The accompanying files contain a synthetic case and its acceptance contract.

Core objects:

- `case`: synthetic customer and policy context;
- `documents`: source-labelled records with issue dates and declared fields;
- `facts`: extracted values with source references and confidence metadata;
- `conflicts`: unresolved incompatible values;
- `proposed_action`: exact action, target and content digest;
- `approval`: approver identity, scope, timestamp and policy digest;
- `event`: attempted action and source-reported result;
- `observation`: independently read post-action state;
- `evaluation`: verifier outcome and missing evidence;
- `audit_record`: immutable sequence and digests.

The trust boundary is explicit: source reports are useful trace data, but canonical completion evidence comes from the independent observation.

## 9. Migration and implementation plan

### Phase 0 — discovery and baseline

- map the real workflow with case handlers;
- sample ordinary, incomplete, conflicting and failed cases;
- record baseline handling time, rework, duplicate contacts and missed-action rate;
- identify systems of record and data owners;
- agree the exact actions that remain human-only.

### Phase 1 — shadow mode

- use synthetic or approved de-identified cases;
- generate recommendations without performing actions;
- compare recommendations with human decisions;
- refine evidence requirements and exception categories;
- do not measure success through model confidence.

### Phase 2 — confined pilot

- permit one low-risk simulated or sandbox mutation;
- require explicit approval for every action;
- verify resulting state independently;
- preserve all failed and aborted attempts;
- stop automatically on policy mismatch, duplicate risk or security rejection.

### Phase 3 — limited production trial

- restrict to a narrow case type and trained user group;
- use least-privilege service identity and idempotency controls;
- keep customer-facing communication human-approved;
- review daily exceptions and weekly metrics;
- maintain rollback to the existing manual process.

### Phase 4 — scale decision

Scale only if the evidence shows improved throughput without unacceptable increases in error, rework, privacy exposure or user burden.

## 10. Test strategy

### Functional tests

- complete case produces a permitted recommendation;
- missing mandatory document blocks completion;
- conflicting facts produce a resolution task;
- exact approved action succeeds;
- action content differing from approval is rejected;
- successful retry recovers a transient failure;
- later failure or rollback overrides earlier success;
- observation proves completion even when the source did not claim it.

### Adversarial tests

- false success with no resulting state;
- partial record creation;
- duplicate retry;
- path or target substitution;
- stale approval reused against changed content;
- malformed role output;
- prompt or note leakage into public export;
- unauthorised external execution;
- aborted run omitted from a later summary;
- tampered aggregate metrics.

### Release gates

These are **pilot acceptance targets, not measured production results**:

- zero accepted completion claims without the full evidence contract;
- 100% of customer-facing actions require recorded approval;
- 100% of mutations have a matching observation and audit record;
- zero silent omission of failed or aborted attempts;
- exact replay reproduces the published summary;
- all security-rejection scenarios terminate without mutation;
- test and packaging checks pass on every supported Python version.

## 11. Measurement plan

### Reliability

- verified completion rate;
- false-completion rate;
- claim precision;
- partial and failed outcome counts;
- duplicate-action rate;
- recovery rate;
- unresolved-conflict rate.

### Operations

- median active handling time;
- queue age;
- rework per case;
- customer follow-up delay;
- reviewer override rate;
- exception volume by category.

### Cost and complexity

- logical role calls;
- provider calls, tokens, latency and measured billing when enabled;
- human review minutes;
- engineering and support effort;
- avoided handling time.

### Illustrative value model

This example is deliberately hypothetical:

- 500 eligible cases per month;
- 8 minutes of active handling saved per case;
- 4,000 minutes, or about 66.7 hours, released per month;
- at an illustrative loaded cost of £25 per hour, gross capacity value is about £1,667 per month before model, implementation, review and support costs.

A deployment decision would use observed values, include error and rework costs, and avoid treating released capacity as guaranteed cash savings.

## 12. Rollout and change management

- name an accountable process owner;
- train users on evidence status rather than model confidence;
- show blocked reasons and the exact next human action;
- run office hours during the pilot;
- publish a short operating guide and escalation path;
- review false positives, false negatives and overrides weekly;
- keep the manual workflow available during the controlled trial;
- communicate that automation assists case handling and does not provide regulated advice.

## 13. Risks and controls

| Risk | Control |
|---|---|
| fabricated or weakly sourced fact | mandatory source reference and conflict gate |
| autonomous customer communication | explicit human approval and exact content digest |
| false tool success | independent observation and verifier contract |
| duplicate contact | idempotency key and latest-state check |
| excessive access | least privilege and function-level authority boundaries |
| sensitive evidence disclosure | private raw records and allow-listed export |
| misleading performance claim | raw evidence replay and explicit publication boundary |
| indefinite recovery loop | one justified bounded recovery attempt |
| adoption failure | shadow mode, user training, exception review and rollback |

## 14. Deliverables to a client or hiring panel

- discovery and requirements map;
- synthetic case and acceptance contract;
- architecture and authority model;
- implementation and migration plan;
- functional and adversarial test plan;
- rollout and rollback plan;
- measurement and illustrative value model;
- five-minute demonstration script;
- inspectable underlying reliability repository and reproducible fixture.

## 15. Honest evidence statement

This implementation case demonstrates Luca Panayiotou's ability to define the operational failure, set evidence and authority requirements, structure an implementation, identify risks, specify tests, control claims and communicate trade-offs. The underlying repository contains AI-assisted Python implementation, tests and release tooling produced under his direction and review.

It does not establish unaided software authorship, production deployment in insurance, regulatory approval, customer outcomes or seniority across every role to which the skills may be relevant. Those boundaries are part of the evidence discipline being demonstrated.