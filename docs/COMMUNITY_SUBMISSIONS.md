# Technical-community submission copy

These drafts are prepared for selective use in developer, AI evaluation and reliability-focused communities. They are not a real-model leaderboard announcement.

## Technical submission

**Title:** Agent Reliability Arena: independent state verification for controlled agent-orchestration experiments

I’ve published Agent Reliability Arena, a Python project that compares one general agent with a same-model specialist workflow while holding the task, tools, sandbox, injected failures, mutation limit and exact completion contract constant.

The main design choice is that an agent or tool report is treated as a source claim—not authoritative proof. Completion is determined from independently observed state checked against the configured contract.

The Specialist condition separates:

- Strategist: defines the bounded plan;
- Operator: proposes and performs permitted mutation;
- Auditor: compares source claims with observed state;
- Recovery: permits one evidence-backed retry where justified;
- Synthesiser: reports only the verifier-authorised outcome.

The repository also includes deterministic call plans, strict JSON role contracts, tamper-evident transport ledgers, hard pre-call reservations, safe pause/continuation for repeated experiments, preserved abort evidence and disclosure-safe export.

The public eight-scenario deterministic fixture produced 2/8 verified outcomes in the General condition and 6/8 in the Specialist condition, with three false-completion claims removed and 36 additional logical role calls. These values validate the software experiment and measurement path; they do not describe an external model.

Repository: https://github.com/Luca-1304/agent-reliability-arena  
Showcase: https://github.com/Luca-1304/agent-reliability-arena/blob/main/SHOWCASE.md

Technical criticism is welcome, especially around experimental controls, recovery semantics, evidence authority, statistical framing and what should be required before any real-provider comparison.

## Discussion prompt

When an agent says a task is complete but independent observation disagrees, which record should be authoritative—and how should recovery be bounded so it improves reliability without hiding cost or introducing uncontrolled retries?

Agent Reliability Arena explores that question with a deterministic fixture, explicit role boundaries and independently verified completion evidence:

https://github.com/Luca-1304/agent-reliability-arena

## Maintainer note

Project framing and acceptance standard: Luca Panayiotou. Implementation, testing and documentation were transparently AI-assisted. The repository includes explicit limitations and reproducible provider-free verification.

## Submission rules

- Choose communities where technical discussion is expected; do not mass-post identical copy.
- Read and follow each community's self-promotion and disclosure rules before submission.
- Prefer the technical submission for engineering forums and the discussion prompt for question-led communities.
- Record a public URL and date only after a submission is actually visible.
- Do not represent fixture results as evidence about a commercial or open model.
