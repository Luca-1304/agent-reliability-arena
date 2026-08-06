# Reliability Gate v2 — Design

## Purpose

Replace the monolithic fifteen-pass shell loop with a repository-owned, testable reliability gate that proves more than command success. The gate must establish repeatability across controlled hash-order variation, equivalence between editable and wheel installations, traceable failure evidence, and a hardened GitHub Actions execution boundary.

## Problem statement

The existing workflow improves visibility but remains below the repository's intended standard in five ways:

1. The orchestration logic lives almost entirely in YAML and shell, making it difficult to unit-test or reuse locally.
2. A pass is considered successful when every command exits zero, even if editable and packaged installations produce different semantic outputs.
3. Pass-to-pass determinism is inferred rather than proven. Different `PYTHONHASHSEED` values are exercised, but their outputs are not compared.
4. Diagnostics are primarily free-form logs. They do not provide a stable machine-readable event stream, phase durations, output digests, or a failure classification.
5. External actions are referenced by mutable major-version tags instead of immutable full-length commit SHAs.

## Design principles

- **Repository-owned logic:** GitHub Actions should prepare the environment and invoke one version-controlled Python entry point. The workflow must not contain the business logic of the gate.
- **No runtime dependencies:** The gate runner must use only the Python standard library so it can execute before the package under test is trusted.
- **Fail closed:** Missing evidence, malformed JSON, parity drift, determinism drift, or an incomplete pass is a gate failure.
- **Evidence before summary:** Every command start and finish is recorded before the final human-readable summary is generated.
- **Controlled variation:** Hash-order variation is deliberate and recorded; timezone, locale, source epoch, home directory, and cache directories are controlled per pass.
- **Package parity:** The editable installation and the built wheel must execute the same public CLI surfaces and produce semantically equivalent JSON and artifact trees.
- **Local/CI parity:** The same runner and arguments must work locally and in GitHub Actions.
- **Minimal privilege:** The workflow receives only `contents: read` and external actions are pinned to immutable SHAs.

## Architecture

### 1. Workflow adapter

`.github/workflows/fifteen-pass-verification.yml` becomes a thin adapter responsible for:

- checking out the exact revision;
- selecting Python 3.10 and 3.13;
- installing a hash-locked CI toolchain;
- installing the repository in editable mode;
- invoking `scripts/ci/reliability_gate.py` for 15 passes;
- publishing the generated job summary;
- uploading diagnostics even after failure.

The workflow must trigger for all reliability-relevant source, test, workflow, package, documentation, security, release, and fixture surfaces. It must also include the runner, its tests, and the CI requirements lock in the path filter.

### 2. Reliability runner

`scripts/ci/reliability_gate.py` owns orchestration. Its public interface is:

```text
python scripts/ci/reliability_gate.py \
  --passes 15 \
  --python-label 3.13 \
  --workspace "$GITHUB_WORKSPACE" \
  --work-root "$RUNNER_TEMP/reliability-work" \
  --diagnostics-dir "$RUNNER_TEMP/reliability-diagnostics"
```

The runner creates a fresh pass workspace and wheel virtual environment for each pass. It executes the complete editable and wheel verification surfaces, records every command, compares results, then cleans the disposable virtual environment.

### 3. Evidence model

The diagnostics directory contains:

- `run.json` — immutable run metadata and requested policy;
- `environment.json` — interpreter, platform, selected environment variables, Git revision, and CI identity;
- `events.jsonl` — append-only command and comparison events;
- `summary.json` — final status, counts, timings, baseline digests, and failure classification;
- `summary.md` — human-readable GitHub step summary;
- `failure.json` — exact failing phase, command, pass, seed, exit code, and log path when the gate fails;
- `passes/NN/pass.json` — pass-level result and timings;
- `passes/NN/commands/*.log` — stdout and stderr for every command;
- `passes/NN/outputs/*.json` — captured public CLI outputs;
- `passes/NN/manifests/*.json` — semantic digests and tree manifests.

All JSON is emitted with sorted keys and UTF-8 encoding. Every event includes a UTC timestamp, pass number when applicable, Python label, event type, and status.

### 4. Verification phases

Each pass contains these phases:

1. **Environment isolation** — create pass-specific `HOME`, `TMPDIR`, and cache directories and set deterministic environment values.
2. **Source integrity** — compile `src`, `tests`, and `scripts` and run the complete unit-test suite against the editable installation.
3. **Repository verifiers** — run all release, disclosure, repeated-run, showcase, launch, citation, and supply-chain verification scripts.
4. **Editable CLI contract** — run every public fixture-safe CLI surface and capture its JSON output.
5. **Wheel build and install** — build one wheel without dependencies, create a fresh virtual environment, install the exact wheel, and record its SHA-256 digest.
6. **Wheel test contract** — run the complete tests and repository verifiers using the wheel interpreter.
7. **Wheel CLI contract** — run the same public CLI surfaces from the wheel environment.
8. **Package parity** — compare editable and wheel JSON outputs semantically and compare their generated artifact trees using canonical manifests.
9. **Cross-pass determinism** — compare the current pass's canonical digests with pass one. Any drift is a failure even when all commands exit zero.
10. **Dependency integrity** — run `pip check` in both environments.

### 5. Canonical comparison

JSON files are parsed and re-serialized with sorted keys, compact separators, and UTF-8 before hashing. Non-JSON files are hashed as raw bytes. Tree manifests map normalized relative paths to `{kind, sha256, size}` records. Directory order and JSON formatting cannot create false drift, while semantic JSON changes do.

The parity set includes:

- run command JSON;
- replay JSON;
- public web export JSON;
- showcase verification JSON;
- launch-package verification JSON;
- citation-package verification JSON;
- supply-chain verification JSON;
- generated editable and wheel artifact trees.

### 6. Failure taxonomy

Failures are classified as one of:

- `environment`
- `compile`
- `editable-tests`
- `repository-verifier`
- `editable-cli`
- `wheel-build`
- `wheel-install`
- `wheel-tests`
- `wheel-verifier`
- `wheel-cli`
- `package-parity`
- `cross-pass-determinism`
- `dependency-integrity`
- `internal-gate-error`

A failure record must include the phase, command name, exact argv, exit code, pass number, hash seed, elapsed time, and relative log path. No catch-all success message may overwrite a prior failure.

## Supply-chain controls

- `actions/checkout`, `actions/setup-python`, and `actions/upload-artifact` are pinned to full-length commit SHAs with release comments.
- The CI packaging tools are installed from `requirements/ci-tools.txt` using exact versions and SHA-256 hashes.
- The workflow token remains read-only.
- Checkout credentials are not persisted.
- Artifact upload occurs under `if: always()` and fails when the diagnostics directory is absent.
- The artifact name includes Python version and workflow attempt to prevent collisions.

## Repository enforcement

`tests/test_reliability_gate.py` tests canonicalization, tree manifests, deterministic environment construction, failure records, and drift detection using temporary directories and harmless Python subprocesses.

`tests/test_fifteen_pass_workflow_resilience.py` enforces that:

- the workflow invokes the repository runner;
- external actions are pinned to 40-character SHAs;
- the CI toolchain is installed with `--require-hashes`;
- diagnostics are uploaded on failure;
- the new runner, tests, and lock file trigger the workflow;
- the gate still runs 15 passes on Python 3.10 and 3.13.

These tests make removal of the reliability controls an ordinary test failure rather than an undocumented workflow regression.

## Scope boundaries

This change does not:

- enable live provider calls;
- change package behaviour or public claims;
- modify Vercel, deployment, privacy, or release status;
- add runtime package dependencies;
- publish artifacts externally;
- change the production NASA project.

## Acceptance criteria

The design is complete when all of the following are true:

1. Contract tests fail against the pre-v2 workflow and absent runner.
2. Unit tests for the runner pass on Python 3.10 through 3.13.
3. The full gate passes 15/15 on Python 3.10 and 15/15 on Python 3.13.
4. Each pass proves editable/wheel semantic parity.
5. Passes 2–15 prove equality with pass-one baseline digests.
6. Diagnostics contain machine-readable run, environment, event, pass, summary, and failure records.
7. All third-party actions are immutable SHA references.
8. CI tools are version- and hash-locked.
9. CodeQL, history protection, privacy packaging, repository health, and existing test workflows remain green.
10. The final PR contains no package behaviour, provider, deployment, or privacy-scope change.
