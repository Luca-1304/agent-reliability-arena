# AI Agent Reliability Audit — Report Template

## Document control

- Client/workflow:
- Audit version:
- Evidence cut-off:
- Auditor:
- Client reviewer:
- Scope approved on:
- Delivery date:

## Executive finding

State the most important conclusion in plain language. Separate confirmed findings from unverified concerns.

- Overall completion-evidence confidence: high / moderate / low / insufficient evidence
- Highest-severity confirmed issue:
- Immediate action recommended:
- Production change performed during audit: none / separately authorised and recorded

## 1. Scope and exclusions

### Included

- One bounded workflow:
- Systems reviewed:
- Evidence supplied:
- Scenarios exercised:

### Excluded

- Systems not accessed:
- Security/compliance work outside scope:
- Production actions not authorised:
- Evidence that could not be obtained:

## 2. Intended outcome and authority map

Describe the required external state, acting components, human approvals and final-verdict authority.

| Component | May plan | May mutate | May verify | May approve completion |
|---|---:|---:|---:|---:|
| | | | | |

## 3. Completion contract

| Requirement | Observable evidence | Source | Invalidation condition | Required? |
|---|---|---|---|---:|
| | | | | |

Canonical outcomes:

- **VERIFIED_COMPLETE** — every required postcondition is independently supported and remains valid.
- **PARTIAL** — some required state exists, but completion is incomplete or later invalidated.
- **UNVERIFIED** — the claim may be true, but the required evidence is absent or inaccessible.
- **FAILED** — authoritative evidence shows the required outcome was not achieved.

## 4. Evidence inventory

| Evidence item | Time range | Integrity/limitations | Retained? |
|---|---|---|---:|
| | | | |

Do not include credentials, authentication headers or unnecessary personal/customer data.

## 5. Scenario results

| Scenario | Agent claim | Observed state | Canonical verdict | Recovery | Notes |
|---|---|---|---|---|---|
| | | | | | |

## 6. Findings

Use one entry per finding.

### Finding AR-001 — Title

- Severity: critical / high / medium / low / observation
- Confidence: confirmed / strong / tentative
- Affected stage:
- Evidence:
- Expected state:
- Observed state:
- Consequence:
- Reproduction:
- Recommended repair:
- Verification required after repair:

Severity guidance:

- **Critical** — false completion can directly create severe legal, financial, safety or irreversible operational harm.
- **High** — likely material harm, widespread incorrect state or loss of control without timely detection.
- **Medium** — meaningful reliability failure with bounded impact or practical detection/recovery.
- **Low** — limited impact, clarity gap or defence-in-depth weakness.
- **Observation** — improvement opportunity without a demonstrated failure.

## 7. Strengths retained

Record controls that worked so repairs do not remove useful behaviour.

- 

## 8. Prioritised repair plan

| Priority | Repair | Owner | Dependency | Acceptance evidence |
|---:|---|---|---|---|
| 1 | | | | |

## 9. Regression gate

Define the minimum repeatable checks required before release.

- Deterministic cases:
- Failure injection:
- Independent postcondition checks:
- Retry/rollback checks:
- Human approval checks:
- Provider/tool spend ceiling:
- Stop conditions:

## 10. Claims boundary

This report evaluates the evidence and workflow within the agreed scope and evidence window. It is not a penetration test, legal compliance certification, formal safety certification, universal production-readiness guarantee or proof that no undiscovered defect exists.

## Client acknowledgement

- Findings received:
- Disputed facts or missing evidence:
- Approved public testimonial/case-study language, if any:
- Permission to publish: none / anonymised / named and separately approved
