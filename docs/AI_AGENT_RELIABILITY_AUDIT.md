# AI Agent Reliability Audit

A fixed-scope technical review for teams using AI agents or tool-calling workflows that need stronger evidence before an action is treated as complete.

## The problem

An agent can produce a convincing completion message even when an email was not sent, a file was only partly written, a record was created with the wrong fields, a retry failed, or a later rollback invalidated an earlier success.

The audit separates **what the agent said** from **what the system can independently prove**.

## Suitable workflows

- customer or internal email automation;
- CRM, ticketing or database updates;
- document and file-generation pipelines;
- research or data-collection agents;
- multi-step operational workflows;
- general versus specialist-agent orchestration;
- prototypes preparing for controlled internal use.

## Fixed-scope audit

One audit covers one clearly bounded workflow and normally includes:

1. **Workflow map** — requested outcome, tools, permissions, handoffs and failure points.
2. **Completion contract** — the observable evidence required before the workflow may claim success.
3. **Trace review** — claims, tool events, retries, partial actions, rollbacks and missing evidence.
4. **Adversarial cases** — realistic false-success, partial-completion and recovery scenarios.
5. **Independent checks** — practical postconditions that do not rely only on the acting agent's own report.
6. **Findings report** — verified strengths, unsupported claims, failure severity and prioritised repairs.
7. **Implementation plan** — bounded recommendations for evidence capture, recovery and human approval.

## Optional implementation phase

After the audit, implementation can be scoped separately. Possible work includes:

- adding evidence fields and acceptance checks;
- integrating the Agent Completion Verifier;
- adding safe retries and rollback handling;
- separating actor, auditor and final-verdict authority;
- building deterministic regression cases;
- preparing a controlled pilot and release gate.

## Working model

- A short fit review establishes whether the workflow is sufficiently bounded.
- The fixed scope, evidence access, exclusions, delivery format and fixed price are agreed before work begins.
- Sensitive data should be minimised, redacted or replaced with representative fixtures wherever possible.
- Credentials are not requested during ordinary intake and should never be pasted into email, chat or shared documents.
- No production mutation or provider spend is made without separate explicit written approval.
- Findings are evidence-led: uncertain or inaccessible facts are labelled rather than guessed.

## What the audit is not

It is not a penetration test, legal compliance certification, formal safety certification, guarantee of production reliability or claim that every undiscovered defect has been eliminated. Security-critical systems may require a qualified specialist assessment in addition to this work.

## Public proof

The supporting open-source work includes:

- **Agent Completion Verifier** — evaluates completion claims against explicit evidence requirements.
- **Agent Reliability Arena** — compares general and bounded specialist orchestration under the same controlled task, tools and evidence rules.
- reproducible packaging, adversarial fixtures, independent state observation, trace replay and fail-closed verification.

The current published Arena results are deterministic software evidence, not a real-provider performance claim.

## Enquiries

For a role, contract or scoped reliability review, contact Luca Panayiotou with:

- the workflow's purpose;
- the tools or systems it changes;
- what currently counts as “done”;
- one known failure or uncertainty;
- whether representative, redacted evidence is available.

Email: `Lucapanay13@gmail.com`
