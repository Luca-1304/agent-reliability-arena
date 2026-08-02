# AI Agent Reliability Audit — Remediation Acceptance

Use this after repairs. A change is not accepted because it sounds correct; it must satisfy observable evidence.

## Change under review

- Finding ID:
- Repair owner:
- Code/configuration version:
- Environment:
- Reviewer:
- Review date:

## Required postconditions

| Postcondition | Independent evidence | Result | Notes |
|---|---|---|---|
| | | pass / fail / unverified | |

## Regression scenarios

- [ ] Genuine success
- [ ] False-success claim with missing state
- [ ] Partial external state
- [ ] Timeout before mutation
- [ ] Timeout after mutation
- [ ] Retry without duplicate action
- [ ] Rollback or later invalidation
- [ ] Evidence-store failure
- [ ] Human-approval refusal
- [ ] Permission or path violation

Mark non-applicable cases and explain why.

## Evidence integrity

- [ ] Raw evidence was retained before interpretation.
- [ ] The acting agent did not approve its own completion.
- [ ] Required timestamps/order are available.
- [ ] Secrets and unrelated private data are absent.
- [ ] Provider/tool usage remained within the approved ceiling.

## Decision

- [ ] Accepted — every required postcondition passes.
- [ ] Partially accepted — bounded improvement, remaining requirements listed.
- [ ] Rejected — authoritative evidence contradicts completion.
- [ ] Unverified — evidence is missing or inaccessible.

Remaining work:

Claims boundary: acceptance applies only to the reviewed version, environment, workflow boundary and scenarios. It does not establish universal production reliability.
