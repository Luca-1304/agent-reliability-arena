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

Plan, preflight, start, final summary and abort records are immutable create-once files. The checkpoint is the only replaceable root artifact and is atomically replaced after a trial has completed and independently verified.

Private directories and JSON evidence use restrictive permissions where the operating system supports them.

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

## Safe pause and continuation

The provider-free API supports a deliberate `max_new_trials` limit. This allows an operator to run a bounded number of new trials and stop only after the last new trial has independently verified.

Continuation is permitted only when all existing trial directories form a contiguous prefix of the preregistered schedule and every one is a verified completed trial.

On continuation:

- completed trials are re-verified;
- completed trial calls are not reconstructed or replayed;
- the next preregistered trial begins;
- the same exact plan, preflight and start records must match.

## Terminal conditions

The same experiment root must not continue after any of the following:

- `experiment-abort.json` exists;
- any trial contains `abort.json`;
- any trial directory is partial;
- trial directories are non-contiguous;
- an unexpected file or directory appears in the experiment root;
- plan, preflight, start or checkpoint digests drift;
- a completed trial ledger or final summary no longer verifies;
- a provider request falls outside that trial's preflight;
- parser, contract, sandbox or verifier evidence becomes inconsistent.

A terminal root remains evidence. To try again, create a new reviewed plan and a new private root. Reusing the old root could conceal duplicate provider calls and is therefore prohibited.

## Descriptive analysis

`analyse_repeated_experiment` re-verifies completed trial evidence and then reports:

- planned, completed and aborted trial counts;
- General and Specialist verified-completion counts;
- both-complete, neither-complete, Specialist-only and General-only pairs;
- absolute completion proportions;
- Specialist-minus-General paired completion difference;
- Wilson 95% intervals for each condition proportion;
- a labelled paired normal-approximation 95% interval;
- an exact two-sided binomial sign-test p-value over discordant pairs;
- measured calls, tokens, wall-clock latency and provider-processing time when recorded.

The output names every statistical method and includes limitations. A p-value or interval applies only to the recorded sample. It does not establish causality, representativeness, universal superiority, practical value or production safety.

Monetary cost is not inferred from tokens. Any cost calculation requires separately dated price-source metadata and remains distinct from provider billing.

## Provider-free release reproduction

`scripts/verify_repeated_release.py` proves the mechanism without credentials or network access. It:

1. preregisters four success-scenario trials with two General-first and two Specialist-first orders;
2. runs one trial and pauses after its verified evidence;
3. resumes with a fresh scripted transport and proves the first trial is not replayed;
4. completes all four trials and verifies 20 ledger records;
5. reconstructs 400 measured total tokens and 20 ms of scripted latency;
6. creates a separate invalid-output experiment;
7. preserves its trial and experiment abort records;
8. proves continuation of that aborted root is refused.

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

The repeated runner, resume rules and analysis methods can be validated using provider-free scripted evidence. That proves experiment infrastructure, not hosted-model performance. Real comparative claims remain prohibited until a preregistered real dataset is complete, independently verified, disclosure-safe and interpreted with its limitations intact.
