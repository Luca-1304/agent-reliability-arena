# Deterministic Live Request Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and verify every permitted general and specialist model request before any provider execution.

**Architecture:** Add strict prompt-catalogue value types and a `LiveRequestFactory` that derives requests exclusively from `ExperimentConfig`. Add a provider-free preflight manifest that enumerates required and conditional calls and proves the held-constant experiment fields.

**Tech Stack:** Python 3.10–3.13 standard library, frozen dataclasses, canonical JSON, SHA-256, `unittest`, GitHub Actions.

## Global Constraints

- No provider, network, API key or paid request.
- Prompt catalogue roles are exactly general, strategist, operator, auditor, recovery and synthesiser.
- Prompt catalogue version must equal `ExperimentConfig.prompt_version`.
- Model ID, model version, seed, task and contract come only from `ExperimentConfig`.
- Every request has a deterministic call ID and canonical JSON input.
- Existing deterministic fixture artifacts and metrics remain byte-identical.
- Full source, release, CLI, wheel and clean-wheel verification must pass on Python 3.10–3.13.

---

### Task 1: Prompt catalogue and strict request factory

**Files:**
- Create: `tests/test_live_requests.py`
- Create: `src/agent_reliability_arena/live_requests.py`
- Create: `examples/live_prompt_catalog.json`

**Interfaces:**
- Produces: `RolePrompt`, `PromptCatalog`, `LiveRequestFactory`.
- Consumes: `ExperimentConfig`, `ModelCallRequest`, canonical JSON SHA-256.

- [ ] **Step 1: Write failing catalogue tests**

Test exact role coverage, deterministic round-trip/digest, positive output limits, and missing/unknown role rejection.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
python -m unittest tests.test_live_requests.PromptCatalogTests -v
```

Expected: import failure because `live_requests.py` does not exist.

- [ ] **Step 3: Implement `RolePrompt` and `PromptCatalog`**

Use frozen dataclasses, strict `from_dict`, `to_dict`, and canonical `digest`. Require schema version `"1"` and the exact six-role set.

- [ ] **Step 4: Run catalogue tests and verify GREEN**

- [ ] **Step 5: Write failing request-factory tests**

Cover exact general/operator requests, deterministic call IDs, canonical input payload, metadata, prompt-version mismatch, role-condition mismatch, invalid attempts, unknown scenarios and non-object/non-JSON-compatible payloads.

- [ ] **Step 6: Run factory tests and verify RED**

- [ ] **Step 7: Implement `LiveRequestFactory.build(...)`**

Signature:

```python
def build(
    self,
    *,
    condition: str,
    role: str,
    scenario_id: str,
    attempt_number: int,
    role_payload: dict[str, object],
) -> ModelCallRequest:
```

Use call ID:

```text
{experiment_id}--{condition}--{scenario_id}--{role}--{attempt_number}
```

Canonical input contains `experiment_id`, `config_digest`, `task`, `scenario_id`, `attempt_number`, `contract`, and `role_payload`.

- [ ] **Step 8: Run all live-request tests and verify GREEN**

```bash
python -m unittest tests.test_live_requests -v
```

- [ ] **Step 9: Commit**

```bash
git add tests/test_live_requests.py src/agent_reliability_arena/live_requests.py examples/live_prompt_catalog.json
git commit -m "Add deterministic live request factory"
```

---

### Task 2: Provider-free preflight manifest and release integration

**Files:**
- Modify: `tests/test_live_requests.py`
- Modify: `src/agent_reliability_arena/live_requests.py`
- Modify: `scripts/verify_release.py`
- Modify: `docs/LIVE_MODEL_TRANSPORT.md`

**Interfaces:**
- Produces: `build_live_request_preflight(config, catalog) -> dict[str, object]`.

- [ ] **Step 1: Write failing preflight tests**

Require one general template and seven maximum specialist templates per scenario. Mark recovery, second operator and second auditor as conditional. Assert held-constant fairness fields, catalogue/config digests and deterministic manifest digest.

- [ ] **Step 2: Run preflight tests and verify RED**

- [ ] **Step 3: Implement preflight manifest**

Enumerate templates without calling a transport. Digest the manifest excluding `manifest_digest`, then attach it.

- [ ] **Step 4: Run live-request and complete source tests**

```bash
python -m unittest tests.test_live_requests -v
python -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 5: Extend release verification**

Load `examples/live_prompt_catalog.json`, build the preflight manifest, verify its digest and expected template counts, and include `live_request_templates_verified` in release output.

- [ ] **Step 6: Document preflight boundaries**

State that the catalogue and manifest define permission and fairness, not execution or success.

- [ ] **Step 7: Run all release gates**

```bash
python -m compileall -q src tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verify_release.py
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
python -m pip check
```

- [ ] **Step 8: Verify GitHub matrix and merge only when green**

Require Python 3.10, 3.11, 3.12 and 3.13 to pass source, release, CLI, wheel, clean-wheel and dependency gates.
