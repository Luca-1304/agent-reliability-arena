# Agent Evidence Ledger — Retry Budget Amendment

Date: 2026-07-22  
Applies to: the approved design, final adversarial review and implementation plan  
Status: Normative execution constraint

The final plan review found that `remaining_attempts` was bounded in wording but not derived from a declared maximum. This amendment makes the bound executable.

## Contract payload

`contract_declared.payload` must include:

```json
{
  "max_attempts": 2
}
```

Rules:

- `max_attempts` is an integer from 1 through 16;
- the value is part of the hashed contract event;
- one initial attempt is included in the maximum;
- the value cannot change within the ledger.

## Lifecycle state

`LifecycleSnapshot` additionally contains:

```python
max_attempts: int = 0
attempts_used: int = 0
```

Transitions:

- `contract_declared` sets `max_attempts` from its payload;
- every legal `tool_attempted` increments `attempts_used` by one;
- `tool_attempted` is illegal when `attempts_used >= max_attempts` before the increment;
- `recovery_authorized` is legal only when `max_attempts - attempts_used > 0`;
- `recovery_authorized.payload.remaining_attempts` must exactly equal `max_attempts - attempts_used`;
- `recovery_authorized` must reference exactly the current `verification_decided` event;
- a new attempt still requires a new `action_proposed` and `action_authorized` event;
- closure as `aborted` remains legal instead of consuming the remaining allowance.

## Decision consistency

The implementation must additionally reject:

- `UNVERIFIED` when the latest valid observation already proves full contract satisfaction;
- `FAILED` when the latest valid observation matches the full contract and no later contradictory observation exists;
- `PARTIAL` when the observation is not explicitly classified as partial;
- any decision that does not reference the active contract and current attempt, plus the current observation when that status requires one.

## Required tests

Add tests proving:

1. `max_attempts` below 1 or above 16 is rejected;
2. a second attempt is illegal when `max_attempts` is 1;
3. recovery reports the exact derived remaining count;
4. a recovery event referencing an older decision is rejected;
5. a fresh proposal and authorisation are required after recovery;
6. `UNVERIFIED` and `FAILED` cannot contradict a matching observation;
7. choosing `aborted` closes a recoverable decision without consuming another attempt.

This amendment takes precedence over less specific retry wording in the earlier documents.