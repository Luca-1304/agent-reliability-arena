# Assurance Router design

Date: 8 August 2026
Status: approved design, implementation not started
Base: `main` at `207d6b806eea8b24fde87bd45241f18a1da52efc`

## Purpose

Build a deterministic, provider-free local change classifier that answers four questions for a proposed repository change:

1. Which assurance surfaces did the change touch?
2. Why does each touched surface matter?
3. What evidence should be collected before merge or release?
4. What remains unknown and therefore requires attention?

The Router is not a probability model and does not invent a numerical risk score. It is an evidence-routing tool.

## Non-goals

The first version must not:

- call an AI model or third-party service;
- upload repository content;
- read or require credentials;
- mutate Git, GitHub, Vercel, production, branch protection, or provider state;
- replace, weaken, skip, or auto-satisfy an existing required CI gate;
- infer that a change is safe merely because it was classified;
- claim calibrated defect probability, production reliability, or security assurance;
- inspect historical sensitive CV content.

## Inputs

The core engine accepts an ordered set of repository-relative changed paths. A thin CLI adapter may obtain those paths from one of these explicit sources:

- `--path PATH` repeated one or more times;
- `--paths-file FILE`, one repository-relative path per line;
- `--base REF --head REF`, resolved locally with `git diff --name-only`.

The core classifier must not shell out. Git invocation belongs only in the adapter so the classification logic is deterministic and directly testable.

Input rules:

- normalize separators to `/`;
- reject absolute paths;
- reject traversal such as `../`;
- deduplicate while preserving deterministic sorted output;
- an empty change set is valid and reports no touched surfaces plus an explicit observation;
- any syntactically valid path that matches no known rule is classified as `unknown`, never silently ignored.

## Assurance surfaces

Version 1 defines these surfaces:

### runtime

Examples: `src/**`, executable application code, runtime configuration.

Evidence intent: normal tests plus the existing reliability gates appropriate to the repository policy.

### tests

Examples: `tests/**`.

Evidence intent: test-suite execution and test-contract review. Test-only changes are not treated as inherently safe because tests can weaken assurance.

### ci-policy

Examples: `.github/workflows/**`, `reliability-policy.json`, CI policy parsers and CI evidence scripts.

Evidence intent: structural CI-policy verification, workflow security checks, role-summary evidence, and careful review for weakened requirements.

### security-privacy

Examples: `security/**`, privacy verifiers, history-boundary logic, public-CV verification, credential/diagnostic scanners.

Evidence intent: security/privacy-specific checks in addition to ordinary tests. A touched privacy verifier cannot self-certify its own safety merely by passing itself.

### deployment-publication

Examples: Pages staging/deployment logic, Vercel fail-closed configuration, public-site packaging, release publication logic.

Evidence intent: staging/package checks and, where applicable, independent live verification. The Router itself never deploys.

### dependency-supply-chain

Examples: `pyproject.toml`, `requirements/**`, lock/constraint files, supply-chain manifests, release dependency metadata.

Evidence intent: clean installation/build plus supply-chain verification. Dependency changes remain distinct from ordinary source changes.

### release-evidence

Examples: `release/**`, `citation/**`, `reference_runs/**`, public evidence/export manifests and release verification scripts.

Evidence intent: release/evidence verifiers and claim-boundary review.

### documentation

Examples: `docs/**`, `README.md`, `CHANGELOG.md`, `ROADMAP.md`.

Evidence intent: documentation consistency and any existing policy-triggered gates. Documentation is not automatically low consequence because it can define operational or merge policy.

### unknown

Any valid changed path not mapped above.

Evidence intent: manual attention. Unknown classification must be visible and advisory-fail-closed: it cannot produce a `clear` recommendation.

A path may map to more than one surface.

## Relationship to existing reliability policy

The Router must complement, not fork, `reliability-policy.json`.

- Existing `trigger_surfaces` remain authoritative for deciding whether layered reliability workflows should be triggered.
- The Router may add a more human-meaningful assurance classification over those paths.
- If a changed path lies outside `trigger_surfaces`, the Router must report that fact explicitly as `outside_reliability_trigger_surface` rather than pretending the change is covered.
- The Router must never advise removing an existing Fast, Specialist, Deep, CodeQL, Pages/privacy, history, or other independent required check.
- Scheduled ecosystem evidence remains advisory unless repository policy separately changes.

## Rule representation

Rules live in one versioned, reviewable data structure in the package, not scattered conditionals in the CLI.

Each rule has:

- stable rule ID;
- path pattern;
- one or more assurance surfaces;
- concise rationale;
- required/recommended evidence labels;
- optional observation flags.

Rules use deterministic repository-relative glob matching. No regex supplied by the user is executed.

The initial rule set is code-owned rather than externally configurable. This avoids creating a policy-injection surface before the semantics are stable. A future config format requires a separate design review.

## Output contract

The engine returns a machine-readable report with schema version `assurance-router-v1` containing at least:

- normalized changed paths;
- touched assurance surfaces;
- per-path matched rule IDs and surfaces;
- evidence recommendations, deduplicated and sorted;
- unknown paths;
- paths outside the existing reliability trigger surface;
- observations;
- `attention_required` boolean;
- `authoritative: false`.

`attention_required` is true when any of these apply:

- an unknown path exists;
- a path falls outside the current reliability trigger surface;
- a security/privacy, CI-policy, deployment/publication, or dependency/supply-chain surface is touched.

This boolean is deliberately not named `unsafe` or `blocked`: the Router identifies review/evidence needs; existing policy and CI decide merge eligibility.

The CLI supports:

- default human-readable Markdown-like terminal output;
- `--json` for canonical JSON to stdout.

Output ordering must be stable across runs and supported Python versions.

## Error handling

User/input errors return exit code `2` and a concise stderr message, including:

- invalid absolute/traversal path;
- unreadable paths file;
- malformed local Git invocation request;
- Git not available when `--base/--head` mode is requested;
- Git diff failure.

Successful classification returns `0`, including when attention is required. This keeps version 1 advisory and prevents the Router from accidentally becoming a new blocking gate without explicit policy approval.

Unexpected internal failures return a non-zero code and must not emit a misleading successful report.

## Package structure

Proposed implementation units:

- `src/agent_reliability_arena/assurance_router.py` — pure normalization, rule matching, report model and serialization;
- `src/agent_reliability_arena/cli_assurance.py` — argument parsing, optional local Git adapter, stdout/stderr contract;
- `tests/test_assurance_router.py` — pure engine contract tests;
- `tests/test_assurance_router_cli.py` — CLI and local Git-adapter tests;
- `pyproject.toml` — console entry point `arena-assurance-route` only after engine/CLI tests pass;
- documentation update only after behavior is verified.

No workflow change is required for the first implementation unless the existing trigger policy fails to run the normal reliability workflows for these files. If a workflow trigger change is required, that is a separate test-first policy change in the same PR and must not reduce coverage.

## Test-first acceptance cases

The first failing tests must establish behavior before implementation.

Minimum cases:

1. `src/...` maps to `runtime` and recommends normal reliability evidence.
2. `tests/...` maps to `tests` and does not describe a test-only change as safe.
3. `.github/workflows/...` maps to `ci-policy` and requires attention.
4. public CV/privacy verifier changes map to `security-privacy` and require attention.
5. Pages/Vercel publication files map to `deployment-publication` without performing a deployment.
6. dependency metadata maps to `dependency-supply-chain` and requires attention.
7. docs can map to `documentation` and, when relevant, additional operational surfaces.
8. one path may map to multiple surfaces.
9. unknown valid paths are preserved in `unknown_paths` and force `attention_required=true`.
10. paths outside existing reliability trigger surfaces are explicitly reported.
11. absolute and traversal paths fail closed.
12. duplicate and differently ordered inputs produce byte-stable canonical JSON.
13. empty input produces a valid deterministic report rather than an exception.
14. CLI `--json` output round-trips as valid JSON.
15. Git adapter errors do not produce a successful report.
16. no test or production path requires network access or credentials.

## Adversarial / adaptation review

Because classification rules can change contributor behavior, verification must include likely adaptations:

- intended adaptation: contributors use the report to collect the right evidence earlier;
- gaming adaptation: renaming or relocating files must not turn a consequential change invisible; unknown/outside-trigger paths therefore remain visible;
- strategic adaptation: test-only, docs-only, or policy-only changes must not receive a blanket low-risk label;
- equilibrium effect: if teams begin depending on the Router, it must remain explicitly non-authoritative until evidence supports a formal blocking role;
- failure signal: growth in unknown paths, repeated post-merge defects from supposedly covered surfaces, or mismatch with CI trigger behavior indicates the rule model needs revision.

## Verification and merge boundary

Implementation stays on `feature/assurance-router` until reviewed through a pull request.

Before merge, require fresh evidence from the existing repository machinery for the exact PR head. At minimum, the change must not bypass the existing Fast, Specialist, Deep, normal tests, CodeQL, public-site/privacy packaging, and writable-history boundaries when those workflows are applicable.

No merge is justified solely by Router output. No production or provider action is part of this feature.

## Future extension

A visual assurance dashboard may later consume the stable `assurance-router-v1` report. It is intentionally excluded from version 1 so presentation cannot drive or distort classifier semantics. The dashboard requires a separate design after the deterministic engine is proven.
