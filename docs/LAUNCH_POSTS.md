# Public launch posts

These drafts are prepared for manual posting from Luca Panayiotou's own accounts. No external post is claimed complete until its public URL and date are recorded.

## LinkedIn

I’ve published **Agent Reliability Arena**, an evidence-first engineering project for testing a practical question in agent systems:

**Does separating planning, execution, audit, recovery and synthesis improve verified completion enough to justify the extra calls and complexity?**

The comparison holds the task, tools, sandbox, injected failures, mutation limits and exact completion contract constant. The main change is orchestration.

The system includes:

- deterministic request and experiment planning;
- bounded Strategist, Operator, Auditor, Recovery and Synthesiser roles;
- exact permission checks before mutation;
- independent state observation and completion verification;
- tamper-evident evidence and preserved abort records;
- safe pause and continuation without replaying verified trials;
- disclosure-safe public evidence;
- Python 3.10–3.13 source, wheel and clean-install verification.

In the locked **deterministic fixture**, the General condition reached 2/8 independently verified outcomes and the Specialist condition reached 6/8. The Specialist path removed three false-completion claims, while requiring 36 additional logical role calls.

Those numbers validate the experiment and evidence plumbing. They are not measurements of an external model, and the project keeps that boundary explicit.

Repository: https://github.com/Luca-1304/agent-reliability-arena  
Showcase: https://github.com/Luca-1304/agent-reliability-arena/blob/main/SHOWCASE.md

I’m particularly interested in conversations around AI reliability, agent evaluation, verified tool use, evidence design and safety-focused applied engineering.

Project direction and acceptance standard: Luca Panayiotou. Implementation, testing and documentation were transparently AI-assisted.

## Short-form

Published: **Agent Reliability Arena** — a controlled, evidence-first comparison between one general agent and a same-model specialist workflow.

The public deterministic fixture shows 2/8 vs 6/8 verified outcomes, three false completions removed and +36 logical role calls. It validates the evaluation system, not an external model.

Includes independent state verification, bounded recovery, tamper-evident evidence, safe repeated-run continuation and disclosure-safe public output.

https://github.com/Luca-1304/agent-reliability-arena

## Technical teaser

A tool reports success. The requested state does not exist.

Should the agent still be allowed to claim completion?

Agent Reliability Arena says no: the authoritative result comes from independently observed state checked against an exact contract.

The public trace viewer demonstrates false success, partial writes, rollback, timeouts and path escapes under fixed comparison rules:

https://github.com/Luca-1304/agent-reliability-arena/blob/main/SHOWCASE.md

## Posting rules

- Keep the deterministic-fixture qualification in the same post as the numbers.
- Do not imply external-model testing, customer use, revenue, production deployment or third-party endorsement.
- Record the final public URL and posting date in `showcase/distribution-register.json` after publication.
- Do not paste private evidence, local screenshots containing paths, credentials or provider metadata.
