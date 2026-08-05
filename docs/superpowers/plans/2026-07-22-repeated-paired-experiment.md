# Repeated Paired Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preregistered, counterbalanced and safely resumable repeated paired-experiment runner on top of the existing private pilot.

**Architecture:** Add a focused plan/preflight module, extend the paired runner with an explicit condition-order parameter, add a repeated runner that reuses verified trial boundaries, and add a separate descriptive analysis module. Every behavior is test-first and provider-free under CI.

**Tech Stack:** Python 3.10+, standard library only, `unittest`, SHA-256 canonical JSON, existing `PilotPolicy`, `run_private_paired_pilot`, transport ledger and disclosure exporter.

## Global Constraints

- No external provider call in tests, release verification or installed command checks.
- No automatic retry of calls or aborted trials.
- Every trial has one scenario, one unique seed and one exact condition order.
- Existing single-pilot callers remain compatible through a general-first default.
- Continuing an experiment may skip only a contiguous prefix of independently verified completed trials.
- Any aborted, partial, altered or unexpected trial makes the root terminal.
- Statistical output remains descriptive and sets `comparative_claim_permitted` to `false`.
- Python 3.10, 3.11, 3.12 and 3.13 must pass source and clean-wheel gates.

---

### Task 1: Trial plan and deterministic schedule

**Files:**
- Create: `src/agent_reliability_arena/repeated_plan.py`
- Test: `tests/test_repeated_plan.py`

**Interfaces:**
- Produces: `TrialPlan`, `RepeatedExperimentPlan`, `build_counterbalanced_plan`, `build_repeated_experiment_preflight`.
- Consumes: `ExperimentConfig`, `PromptCatalog`, `PilotPolicy`, `build_pilot_preflight`, `canonical_json_sha256`.

- [ ] **Step 1: Write failing schema and schedule tests**

Test deterministic round-robin schedules, alternating condition order, unique seeds, canonical digests and rejection of duplicate IDs/seeds, unknown scenarios and order imbalance.

- [ ] **Step 2: Run the focused test**

Run: `python -m unittest tests.test_repeated_plan -v`

Expected: import failure because `agent_reliability_arena.repeated_plan` does not exist.

- [ ] **Step 3: Implement immutable plan types and schedule generation**

Use frozen dataclasses. `TrialPlan.to_dict()` returns exactly `trial_id`, `scenario_id`, `seed`, `condition_order`. `RepeatedExperimentPlan.to_dict()` returns only canonical documented fields and exposes `.digest`.

- [ ] **Step 4: Add exact preflight derivation**

For each trial, clone the base config with `dataclasses.replace(config, seed=trial.seed)`, derive a one-scenario policy from the template, call `build_pilot_preflight`, and sum exact ceilings. Add a canonical `manifest_digest`.

- [ ] **Step 5: Run focused and complete source tests**

Run:

```bash
python -m unittest tests.test_repeated_plan -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/agent_reliability_arena/repeated_plan.py tests/test_repeated_plan.py
git commit -m "feat: add repeated experiment planning"
```

### Task 2: Explicit paired condition order

**Files:**
- Modify: `src/agent_reliability_arena/private_pilot.py`
- Modify: `tests/test_private_pilot.py`

**Interfaces:**
- Produces: `run_private_paired_pilot(..., condition_order=("general", "specialist"))`.
- Preserves: all existing calls and artifact names.

- [ ] **Step 1: Write failing specialist-first test**

Use a scripted transport that records call conditions. Assert specialist calls occur before the general call when the order is `("specialist", "general")`; assert start and summary artifacts record the same order.

- [ ] **Step 2: Run the focused test**

Run: `python -m unittest tests.test_private_pilot -v`

Expected: failure because the runner does not accept or honour `condition_order`.

- [ ] **Step 3: Implement order validation and ordered execution**

Accept only the two exact permutations. Replace the hard-coded execution block with a loop that dispatches to the existing general or specialist orchestrator and stores results by condition name.

- [ ] **Step 4: Preserve abort evidence**

Pass the selected order into `_abort_payload` and write it into start, abort and final summary artifacts.

- [ ] **Step 5: Run focused and complete tests**

Run:

```bash
python -m unittest tests.test_private_pilot -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/agent_reliability_arena/private_pilot.py tests/test_private_pilot.py
git commit -m "feat: support counterbalanced pilot order"
```

### Task 3: Repeated private runner and safe continuation

**Files:**
- Create: `src/agent_reliability_arena/repeated_runner.py`
- Test: `tests/test_repeated_runner.py`

**Interfaces:**
- Produces: `run_private_repeated_experiment` and `verify_completed_trial`.
- Consumes: Task 1 plan/preflight and Task 2 ordered pilot runner.

- [ ] **Step 1: Write failing successful-run test**

Construct four scripted trials with alternating order. Assert immutable plan/preflight/start files, four trial directories, checkpoint advancement, final summary and no comparative claim.

- [ ] **Step 2: Write failing continuation test**

Pre-populate one independently verified completed trial and checkpoint. Use a transport that would fail if an earlier call is replayed. Assert only remaining trials execute.

- [ ] **Step 3: Write failing terminal-evidence tests**

Cover trial abort, incomplete trial directory, extra directory, changed plan digest, changed trial summary and non-contiguous completed prefix.

- [ ] **Step 4: Run the focused test**

Run: `python -m unittest tests.test_repeated_runner -v`

Expected: import failure because `repeated_runner` does not exist.

- [ ] **Step 5: Implement private root and immutable artifact helpers**

Reuse the private permissions and exclusive-write conventions from `private_pilot.py`. Use atomic replace only for the checkpoint; immutable plan, preflight, start, final and abort records remain create-once.

- [ ] **Step 6: Implement trial derivation and execution**

Derive trial config and one-scenario policy exactly as preflight did. Execute `run_private_paired_pilot` in the planned order. Verify ledger record count, status, scenario, seed-related config digest, policy digest and condition order before checkpoint advancement.

- [ ] **Step 7: Implement continuation verification**

Allow existing directories only when they equal a contiguous completed prefix. Reject any experiment/trial abort or partial evidence. Do not call the transport for skipped trials.

- [ ] **Step 8: Run focused and complete tests**

Run:

```bash
python -m unittest tests.test_repeated_runner -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add src/agent_reliability_arena/repeated_runner.py tests/test_repeated_runner.py
git commit -m "feat: add repeated private experiment runner"
```

### Task 4: Descriptive paired analysis

**Files:**
- Create: `src/agent_reliability_arena/repeated_analysis.py`
- Test: `tests/test_repeated_analysis.py`

**Interfaces:**
- Produces: `analyse_repeated_experiment`, `wilson_interval`, `paired_normal_interval`, `exact_sign_test_p_value`.
- Consumes: verified trial summaries only.

- [ ] **Step 1: Write failing exact-count tests**

Use fixed completed summaries representing both-complete, neither-complete, specialist-only and general-only outcomes. Assert absolute counts and specialist-minus-general difference.

- [ ] **Step 2: Write failing uncertainty tests**

Assert Wilson intervals stay in `[0, 1]`, paired interval stays in `[-1, 1]`, zero-discordance p-value is `None`, and a balanced discordant sample returns `1.0`.

- [ ] **Step 3: Run the focused test**

Run: `python -m unittest tests.test_repeated_analysis -v`

Expected: import failure because `repeated_analysis` does not exist.

- [ ] **Step 4: Implement standard-library calculations**

Use `statistics.NormalDist().inv_cdf(0.975)` for the 95% z value, the standard Wilson formula, sample variance of paired differences for the labelled normal approximation, and exact binomial tail enumeration for the sign test.

- [ ] **Step 5: Aggregate usage and latency**

Sum verified ledger usage and latency fields without inventing missing measurements. Include method names, sample size, limitations and `comparative_claim_permitted: false`.

- [ ] **Step 6: Run focused and complete tests**

Run:

```bash
python -m unittest tests.test_repeated_analysis -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/agent_reliability_arena/repeated_analysis.py tests/test_repeated_analysis.py
git commit -m "feat: add repeated experiment analysis"
```

### Task 5: Provider-free release reproduction

**Files:**
- Create: `src/agent_reliability_arena/release_repeated_fixture.py`
- Create: `scripts/verify_repeated_release.py`
- Modify: `.github/workflows/test.yml`
- Modify: `scripts/verify_release.py`

**Interfaces:**
- Produces: a permanent four-trial provider-free experiment reproduction and release summary fields.

- [ ] **Step 1: Write a failing release-verifier expectation**

Add assertions for four planned/completed trials, balanced order, zero external calls, verified ledgers and descriptive analysis with comparative claims disabled.

- [ ] **Step 2: Run release verification**

Run: `python scripts/verify_release.py`

Expected: failure because repeated release fields do not exist.

- [ ] **Step 3: Implement scripted repeated fixture**

Use provider-shaped scripted responses only. Include at least one specialist-only and one both-complete outcome. Do not import or instantiate the real provider adapter.

- [ ] **Step 4: Add editable and clean-wheel CI steps**

Run `python scripts/verify_repeated_release.py` after the existing disclosure reproduction in both environments.

- [ ] **Step 5: Run release and complete tests**

Run:

```bash
python scripts/verify_repeated_release.py
python scripts/verify_release.py
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/agent_reliability_arena/release_repeated_fixture.py scripts/verify_repeated_release.py scripts/verify_release.py .github/workflows/test.yml
git commit -m "test: verify repeated experiment release"
```

### Task 6: Documentation and final branch verification

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/PROJECT_STATUS.md`
- Create: `docs/REPEATED_EXPERIMENT_RUNBOOK.md`

**Interfaces:**
- Documents: exact provider-free capability and the unchanged real-provider boundary.

- [ ] **Step 1: Update documentation**

Describe the plan, schedule, continuation refusal rules, artifact tree, analysis methods and explicit non-claims. Keep #14 and #15 open.

- [ ] **Step 2: Run documentation-sensitive release verification**

Run:

```bash
python scripts/verify_release.py
python scripts/verify_repeated_release.py
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add README.md ROADMAP.md CHANGELOG.md docs/PROJECT_STATUS.md docs/REPEATED_EXPERIMENT_RUNBOOK.md
git commit -m "docs: document repeated experiment boundary"
```

- [ ] **Step 4: Open or update the pull request**

Record the initial red run, every demonstrated repair and the exact final head.

- [ ] **Step 5: Require final GitHub Actions matrix**

Verify Python 3.10–3.13 pass source compilation, complete source tests, all release reproductions, installed commands, wheel build, clean-wheel tests and dependency validation on the unchanged final head.

- [ ] **Step 6: Merge only the verified head**

Use the expected head SHA in the merge request and leave issue #21 open only if any real-evidence validation remains.
