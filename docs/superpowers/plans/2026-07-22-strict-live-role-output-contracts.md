# Strict Live Role Output Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate every live role response as one strict typed JSON object before any orchestration or tool execution.

**Architecture:** Add two proposal dataclasses, one evidence envelope and one strict role-dispatch parser. Reuse existing strategist, auditor, recovery and synthesis schemas. Reject malformed JSON, duplicate keys, unknown fields, unsafe paths and invalid role invariants without repair.

**Tech Stack:** Python 3.10–3.13 standard library, frozen dataclasses, strict `json.loads`, `PurePosixPath`, SHA-256, `unittest`, GitHub Actions.

## Global Constraints

- No provider, network, API key, tool execution or state mutation.
- Maximum encoded output size: 65,536 bytes.
- One top-level JSON object only; no markdown or extraction.
- Duplicate keys and non-finite numbers fail closed.
- Exact field sets for every role.
- Safe relative POSIX paths only.
- Full source, release, CLI, wheel and clean-wheel verification on Python 3.10–3.13.

---

### Task 1: Strict JSON boundary and proposal types

**Files:**
- Create: `tests/test_live_role_outputs.py`
- Create: `src/agent_reliability_arena/live_role_outputs.py`

- [ ] Write failing tests for valid general and operator proposals, exact-byte/canonical digests, markdown, duplicate keys, trailing values, non-object roots, oversized output, non-finite numbers and unsafe paths.
- [ ] Run focused tests and verify RED because the module does not exist.
- [ ] Implement `GeneralProposal`, `OperatorProposal`, `ParsedRoleOutput` and strict JSON/path helpers.
- [ ] Run focused tests and verify GREEN.

### Task 2: Existing role schema dispatch

**Files:**
- Modify: `tests/test_live_role_outputs.py`
- Modify: `src/agent_reliability_arena/live_role_outputs.py`

- [ ] Write failing tests for strategist, auditor, recovery and synthesiser outputs.
- [ ] Verify exact-field, tuple-list and existing invariant failures.
- [ ] Implement role dispatch to `StrategyPlan`, `AuditRecord`, `RecoveryRecord` and `SynthesisRecord`.
- [ ] Run all role-output tests and verify GREEN.

### Task 3: Release integration and documentation

**Files:**
- Modify: `scripts/verify_release.py`
- Modify: `tests/test_release.py`
- Modify: `docs/LIVE_MODEL_TRANSPORT.md`

- [ ] Add provider-free release verification for one valid output per role and digest checks.
- [ ] Include `live_role_outputs_verified: 6` and `live_role_output_digests_verified: true` in release output.
- [ ] Document that parsing proves structure, not truth or completion.
- [ ] Run complete source, release, wheel and clean-wheel gates.
- [ ] Merge only after the Python 3.10–3.13 matrix is fully green.
