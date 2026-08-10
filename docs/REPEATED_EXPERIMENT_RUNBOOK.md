# Repeated paired experiment runbook

This runbook describes the preregistered repeated paired-experiment boundary in Agent Reliability Arena v0.2.0rc1.

The implemented release path is provider-neutral and has been rehearsed with scripted responses only. It does not authorise a real provider call, does not contain credentials and does not establish model performance.

## Purpose

A repeated experiment prevents a single favourable or unfavourable pilot from becoming the entire conclusion. Before any trial starts, it fixes:

- the complete ordered trial list;
- scenario ID for every trial;
- a unique seed for every trial;
- whether General or Specialist runs first;
- provider, exact model version and prompt version;
- configuration, contract, catalogue and policy-template digests;
- per-trial and aggregate call, token and monetary reservations;
- the stop-on-abort rule.

The complete plan and preflight are SHA-256 committed before trial evidence is written.

## Provider-free planning

Planning uses:

- `TrialPlan`;
- `RepeatedExperimentPlan`;
- `build_counterbalanced_plan`;
- `build_repeated_experiment_preflight`.

The schedule is deterministic. Trials are produced in round-robin scenario order, and the first condition alternates within each scenario. An odd number of repetitions is allowed, but the General-first versus Specialist-first imbalance may never exceed one.

Every planned seed is unique. The same seed is then shared by both conditions inside that trial.

Planning performs no provider request and needs no API key.

## Private artifact layout

A new experiment root contains:

```text
experiment-root/
├── experiment-plan.json
├── experiment-preflight.json
├── experiment-start.json
├── experiment-evidence-witness.jsonl
├── experiment-checkpoint.json
├── trial-0001/
│   ├── preflight.json
│   ├── policy.json
│   ├── run-start.json
│   ├── general/
│   ├── specialist/
│   ├── transport-calls.jsonl
│   └── verification-summary.json  or abort.json
├── trial-0002/
│   └── ...
└── experiment-summary.json        or experiment-abort.json
```

Plan, preflight, start, final summary and abort records are immutable create-once files. The evidence witness is append-only and hash-chained: one root-level record is durably appended for each independently verified completed trial. The checkpoint remains the only replaceable root artifact and is atomically replaced only after the corresponding witness record has been written and reverified.

Private directories and evidence files use restrictive permissions where the operating system supports them.

## Trial execution

Each trial derives:

1. a configuration with the preregistered seed;
2. a one-scenario `PilotPolicy` from the reviewed template;
3. the exact existing pilot preflight;
4. the planned condition order;
5. a fresh private paired-pilot directory.

The existing private paired runner then executes General and Specialist in the scheduled order while keeping the condition directories named `general` and `specialist`.

A trial is not counted as completed merely because the function returns. Before the experiment checkpoint advances, the repeated runner verifies:

- the persisted final summary;
- scenario and condition order;
- provider, model and prompt identifiers;
- trial configuration and policy digests;
- pilot preflight digest;
- contract and prompt-catalogue digests;
- both condition result shapes;
- the complete transport ledger and its recorded summary;
- `comparative_claim_permitted: false`.

After that independent trial verification succeeds, the runner appends a root-level witness record containing the exact trial ID, plan/preflight commitments, verified ledger schema and record count, whole-ledger SHA-256 and raw verification-summary SHA-256. The witness record itself is chained to the preceding witness digest. The complete witnessed prefix is reverified before the ordinary replaceable checkpoint may advance.

## Evidence continuity witness

`experiment-evidence-witness.jsonl` exists to protect the interval between completed trials and later final evidence indexing.

Transport ledger schema 2 already links records *inside* a ledger, while the disclosure-safe private evidence-set index commits finalized evidence sets. The witness has a different job: it makes the sequence of already accepted trials monotonic during a repeated experiment.

For witness sequence 1, `previous_witness_digest` is `null`. Every later witness record points to the immediately preceding `witness_digest`. Each digest covers the entire unsigned witness record through canonical JSON SHA-256.

On continuation, the witness must exactly equal the independently reverified completed-trial prefix:

- same number of records;
- same ordered trial IDs;
- same plan and preflight digests;
- same witness sequence and predecessor links;
- same ledger schema, record count and whole-ledger SHA-256;
- same raw verification-summary SHA-256;
- same recomputed witness digests.

A completed trial with no matching witness, a shorter witness, a witness ahead of trial evidence, or any witness/evidence mismatch fails closed before another provider-shaped call starts. The runner does not silently backfill unwitnessed completed history.

This is a **local continuity control**, not an external notarization system. It detects later truncation or consistent rewriting of already-witnessed trial evidence while the witness remains trustworthy. An actor able to rewrite both the complete local evidence history and the complete witness history can still construct a different internally consistent local history. Defeating that stronger threat requires an independently controlled external anchor, signature/transparency service, hardware-backed monotonic counter or equivalent separately reviewed mechanism.

## Detached continuity receipt

A detached receipt lets an operator preserve a compact checkpoint of a verified witness prefix **outside** the experiment root without adding network or Git authority.

Create a receipt only after the relevant completed trial evidence has verified and the root witness contains the checkpoint you want to retain:

```bash
python -m agent_reliability_arena.repeated_receipt create \
  --experiment-root /private/experiment-root \
  --receipt /separate/receipts/checkpoint-0001.json
```

Verify that retained receipt later with:

```bash
python -m agent_reliability_arena.repeated_receipt verify \
  --experiment-root /private/experiment-root \
  --receipt /separate/receipts/checkpoint-0001.json
```

The receipt is deterministic and create-once. It stores only:

- plan and preflight digests;
- number of witness records covered;
- exact byte length and SHA-256 of the covered witness prefix;
- witness-head digest at that checkpoint;
- final trial ID covered by the receipt;
- canonical receipt digest.

It stores no path, prompt, model output, provider payload, credential, operator note, billing value or timestamp.

The receipt commits an exact **prefix**, not only the whole current witness file. This means a receipt created after trial 1 remains valid after trials 2–N are appended, as long as every byte in the original trial-1 witness prefix is unchanged. Verification also revalidates the complete current witness against its referenced trial ledgers and verification summaries before accepting the detached checkpoint.

Receipt creation refuses an existing output and requires the resolved destination parent to be outside the experiment root. Receipt verification applies the same detached-path rule. The software does not create external storage and does not claim that another directory on the same machine is an independent trust domain; the operator must retain at least one copy somewhere outside the failure/adversary domain that could rewrite the experiment root for the receipt to strengthen that threat boundary.

A retained old receipt can therefore detect a wholesale replacement of the local witness/evidence history when the replacement changes the committed prefix. If an actor can rewrite both the complete experiment root **and every retained detached receipt**, this mechanism does not provide external notarization. A stronger stage would require separately controlled signatures, timestamping, transparency infrastructure, hardware-backed monotonic state or another independently governed anchor.

## Authenticated detached receipt

A detached receipt may additionally be protected with a create-once HMAC-SHA256 authentication envelope. This adds a separate secret-dependent boundary without changing the receipt itself.

The authentication key must be a uniformly random 32-byte value retained outside the experiment-root failure/adversary domain. The command-line interface reads it only from `ARENA_RECEIPT_AUTH_KEY_HEX`, encoded as exactly 64 hexadecimal characters. Do not commit this value, put it in a receipt/auth file, pass it as a CLI argument, or store it inside the experiment root.

Create the authentication envelope after the detached receipt verifies:

```bash
export ARENA_RECEIPT_AUTH_KEY_HEX='<64-hex-character secret>'
python -m agent_reliability_arena.repeated_receipt_auth create \
  --experiment-root /private/experiment-root \
  --receipt /separate/receipts/checkpoint-0001.json \
  --auth /separate/auth/checkpoint-0001.auth.json
```

Verify it later with the same independently retained secret:

```bash
export ARENA_RECEIPT_AUTH_KEY_HEX='<same 64-hex-character secret>'
python -m agent_reliability_arena.repeated_receipt_auth verify \
  --experiment-root /private/experiment-root \
  --receipt /separate/receipts/checkpoint-0001.json \
  --auth /separate/auth/checkpoint-0001.auth.json
```

The envelope stores only the fixed schema/algorithm, the receipt digest, a domain-separated non-secret key identifier and a domain-separated HMAC tag. It stores no secret key or experiment content. The auth output must resolve outside the experiment root, is create-once, rejects symlinks, and verification rejects an envelope with multiple hard links because another writable pathname would weaken the detached boundary.

Authentication first runs the ordinary detached-receipt verifier. A correct HMAC therefore cannot make a broken witness, ledger or receipt pass. If the experiment root and detached receipt are both replaced, a valid replacement authentication envelope still cannot be produced without the independently retained key.

This is **shared-secret authentication, not a digital signature**. Anyone who obtains the HMAC key can create valid envelopes. It provides no trusted timestamp, transparency-log inclusion, public third-party verification or protection after key compromise. A later asymmetric-signature or external-transparency stage would require its own dependency, key-lifecycle and trust review.

## Safe pause and continuation

The provider-free API supports a deliberate `max_new_trials` limit. This allows an operator to run a bounded number of new trials and stop only after the last new trial has independently verified and been witnessed.

Continuation is permitted only when all existing trial directories form a contiguous prefix of the preregistered schedule, every one is a verified completed trial, and the root witness exactly commits that same prefix.

On continuation:

- completed trials are re-verified;
- the witness chain and every completed-trial commitment are reverified before checkpoint replacement;
- completed trial calls are not reconstructed or replayed;
- the next preregistered trial begins;
- the same exact plan, preflight and start records must match.

The checkpoint remains useful as an atomic progress convenience, but it is not the stronger history commitment: the append-only witness must agree first. Detached receipts and their optional authentication envelopes are operator-retained checkpoints and are not required for ordinary provider-free runner continuation.

## Terminal conditions

The same experiment root must not continue after any of the following:

- `experiment-abort.json` exists;
- any trial contains `abort.json`;
- any trial directory is partial;
- trial directories are non-contiguous;
- an unexpected file or directory appears in the experiment root;
- plan, preflight, start or checkpoint digests drift;
- a completed trial ledger or final summary no longer verifies;
- the witness is missing, shorter, ahead, malformed, reordered, broken, or disagrees with the completed prefix;
- a provider request falls outside that trial's preflight;
- parser, contract, sandbox or verifier evidence becomes inconsistent.

A terminal root remains evidence. To try again, create a new reviewed plan and a new private root. Reusing the old root could conceal duplicate provider calls and is therefore prohibited.

A process crash in the narrow interval after a trial has persisted completed evidence but before its witness append completes is intentionally not auto-repaired. That root is treated as incomplete evidence instead of silently accepting unwitnessed history.

## Descriptive analysis

`analyse_repeated_experiment` re-verifies completed trial evidence and then reports:

- planned, completed and aborted trial counts;
- General and Specialist verified-completion counts;
- both-complete, neither-complete, Specialist-only and General-only pairs;
- absolute completion proportions;
- Specialist-minus-General paired completion difference;
- Wilson 95% condition intervals;
- a labelled paired normal-approximation 95% interval;
- an exact two-sided binomial sign-test p-value over discordant pairs;
- measured calls, tokens, wall-clock latency and provider-processing time when recorded.

The output names every statistical method and includes limitations. A p-value or interval applies only to the recorded sample. It does not establish causality, representativeness, universal superiority, practical value or production safety.

Monetary cost is not inferred from tokens. Any cost calculation requires separately dated price-source metadata and remains distinct from provider billing.

## Provider-free release reproduction

`scripts/verify_repeated_release.py` proves the mechanism without credentials or network access. It:

1. preregisters four success-scenario trials with two General-first and two Specialist-first orders;
2. runs one trial and pauses after its verified, witnessed evidence;
3. resumes with a fresh scripted transport and proves the first trial is not replayed;
4. completes all four trials, producing a four-record witness chain and 20 verified ledger records;
5. reconstructs 400 measured total tokens and 20 ms of scripted latency;
6. creates a separate invalid-output experiment;
7. preserves its trial and experiment abort records;
8. proves continuation of that aborted root is refused.

Dedicated witness regression tests prove retained-witness rejection of a valid-looking ledger suffix truncation even when the trial's ledger summary is rewritten to match the shorter still-valid ledger. Detached-receipt tests additionally prove that an older separately retained prefix receipt remains valid after later witness appends but rejects a rewritten committed prefix or a different locally valid replacement history. Authentication-envelope tests prove that replacing the root and receipt still cannot produce a valid replacement HMAC envelope without the independently retained 256-bit key.

The release reproduction explicitly reports `provider_called: false` and `comparative_claim_permitted: false`.

## Real-provider boundary

A real repeated experiment remains blocked behind the same operator requirements as the first pilot:

- exact dated provider model snapshot;
- enabled private policy reviewed by digest;
- explicit external-execution approval;
- environment-only credential handling;
- exact worst-case call, token and monetary ceilings;
- private storage with no public raw ledger;
- immediate stop on any evidence inconsistency.

No standard test, release verifier or installed public command makes a real provider call.

## Claims boundary

The repeated runner, witness, optional detached receipts and optional HMAC authentication envelopes, resume rules and analysis methods can be validated using provider-free scripted evidence. That proves experiment infrastructure, not hosted-model performance. The local witness strengthens continuity while retained; a detached receipt can additionally detect replacement of the prefix it committed; HMAC authentication can additionally reject replacement of the receipt when the independently retained secret remains uncompromised. None of these mechanisms is a public-key signature, trusted timestamp or external notarization. Real comparative claims remain prohibited until a preregistered real dataset is complete, independently verified, disclosure-safe and interpreted with its limitations intact.
