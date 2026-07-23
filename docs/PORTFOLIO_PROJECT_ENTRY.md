# Portfolio project entry

## Project

**Agent Reliability Arena**  
Evidence-first evaluation and release system for comparing general and role-specialised agent orchestration.

## Problem

Agent systems can report success even when the requested state was not created, was only partially created, escaped the permitted scope or became invalid after a timeout or rollback. Many demonstrations also change several variables at once, making it difficult to identify whether orchestration itself helped.

Agent Reliability Arena isolates the orchestration difference while keeping the task, tools, sandbox, failure schedule, mutation limits and exact completion contract constant.

## Engineering contribution

Luca Panayiotou defined the project direction and acceptance standard: completion must be grounded in independently observed state, not an agent statement or success-shaped tool receipt.

The implementation provides:

- a General condition and a bounded Specialist condition;
- Strategist, Operator, Auditor, Recovery and Synthesiser role contracts;
- exact path/content permission checks before mutation;
- independent post-action observation and completion verification;
- one evidence-backed recovery attempt with terminal security rejection;
- provider-neutral model transport and strict output parsing;
- deterministic request plans and hard execution reservations;
- tamper-evident private ledgers and preserved abort records;
- safe repeated-experiment pause and continuation without replay;
- disclosure-safe export and public replay;
- source, wheel and clean-install release verification across Python 3.10–3.13.

## Public demonstration

The public trace viewer exposes failure scenarios such as false success, partial writes, rollback, timeouts and path escapes. Reviewers can follow the source claim, independent observation, audit decision, recovery decision and final verifier status.

The locked deterministic fixture reports:

| Measure | General | Specialist |
|---|---:|---:|
| Independently verified outcomes | 2/8 | 6/8 |
| False completion claims | 3 | 0 |
| Logical role calls | 8 | 44 |

The comparison therefore shows four additional verified fixture outcomes and three removed false completions at the cost of 36 additional logical calls.

## Evidence boundary

These are controlled software-fixture results. They demonstrate that the experiment, failure handling, measurement and verification paths behave as designed. They do not measure a commercial model, an open model, a production deployment or real operating cost.

## Review links

- Repository: `github.com/Luca-1304/agent-reliability-arena`
- Showcase route: `SHOWCASE.md`
- Launch package: `LAUNCH.md`
- Public verifier: `arena-verify-showcase`
- Launch verifier: `arena-verify-launch-package`

## Authorship

Project framing, acceptance standard and publication approval: **Luca Panayiotou**.  
Implementation, testing and documentation: transparently AI-assisted under Luca's review direction and evidence requirements.
