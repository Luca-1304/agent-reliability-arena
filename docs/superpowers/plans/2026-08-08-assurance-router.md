# Assurance Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, dependency-free `arena-assurance-route` command that classifies changed repository paths into assurance surfaces, recommends evidence, exposes coverage gaps, and never performs network/provider/deployment mutations.

**Architecture:** Keep the classifier pure in `assurance_router.py`; it receives repository-relative paths plus the existing reliability trigger patterns and returns an immutable deterministic report. Keep filesystem/Git access in `cli_assurance.py`; the CLI obtains paths explicitly, loads `reliability-policy.json`, calls the engine, and renders either canonical JSON or a concise human summary. Existing CI remains authoritative; Router output is advisory and `authoritative=false`.

**Tech Stack:** Python >=3.10 standard library only, `unittest`, existing setuptools console-script packaging, existing GitHub Actions reliability stack.

## Global Constraints

- No network, model, provider, credential, Vercel, deployment, branch-protection, or production calls from the feature.
- No new runtime dependency.
- No scalar/fake risk score.
- Existing `reliability-policy.json` trigger surfaces remain authoritative for CI coverage.
- Unknown or outside-trigger paths remain visible and set `attention_required=true`.
- Successful classification exits `0` even when attention is required; malformed input/Git adapter failures exit `2`.
- Output ordering must be deterministic across Python 3.10–3.13.
- Existing required checks are never weakened, skipped, replaced, or auto-satisfied.

---

### Task 1: Pure classifier contract and red tests

**Files:**
- Create: `tests/test_assurance_router.py`
- Create after RED: `src/agent_reliability_arena/assurance_router.py`

**Interfaces:**
- Produces: `normalize_path(path: str) -> str`
- Produces: `classify_paths(paths: Sequence[str], trigger_patterns: Sequence[str]) -> AssuranceReport`
- Produces: `AssuranceReport.to_dict() -> dict[str, object]`
- Produces: `AssuranceReport.to_json() -> str`

- [ ] **Step 1: Write failing engine tests**

Cover the spec with direct behavior assertions, including:

```python
class AssuranceRouterTests(unittest.TestCase):
    def test_runtime_path_routes_reliability_evidence(self) -> None:
        report = classify_paths(["src/agent_reliability_arena/runner.py"], ["src/**"])
        self.assertEqual(report.touched_surfaces, ("runtime",))
        self.assertIn("reliability.required", report.evidence_ids)
        self.assertFalse(report.attention_required)

    def test_workflow_change_requires_attention(self) -> None:
        report = classify_paths([".github/workflows/reliability-fast.yml"], [".github/workflows/**"])
        self.assertIn("ci-policy", report.touched_surfaces)
        self.assertTrue(report.attention_required)

    def test_unknown_and_outside_trigger_path_fails_visible(self) -> None:
        report = classify_paths(["ops/new-surface.txt"], ["src/**"])
        self.assertEqual(report.unknown_paths, ("ops/new-surface.txt",))
        self.assertEqual(report.outside_reliability_trigger_surface, ("ops/new-surface.txt",))
        self.assertTrue(report.attention_required)

    def test_canonical_json_is_order_independent(self) -> None:
        left = classify_paths(["README.md", "src/a.py", "README.md"], ["README.md", "src/**"])
        right = classify_paths(["src/a.py", "README.md"], ["src/**", "README.md"])
        self.assertEqual(left.to_json(), right.to_json())
```

Also test: tests-only, privacy verifier, Pages/Vercel publication files, dependency metadata, release evidence, documentation, multi-surface matching, absolute paths, traversal, separator normalization, empty input, duplicate inputs, and `authoritative=false`.

- [ ] **Step 2: Run the engine tests and verify RED**

Run:

```bash
python -m unittest tests.test_assurance_router -v
```

Expected: failure because `agent_reliability_arena.assurance_router` does not exist.

- [ ] **Step 3: Implement the minimal pure engine**

Use immutable dataclasses and code-owned rules. Rule matching must use explicit deterministic semantics:

```python
@dataclass(frozen=True)
class AssuranceRule:
    rule_id: str
    prefix: str | None = None
    exact: tuple[str, ...] = ()
    contains: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""
```

Repository trigger matching is limited to the forms already used by `reliability-policy.json`: exact path or a suffix `/**`, implemented as exact-or-descendant prefix matching. Any unsupported trigger syntax must be reported as an observation rather than silently interpreted.

Initial stable evidence IDs:

```python
EVIDENCE = {
    "reliability.required",
    "tests.contract-review",
    "ci.structural-policy",
    "privacy.independent-verification",
    "publication.staged-verification",
    "publication.live-independent-verification",
    "supply-chain.clean-build",
    "supply-chain.verification",
    "release.claim-boundary-review",
    "docs.consistency-review",
    "manual.unknown-surface-review",
}
```

The report schema contains normalized paths, touched surfaces, per-path matches, evidence IDs, unknown paths, outside-trigger paths, observations, `attention_required`, and `authoritative=False`.

- [ ] **Step 4: Run engine tests and verify GREEN**

```bash
python -m unittest tests.test_assurance_router -v
```

Expected: all engine tests pass.

- [ ] **Step 5: Run existing unit tests before committing**

```bash
python -m unittest discover -s tests -v
```

Expected: existing suite plus new engine tests pass.

---

### Task 2: CLI adapter and Git-path acquisition

**Files:**
- Create: `tests/test_assurance_router_cli.py`
- Create after RED: `src/agent_reliability_arena/cli_assurance.py`

**Interfaces:**
- Consumes: `classify_paths(...)`
- Produces: `main(argv: Sequence[str] | None = None) -> int`
- Supports exactly one input mode: repeated `--path`, `--paths-file`, or `--base REF --head REF`.
- Loads trigger patterns from repository-root `reliability-policy.json` by default.

- [ ] **Step 1: Write failing CLI tests**

Use real subprocesses for Git adapter behavior and direct `main()` calls for argument/output behavior. Minimum examples:

```python
def test_json_mode_emits_valid_non_authoritative_report(self) -> None:
    code = main(["--path", "src/a.py", "--json"])
    self.assertEqual(code, 0)
    payload = json.loads(stdout.getvalue())
    self.assertFalse(payload["authoritative"])


def test_git_failure_returns_input_error_without_success_report(self) -> None:
    code = main(["--base", "missing-ref", "--head", "HEAD", "--json"])
    self.assertEqual(code, 2)
    self.assertEqual(stdout.getvalue(), "")
```

Also test mixed input modes rejected, unreadable paths file rejected, malformed policy rejected, missing Git executable/failing diff mapped to exit `2`, and human mode includes surfaces/evidence/unknowns without claiming safety.

- [ ] **Step 2: Run CLI tests and verify RED**

```bash
python -m unittest tests.test_assurance_router_cli -v
```

Expected: failure because `cli_assurance` does not exist.

- [ ] **Step 3: Implement minimal CLI**

`argparse` contract:

```text
arena-assurance-route [--path PATH ... | --paths-file FILE | --base REF --head REF] [--policy FILE] [--json]
```

Rules:
- `--base` and `--head` are a pair.
- Git command is exactly `git diff --name-only --no-renames BASE HEAD --`.
- `subprocess.run(..., check=False, capture_output=True, text=True)` only; no shell.
- policy must be a JSON object containing a list of string `trigger_surfaces`.
- expected input/Git/policy failures print one concise stderr line and return `2`.
- JSON is emitted only after successful classification.

- [ ] **Step 4: Run CLI tests and verify GREEN**

```bash
python -m unittest tests.test_assurance_router_cli -v
```

- [ ] **Step 5: Re-run complete tests**

```bash
python -m unittest discover -s tests -v
```

---

### Task 3: Package entry point and installed-command proof

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_assurance_router_cli.py`

**Interfaces:**
- Produces installed command: `arena-assurance-route = "agent_reliability_arena.cli_assurance:main"`

- [ ] **Step 1: Add a failing installed-command test**

```python
def test_installed_command_runs_from_clean_editable_install(self) -> None:
    result = subprocess.run(
        ["arena-assurance-route", "--path", "README.md", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(json.loads(result.stdout)["schema_version"], "assurance-router-v1")
```

- [ ] **Step 2: Verify the command test is RED before editing `pyproject.toml`**

Expected: command not found / missing entry point.

- [ ] **Step 3: Add only the console-script line**

```toml
arena-assurance-route = "agent_reliability_arena.cli_assurance:main"
```

No dependency/version change.

- [ ] **Step 4: Reinstall editable package and verify GREEN**

```bash
python -m pip install -e .
python -m unittest tests.test_assurance_router_cli -v
```

- [ ] **Step 5: Run the complete unit suite**

```bash
python -m unittest discover -s tests -v
```

---

### Task 4: User documentation without expanding authority

**Files:**
- Modify: `README.md`
- Test: `tests/test_assurance_router.py`

**Interfaces:**
- Documents only behavior already proven by Tasks 1–3.

- [ ] **Step 1: Add a failing documentation-boundary test**

Test that README contains the command name, `advisory`, `authoritative`, and `unknown`, and does not describe the Router as a risk score or merge authority.

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_assurance_router.AssuranceRouterDocumentationTests -v
```

- [ ] **Step 3: Add concise README section**

Document:
- explicit input modes;
- example JSON command;
- surfaces/evidence/unknown-path behavior;
- `attention_required` meaning;
- no-network/provider/deployment boundary;
- existing CI remains authoritative.

- [ ] **Step 4: Verify GREEN and full suite**

```bash
python -m unittest tests.test_assurance_router.AssuranceRouterDocumentationTests -v
python -m unittest discover -s tests -v
```

---

### Task 5: Exact-head repository verification and PR

**Files:**
- No production code changes unless verification exposes a real defect.

**Interfaces:**
- Consumes the exact branch head produced by Tasks 1–4.
- Produces a reviewable PR only if local tests are green.

- [ ] **Step 1: Inspect final diff against `main`**

Confirm only the design, plan, engine, CLI, tests, `pyproject.toml`, and README changed. Confirm no workflow/provider/deployment/privacy-history file changed unexpectedly.

- [ ] **Step 2: Run local verification**

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
arena-assurance-route --path src/agent_reliability_arena/assurance_router.py --path .github/workflows/reliability-fast.yml --json
```

Expected Router result: valid `assurance-router-v1`, `authoritative=false`, runtime + CI-policy coverage, `attention_required=true` because a CI-policy surface is present.

- [ ] **Step 3: Open PR to `main`**

PR body must state that the Router is advisory, provider-free, and does not alter existing gates.

- [ ] **Step 4: Verify exact PR head using existing GitHub Actions**

Require applicable fresh evidence from normal tests, Fast, Specialist, Deep, CodeQL, public-site/privacy packaging, and writable-history checks. Scheduled ecosystem evidence is advisory and is not required for this PR.

- [ ] **Step 5: Do not merge on partial evidence**

If an applicable required check fails, diagnose the failure and fix through another RED/GREEN cycle. Merge only when the exact head has acceptable fresh evidence and the final diff still respects the design boundary.
