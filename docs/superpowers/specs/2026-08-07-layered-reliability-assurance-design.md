# Layered Reliability Assurance Design

Date: 2026-08-07
Status: Proposed design for user review
Repository: `Luca-1304/agent-reliability-arena`

## 1. Purpose

Upgrade the repository from a strong repeated-verification workflow into an above-standard reliability assurance system that is harder to bypass, easier to diagnose, and more resistant to environmental drift, packaging inconsistency, dependency changes, race conditions, stale CI policy, and opaque failures.

The design deliberately combines the strongest parts of all three considered approaches:

- **Approach A** becomes the hardened inner stress loop.
- **Approach B** becomes a set of specialist verification gates with narrow responsibilities.
- **Approach C** becomes the governing architecture: one central policy, one evidence model, one merge-decision contract, and clear separation between fast PR checks, deep reliability checks, and scheduled ecosystem checks.

This avoids two failure modes: a single giant workflow that becomes opaque, and many disconnected workflows that gradually disagree about what "safe to merge" means.

## 2. Design principles

1. **Policy before implementation.** Reliability requirements live in one machine-readable policy file and are consumed by workflows and tests.
2. **Evidence before claims.** A green status is not enough; each critical gate emits structured evidence explaining what was checked.
3. **Isolation by default.** Tests, builds, installs, runs, and replays operate in fresh directories or environments unless persistence is itself under test.
4. **Determinism where promised.** Outputs claimed to be deterministic are compared semantically across controlled environmental variation.
5. **Variation where useful.** Hash seeds, supported Python versions, install modes, cold/warm cache states, and selected process boundaries vary deliberately instead of repeating identical conditions.
6. **Minimum privilege.** Reliability jobs are read-only and do not receive deployment credentials or unnecessary secrets.
7. **Fast feedback plus deep assurance.** Normal pull requests receive rapid feedback; high-risk surfaces additionally trigger deep verification; ecosystem drift is tested separately on a schedule.
8. **No silent weakening.** Repository tests structurally validate workflow policy so later YAML edits cannot quietly remove required protection.
9. **Actionable failure bundles.** A failure must identify the failing class, environment, command, pass, seed, dependency fingerprint, timing, and relevant artifact paths.
10. **No false precision.** Performance or reproducibility requirements become hard failures only where evidence supports a stable threshold.

## 3. Architecture

### 3.1 Reliability Policy

Introduce a machine-readable reliability policy, proposed path:

`reliability-policy.json`

It defines the authoritative contract for:

- supported Python versions;
- deep-stress Python versions;
- minimum stress passes;
- required trigger surfaces;
- maximum workflow permissions;
- required checkout settings;
- required install modes;
- deterministic output classes;
- required verifiers and CLIs;
- artifact-retention bounds;
- diagnostic fields;
- timeout ceilings;
- cache-independence requirements;
- clean-room requirements;
- scheduled compatibility dimensions.

Workflow YAML, repository tests, and diagnostic tooling must consume or validate against this same policy rather than duplicating constants independently.

### 3.2 Fast Gate

Purpose: give fast, high-signal pull-request feedback.

Responsibilities:

- unit and integration tests;
- syntax/compile checks;
- policy-schema validation;
- CI-policy structural tests;
- package metadata validation;
- security/privacy static checks;
- minimal wheel build/install smoke test;
- required permission and checkout-authentication assertions.

The Fast Gate should finish quickly enough to remain useful during normal development.

### 3.3 Deep Reliability Gate

Purpose: challenge merge candidates under controlled variation and fresh-state execution.

Approach A lives here as the hardened inner stress engine.

Dimensions include:

- Python 3.10 and 3.13 initially for deepest repetition, while ordinary support remains 3.10-3.13;
- `PYTHONHASHSEED` rotation across at least 15 deterministic values;
- fixed timezone and locale;
- fresh per-pass run directories;
- fresh wheel environments;
- editable-install versus wheel-install execution;
- clean-room build/install path;
- cold-cache verification path;
- selected concurrent independent runs to detect state leakage;
- normalized output digest comparison for deterministic artifacts;
- package-content comparison across independently built wheels;
- command-level and pass-level timeout discipline.

A 15/15 exit-success result is necessary but not sufficient. The gate must also confirm any policy-designated deterministic outputs remain equivalent under the tested variations.

### 3.4 Specialist Gates

Approach B lives here. Each specialist gate has one clear responsibility and emits evidence in the common format.

Initial specialist gates:

1. **Packaging/Reproducibility**
   - independent builds from clean states;
   - normalized wheel-content comparison;
   - metadata and entry-point validation;
   - package manifest verification.

2. **Determinism**
   - semantic digest comparison for policy-designated outputs;
   - hash-order variance;
   - replay stability;
   - normalized diff on mismatch.

3. **Security/Privacy**
   - minimum permissions;
   - `persist-credentials: false`;
   - no deployment secrets in validation jobs;
   - generated-artifact secret/path/privacy scans;
   - existing CV/history/privacy protections remain independent.

4. **Clean-room Installation**
   - fresh environment;
   - no editable-install residue;
   - build, install, execute, replay, verify from the packaged artifact.

5. **Concurrency/Isolation**
   - two or more independent runs execute without output collision;
   - temporary directories cannot cross-contaminate;
   - cleanup leaves no state required by later passes.

6. **Release/Supply-chain**
   - existing signed/tamper-evident release verification;
   - policy-aware regeneration only when relevant protected inputs change;
   - source-to-artifact claim consistency.

### 3.5 Scheduled Ecosystem Gate

Purpose: detect external drift without making ordinary development depend on upstream churn.

Runs on a schedule and optionally manually.

Responsibilities:

- newer compatible dependency versions;
- newer build tooling;
- cold caches;
- broader environment combinations where useful;
- dependency-resolution fingerprinting;
- compatibility warnings before they become merge blockers.

Scheduled-gate failures do not automatically invalidate an already-reviewed commit unless they reveal a current safety/release defect. They create a clearly classified maintenance issue instead.

## 4. Evidence model

Introduce a common machine-readable diagnostic manifest per critical job, for example:

`diagnostics/manifest.json`

Required top-level fields:

- schema version;
- repository;
- commit SHA;
- workflow/run/attempt identifiers;
- event/ref;
- runner OS/architecture;
- Python version;
- timezone/locale;
- hash seed where applicable;
- install mode;
- toolchain versions;
- dependency fingerprint;
- cache mode;
- command ledger;
- timing records;
- output digests;
- failure records;
- final status.

Failure records use a controlled classification vocabulary:

- `TEST`
- `BUILD`
- `PACKAGE`
- `REPLAY`
- `DETERMINISM`
- `SECURITY`
- `DEPENDENCY`
- `ENVIRONMENT`
- `TIMEOUT`
- `CONCURRENCY`
- `POLICY`
- `UNKNOWN`

Each failure record includes the exact command, sequence number, pass number, environment identifiers, exit code, relevant artifact paths, and normalized diff when appropriate.

Human-readable summaries remain, but machine-readable evidence is authoritative for future automated comparison.

## 5. Determinism contract

Not every output must be byte-identical. The policy distinguishes three classes:

1. **Byte deterministic** — exact bytes must match.
2. **Semantically deterministic** — normalized structured content must match after permitted volatile fields are removed.
3. **Non-deterministic but bounded** — values may vary, but schema, safety properties, and defined invariants must hold.

The system must never silently normalize away new differences. Allowed volatile fields are explicit in policy and covered by tests.

When a semantic digest differs, the gate emits a normalized diff rather than only two hashes.

## 6. Reproducible packaging

At least two independent clean builds are produced for reproducibility analysis.

Verification compares:

- file list;
- normalized archive contents;
- package metadata;
- entry points;
- declared dependencies;
- version identity;
- protected manifest files.

Archive timestamps or known build metadata are normalized only where the packaging format makes byte equality inappropriate.

A wheel that passes tests but contains unexpected files, absolute paths, local build residue, or altered metadata fails packaging verification.

## 7. Dependency integrity and drift

Merge-critical verification records a deterministic dependency/toolchain fingerprint.

The design separates two concerns:

- **Merge reproducibility:** controlled toolchain/dependency bounds suitable for stable evidence.
- **Ecosystem compatibility:** scheduled tests deliberately exercise newer compatible tooling/dependencies.

This prevents a package released upstream on a random day from making a previously deterministic merge gate behave differently without explanation.

No dependency is pinned merely for the appearance of determinism; bounds must reflect actual project compatibility and maintenance needs.

## 8. Timeout and performance discipline

Replace reliance on only a broad six-hour job timeout with layered limits:

- command-level timeout for individual verifiers where practical;
- pass-level maximum duration;
- overall workflow ceiling;
- recorded duration for every command/pass;
- median and worst-case summaries.

Performance data begins as observational telemetry. Hard thresholds are introduced only after enough clean baseline runs exist to distinguish real regressions from runner noise.

A timeout is classified separately from a test assertion failure.

## 9. Cache and clean-state discipline

Use both:

- cached verification for development speed;
- explicit cold-cache verification for reliability assurance.

The cold path must not depend on prior wheel artifacts, generated outputs, editable-install residue, or runner-local project state.

Each deep pass owns its own run root and environment. Shared mutable state is prohibited unless a test is specifically verifying concurrency behaviour.

## 10. Concurrency and state-leak checks

Add a bounded concurrency test that launches independent arena executions against separate run roots.

Required assertions:

- no file collisions;
- no shared result mutation;
- replay uses the correct run only;
- cleanup of one run cannot damage another;
- output identities remain attributable to the correct invocation.

This is not a load test. It exists to expose shared temporary paths, globals, caches, or hidden process-level state.

## 11. Security and privacy controls

Reliability infrastructure must not become a new data-exposure surface.

Requirements:

- validation jobs use read-only repository permissions;
- checkout authentication is not persisted;
- deployment/provider secrets are not provided to stress jobs;
- diagnostics never dump the complete environment;
- only allow-listed environment fields are recorded;
- diagnostic artifacts are scanned for secret-like values, absolute user paths, private URLs, and prohibited personal data patterns;
- artifact retention remains bounded by policy;
- no reliability job publishes public artifacts unless an existing release workflow explicitly owns publication.

Existing historical-CV and provider-deletion safeguards remain separate blockers and are not declared solved by this architecture.

## 12. CI policy enforcement

Replace shallow string-presence assertions with structured workflow validation.

Tests parse workflow YAML and assert, at minimum:

- required triggers and path coverage;
- required supported/deep Python matrices;
- minimum stress-pass count;
- permission ceilings;
- checkout credential policy;
- timeout presence and ceilings;
- diagnostic upload on `always()`;
- retention limits;
- required specialist gates;
- deployment permissions absent from reliability jobs;
- policy-file schema validity;
- workflow-to-policy agreement.

Where GitHub expression syntax prevents safe use of a generic YAML parser, validation may use a small purpose-built structural parser or a parser configured to preserve GitHub's YAML semantics. The implementation must not silently reinterpret GitHub expressions as booleans or other YAML 1.1 values.

## 13. Trigger strategy

Three trigger classes:

### Fast
Runs on all relevant pull requests and `main` pushes.

### Deep
Runs when changes touch reliability-sensitive surfaces including source, tests, scripts, package metadata, release/supply-chain logic, security/privacy logic, public/export code, workflow/policy definitions, and any file explicitly listed by policy.

### Scheduled
Runs ecosystem-drift and wider-compatibility checks independently of code changes.

The reliability policy owns the surface list. Tests fail if workflow trigger coverage diverges from policy.

## 14. Merge decision contract

A merge candidate requiring deep assurance is considered verified only when:

- Fast Gate passes;
- Deep Reliability Gate passes;
- all required specialist gates pass;
- policy validation passes;
- required evidence manifests are produced and schema-valid;
- no privacy/security blocker is newly introduced.

Scheduled ecosystem checks are advisory unless policy explicitly promotes a detected defect to a merge/release blocker.

No single "15/15" label is allowed to stand in for the complete assurance decision.

## 15. Rollout strategy

Implement incrementally to avoid destabilising the repository.

### Phase 1 — Policy and evidence foundation

- add reliability policy and schema;
- add structural policy tests;
- introduce evidence-manifest schema and writer;
- preserve existing successful workflows while policy becomes observable.

### Phase 2 — Harden Approach A

- move current 15-pass logic behind reusable scripts instead of a monolithic shell body;
- add deterministic output classification/digests;
- add layered timeouts;
- add dependency/toolchain fingerprints;
- add clean per-pass isolation and normalized failure records.

### Phase 3 — Introduce Approach B specialist gates

- packaging/reproducibility;
- determinism;
- clean-room installation;
- concurrency/isolation;
- security/privacy diagnostics.

### Phase 4 — Scheduled ecosystem assurance

- dependency/toolchain drift;
- cold-cache scheduled verification;
- broader compatibility dimensions;
- maintenance issue generation only after evidence classification.

### Phase 5 — Consolidation

- remove duplicated checks only after equivalent specialist coverage is proven;
- document merge/release interpretation;
- review runtime/cost and adjust redundant repetition without lowering policy guarantees.

## 16. Testing strategy

Every implementation step uses test-first development.

Required categories:

- policy-schema tests;
- workflow structural tests;
- evidence-manifest schema tests;
- failure-classification tests;
- deterministic normalization tests;
- reproducible-build comparison tests;
- secret/path/privacy scanner tests;
- timeout/failure capture tests;
- concurrency isolation tests;
- clean-room package tests;
- regression tests for current 15-pass behaviour.

The system itself must be testable locally without making provider calls.

## 17. Error handling

Rules:

1. Fail closed when required evidence is absent.
2. Distinguish test failure from infrastructure/environment failure.
3. Preserve evidence on all failures via `always()` artifact handling.
4. Never convert a failed required specialist gate into a warning merely to keep CI green.
5. Scheduled compatibility failures may be advisory only when the policy explicitly says so.
6. Unknown failures remain `UNKNOWN`; they are not guessed into another category.
7. Diagnostic-generation failure is itself a reliability failure because it destroys post-failure observability.

## 18. Non-goals

This project does not attempt to:

- create a full benchmarking platform;
- guarantee absence of all flakes;
- run every Python/environment combination on every PR;
- perform paid or live provider execution;
- replace GitHub/Vercel provider-side privacy obligations;
- add deployment automation to reliability jobs;
- treat CI complexity as a proxy for quality.

## 19. Success criteria

The architecture is considered implemented only when all of the following are demonstrated on exact reviewed heads:

1. Policy is machine-readable and schema-valid.
2. Workflow structure is validated against policy.
3. Fast, deep, specialist, and scheduled responsibilities are clearly separated.
4. Existing 15-pass assurance survives and becomes environment-aware and self-diagnosing.
5. Deterministic outputs are compared by explicit deterministic class.
6. At least two clean builds are compared reproducibly.
7. Editable and packaged execution remain behaviourally consistent.
8. A cold-cache clean-room path passes.
9. Concurrency/isolation checks pass without shared-state leakage.
10. Dependency/toolchain fingerprints are recorded.
11. All critical failures emit machine-readable evidence.
12. Diagnostic artifacts pass secret/privacy/path scans.
13. Reliability jobs remain read-only and credential-minimal.
14. CI policy cannot be silently weakened without tests failing.
15. No release or privacy claim is strengthened solely because this reliability architecture exists.

## 20. Final architecture decision

Adopt **Approach C as the governing system**, explicitly embedding:

- **Approach A** as the hardened deep-stress engine; and
- **Approach B** as the specialist verification layer.

This hybrid is preferred because it captures the depth of A, the separation of concerns of B, and the long-term coherence of C without multiplying disconnected sources of truth.
