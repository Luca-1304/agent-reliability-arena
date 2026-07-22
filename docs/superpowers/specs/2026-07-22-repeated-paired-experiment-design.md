# Repeated Paired Experiment Design

## Purpose

Extend the verified one-scenario private pilot into a preregistered repeated paired experiment while preserving the existing evidence, budget and claims boundaries. The implementation must remain provider-neutral and provider-free under tests and release verification.

## Chosen approach

Use an immutable exact trial schedule rather than a mutable loop or an external workflow file. Every trial is represented before execution by a `TrialPlan` containing its trial ID, scenario ID, seed and condition order. A `RepeatedExperimentPlan` commits to the ordered trial list, the reviewed pilot-policy template and experiment-level stopping rule through canonical SHA-256 digests.

This approach was selected because it makes omission, reordering, duplicate seeds, budget drift and selective continuation detectable. A monolithic runner with implicit repetition counters would be simpler but would not provide a sufficiently reviewable preregistration boundary. A collection of manually launched pilot directories would preserve evidence but would not prove completeness or counterbalancing.

## Scope

### Included

- strict plan and trial schemas;
- deterministic counterbalanced schedule generation;
- exact experiment-level preflight and aggregate reservations;
- ordered private execution through the existing paired-pilot runner;
- configurable first condition for each paired trial;
- safe continuation through an independently verified completed prefix;
- terminal refusal after an aborted or partially started trial;
- provider-free aggregate analysis and uncertainty labels;
- provider-free release reproduction;
- documentation and Python 3.10–3.13 verification.

### Excluded

- real provider execution;
- automatic retry of a model call or an aborted trial;
- concurrent trial execution;
- changing the plan after the first evidence file is written;
- statistical claims of causality, generality or representativeness;
- automatic publication of private evidence;
- arbitrary tools beyond the existing exact file-write fixture.

## Core data model

### `TrialPlan`

Fields:

- `trial_id`: canonical `trial-0001` style identifier;
- `scenario_id`: one configured scenario;
- `seed`: non-negative integer unique within the experiment;
- `condition_order`: exactly `("general", "specialist")` or `("specialist", "general")`.

The canonical dictionary is digestible and contains no secret or path.

### `RepeatedExperimentPlan`

Fields:

- `provider`, `model_id`, `model_version`, `prompt_version`;
- `base_config_digest`, `contract_digest`, `prompt_catalog_digest`;
- `pilot_policy_template_digest`;
- ordered tuple of `TrialPlan` objects;
- `stop_on_abort`, fixed to `True` in schema version 1;
- schema version `1`.

Validation rules:

- at least two trials;
- all trial IDs and seeds are unique;
- all scenarios exist in the supplied `ExperimentConfig`;
- order imbalance within each scenario is at most one;
- provider/model/prompt identifiers match the pilot policy template and configuration;
- the template contains exactly one scenario placeholder when instantiated and external execution may remain disabled for provider-free rehearsal;
- plan digest is canonical SHA-256.

### Schedule generation

`build_counterbalanced_plan` accepts an ordered scenario list, repetitions per scenario and a starting seed. It creates trials in round-robin scenario order. Within each scenario the first condition alternates by repetition index. Odd repetition counts are allowed; the imbalance must never exceed one.

Seeds are assigned monotonically from `starting_seed`, making every request digest distinct while preserving the same seed within both conditions of a trial.

## Experiment preflight

`build_repeated_experiment_preflight` derives each trial’s exact `PilotPolicy` and existing pilot preflight from the plan. It records:

- plan and source digests;
- exact trial order;
- per-trial config digest and policy digest;
- exact call list and maximum role calls;
- requested-output-token, reserved-total-token and monetary ceilings;
- aggregate totals equal to the sum of trial ceilings;
- `provider_called: false`;
- an immutable manifest digest.

No caller may supply aggregate totals independently.

## Paired-pilot condition order

`run_private_paired_pilot` gains an optional `condition_order` parameter defaulting to the current general-first order. It validates the exact two-condition permutation, executes the conditions in that order and records the order in start, abort and final artifacts. Existing callers remain unchanged.

Condition output directories remain named `general` and `specialist`; execution order is represented separately.

## Repeated experiment runner

`run_private_repeated_experiment` receives the base configuration, prompt catalogue, plan, pilot-policy template, transport, private root and explicit reviewed digests/approval.

A fresh root contains:

- `experiment-plan.json`;
- `experiment-preflight.json`;
- `experiment-start.json`;
- one directory per planned trial;
- `experiment-checkpoint.json` rewritten atomically after each verified completed trial;
- either `experiment-summary.json` or `experiment-abort.json`.

Each trial:

1. derives a configuration with the planned seed;
2. derives a one-scenario policy from the reviewed template;
3. executes the existing paired-pilot runner using the planned order;
4. independently verifies the trial ledger and final summary;
5. updates the experiment checkpoint only after verification.

The runner stops on the first exception or trial abort and preserves all existing private evidence.

## Continuation and idempotency

The same function may be called again with the same root only when:

- plan, template and preflight digests exactly match the immutable files;
- all existing trial directories form a contiguous prefix of the plan;
- every directory in that prefix contains a completed, independently verified trial;
- no abort artifact, partial trial directory, extra directory or altered file exists.

Verified completed trials are skipped without constructing or invoking their transport calls. The next planned trial begins.

An experiment containing `experiment-abort.json`, a trial `abort.json`, or an incomplete trial directory is terminal. Continuing requires a new experiment plan and root so duplicate provider calls cannot be hidden.

## Aggregate analysis

`analyse_repeated_experiment` consumes verified completed trial summaries and returns:

- planned, completed and aborted trial counts;
- verified-complete counts per condition;
- both-complete, neither-complete, specialist-only and general-only paired counts;
- completion proportions per condition;
- paired completion-rate difference `specialist - general`;
- Wilson 95% interval for each condition proportion;
- paired normal-approximation 95% interval using trial-level differences in `{-1, 0, 1}`;
- discordant-pair exact two-sided sign-test p-value when at least one discordant pair exists;
- total model calls, measured token fields and measured latency fields when present;
- explicit method names and limitations;
- `comparative_claim_permitted: false`.

The analysis is descriptive infrastructure. The presence of an interval or p-value does not make the sample representative.

## Failure handling

Fail closed on:

- malformed or duplicate trial definitions;
- source/config/policy/plan digest mismatch;
- unbalanced order schedule;
- unknown scenario or duplicate seed;
- aggregate reservation mismatch;
- unsafe, reused or unexpected paths;
- non-contiguous existing trial directories;
- partial or aborted trial during continuation;
- ledger, summary or verifier inconsistency;
- transport request outside a trial preflight;
- attempt to continue after terminal experiment abort.

No automatic retry is introduced.

## Test strategy

Tests must first fail before implementation and cover:

- deterministic schedule generation and digest stability;
- duplicate seed, trial ID, unknown scenario and order imbalance rejection;
- exact aggregate preflight totals;
- specialist-first and general-first pilot execution;
- successful multi-trial run with counterbalanced order;
- skip of a verified completed prefix without duplicate transport calls;
- refusal on partial, aborted, altered or extra trial evidence;
- terminal abort preservation;
- paired aggregate and interval reconstruction;
- no provider call during planning, analysis, replay or release verification;
- complete editable and clean-wheel matrix.

## Claims boundary

Provider-free scripted evidence validates the repeated-experiment mechanism only. Until retained real-provider evidence exists, the repository must continue to state that no hosted or local model performance, cost efficiency, statistical significance, production readiness or general safety result has been established.
