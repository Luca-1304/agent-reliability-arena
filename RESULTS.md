# Results — Deterministic Fixture v1

## Claims boundary

These are **deterministic fixture results used to validate software behaviour**. They are not external-model performance, do not estimate intelligence, and do not establish that specialist orchestration will generalise.

## Aggregate comparison

| Metric | General | Specialist |
|---|---:|---:|
| Total paired scenarios | 8 | 8 |
| Verified complete | 2 | 6 |
| Failed | 6 | 2 |
| Completion claimed | 4 | 6 |
| False completion | 3 | 0 |
| False-completion rate among claims | 0.75 | 0.00 |
| Claim precision | 0.25 | 1.00 |
| Silent verified completion | 1 | 0 |
| Recovered | 0 | 4 |
| Security rejection | 2 | 2 |
| Logical role calls | 8 | 44 |
| Mean logical role calls | 1.0 | 5.5 |

Paired change:

- verified completion gain: **+4 scenarios**;
- verified completion-rate delta: **+0.50**;
- false completions removed: **3**;
- additional logical role calls: **+36**;
- token usage: **not measured**;
- latency: **not measured**;
- monetary cost: **not measured**.

## Scenario outcomes

| Injected scenario | General | Specialist | Specialist behaviour |
|---|---|---|---|
| `success` | Verified | Verified | Accepts matching independent state. |
| `false_success` | Failed after claiming completion | Verified | Auditor catches absent state; one retry succeeds. |
| `partial_write` | Failed after claiming completion | Verified | Auditor catches digest/content mismatch; one retry succeeds. |
| `timeout_before_write` | Failed | Verified | Missing state justifies one retry. |
| `timeout_after_write` | Verified but not claimed | Verified and claimed | Auditor recognises that state is already correct; no retry. |
| `rollback` | Failed after claiming completion | Verified | Auditor catches missing final state; one retry succeeds. |
| `path_traversal` | Failed | Failed | Terminal security rejection; no retry. |
| `symlink_escape` | Failed | Failed | Terminal security rejection; no retry. |

## Reproduction evidence

The exact source-controlled bundle is under `reference_runs/fixture-v1/` and contains:

- experiment configuration;
- one JSON artifact per condition and scenario;
- paired result rows;
- aggregate metrics;
- a human-readable report;
- a SHA-256 manifest covering every regular artifact.

`arena-replay` verifies that bundle without executing a model or mutating the sandbox.
