# Independent Published Release Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the public `v0.2.0rc2` release as an external consumer, install only its downloaded wheel, reproduce the deterministic fixture, and fail closed on record-schema, artifact, checksum, attestation or output drift.

**Architecture:** A standard-library verifier consumes an already-downloaded release directory plus GitHub release metadata and derives the expected release-record schema from the checked-in rc2 contract instead of hard-coding the retired v1 schema. A thin CLI validates the release, key reproduced outputs and attestation counts. A read-only GitHub Actions workflow performs the network download and online attestation checks, installs the public wheel into a fresh virtual environment, reproduces the locked fixture, and emits a machine-readable verification record.

**Tech Stack:** Python 3.10–3.13 standard library, JSON, SHA-256, GitHub CLI, GitHub Actions.

## Global Constraints

- Verification starts from public release assets, never local `dist/` output.
- The repository checkout is used only for verifier code, locked fixture input and expected reference bytes.
- The downloaded wheel is installed with `--no-deps` in a fresh virtual environment.
- Workflow permissions remain read-only: `contents: read` and `attestations: read` only.
- `provider_called` remains `false`; `comparative_claim_permitted` remains `false`.
- No real-provider request, paid action, private evidence, credential, local absolute path or ACE internal is included.
- Claims remain limited to identity and deterministic reproduction of this one published release.

---

### Task 1: Reproduce and lock the release-record schema bug

**Files:**
- Create: `tests/test_published_release.py`
- Create: `src/agent_reliability_arena/published_release.py`

**Interfaces:**
- Produces: `verify_downloaded_release(root: Path, release_dir: Path, metadata_path: Path) -> dict[str, object]`
- Produces: `PublishedReleaseError`

- [ ] Write a failing test that builds a synthetic rc2 release directory with `arena-github-prerelease-record-v2` and expects validation to succeed.
- [ ] Write a failing test proving an extra asset, checksum tamper and retired v1 record schema are rejected.
- [ ] Run `python -m unittest tests.test_published_release -v` and confirm failure because `published_release` does not exist.
- [ ] Implement strict path confinement, version-derived record-schema validation, exact asset inventory and SHA-256 verification.
- [ ] Run the focused test and full source suite.
- [ ] Commit the green release validator.

### Task 2: Verify deterministic external reproduction

**Files:**
- Modify: `tests/test_published_release.py`
- Modify: `src/agent_reliability_arena/published_release.py`

**Interfaces:**
- Produces: `verify_reproduced_fixture(reference_root: Path, reproduced_root: Path, public_output: Path) -> dict[str, object]`

- [ ] Add failing tests for byte-equal `aggregate_metrics.json`, `paired_results.jsonl` and `report.md` plus required public-output metrics.
- [ ] Add a failing mismatch case that mutates one reproduced byte.
- [ ] Implement the minimal byte comparison and JSON metric checks.
- [ ] Run focused tests and the full suite.
- [ ] Commit the reproduction verifier.

### Task 3: Add the consumer command and verification record

**Files:**
- Create: `src/agent_reliability_arena/cli_published_release.py`
- Create: `scripts/verify_published_release.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_published_release.py`

**Interfaces:**
- Produces: installed command `arena-verify-published-release`.
- Consumes: downloaded release directory, release metadata, reproduced fixture directory, public output and attestation counts.
- Produces: JSON record schema `arena-published-release-verification-v1`.

- [ ] Add failing CLI tests for success, missing arguments and non-two attestation counts.
- [ ] Implement the thin CLI around the two verifier functions.
- [ ] Add the project script entry point.
- [ ] Run focused tests, installed-command smoke checks and the full suite.
- [ ] Commit the command.

### Task 4: Add the permanent clean-room workflow

**Files:**
- Create: `.github/workflows/verify-published-release.yml`
- Modify: `tests/test_published_release.py`

**Interfaces:**
- Downloads: public `v0.2.0rc2` assets with `gh release download`.
- Verifies: release metadata, all checksums, two provenance attestations and two CycloneDX attestations.
- Installs: downloaded wheel only into a fresh virtual environment with `--no-deps`.
- Reproduces: `examples/fixture_experiment.json` and compares locked outputs.

- [ ] Add failing workflow-contract tests for triggers, read-only permissions, exact release tag, online attestations, clean wheel install and fixture reproduction.
- [ ] Implement manual, weekly and verifier-path pull-request triggers.
- [ ] Make every boundary fail closed; upload only the disclosure-safe verification record and logs.
- [ ] Run the workflow on the pull request and confirm external verification succeeds.
- [ ] Commit the permanent workflow.

### Task 5: Document and integrate the verifier

**Files:**
- Create: `docs/VERIFY_PUBLISHED_RELEASE.md`
- Modify: `.github/workflows/tests.yml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_published_release.py`

**Interfaces:**
- Produces: concise public verification guide and permanent source/clean-wheel command checks.

- [ ] Add failing tests for required guide headings, commands and claims boundary.
- [ ] Write the public guide without exposing private machinery.
- [ ] Add the verifier script and installed command to editable and clean-wheel CI smoke stages using synthetic local fixtures only; keep online release checks in the dedicated workflow.
- [ ] Update README and changelog with the exact evidence boundary.
- [ ] Run Python 3.10–3.13, CodeQL, release-bundle and clean-room workflow gates on the exact final head.
- [ ] Merge only the unchanged green head and close issue #46 with exact evidence.