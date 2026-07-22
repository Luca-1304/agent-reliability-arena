# 90-second showcase demo

## Script

**0–12 seconds — Set the question**

“Agent Reliability Arena compares one general agent with one role-specialised system. The model label, task, tool boundary, seed and completion contract stay fixed. Only the orchestration changes.”

**12–28 seconds — Show the core failure**

“Here is the false-success scenario. The source reports success, but the independently observed state does not match the contract. The general condition still claims completion, so the verifier rejects it.”

**28–46 seconds — Show bounded recovery**

“The specialist path separates planning, operation and audit. The Auditor detects the conflict, Recovery permits one exact retry, and the Synthesiser can report completion only after the verifier confirms the required state.”

**46–62 seconds — Show the trade-off**

“In the deterministic eight-scenario fixture, verified outcomes move from two to six and three unsupported completion claims disappear. The specialist system also uses thirty-six additional logical calls, so the overhead remains visible beside the gain.”

**62–78 seconds — Show the engineering depth**

“Behind the viewer are strict output schemas, exact action contracts, tamper-evident transport records, guarded external-execution boundaries, preregistered repeated trials, safe continuation rules and disclosure-safe public export.”

**78–90 seconds — State the boundary**

“This is software-validation and provider-free integration evidence, not a hosted-model leaderboard. No real-provider benchmark request or provider spend has been executed. The public package is digest-pinned and machine checked before publication.”

## On-screen route

1. Hero statement: “Same model. Same tools. Same evidence rules. Different orchestration.”
2. Fixture-results cards.
3. Select `false_success` in the paired trace explorer.
4. Point to the source report, independent observation and final verifier status.
5. Scroll to “What this proves.”
6. Show the architecture and verified-build sections.
7. Finish on the claims boundary and authorship section.

## Claims to avoid

Do not describe the deterministic fixture as a real-model benchmark. Do not say the specialist path always wins. Do not imply measured billing, unrestricted-tool safety or unattended deployment. Do not hide the extra calls, failures, limitations or provider-free evidence classification.
