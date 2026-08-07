# Layered Reliability Assurance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved layered reliability architecture with Approach C governing the system, Approach A providing the deep stress engine, and Approach B providing isolated specialist verification gates.

**Architecture:** Preserve and reconcile the useful implementation already present in draft PR #83 (`ci/reliability-gate-v2`) instead of rewriting it. Add one machine-readable reliability policy and one evidence contract, make the deep gate consume them, split specialist concerns into narrow standard-library tools/workflows, and enforce merge/release interpretation through repository-owned structural tests. Keep provider execution, deployment, privacy closure, and NASA production outside this project.

**Tech Stack:** Python 3.10–3.13 standard library, `unittest`, GitHub Actions, pip/setuptools/wheel, JSON policy/schema documents, existing Agent Reliability Arena CLIs and verifiers.

## Global Constraints

- No runtime package dependencies.
- No live provider calls.
- No deployment or provider credentials in reliability jobs.
- Reliability jobs remain read-only with `contents: read` and `persist-credentials: false`.
- External GitHub Actions remain pinned to full-length 40-character commit SHAs.
- CI bootstrap tools remain exact-version and SHA-256 locked where merge-critical reproducibility depends on them.
- Supported Python remains 3.10, 3.11, 3.12, and 3.13; deepest repetition remains Python 3.10 and 3.13 initially.
- Minimum deep stress count remains 15 passes.
- Timezone and locale remain controlled as UTC / `C.UTF-8`.
- Diagnostics record only allow-listed environment fields; never dump the full process environment.
- Diagnostic artifacts must be secret/path/privacy scanned before upload.
- Determinism has three explicit classes: `byte`, `semantic`, and `bounded`.
- No unexplained difference may be normalized away.
- Scheduled ecosystem failures are advisory unless policy explicitly promotes the detected condition to blocking.
- Existing historical-CV and provider-deletion blockers remain independent and must not be declared solved by this work.
- Existing release/supply-chain checks remain authoritative unless an equivalent replacement is proven before removal.
- Every task uses a red → green → refactor test cycle and ends in a reviewable commit or PR-sized deliverable.

---

## File Structure

### Existing implementation to preserve/reconcile

- `.github/workflows/fifteen-pass-verification.yml` — current deep stress adapter; PR #83 replaces the monolithic shell loop with a repository-owned Python runner.
- `scripts/ci/reliability_gate.py` — PR #83 deep gate implementation; becomes the Approach A engine under central policy.
- `tests/test_reliability_gate.py` — PR #83 unit coverage for canonical digests, manifests, isolation, command evidence, and failure capture.
- `tests/test_fifteen_pass_workflow_resilience.py` — current workflow contract tests; migrate from string presence to structural/policy agreement.
- `requirements/ci-tools.txt` — PR #83 hash-locked CI bootstrap.

### New policy/evidence foundation

- `reliability-policy.json` — single authoritative reliability contract.
- `schemas/reliability-policy.schema.json` — documented policy shape and version.
- `schemas/reliability-evidence.schema.json` — documented machine-readable evidence shape and failure taxonomy.
- `scripts/ci/reliability_policy.py` — standard-library policy loading and strict validation.
- `scripts/ci/reliability_evidence.py` — evidence/failure helpers shared by deep and specialist gates.
- `scripts/ci/workflow_contract.py` — purpose-built GitHub Actions structural reader for enforced fields; must preserve GitHub expression syntax and avoid YAML 1.1 `on` coercion.

### New specialist tools

- `scripts/ci/verify_reproducible_build.py` — independent clean builds and normalized package comparison.
- `scripts/ci/verify_determinism.py` — policy-driven deterministic-class normalization, digesting, and diff production.
- `scripts/ci/verify_clean_room.py` — cold-cache packaged install/run/replay/verify path.
- `scripts/ci/verify_concurrency.py` — bounded independent-run state isolation test.
- `scripts/ci/scan_diagnostics.py` — secret/private-path/private-URL/privacy scan for evidence bundles.
- `scripts/ci/verify_ci_policy.py` — repository-level agreement check between policy and workflow structure.

### New workflows

- `.github/workflows/reliability-fast.yml` — policy/schema/workflow/security/package smoke feedback.
- `.github/workflows/reliability-specialists.yml` — reproducibility, determinism, clean-room, concurrency, and diagnostic-security jobs.
- `.github/workflows/reliability-ecosystem.yml` — scheduled/manual compatibility and cold-cache drift checks.
- `.github/workflows/fifteen-pass-verification.yml` — remains the deep gate, thin adapter only.

### New tests

- `tests/test_reliability_policy.py`
- `tests/test_reliability_evidence.py`
- `tests/test_workflow_contract.py`
- `tests/test_reproducible_build.py`
- `tests/test_determinism.py`
- `tests/test_clean_room.py`
- `tests/test_concurrency_isolation.py`
- `tests/test_diagnostic_scanner.py`
- `tests/test_ci_policy.py`

---

### Task 1: Reconcile PR #83 with the approved architecture

**Files:**
- Rebase/update branch: `ci/reliability-gate-v2`
- Preserve: `scripts/ci/reliability_gate.py`
- Preserve: `tests/test_reliability_gate.py`
- Preserve: `requirements/ci-tools.txt`
- Preserve: `.github/workflows/fifteen-pass-verification.yml`
- Reference: `docs/superpowers/specs/2026-08-07-layered-reliability-assurance-design.md`

**Interfaces:**
- Consumes: draft PR #83 head plus `main` containing the approved layered design.
- Produces: a conflict-free Approach A foundation whose behaviour is unchanged except where later tasks explicitly move constants into central policy/evidence helpers.

- [ ] **Step 1: Update PR #83 branch onto the approved design commit without flattening its useful implementation.**

Run:

```bash
git fetch origin main ci/reliability-gate-v2
git switch ci/reliability-gate-v2
git rebase origin/main
```

Expected: the branch contains the approved `2026-08-07-layered-reliability-assurance-design.md` and the existing v2 runner files. Resolve conflicts by preserving `main` documentation and PR #83 code; do not remove reliability controls merely to make the rebase easy.

- [ ] **Step 2: Run the focused existing v2 tests before architecture changes.**

Run:

```bash
python -m unittest tests.test_reliability_gate tests.test_fifteen_pass_workflow_resilience -v
```

Expected: PASS. If current-head GitHub-hosted runners remain unavailable, record that as infrastructure status; do not count runner boot failures as repository test failures.

- [ ] **Step 3: Verify the existing runner public helpers remain available for migration.**

Add this compatibility test to `tests/test_reliability_gate.py` before moving code:

```python
class ExistingRunnerCompatibilityTests(unittest.TestCase):
    def test_foundation_interfaces_exist(self) -> None:
        self.assertTrue(callable(reliability_gate.canonical_digest))
        self.assertTrue(callable(reliability_gate.tree_manifest))
        self.assertTrue(callable(reliability_gate.compare_manifest))
        self.assertTrue(callable(reliability_gate.build_pass_environment))
        self.assertTrue(callable(reliability_gate.run_command))
        self.assertTrue(callable(reliability_gate.execute))
```

Run:

```bash
python -m unittest tests.test_reliability_gate.ExistingRunnerCompatibilityTests -v
```

Expected: PASS before later refactors and PASS after them.

- [ ] **Step 4: Commit only the branch reconciliation/compatibility test.**

```bash
git add tests/test_reliability_gate.py docs/superpowers/specs/2026-08-07-layered-reliability-assurance-design.md
git commit -m "test: preserve reliability gate foundation interfaces"
```

---

### Task 2: Add the central machine-readable reliability policy

**Files:**
- Create: `reliability-policy.json`
- Create: `schemas/reliability-policy.schema.json`
- Create: `scripts/ci/reliability_policy.py`
- Create: `tests/test_reliability_policy.py`

**Interfaces:**
- Produces: `load_policy(path: Path) -> ReliabilityPolicy`
- Produces: `validate_policy_payload(payload: Mapping[str, object]) -> None`
- Produces: `ReliabilityPolicy` with immutable accessors for supported/deep Python versions, stress passes, trigger surfaces, permissions, install modes, deterministic outputs, retention bounds, timeout ceilings, and scheduled dimensions.
- Later tasks consume only this policy object for constants that affect reliability decisions.

- [ ] **Step 1: Write the failing policy loader/validation tests.**

Create `tests/test_reliability_policy.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_policy import PolicyError, load_policy


class ReliabilityPolicyTests(unittest.TestCase):
    def test_repository_policy_has_required_contract(self) -> None:
        policy = load_policy(Path("reliability-policy.json"))
        self.assertEqual(policy.schema_version, "reliability-policy-v1")
        self.assertEqual(policy.supported_python, ("3.10", "3.11", "3.12", "3.13"))
        self.assertEqual(policy.deep_python, ("3.10", "3.13"))
        self.assertGreaterEqual(policy.stress_passes, 15)
        self.assertEqual(policy.max_permissions, {"contents": "read"})
        self.assertFalse(policy.persist_credentials)
        self.assertIn("semantic", policy.determinism_classes)
        self.assertIn("cold", policy.cache_modes)

    def test_unknown_top_level_key_fails_closed(self) -> None:
        payload = json.loads(Path("reliability-policy.json").read_text(encoding="utf-8"))
        payload["surprise"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "unknown policy keys"):
                load_policy(path)

    def test_weakened_stress_count_is_rejected(self) -> None:
        payload = json.loads(Path("reliability-policy.json").read_text(encoding="utf-8"))
        payload["deep_gate"]["minimum_passes"] = 14
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "policy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PolicyError, "minimum_passes"):
                load_policy(path)
```

Run:

```bash
python -m unittest tests.test_reliability_policy -v
```

Expected: FAIL because the policy module/file do not yet exist.

- [ ] **Step 2: Create the authoritative policy with explicit values.**

Create `reliability-policy.json` with this initial contract:

```json
{
  "schema_version": "reliability-policy-v1",
  "supported_python": ["3.10", "3.11", "3.12", "3.13"],
  "deep_gate": {
    "python": ["3.10", "3.13"],
    "minimum_passes": 15,
    "timezone": "UTC",
    "locale": "C.UTF-8",
    "hash_seeds": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    "command_timeout_seconds": 900,
    "pass_timeout_seconds": 1800,
    "job_timeout_minutes": 180
  },
  "permissions": {
    "maximum": {"contents": "read"},
    "persist_credentials": false
  },
  "install_modes": ["editable", "wheel", "clean-room-wheel"],
  "cache_modes": ["warm", "cold"],
  "determinism_classes": ["byte", "semantic", "bounded"],
  "diagnostics": {
    "schema_version": "reliability-evidence-v1",
    "retention_days": 14,
    "required_files": ["manifest.json", "summary.json", "summary.md", "events.jsonl"],
    "failure_categories": ["TEST", "BUILD", "PACKAGE", "REPLAY", "DETERMINISM", "SECURITY", "DEPENDENCY", "ENVIRONMENT", "TIMEOUT", "CONCURRENCY", "POLICY", "UNKNOWN"]
  },
  "trigger_surfaces": ["src/**", "tests/**", "scripts/**", "examples/**", "security/**", "release/**", "reference_runs/**", "web/**", "docs/**", "citation/**", "requirements/**", "schemas/**", "reliability-policy.json", "pyproject.toml", "README.md", "CHANGELOG.md", "ROADMAP.md", ".github/workflows/**"],
  "scheduled": {
    "blocking_by_default": false,
    "dimensions": ["latest-compatible-build-tools", "cold-cache", "dependency-resolution"]
  }
}
```

- [ ] **Step 3: Implement strict standard-library validation.**

Create `scripts/ci/reliability_policy.py` around these exact public types:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ReliabilityPolicy:
    schema_version: str
    supported_python: tuple[str, ...]
    deep_python: tuple[str, ...]
    stress_passes: int
    max_permissions: dict[str, str]
    persist_credentials: bool
    determinism_classes: tuple[str, ...]
    cache_modes: tuple[str, ...]
    trigger_surfaces: tuple[str, ...]
    raw: dict[str, object]


def load_policy(path: Path) -> ReliabilityPolicy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_policy_payload(payload)
    deep_gate = payload["deep_gate"]
    permissions = payload["permissions"]
    return ReliabilityPolicy(
        schema_version=str(payload["schema_version"]),
        supported_python=tuple(payload["supported_python"]),
        deep_python=tuple(deep_gate["python"]),
        stress_passes=int(deep_gate["minimum_passes"]),
        max_permissions=dict(permissions["maximum"]),
        persist_credentials=bool(permissions["persist_credentials"]),
        determinism_classes=tuple(payload["determinism_classes"]),
        cache_modes=tuple(payload["cache_modes"]),
        trigger_surfaces=tuple(payload["trigger_surfaces"]),
        raw=dict(payload),
    )
```

`validate_policy_payload` must reject unknown top-level keys, missing required keys, unsupported Python version strings, `minimum_passes < 15`, permissions broader than `{"contents": "read"}`, `persist_credentials: true`, retention outside 1–30 days, duplicate hash seeds, and any determinism class outside `byte|semantic|bounded`.

- [ ] **Step 4: Add a JSON Schema document matching the same shape.**

`schemas/reliability-policy.schema.json` must use Draft 2020-12, `additionalProperties: false` at each defined object, enumerate the three determinism classes and required failure categories, and set `minimum: 15` for `deep_gate.minimum_passes`.

- [ ] **Step 5: Run focused tests.**

```bash
python -m unittest tests.test_reliability_policy -v
```

Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add reliability-policy.json schemas/reliability-policy.schema.json scripts/ci/reliability_policy.py tests/test_reliability_policy.py
git commit -m "feat: centralize reliability policy"
```

---

### Task 3: Extract a common evidence and failure contract

**Files:**
- Create: `schemas/reliability-evidence.schema.json`
- Create: `scripts/ci/reliability_evidence.py`
- Create: `tests/test_reliability_evidence.py`
- Modify: `scripts/ci/reliability_gate.py`
- Modify: `tests/test_reliability_gate.py`

**Interfaces:**
- Produces: `FailureCategory` string constants matching policy.
- Produces: `FailureRecord` dataclass with `to_dict()`.
- Produces: `EvidenceManifest` dataclass with `to_dict()`.
- Produces: `write_json_atomic(path, payload)`, `append_jsonl(path, payload)`, `sha256_bytes(data)`, `dependency_fingerprint(rows)`.
- Deep and specialist gates must emit `manifest.json` conforming to `reliability-evidence-v1`.

- [ ] **Step 1: Write failing evidence tests.**

Create `tests/test_reliability_evidence.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.reliability_evidence import EvidenceManifest, FailureRecord, write_json_atomic


class ReliabilityEvidenceTests(unittest.TestCase):
    def test_failure_record_uses_controlled_vocabulary(self) -> None:
        record = FailureRecord(
            category="TIMEOUT",
            phase="deep",
            command_name="unit-tests",
            argv=("python", "-m", "unittest"),
            sequence=4,
            pass_number=2,
            hash_seed=1,
            exit_code=124,
            duration_seconds=900.0,
            log_path="passes/02/commands/04-unit-tests.log",
            message="command timed out",
        )
        self.assertEqual(record.to_dict()["category"], "TIMEOUT")

    def test_manifest_is_machine_readable_and_versioned(self) -> None:
        manifest = EvidenceManifest.minimum_for_test(commit_sha="a" * 40)
        payload = manifest.to_dict()
        self.assertEqual(payload["schema_version"], "reliability-evidence-v1")
        self.assertEqual(payload["commit_sha"], "a" * 40)
        self.assertIn("commands", payload)
        self.assertIn("failures", payload)

    def test_atomic_json_never_leaves_partial_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "manifest.json"
            write_json_atomic(target, {"ok": True})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"ok": True})
```

Run:

```bash
python -m unittest tests.test_reliability_evidence -v
```

Expected: FAIL because the common evidence module does not exist.

- [ ] **Step 2: Implement the evidence module with frozen dataclasses and controlled categories.**

The category set must be exactly:

```python
FAILURE_CATEGORIES = frozenset({
    "TEST", "BUILD", "PACKAGE", "REPLAY", "DETERMINISM", "SECURITY",
    "DEPENDENCY", "ENVIRONMENT", "TIMEOUT", "CONCURRENCY", "POLICY", "UNKNOWN",
})
```

`FailureRecord.__post_init__` must raise `ValueError` for any other category. `EvidenceManifest.to_dict()` must sort command/failure entries by sequence and include: schema version, repository, commit SHA, workflow/run/attempt, event/ref, runner OS/arch, Python version, timezone, locale, hash seed, install mode, toolchain, dependency fingerprint, cache mode, commands, timings, output digests, failures, and final status.

- [ ] **Step 3: Move PR #83 evidence helpers behind compatibility aliases.**

In `scripts/ci/reliability_gate.py`, import:

```python
from scripts.ci.reliability_evidence import (
    EvidenceManifest,
    FailureRecord,
    append_jsonl as append_event,
    write_json_atomic as write_json,
)
```

Remove duplicate `FailureRecord`, `write_json`, and `append_event` implementations only after existing tests pass through the imported functions. Preserve `canonical_digest`, `tree_manifest`, `compare_manifest`, `build_pass_environment`, `run_command`, and `execute` signatures from Task 1.

- [ ] **Step 4: Write `manifest.json` in every deep-gate outcome.**

At gate start, initialize an `EvidenceManifest`; after every `CommandResult`, append the command record; on failure append the common `FailureRecord`; in `finally`, atomically write `diagnostics/manifest.json` before returning.

- [ ] **Step 5: Add schema document and fixture validation tests.**

`schemas/reliability-evidence.schema.json` must set `additionalProperties: false`, require `schema_version`, `commit_sha`, `commands`, `failures`, and `final_status`, enumerate failure categories, and require full 40-character lower-case hex SHAs when a commit is known.

- [ ] **Step 6: Run all affected tests.**

```bash
python -m unittest tests.test_reliability_evidence tests.test_reliability_gate -v
```

Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add schemas/reliability-evidence.schema.json scripts/ci/reliability_evidence.py scripts/ci/reliability_gate.py tests/test_reliability_evidence.py tests/test_reliability_gate.py
git commit -m "feat: standardize reliability evidence"
```

---

### Task 4: Make the deep gate policy-driven and add layered timeout/dependency evidence

**Files:**
- Modify: `scripts/ci/reliability_gate.py`
- Modify: `.github/workflows/fifteen-pass-verification.yml`
- Modify: `tests/test_reliability_gate.py`
- Modify: `tests/test_fifteen_pass_workflow_resilience.py`

**Interfaces:**
- Consumes: `ReliabilityPolicy` from Task 2 and evidence helpers from Task 3.
- Produces: policy-driven pass count/hash seeds/timeouts, `toolchain.json`, `dependencies.json`, command timing records, and pass-level timeout classification.

- [ ] **Step 1: Write failing tests that reject duplicated deep-gate constants.**

Add:

```python
class PolicyDrivenGateTests(unittest.TestCase):
    def test_gate_config_uses_policy_pass_count(self) -> None:
        policy = reliability_policy.load_policy(Path("reliability-policy.json"))
        config = reliability_gate.GateConfig.from_policy(
            policy=policy,
            python_label="3.10",
            workspace=Path.cwd(),
            work_root=Path("/tmp/work"),
            diagnostics_dir=Path("/tmp/diag"),
        )
        self.assertEqual(config.passes, policy.stress_passes)
        self.assertEqual(config.hash_seeds, tuple(range(15)))
```

Run and expect FAIL because `GateConfig.from_policy` does not exist.

- [ ] **Step 2: Add policy-backed gate configuration.**

Implement:

```python
@classmethod
def from_policy(cls, *, policy, python_label, workspace, work_root, diagnostics_dir):
    deep = policy.raw["deep_gate"]
    return cls(
        passes=policy.stress_passes,
        python_label=python_label,
        workspace=workspace,
        work_root=work_root,
        diagnostics_dir=diagnostics_dir,
        hash_seeds=tuple(int(value) for value in deep["hash_seeds"]),
        command_timeout_seconds=int(deep["command_timeout_seconds"]),
        pass_timeout_seconds=int(deep["pass_timeout_seconds"]),
    )
```

Extend `GateConfig` with `hash_seeds`, `command_timeout_seconds`, and `pass_timeout_seconds`. `run_pass` must use `config.hash_seeds[pass_number - 1]` rather than deriving seed from the pass number.

- [ ] **Step 3: Record toolchain and dependency fingerprints without dumping environment variables.**

Add commands that capture only:

```text
python --version
python -m pip --version
python -m pip freeze --all
python -m pip check
git --version
```

Parse `pip freeze --all` into sorted non-editable rows and hash the normalized newline-joined representation with SHA-256. Store the rows in `dependencies.json` and the digest in `manifest.json`.

- [ ] **Step 4: Add pass-level timeout enforcement.**

Use monotonic time at `run_pass` entry. Before each command, compute remaining pass budget; set `CommandSpec.timeout_seconds = min(command_timeout, max(1, remaining_seconds))`. If no budget remains, create a `TIMEOUT` failure with command name `pass-budget`, sequence `context.command_index + 1`, and no subprocess execution.

- [ ] **Step 5: Reduce the workflow job timeout from six hours to the policy ceiling.**

The workflow adapter must set:

```yaml
timeout-minutes: 180
```

and pass only the policy path, Python label, workspace, work root, and diagnostics directory to the runner. The runner owns the pass count.

- [ ] **Step 6: Run focused and full workflow contract tests.**

```bash
python -m unittest tests.test_reliability_gate tests.test_fifteen_pass_workflow_resilience -v
```

Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add reliability-policy.json scripts/ci/reliability_gate.py .github/workflows/fifteen-pass-verification.yml tests/test_reliability_gate.py tests/test_fifteen_pass_workflow_resilience.py
git commit -m "feat: drive deep reliability gate from policy"
```

---

### Task 5: Add explicit determinism classes and reproducible-build specialist

**Files:**
- Create: `scripts/ci/verify_determinism.py`
- Create: `scripts/ci/verify_reproducible_build.py`
- Create: `tests/test_determinism.py`
- Create: `tests/test_reproducible_build.py`
- Modify: `reliability-policy.json`

**Interfaces:**
- Produces: `normalize_output(path: Path, rule: Mapping[str, object]) -> bytes`
- Produces: `compare_deterministic_outputs(left, right, rule) -> ComparisonResult`
- Produces: `normalized_wheel_manifest(path: Path) -> dict[str, dict[str, object]]`
- Produces: specialist `manifest.json`, `summary.json`, and normalized diff evidence.

- [ ] **Step 1: Define explicit deterministic-output rules in policy.**

Add:

```json
"deterministic_outputs": {
  "fixture_run": {"class": "semantic", "format": "json", "ignore_json_pointers": []},
  "fixture_replay": {"class": "semantic", "format": "json", "ignore_json_pointers": []},
  "public_export": {"class": "semantic", "format": "json", "ignore_json_pointers": []},
  "wheel_contents": {"class": "semantic", "format": "zip-tree", "ignore_archive_metadata": ["timestamp"]}
}
```

No ignored field may be added without a unit test demonstrating that the field is genuinely volatile and non-semantic.

- [ ] **Step 2: Write failing normalization tests.**

```python
class DeterminismTests(unittest.TestCase):
    def test_semantic_json_ignores_formatting_not_values(self) -> None:
        left = b'{"b":2,"a":1}\n'
        right = b'{\n  "a": 1,\n  "b": 2\n}\n'
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertNotEqual(canonical_json_bytes(left), canonical_json_bytes(b'{"a":1,"b":3}'))

    def test_unlisted_difference_is_reported(self) -> None:
        result = compare_json_values({"a": 1}, {"a": 2}, ignored_pointers=())
        self.assertFalse(result.equal)
        self.assertIn("/a", result.diff)
```

- [ ] **Step 3: Implement JSON-pointer-limited semantic normalization.**

Only remove pointers explicitly listed in policy. Reject an ignore pointer that does not exist in both compared payloads; this prevents silently hiding a newly introduced field.

- [ ] **Step 4: Write failing reproducible wheel tests using two tiny synthetic wheels.**

Create wheels with the same files but different ZIP timestamps and assert `normalized_wheel_manifest` matches. Change a package file byte and assert mismatch reports that path.

- [ ] **Step 5: Implement normalized wheel comparison.**

Use `zipfile.ZipFile`. Ignore only archive timestamp/order metadata; compare exact member names, compression-independent uncompressed bytes, `METADATA`, `WHEEL`, entry points, and `RECORD` semantic rows. Reject symbolic-link entries and absolute/traversal paths.

- [ ] **Step 6: Make the specialist build the repository twice from independent clean directories.**

Each build must use the hash-locked CI toolchain, `SOURCE_DATE_EPOCH`, no previous `dist/` or `build/`, and separate `HOME`, temp, cache, and work roots. Compare normalized wheel manifests and emit `PACKAGE` or `DETERMINISM` failure evidence.

- [ ] **Step 7: Run tests.**

```bash
python -m unittest tests.test_determinism tests.test_reproducible_build -v
```

Expected: PASS.

- [ ] **Step 8: Commit.**

```bash
git add reliability-policy.json scripts/ci/verify_determinism.py scripts/ci/verify_reproducible_build.py tests/test_determinism.py tests/test_reproducible_build.py
git commit -m "feat: verify deterministic outputs and reproducible builds"
```

---

### Task 6: Add cold clean-room installation and concurrency/isolation specialists

**Files:**
- Create: `scripts/ci/verify_clean_room.py`
- Create: `scripts/ci/verify_concurrency.py`
- Create: `tests/test_clean_room.py`
- Create: `tests/test_concurrency_isolation.py`

**Interfaces:**
- `verify_clean_room.py` consumes one built wheel and fixture config; it must not import the package from the checkout.
- `verify_concurrency.py` launches at least two isolated fixture runs and verifies no shared files/results/state.
- Both emit the common evidence schema.

- [ ] **Step 1: Write a failing clean-room path-leak test.**

```python
class CleanRoomTests(unittest.TestCase):
    def test_pythonpath_excludes_workspace(self) -> None:
        env = build_clean_room_environment(
            base={"PATH": "/usr/bin", "PYTHONPATH": "/repo/src"},
            workspace=Path("/repo"),
            root=Path("/tmp/clean"),
        )
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("/repo", "\n".join(env.values()))
```

- [ ] **Step 2: Implement cold clean-room environment creation.**

Remove `PYTHONPATH`, `VIRTUAL_ENV`, package-specific provider secrets, and workspace-bearing cache variables. Set fresh `HOME`, temp, `PIP_CACHE_DIR` and `XDG_CACHE_HOME`. Create a fresh venv, install only the wheel with `--no-deps`, run `pip check`, then run fixture `arena-run`, `arena-replay`, public export, and all repository verifier CLIs from the installed wheel entry points.

- [ ] **Step 3: Assert the installed package resolves outside the workspace.**

Run:

```python
import agent_reliability_arena, pathlib
print(pathlib.Path(agent_reliability_arena.__file__).resolve())
```

Fail `PACKAGE` if the resolved path is within the checkout.

- [ ] **Step 4: Write failing concurrency collision tests.**

Use two temporary roots and a harmless fake runner in tests. Assert simultaneous execution produces two disjoint artifact trees and cleanup of one root cannot remove the other.

- [ ] **Step 5: Implement bounded concurrent real fixture verification.**

Use `concurrent.futures.ThreadPoolExecutor(max_workers=2)` only to supervise two subprocess-based arena runs. Each subprocess gets a unique `HOME`, temp/cache directory, output root, and `PYTHONHASHSEED`. After both finish, verify result IDs/paths belong to their invocation and compare each replay against its own run only.

- [ ] **Step 6: Run tests.**

```bash
python -m unittest tests.test_clean_room tests.test_concurrency_isolation -v
```

Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add scripts/ci/verify_clean_room.py scripts/ci/verify_concurrency.py tests/test_clean_room.py tests/test_concurrency_isolation.py
git commit -m "feat: verify clean-room and concurrent isolation"
```

---

### Task 7: Add privacy-safe diagnostic scanning

**Files:**
- Create: `scripts/ci/scan_diagnostics.py`
- Create: `tests/test_diagnostic_scanner.py`
- Modify: `reliability-policy.json`
- Modify: deep/specialist workflows after scanner exists.

**Interfaces:**
- Produces: `scan_tree(root: Path, *, workspace: Path, policy: ReliabilityPolicy) -> ScanReport`
- Fails with category `SECURITY` before upload if evidence contains prohibited material.

- [ ] **Step 1: Add scanner policy.**

Add diagnostic scanner rules:

```json
"scanner": {
  "forbid_absolute_workspace_paths": true,
  "forbid_private_url_hosts": ["localhost", "127.0.0.1", "0.0.0.0"],
  "secret_name_fragments": ["api_key", "token", "password", "secret"],
  "max_text_file_bytes": 5000000
}
```

Do not place actual credentials, personal addresses, or historical private URLs in this policy.

- [ ] **Step 2: Write tests for real false-positive/false-negative boundaries.**

```python
class DiagnosticScannerTests(unittest.TestCase):
    def test_detects_workspace_path(self) -> None:
        report = scan_text("log", "cwd=/home/runner/work/repo/repo/src", workspace=Path("/home/runner/work/repo/repo"))
        self.assertTrue(report.findings)

    def test_detects_secret_assignment_without_echoing_value(self) -> None:
        report = scan_text("log", "OPENAI_API_KEY=sk-example-not-real", workspace=Path("/repo"))
        self.assertEqual(report.findings[0].kind, "secret-like-assignment")
        self.assertNotIn("sk-example", report.findings[0].rendered)

    def test_normal_command_argv_is_allowed(self) -> None:
        report = scan_text("log", "python -m unittest discover -s tests", workspace=Path("/repo"))
        self.assertEqual(report.findings, [])
```

- [ ] **Step 3: Implement streaming text scan and JSON-aware key inspection.**

Never include matched secret values in scanner output. Render only file, line number, finding kind, and redacted key/context. Skip binary files except to flag prohibited absolute path byte sequences. Reject symlinks.

- [ ] **Step 4: Require scanner success before artifact upload.**

Every critical workflow order becomes:

```text
run gate -> write evidence -> scan diagnostics -> publish summary -> upload artifact
```

`upload-artifact` remains `if: always()`, but if the scanner fails, upload only a minimal scanner report and non-sensitive manifest/summary files, not the unscanned evidence tree.

- [ ] **Step 5: Run tests.**

```bash
python -m unittest tests.test_diagnostic_scanner -v
```

Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add reliability-policy.json scripts/ci/scan_diagnostics.py tests/test_diagnostic_scanner.py
git commit -m "feat: scan reliability diagnostics before upload"
```

---

### Task 8: Replace string-based CI tests with structural policy enforcement

**Files:**
- Create: `scripts/ci/workflow_contract.py`
- Create: `scripts/ci/verify_ci_policy.py`
- Create: `tests/test_workflow_contract.py`
- Create: `tests/test_ci_policy.py`
- Modify: `tests/test_fifteen_pass_workflow_resilience.py`

**Interfaces:**
- Produces: `read_workflow_contract(path: Path) -> WorkflowContract`
- Produces: `verify_workflow_against_policy(contract, policy, *, role: str) -> list[PolicyViolation]`
- Must structurally inspect triggers, permissions, jobs, timeouts, action `uses`, checkout persistence, artifact upload `if`, and retention.

- [ ] **Step 1: Write a failing parser test for GitHub's `on:` key.**

```python
class WorkflowContractTests(unittest.TestCase):
    def test_on_is_preserved_as_trigger_key(self) -> None:
        contract = read_workflow_contract(Path(".github/workflows/fifteen-pass-verification.yml"))
        self.assertIn("pull_request", contract.triggers)
        self.assertIn("push", contract.triggers)
```

The parser must not interpret `on` as boolean `True`.

- [ ] **Step 2: Implement a purpose-built indentation parser only for enforced fields.**

Parse line-by-line with indentation tracking; preserve raw `${{ ... }}` expressions as strings. The parser does not need to understand arbitrary YAML. It must understand top-level `on`, `permissions`, `concurrency`, `jobs`; per-job `runs-on`, `timeout-minutes`, `permissions`; and step `uses`, `if`, `with.persist-credentials`, `with.retention-days`.

- [ ] **Step 3: Write policy agreement tests.**

```python
class CiPolicyTests(unittest.TestCase):
    def test_deep_workflow_matches_policy(self) -> None:
        policy = load_policy(Path("reliability-policy.json"))
        contract = read_workflow_contract(Path(".github/workflows/fifteen-pass-verification.yml"))
        violations = verify_workflow_against_policy(contract, policy, role="deep")
        self.assertEqual(violations, [])
```

Add mutation fixtures that intentionally set `contents: write`, `persist-credentials: true`, retention 60, missing `always()`, job timeout 360, and missing trigger surfaces; assert each yields a specific violation.

- [ ] **Step 4: Replace shallow string assertions with structural calls.**

Keep only behavioural tests that are not policy duplication. The old `assertIn("TZ: UTC", workflow_text)` style checks should be removed once equivalent structural/policy assertions are green.

- [ ] **Step 5: Add the CLI verifier.**

`scripts/ci/verify_ci_policy.py` loads `reliability-policy.json`, validates all reliability workflows, prints JSON to stdout with `{"status":"passed","violations":[]}` on success, and exits 1 with a non-empty violations list on failure.

- [ ] **Step 6: Run tests.**

```bash
python -m unittest tests.test_workflow_contract tests.test_ci_policy tests.test_fifteen_pass_workflow_resilience -v
```

Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add scripts/ci/workflow_contract.py scripts/ci/verify_ci_policy.py tests/test_workflow_contract.py tests/test_ci_policy.py tests/test_fifteen_pass_workflow_resilience.py
git commit -m "feat: enforce CI structure against reliability policy"
```

---

### Task 9: Add Fast, Specialist, and Scheduled gates without duplicating the Deep gate

**Files:**
- Create: `.github/workflows/reliability-fast.yml`
- Create: `.github/workflows/reliability-specialists.yml`
- Create: `.github/workflows/reliability-ecosystem.yml`
- Modify: `reliability-policy.json`
- Modify: `tests/test_ci_policy.py`

**Interfaces:**
- Fast Gate: immediate policy/schema/unit/package-smoke/security feedback.
- Deep Gate: existing `fifteen-pass-verification.yml`, Approach A only.
- Specialist Gate: Approach B jobs using Tasks 5–7 tools.
- Scheduled Gate: non-blocking-by-default ecosystem drift evidence.

- [ ] **Step 1: Add workflow-role policy.**

Add:

```json
"workflow_roles": {
  "fast": ["reliability-fast.yml"],
  "deep": ["fifteen-pass-verification.yml"],
  "specialist": ["reliability-specialists.yml"],
  "scheduled": ["reliability-ecosystem.yml"]
}
```

- [ ] **Step 2: Create Fast Gate.**

It must run on all policy trigger surfaces and include jobs for:

```text
policy + workflow contract
Python 3.10–3.13 unit/integration suite
compile/package metadata
one clean wheel build/install smoke
existing privacy/security static checks
```

It must not invoke 15 repeated passes.

- [ ] **Step 3: Create Specialist Gate.**

Use separate jobs:

```text
reproducible-build
explicit-determinism
clean-room
concurrency-isolation
diagnostic-security
```

Each job has `contents: read`, SHA-pinned actions, non-persistent checkout, its own timeout, common evidence output, scanner-before-upload, and no provider/deployment secrets.

- [ ] **Step 4: Create Scheduled Ecosystem Gate.**

Trigger:

```yaml
on:
  schedule:
    - cron: "17 4 * * 2"
  workflow_dispatch:
```

Run cold cache and latest-compatible build-tool/dependency resolution in an isolated environment. Do not mutate `requirements/ci-tools.txt`. Emit an advisory evidence artifact and GitHub step summary. The job itself may fail red to signal maintenance, but `verify_ci_policy.py` must classify it as scheduled/advisory rather than a merge requirement.

- [ ] **Step 5: Add structural tests proving role separation.**

Assert Deep Gate does not contain scheduled `cron`; Scheduled Gate does not trigger on `pull_request`; Fast Gate does not invoke `reliability_gate.py --passes 15`; Specialist Gate contains each required specialist tool exactly once.

- [ ] **Step 6: Run policy and workflow tests.**

```bash
python -m unittest tests.test_ci_policy tests.test_workflow_contract -v
```

Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add reliability-policy.json .github/workflows/reliability-fast.yml .github/workflows/reliability-specialists.yml .github/workflows/reliability-ecosystem.yml tests/test_ci_policy.py
git commit -m "feat: separate fast specialist and ecosystem reliability gates"
```

---

### Task 10: Add merge-decision evidence and performance telemetry without false thresholds

**Files:**
- Create: `scripts/ci/summarize_reliability.py`
- Create: `tests/test_reliability_summary.py`
- Modify: `reliability-policy.json`
- Modify: reliability workflows to publish summaries.

**Interfaces:**
- Produces: one non-authoritative human summary from authoritative machine manifests.
- Produces: median/worst command and pass durations.
- Does not create hard performance thresholds until policy explicitly contains a baseline backed by evidence.

- [ ] **Step 1: Write summary tests.**

```python
class ReliabilitySummaryTests(unittest.TestCase):
    def test_required_gate_failure_blocks_summary(self) -> None:
        result = summarize([
            {"role": "fast", "required": True, "status": "passed"},
            {"role": "deep", "required": True, "status": "failed"},
            {"role": "scheduled", "required": False, "status": "failed"},
        ])
        self.assertEqual(result.decision, "blocked")

    def test_scheduled_failure_is_advisory_by_default(self) -> None:
        result = summarize([
            {"role": "fast", "required": True, "status": "passed"},
            {"role": "deep", "required": True, "status": "passed"},
            {"role": "specialist", "required": True, "status": "passed"},
            {"role": "scheduled", "required": False, "status": "failed"},
        ])
        self.assertEqual(result.decision, "verified-with-advisory")
```

- [ ] **Step 2: Implement summary aggregation.**

Do not infer missing evidence as pass. Missing required manifest = `blocked`. Unknown status = `blocked`. Scheduled/advisory failure cannot upgrade or downgrade an already failed required gate; it appears in advisories.

- [ ] **Step 3: Calculate observational timing statistics.**

For every manifest, aggregate command durations and pass durations; report median and maximum. The output may flag `observation: slower-than-recent-median` only if at least 10 prior evidence samples are explicitly supplied. No hard failure threshold is added in this task.

- [ ] **Step 4: Add policy field proving performance is observational.**

```json
"performance": {
  "mode": "observational",
  "minimum_samples_before_threshold": 10
}
```

- [ ] **Step 5: Run tests.**

```bash
python -m unittest tests.test_reliability_summary -v
```

Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add reliability-policy.json scripts/ci/summarize_reliability.py tests/test_reliability_summary.py
git commit -m "feat: summarize layered reliability evidence"
```

---

### Task 11: Full verification, rollout, and removal of duplicated checks

**Files:**
- Modify only files justified by verification evidence.
- Update: `README.md`
- Update: `ROADMAP.md`
- Update: `docs/superpowers/specs/2026-08-07-layered-reliability-assurance-design.md` only if implementation reveals a factual clarification; architecture changes require user review rather than silent spec edits.

**Interfaces:**
- Consumes: all policy, evidence, deep, specialist, and scheduled components.
- Produces: exact-head evidence that the layered architecture is operating as designed.

- [ ] **Step 1: Run the complete local provider-free test suite.**

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/ci/verify_ci_policy.py
```

Expected: PASS.

- [ ] **Step 2: Run the Fast Gate on Python 3.10–3.13.**

Expected: all supported Python jobs pass; policy/workflow structure passes; wheel smoke passes; privacy/security static checks pass.

- [ ] **Step 3: Run the Deep Gate 15/15 on Python 3.10 and 3.13.**

Expected for each Python version:

```text
15 completed passes
15 distinct policy hash seeds
editable/wheel parity true
cross-pass deterministic outputs equal under their policy class
no provider execution
manifest.json schema-valid
scanner passed
```

- [ ] **Step 4: Run every Specialist Gate.**

Expected:

```text
reproducible-build: passed
explicit-determinism: passed
clean-room: passed
concurrency-isolation: passed
diagnostic-security: passed
```

- [ ] **Step 5: Run Scheduled Gate manually once before enabling the cron result as maintenance evidence.**

Expected: evidence produced even if latest-compatible dependency drift discovers an incompatibility. Such an incompatibility is classified `DEPENDENCY` and advisory unless it exposes a present release/safety defect.

- [ ] **Step 6: Inspect evidence bundles, not just statuses.**

For each required job verify:

```text
manifest.json exists and is schema-valid
summary.json exists
summary.md exists
events.jsonl is parseable line-by-line
commit SHA matches reviewed head
failure list is empty on green runs
dependency fingerprint exists where required
output digests exist where required
no workspace absolute path or secret-like material is present
artifact retention is within policy
```

- [ ] **Step 7: Remove duplicated verification only where equivalence is proven.**

Before deleting any old command from a workflow, add a test mapping the old control to the specialist/deep replacement. Example:

```python
def test_supply_chain_verifier_remains_required(self) -> None:
    policy = load_policy(Path("reliability-policy.json"))
    required = policy.raw["required_verifiers"]
    self.assertIn("verify_supply_chain.py", required)
```

If there is no proven equivalent, keep the old check.

- [ ] **Step 8: Update README/ROADMAP with operational interpretation.**

Document exactly:

```text
Fast = rapid merge feedback
Deep = Approach A repeated/adversarial assurance
Specialist = Approach B narrow verification
Scheduled = ecosystem drift/advisory
Policy + evidence = Approach C governing system
```

Explicitly state that these checks do not prove provider deletion, production deployment health, or absence of all flakes.

- [ ] **Step 9: Final scope/security review.**

Search the final diff for credentials, personal data, historical Vercel URLs, broad permissions, `persist-credentials: true`, unpinned external actions, `TODO`, `TBD`, unexplained normalization, and new provider calls. Any match must be resolved or explicitly demonstrated as a harmless fixture before merge.

- [ ] **Step 10: Merge in staged PRs, not one giant unreviewable change.**

Recommended PR boundaries:

```text
PR A: reconcile #83 + policy/evidence foundation + policy-driven Deep Gate
PR B: determinism + reproducible-build + clean-room + concurrency specialists
PR C: diagnostic scanner + structural CI policy enforcement
PR D: Fast/Specialist/Scheduled workflow separation + summary/telemetry + docs
```

Each PR must have its own green current-head checks before merge. Do not use a later PR's checks to justify an earlier unverified head.

---

## Spec Coverage Self-Review

- Policy before implementation: Tasks 2, 4, 8, 9.
- Evidence before claims: Tasks 3, 7, 10, 11.
- Isolation by default: Tasks 4, 6.
- Determinism where promised: Task 5.
- Variation where useful: Tasks 4, 5, 6, 9.
- Minimum privilege: Tasks 7, 8, 9, 11.
- Fast feedback plus deep assurance: Task 9.
- No silent weakening: Task 8.
- Actionable failure bundles: Tasks 3, 4, 7.
- No false precision/performance telemetry: Task 10.
- Central reliability policy: Task 2.
- Fast/Deep/Specialist/Scheduled architecture: Tasks 4 and 9.
- Reproducible packaging: Task 5.
- Dependency/toolchain fingerprints: Task 4 and scheduled Task 9.
- Cache/cold clean state: Tasks 6 and 9.
- Concurrency/state leakage: Task 6.
- Security/privacy diagnostics: Task 7.
- Structural workflow validation without YAML 1.1 corruption: Task 8.
- Merge decision contract: Task 10 and Task 11.
- Incremental rollout and no premature deletion of existing checks: Task 11.
- No provider/live/deployment/privacy overclaim: Global Constraints and Task 11.

## Placeholder / Ambiguity Self-Review

- No `TBD`, `TODO`, or implementation placeholders are intentionally present.
- The only allowed normalization is explicitly policy-listed and test-backed.
- Scheduled checks are advisory by default and cannot silently become merge blockers.
- PR #83 is reused as the Approach A foundation; it is not assumed merged until current-head verification succeeds.
- Specialist tools share the common evidence schema rather than inventing per-workflow formats.
- Python 3.10–3.13 support and 3.10/3.13 deep repetition are explicit.
- Provider execution remains prohibited throughout this plan.
