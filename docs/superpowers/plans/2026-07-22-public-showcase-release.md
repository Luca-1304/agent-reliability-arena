# Public Showcase Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a disclosure-safe repository showcase whose exact files, metrics and claims are machine verified.

**Architecture:** The existing static `web/` trace viewer remains the interactive core. A canonical JSON manifest allow-lists the compact public package, while a standard-library verifier validates the manifest digest, required content, public fixture metrics, path confinement and prohibited-marker rules. CI runs the verifier from source and from the clean wheel.

**Tech Stack:** Python 3.10–3.13 standard library, static HTML/CSS/JavaScript, JSON, GitHub Actions.

## Global Constraints

- No external request, API key, analytics, tracker or third-party dependency.
- No complete private prompt, raw provider payload, private ledger, operator note, enabled policy, private budget or local machine path.
- Public fixture metrics must match the committed deterministic reference.
- `comparative_claim_permitted` remains `false`.
- No real-model benchmark, representative-performance, universal-superiority, production-safety or measured-cost claim.

---

### Task 1: Lock the publication contract

**Files:**
- Create: `tests/test_showcase_release.py`
- Create: `showcase/publication-manifest.json`
- Create: `src/agent_reliability_arena/showcase_release.py`

**Interfaces:**
- Produces: `load_showcase_manifest(root: Path) -> dict[str, object]`
- Produces: `verify_showcase_release(root: Path) -> dict[str, object]`

- [ ] Write failing tests for exact manifest schema, canonical digest, allowed-file confinement, required files, prohibited paths and known fixture metrics.
- [ ] Run the showcase test module and confirm import failure because `showcase_release` does not exist.
- [ ] Implement the minimal manifest loader and verifier.
- [ ] Run the showcase tests and full source suite.
- [ ] Commit the green contract.

### Task 2: Build the public documentation package

**Files:**
- Create: `docs/PUBLICATION_BOUNDARY.md`
- Create: `docs/EMPLOYER_TECHNICAL_SUMMARY.md`
- Create: `docs/SHOWCASE_DEMO_SCRIPT.md`
- Modify: `showcase/publication-manifest.json`
- Modify: `tests/test_showcase_release.py`

**Interfaces:**
- Consumes: exact allowed-file schema from Task 1.
- Produces: public prose with required evidence, attribution and limitation markers.

- [ ] Add failing tests for required headings and prohibited private material.
- [ ] Write the three concise documents.
- [ ] Add them to the manifest allow-list and recalculate its digest.
- [ ] Run the focused and full source suites.
- [ ] Commit the documentation package.

### Task 3: Upgrade the static landing page

**Files:**
- Modify: `web/index.html`
- Modify: `web/styles.css`
- Modify: `web/app.js`
- Modify: `tests/test_showcase_release.py`

**Interfaces:**
- Consumes: existing `web/data/fixture-v1.json`.
- Produces: an accessible landing page with trace explorer, proof, architecture, verified-build and authorship sections.

- [ ] Add failing tests for required landing-page IDs, claims markers, public links and authorship text.
- [ ] Add the new semantic HTML sections without changing the fixture trace data model.
- [ ] Add responsive styles and progressive enhancement only.
- [ ] Keep JavaScript data rendering fail-closed and add no network target beyond the local fixture JSON.
- [ ] Run source tests and commit.

### Task 4: Add the verifier command and adversarial cases

**Files:**
- Create: `scripts/verify_showcase_release.py`
- Modify: `tests/test_showcase_release.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: provider-free `arena-verify-showcase` command and JSON verification summary.

- [ ] Add failing subprocess tests for the script and installed command.
- [ ] Add adversarial temporary bundles for credential-shaped text, absolute paths, private-evidence paths, provider identifiers, internal notes, unsupported claims, symlinks and digest drift.
- [ ] Implement the thin CLI wrappers around `verify_showcase_release`.
- [ ] Run focused tests and full source suite.
- [ ] Commit the command and adversarial proof.

### Task 5: Make showcase proof permanent

**Files:**
- Modify: `.github/workflows/tests.yml`
- Modify: `scripts/verify_release.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `ROADMAP.md`
- Modify: `docs/PROJECT_STATUS.md`

**Interfaces:**
- Consumes: `arena-verify-showcase` and `scripts/verify_showcase_release.py`.
- Produces: editable and clean-wheel release evidence plus aligned public status.

- [ ] Add the showcase verifier to editable and clean-wheel workflow stages.
- [ ] Add the showcase bundle to the main release verifier summary.
- [ ] Update public documentation with the exact evidence class and claims boundary.
- [ ] Run the complete Python 3.10–3.13 matrix on the final unchanged head.
- [ ] Record the exact run and head SHA in the PR, merge only that head, and update issue #23 without claiming an external launch platform was used.