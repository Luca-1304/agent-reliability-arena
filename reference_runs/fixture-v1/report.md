# Agent Reliability Arena — Deterministic Fixture Results

**Evidence status:** deterministic fixture; these are software-validation results, not external-model performance.

## Controlled comparison

- Experiment: `fixture-v1`
- Fixture model label: `fixture-model-v1` version `1`
- Scenarios: 8
- Same contract digest: `217bbae310eb748bd647a14523aada67497d6dda3cdf407da8d02ad2bc795b67`
- Maximum mutation attempts: 2

## Results

| Metric | General | Specialist |
|---|---:|---:|
| Verified completion | 2/8 | 6/8 |
| False completion | 3 | 0 |
| Claim precision | 0.25 | 1.00 |
| Recovered scenarios | 0 | 4 |
| Logical role calls | 8 | 44 |

The specialist fixture improves 4 paired outcomes and removes 3 false-completion cases, while using 36 additional logical role calls.

## Claims boundary

No token, latency, price, or external-model score is fabricated. Real-model conclusions require fixed model versions, repeated paired runs, measured usage, and uncertainty analysis.
