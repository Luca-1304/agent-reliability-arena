# 90-second demonstration script

## 0–12 seconds — The question

“Agent Reliability Arena holds the model label, task, tools and evidence rules constant. It changes only the orchestration: one general agent versus five bounded specialist roles.”

## 12–28 seconds — The failure

Select `false success` in the trace viewer.

“The tool-shaped source returns a success receipt, but no file exists. The general condition accepts the receipt and claims completion.”

Point to the red `Not verified` status and the independent observation.

## 28–48 seconds — The audit

“The specialist condition separates execution from approval. Its Auditor compares the source report with actual sandbox state and detects the conflict.”

Point to `reported_success_without_matching_state` and the evidence trust basis.

## 48–65 seconds — Bounded recovery

“The Recovery role is allowed one exact retry because this is a recoverable mismatch, not a security failure. The Operator writes the contracted content, and the observer verifies path, size, digest and bytes.”

## 65–78 seconds — Honest outcome

“The specialist condition reaches a verified completion in this scenario. The same system refuses to retry path traversal and symlink escape.”

## 78–90 seconds — Trade-off and evidence status

“Across the eight deterministic fixtures, verified outcomes move from 2/8 to 6/8 and false completions from three to zero—but logical role calls rise from 8 to 44. One trace is illustrative; the aggregate fixture report and replayable artifacts carry the complete evidence. These are software-validation fixtures, not model performance results.”
