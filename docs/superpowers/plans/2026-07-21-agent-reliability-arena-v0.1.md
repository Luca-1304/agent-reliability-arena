# Agent Reliability Arena v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, employer-facing deterministic comparison of one general agent versus a same-model specialist system under identical local tools and independent evidence rules.

**Architecture:** The repository vendors the verified Agent Completion Verifier v0.6.0 Python package and wraps its confined file sandbox with two deterministic orchestration conditions. Strict schemas, fairness invariants, paired metrics, digest-verified artifacts, replay, and a static trace viewer keep software evidence separate from future real-model experiments.

**Tech Stack:** Python 3.10–3.13 standard library, vendored Agent Completion Verifier v0.6.0, static HTML/CSS/JavaScript, GitHub Actions.

## Global Constraints

- Deterministic fixtures are labelled software tests, not model performance.
- Both conditions use the same task, contract, scenario, seed and verifier.
- The verifier remains authoritative; orchestration cannot override observed state.
- No live API call, API key, external network, shell tool or remote mutation is required.
- Fixture token and latency values are not invented; only logical call counts are reported.
- The initial action domain is confined UTF-8 file writing.
- The public viewer is read-only and uses exported non-sensitive artifacts.
- Every release is tested from source and from a clean wheel on Python 3.10–3.13.

---

### Task 1: Package boundary and verifier snapshot

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_reliability_arena/__init__.py`
- Vendor: `src/completion_verifier/**`
- Create: `VENDORED_VERIFIER.md`
- Test: `tests/test_vendor.py`

**Interfaces:**
- Consumes: Agent Completion Verifier v0.6.0 source at commit `f65fb3450e3c1d7db17f0192667b854d126cd190`.
- Produces: importable `completion_verifier` and `agent_reliability_arena` packages plus a source digest record.

- [ ] Write failing tests for package versions, verifier imports and snapshot digest.
- [ ] Run `python -m unittest tests.test_vendor -v` and verify failure.
- [ ] Add packaging metadata, vendor source and digest record.
- [ ] Rerun the focused test and verify success.

### Task 2: Experiment schemas and fairness invariants

**Files:**
- Create: `src/agent_reliability_arena/config.py`
- Create: `src/agent_reliability_arena/schemas.py`
- Test: `tests/test_config.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Produces: `ExperimentConfig`, `TaskSpec`, `ConditionSpec`, `StrategyPlan`, `OperatorRecord`, `AuditRecord`, `RecoveryRecord`, and `SynthesisRecord`.

- [ ] Write failing tests for deterministic digests, duplicate rejection, identical-condition controls and role permissions.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement immutable validated dataclasses and canonical JSON helpers.
- [ ] Rerun focused tests and verify success.

### Task 3: Deterministic general and specialist orchestration

**Files:**
- Create: `src/agent_reliability_arena/orchestration/general.py`
- Create: `src/agent_reliability_arena/orchestration/specialist.py`
- Create: `src/agent_reliability_arena/orchestration/policies.py`
- Create: `src/agent_reliability_arena/reliability/bridge.py`
- Test: `tests/test_general.py`
- Test: `tests/test_specialist.py`
- Test: `tests/test_fairness.py`

**Interfaces:**
- Consumes: strict experiment and role schemas plus `SandboxReferenceRunner`.
- Produces: `ArenaRun` objects containing role artifacts, source reports, observations and canonical verifier evaluations.

- [ ] Write failing scenario and fairness tests.
- [ ] Run focused tests and verify failure.
- [ ] Implement general policy, specialist state machine and verifier bridge.
- [ ] Rerun focused tests and verify all scenarios and stop rules.

### Task 4: Paired metrics, artifacts and replay

**Files:**
- Create: `src/agent_reliability_arena/metrics.py`
- Create: `src/agent_reliability_arena/artifacts.py`
- Create: `src/agent_reliability_arena/replay.py`
- Test: `tests/test_metrics.py`
- Test: `tests/test_artifacts.py`
- Test: `tests/test_replay.py`

**Interfaces:**
- Produces: deterministic `aggregate_metrics.json`, `paired_results.jsonl`, SHA-256 manifests and read-only replay summaries.

- [ ] Write failing tests for denominators, false completion, recovery, logical calls, determinism and tamper rejection.
- [ ] Run focused tests and verify failure.
- [ ] Implement metrics, artifact writer and replay verification.
- [ ] Rerun focused and full tests.

### Task 5: CLI and reference fixture release

**Files:**
- Create: `src/agent_reliability_arena/cli.py`
- Create: `examples/fixture_experiment.json`
- Create: `scripts/verify_release.py`
- Create: `RESULTS.md`
- Test: `tests/test_cli.py`
- Test: `tests/test_release.py`

**Interfaces:**
- Produces console commands `arena-run`, `arena-replay`, and `arena-export-web`.

- [ ] Write failing CLI and release tests.
- [ ] Implement commands and source-controlled fixture configuration.
- [ ] Generate `reference_runs/fixture-v1` and lock exact fixture metrics.
- [ ] Verify all commands from editable and clean-wheel installs.

### Task 6: Employer-facing static trace viewer

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`
- Create: `web/data/fixture-v1.json`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: public export JSON only.
- Produces: read-only, accessible side-by-side trace and evidence viewer.

- [ ] Write failing structural, accessibility, no-placeholder and no-network tests.
- [ ] Implement responsive static viewer and scenario selector.
- [ ] Export fixture data and validate every metric label and evidence reference.
- [ ] Capture a local rendered screenshot for visual review when browser tooling is available.

### Task 7: Documentation, CI and final verification

**Files:**
- Create: `README.md`
- Create: `docs/METHODOLOGY.md`
- Create: `docs/DEMO_SCRIPT.md`
- Create: `docs/CONTRIBUTION.md`
- Create: `.github/workflows/tests.yml`
- Create: `LICENSE`

**Interfaces:**
- Produces: public release documentation, claims boundary, four-version CI and interview-ready narrative.

- [ ] Document the hypothesis, reproduction path, exact fixture status and limitations.
- [ ] Add Python 3.10–3.13 source and clean-wheel matrix.
- [ ] Run compile, full tests, release verification, secret scan, manifest checks and wheel isolation.
- [ ] Repeat the complete verification from the final archive.
