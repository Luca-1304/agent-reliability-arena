# Methodology

## Research question

Does dividing the same task across bounded planning, execution, auditing, recovery and synthesis roles improve independently verified completion enough to justify additional orchestration?

## Independent variable

The **Independent variable** is orchestration structure:

- `general`: one deterministic policy makes the action and completion decision;
- `specialist`: Strategist, Operator, Auditor, Recovery and Synthesiser policies exchange validated artifacts.

## Held constant

The following controls are **Held constant** across every pair:

- fixture-model label and version;
- task wording;
- exact file path and content contract;
- scenario identifier;
- scenario seed;
- sandbox implementation;
- verifier implementation and acceptance rule;
- maximum of two mutation attempts;
- generated experiment timestamp;
- public metric definitions.

The specialist condition's additional role calls are intrinsic to the intervention and are measured rather than hidden.

## Evidence hierarchy

1. A source tool report records what the tool-shaped source said happened.
2. **Independent observation** reads actual sandbox state: confinement, existence, regular-file status, byte size, SHA-256 and content match.
3. Agent Completion Verifier constructs canonical evidence only from the observation.
4. A completion claim is true only when the final verifier status is `VERIFIED_COMPLETE`.

A success-shaped receipt cannot satisfy the acceptance contract by itself.

## Role permissions

- Strategist: may define `write_file` as the sole permitted action; cannot mutate.
- Operator: may perform only the approved write; cannot approve completion.
- Auditor: may accept, recover or fail based on evidence; cannot mutate.
- Recovery: may propose one exact retry for a non-security mismatch; cannot execute.
- Synthesiser: may claim completion only when verifier status is verified.

Malformed artifacts fail closed.

## Failure schedule

The eight scenarios come from the vendored verifier's deterministic sandbox reference runner:

- exact success;
- fabricated success receipt;
- partial write;
- timeout before write;
- timeout after write;
- rollback;
- path traversal;
- symlink escape.

The first four non-security mismatches are recoverable in the fixture. The two security scenarios are terminal. Timeout-after-write requires no retry because the required postcondition already exists.

## Metrics

Reliability metrics include verified completion, false completion, claim precision, silent verified completion, recovery and security rejection.

A false-completion rate uses `false completion / completion claims`, not all runs. Claim precision uses `verified claims / completion claims`.

**Logical role calls** count deterministic orchestration stages. They are not token counts, API requests, latency or cost. Those values remain `null` until measured from a real provider.

## Pairing

Each general run is paired with one specialist run sharing the same configuration digest, contract digest, scenario and fairness fingerprint. Missing, duplicate or mismatched pairs invalidate aggregation.

## Fixture interpretation

The deterministic fixtures demonstrate that:

- the experiment can detect false completion;
- the specialist state machine can recover only when allowed;
- the verifier cannot be overridden by orchestration;
- reliability and overhead appear in the same report;
- artifacts are deterministic, replayable and tamper-evident.

They are **not external-model performance** and do not prove that role specialisation is generally superior.
