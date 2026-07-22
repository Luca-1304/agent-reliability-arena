# Provider-Free Live Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate request planning, strict parsing, transport evidence, controlled sandbox execution and independent verification without contacting a real provider.

**Architecture:** Add general and specialist orchestrators that accept any `ModelTransport`, build all requests through `LiveRequestFactory`, parse every output through `parse_live_role_output`, enforce exact contract and evidence-derived decisions, then return a deterministic `LiveScenarioExecution`. Tests use a scripted transport wrapped by `RecordingTransport`.

**Tech Stack:** Python 3.10–3.13 standard library, existing Arena transport/request/parser/verifier layers, frozen dataclasses, `unittest`, GitHub Actions.

## Global Constraints

- No network, API key or paid request.
- Exact file-write contract only.
- Every operator proposal must match contract path and content before execution.
- Independent observation and verifier status are authoritative.
- Security rejection is terminal.
- Audit, recovery and synthesis outputs must match locally derived evidence.
- Full source, release, CLI, wheel and clean-wheel verification on Python 3.10–3.13.

---

### Task 1: General integration

**Files:**
- Create: `tests/test_live_orchestration.py`
- Create: `src/agent_reliability_arena/live_orchestration.py`

- [ ] Write failing general-success and false-completion tests using a scripted transport plus private ledger.
- [ ] Verify RED because the integration module does not exist.
- [ ] Implement call records, execution records, strict role invocation and `LiveGeneralOrchestrator`.
- [ ] Verify one call, one sandbox attempt, authoritative final status and ledger count.

### Task 2: Specialist integration

**Files:**
- Modify: `tests/test_live_orchestration.py`
- Modify: `src/agent_reliability_arena/live_orchestration.py`

- [ ] Write failing false-success recovery, timeout-after-write and path-traversal tests.
- [ ] Implement evidence-derived audit decisions, bounded recovery and synthesis checks.
- [ ] Verify call counts: seven for recovery, four for no-recovery paths.
- [ ] Verify security rejection never requests recovery.

### Task 3: Negative evidence-override tests

- [ ] Reject wrong operator path/content before sandbox execution.
- [ ] Reject auditor acceptance over unmatched state.
- [ ] Reject recovery or synthesis mismatches.
- [ ] Preserve `TransportError` separately from `LiveOrchestrationError`.
- [ ] Run the complete source suite.

### Task 4: Release integration and documentation

**Files:**
- Modify: `scripts/verify_release.py`
- Modify: `tests/test_release.py`
- Modify: `docs/LIVE_MODEL_TRANSPORT.md`

- [ ] Run provider-free general success, specialist recovery and specialist security failure in release verification.
- [ ] Verify all private ledgers and exact call/attempt/status outcomes.
- [ ] Add release fields for scenarios, role calls, recovery and terminal security proof.
- [ ] Run the full Python 3.10–3.13 matrix and merge only when entirely green.
