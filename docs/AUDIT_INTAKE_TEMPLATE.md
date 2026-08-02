# AI Agent Reliability Audit — Intake Template

Use this template before accepting or pricing an audit. Do not request credentials, unrestricted production access or unnecessary personal data during intake.

## 1. Workflow identity

- Organisation or project:
- Primary contact and role:
- Workflow name:
- Current environment: prototype / staging / production / other
- Main owner of the workflow:

## 2. Intended outcome

Describe the one outcome the workflow is supposed to complete.

- Requested outcome:
- External system or state that must change:
- Who or what depends on that outcome:
- Consequence if the workflow falsely reports success:

## 3. Tools and authority

List only the systems relevant to this workflow.

| Tool or system | Action performed | Permission level | Human approval required? |
|---|---|---|---|
| | | | |

## 4. Current definition of “done”

- What does the agent currently treat as success?
- What observable evidence exists after a genuine success?
- Is that evidence checked independently of the acting agent?
- Can a later retry, rollback or downstream failure invalidate an earlier success?

## 5. Known uncertainty or failure

Describe at least one real or suspected failure mode.

- What happened or could happen?
- What did the agent report?
- What state actually existed?
- Was recovery attempted?
- Was the evidence retained?

## 6. Available evidence

Select what can be shared safely:

- [ ] Redacted traces
- [ ] Tool-call logs
- [ ] Screenshots
- [ ] Test fixtures
- [ ] Staging access with bounded permissions
- [ ] Source excerpts
- [ ] Existing acceptance criteria
- [ ] Other:

Never include API keys, passwords, session cookies, authentication headers, complete environment dumps or unrelated customer data.

## 7. Constraints

- Systems that must not be changed:
- Data that must not be accessed or retained:
- Maximum provider/tool spend:
- Required review or approval points:
- Deadline or decision date:
- Regulatory, contractual or internal-policy constraints disclosed by the client:

## 8. Requested deliverable

- [ ] Findings report only
- [ ] Findings plus implementation plan
- [ ] Findings plus bounded implementation quote
- [ ] Controlled regression test pack
- [ ] Other:

## 9. Initial suitability decision

Complete after review:

- Bounded enough for audit: yes / no / needs clarification
- Evidence sufficient: yes / no / representative fixture required
- Sensitive-access risk acceptable: yes / no
- Fixed scope possible: yes / no
- Recommended next step:

## Boundary

Submitting intake information does not authorise production changes, provider spending or access beyond the agreed evidence. Scope, exclusions, delivery format, retention and price must be agreed in writing before work begins.
