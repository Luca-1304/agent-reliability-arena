# Employer Review Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a five-minute, evidence-first employer route that exposes the repository's strongest engineering work without modifying locked showcase or release evidence.

**Architecture:** The change is documentation-first and test-enforced. One root employer guide becomes the review entry point; the README opening routes to it; ownership and project-status documents are made more precise; a standard-library unittest checks required sections, exact file links, current release metadata and prohibited claims.

**Tech Stack:** Markdown, Python 3.10–3.13 standard library `unittest`, existing GitHub Actions matrix.

## Global Constraints

- Current public release is exactly `v0.2.0rc2`.
- Evidence class is deterministic fixture plus provider-free integration evidence.
- No real-provider benchmark or provider spend has been executed.
- Do not modify `showcase/publication-manifest.json` or any of its seven locked files.
- Do not modify rc2 release assets, attestations, citation provenance or supply-chain hashes.
- Add no runtime dependency, package command or workflow.
- Keep AI-assisted implementation disclosure explicit.
- Prohibit claims of real-model performance, production readiness, universal superiority, unrestricted-tool safety, complete security or measured provider cost efficiency.
- Remove this plan and its design spec before merge.

---

### Task 1: Lock the employer-facing contract in tests

**Files:**
- Create: `tests/test_employer_review.py`

**Interfaces:**
- Consumes: repository Markdown and exact source/test paths.
- Produces: fail-closed employer-layer documentation contract.

- [ ] **Step 1: Write the failing test**

Create a `unittest.TestCase` that:

```python
ROOT = Path(__file__).resolve().parents[1]
EMPLOYER = ROOT / "EMPLOYER_REVIEW.md"

REQUIRED_HEADINGS = (
    "## 30-second summary",
    "## Verified evidence",
    "## What Luca owned",
    "## Review in five minutes",
    "## Code-review map",
    "## Technical decisions and trade-offs",
    "## Reproduce the public fixture",
    "## Role fit",
    "## What remains unproven",
)

REQUIRED_PATHS = (
    "src/agent_reliability_arena/live_orchestration.py",
    "src/agent_reliability_arena/private_pilot.py",
    "src/agent_reliability_arena/github_prerelease.py",
    "src/agent_reliability_arena/supply_chain.py",
    "tests/test_live_orchestration.py",
    "tests/test_private_pilot.py",
    "tests/test_github_prerelease.py",
    "tests/test_supply_chain_security.py",
    "reference_runs/fixture-v1/manifest.json",
    "web/index.html",
)
```

The test must assert:

- `EMPLOYER_REVIEW.md` exists and contains every heading;
- every required path exists and is linked literally from the employer guide;
- the guide contains `2/8`, `6/8`, `36 additional logical role calls`, `v0.2.0rc2`, `provider_called: false`, and `comparative_claim_permitted: false`;
- the first 90 README lines contain `EMPLOYER_REVIEW.md`, `v0.2.0rc2`, the tests/CodeQL/release badges, `deterministic fixture`, `provider-free integration`, and `No real-provider benchmark request or provider spend has been executed.`;
- `docs/CONTRIBUTION.md` contains `Problem framing and acceptance standard`, `Architecture and authority constraints`, `Review and defect correction`, and `AI-assisted implementation`;
- `docs/PROJECT_STATUS.md` contains `Last verified: 23 July 2026`, `published prerelease`, `attested`, and `Execution pending`;
- employer-facing files do not contain affirmative prohibited phrases: `real-model benchmark completed`, `production ready`, `universally superior`, `fully secure`, `guaranteed safe`, `measured provider cost efficiency`.

- [ ] **Step 2: Run the focused test to verify red**

Run:

```bash
python -m unittest tests.test_employer_review -v
```

Expected: failure because `EMPLOYER_REVIEW.md` does not exist and required first-contact markers are absent.

- [ ] **Step 3: Commit the red contract**

```bash
git add tests/test_employer_review.py
git commit -m "test: define employer review contract"
```

---

### Task 2: Create the five-minute employer route

**Files:**
- Create: `EMPLOYER_REVIEW.md`

**Interfaces:**
- Consumes: existing deterministic fixture, source modules, tests, release, technical report, citation and security documents.
- Produces: the single employer-facing review route linked by README.

- [ ] **Step 1: Write the employer guide**

Use these exact sections and evidence:

- `## 30-second summary`: controlled comparison of one general agent and one bounded specialist system under held-constant task, tools, sandbox, failure schedule and completion contract; independently observed completion is authoritative.
- `## Verified evidence`: deterministic fixture table with General `2/8`, Specialist `6/8`, false completion `3` versus `0`, logical calls `8` versus `44`; explicitly classify as software-validation evidence.
- `## What Luca owned`: problem identification, experiment question, acceptance standard, authority separation, claims/publication boundary, approval and review decisions, release approval and defect correction; state implementation/testing/documentation were AI-assisted.
- `## Review in five minutes`: numbered route through `web/index.html`, false-success scenario, technical report, selected source/tests, release and security evidence.
- `## Code-review map`: a table linking every `REQUIRED_PATHS` entry and explaining what a reviewer should inspect.
- `## Technical decisions and trade-offs`: table covering independent observation versus self-report, bounded specialists versus call overhead, deterministic fixture versus external validity, private evidence versus disclosure, and minimal dependencies versus convenience.
- `## Reproduce the public fixture`: exact editable install, `arena-run`, `arena-replay`, `arena-export-web`, and verifier commands.
- `## Role fit`: AI reliability/evaluation, agent systems, Python backend, test/release engineering, and AI assurance, each tied to repository evidence rather than generic adjectives.
- `## What remains unproven`: no real hosted/local model measurement, no paid pilot, no representative sample, no measured provider billing, no arbitrary-tool safety, no production readiness.
- finish with release, report, citation, security, SBOM and authorship links.

- [ ] **Step 2: Run focused tests**

Run:

```bash
python -m unittest tests.test_employer_review -v
```

Expected: employer file checks pass; README, contribution and project-status checks still fail.

- [ ] **Step 3: Commit the employer route**

```bash
git add EMPLOYER_REVIEW.md
git commit -m "docs: add evidence-first employer review route"
```

---

### Task 3: Improve README first contact

**Files:**
- Modify: `README.md` opening before `## Current evidence status`

**Interfaces:**
- Consumes: `EMPLOYER_REVIEW.md` and existing locked evidence links.
- Produces: concise recruiter/hiring-manager entrance while retaining the technical body unchanged.

- [ ] **Step 1: Replace the README opening**

Keep the title, project motto, research question and preview image. Add:

```markdown
[![tests](https://github.com/Luca-1304/agent-reliability-arena/actions/workflows/tests.yml/badge.svg)](https://github.com/Luca-1304/agent-reliability-arena/actions/workflows/tests.yml)
[![CodeQL](https://github.com/Luca-1304/agent-reliability-arena/actions/workflows/codeql.yml/badge.svg)](https://github.com/Luca-1304/agent-reliability-arena/actions/workflows/codeql.yml)
[![release](https://github.com/Luca-1304/agent-reliability-arena/actions/workflows/release.yml/badge.svg)](https://github.com/Luca-1304/agent-reliability-arena/actions/workflows/release.yml)
[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)
```

Then add:

```markdown
## Employer review

**Current release:** `v0.2.0rc2`  
**Evidence class:** deterministic fixture and provider-free integration  
**Review route:** [five-minute employer review](EMPLOYER_REVIEW.md)

This repository demonstrates controlled evaluation design, agent authority separation, independent completion verification, adversarial testing, reproducible packaging, supply-chain evidence and honest claims management.

| Public proof point | Verified result |
|---|---:|
| General independently verified outcomes | 2/8 |
| Specialist independently verified outcomes | 6/8 |
| False-completion claims removed | 3 |
| Additional logical role calls | 36 |

These are deterministic software-fixture results. **No real-provider benchmark request or provider spend has been executed.**

Start with the [employer review](EMPLOYER_REVIEW.md), [interactive trace viewer](web/index.html), [technical report](docs/TECHNICAL_REPORT.md), or [attested rc2 release](https://github.com/Luca-1304/agent-reliability-arena/releases/tag/v0.2.0rc2).
```

Do not remove or rewrite the detailed body beginning at `## Current evidence status`.

- [ ] **Step 2: Run focused tests**

Run:

```bash
python -m unittest tests.test_employer_review -v
```

Expected: README checks pass; contribution and project-status checks still fail.

- [ ] **Step 3: Commit README entrance**

```bash
git add README.md
git commit -m "docs: sharpen README employer entrance"
```

---

### Task 4: Make ownership and status precise

**Files:**
- Modify: `docs/CONTRIBUTION.md`
- Modify: `docs/PROJECT_STATUS.md`

**Interfaces:**
- Produces: transparent ownership record and current factual status.

- [ ] **Step 1: Expand contribution record**

Use these headings:

```markdown
## Problem framing and acceptance standard
## Architecture and authority constraints
## Review and defect correction
## AI-assisted implementation
## Evidence over authorship claims
## What the project does not claim
```

State concretely that Luca identified false completion as the practical failure mode, chose the held-constant orchestration question, required independent state observation, required bounded roles and explicit execution approvals, approved the publication boundary, rejected unsupported comparative claims, directed iterative reviews, and required discovered defects to be repaired and reverified. State that architecture, code, tests and documentation were AI-assisted and that repository evidence—not either party's assertion—determines correctness.

- [ ] **Step 2: Update project status**

Change the first line to:

```markdown
Last verified: 23 July 2026
```

After the current-state heading, state that `v0.2.0rc2` is a published prerelease with checksum-verified assets, SLSA provenance attestations and CycloneDX attestations. Retain `provider_called: false`, the existing proof/limitation lists and the issue #14 execution-pending boundary.

- [ ] **Step 3: Run focused and full source tests**

Run:

```bash
python -m unittest tests.test_employer_review -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit ownership and status**

```bash
git add docs/CONTRIBUTION.md docs/PROJECT_STATUS.md

git commit -m "docs: clarify ownership and current release status"
```

---

### Task 5: Remove process files and verify the exact public delta

**Files:**
- Delete: `docs/superpowers/specs/2026-07-23-employer-review-layer-design.md`
- Delete: `docs/superpowers/plans/2026-07-23-employer-review-layer.md`

**Interfaces:**
- Produces: final five-file employer layer plus one test, with no planning clutter.

- [ ] **Step 1: Delete temporary process files**

```bash
git rm docs/superpowers/specs/2026-07-23-employer-review-layer-design.md
git rm docs/superpowers/plans/2026-07-23-employer-review-layer.md
git commit -m "chore: remove completed employer-layer planning files"
```

- [ ] **Step 2: Verify changed-file scope**

Expected final changed files relative to branch base:

```text
EMPLOYER_REVIEW.md
README.md
docs/CONTRIBUTION.md
docs/PROJECT_STATUS.md
tests/test_employer_review.py
```

- [ ] **Step 3: Run exact final verification**

Run:

```bash
python -m compileall -q src tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verify_release.py
python scripts/verify_disclosure_release.py
python scripts/verify_repeated_release.py
python scripts/verify_showcase_release.py
python scripts/verify_launch_package.py
python scripts/verify_citation_package.py
python scripts/verify_supply_chain.py
```

Expected: zero failures. Then require the GitHub Python 3.10–3.13 matrix, clean-wheel checks, CodeQL and release rehearsal to pass on the exact unchanged PR head.

- [ ] **Step 4: Merge only the exact green head and close issue #50**

Record the final commit, workflow runs, five-file scope and claims boundary in the pull request and issue before merge.