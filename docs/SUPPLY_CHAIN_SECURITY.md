# Supply-Chain Security and Hardening Review

## Scope and evidence boundary

This document describes the public software-supply-chain controls around Agent Reliability Arena. It is derived from the repository, the immutable `v0.2.0rc1` prerelease and the `v0.2.0rc2` release path, the vendored-verifier snapshot and the public evidence manifests.

It is **not an exhaustive security audit**, penetration test, formal verification result or guarantee that no vulnerability exists. No real-provider request, credential or private operational evidence is needed to reproduce these checks.

## Observed controls

The current public repository already provides several useful integrity boundaries:

- the Python package declares no runtime dependencies;
- the build backend and minimum build requirement are explicit in `pyproject.toml`;
- the vendored Agent Completion Verifier source is pinned by repository, version, source commit and per-file SHA-256 values;
- deterministic fixture artifacts and public publication packages are verified before release;
- the prerelease contains checksums and a source-commit release record;
- public evidence verifiers reject path escapes, symlinks, altered files and unsupported claims;
- external provider execution is disabled by default and remains outside public CI.

These controls reduce ambiguity and accidental drift. They do not prove that all source paths are free from vulnerabilities.

## Desired invariants

We want the following properties to remain falsifiable and reviewable:

1. Every declared runtime or build dependency is visible in one deterministic SBOM.
2. The vendored verifier identity and source commit cannot change without SBOM and manifest drift.
3. Public security files regenerate or verify without provider access, credentials or local machine state.
4. CI workflows use read-only repository access unless a narrowly scoped job requires more authority.
5. Code scanning results are treated as one signal, not a security certification.
6. Dependency-update automation opens reviewable pull requests and never bypasses the full test matrix.
7. Public documents never include private prompts, raw provider payloads, private ledgers, credentials, local paths or unpublished ACE operating material.

## Implemented hardening

### Deterministic CycloneDX SBOM

`security/sbom.cdx.json` is generated from public repository inputs using the Python standard library. It records:

- `agent-reliability-arena` version `0.2.0rc2`;
- vendored `agent-completion-verifier` version `0.6.0` and source commit;
- zero declared runtime dependencies;
- the relationship between the main project and the vendored verifier;
- the MIT licence and public repository identities.

The SBOM intentionally omits a generated timestamp so byte-for-byte regeneration is possible.

### Closed supply-chain manifest

`security/supply-chain-manifest.json` links the SBOM and security documents to the existing showcase, launch and citation provenance. The verifier rejects extra fields, changed file hashes, unknown components, dependency-count drift and unsupported claims.

### Continuous review

Dependabot checks both Python packaging metadata and GitHub Actions. CodeQL analyses Python on pull requests, pushes to `main` and a scheduled cadence. Both mechanisms produce review signals; neither is allowed to authorise a release or a comparative security claim by itself.

### Public reporting policy

`SECURITY.md` directs sensitive reports to GitHub private vulnerability reporting, discourages secret disclosure and explains the supported-version and coordinated-disclosure boundaries.

## Remaining limitations

- The repository has not undergone an exhaustive, multi-pass security scan in this workflow.
- CodeQL cannot prove the absence of logic, protocol, authorisation or operational vulnerabilities.
- A dependency-free runtime still relies on Python, the operating system, GitHub Actions, the build backend and release infrastructure.
- Existing `v0.2.0rc1` assets remain immutable and predate the SBOM package. The `v0.2.0rc2` release path publishes the SBOM and supply-chain manifest as first-class assets and generates GitHub provenance and SBOM attestations for the wheel and source distribution.
- GitHub-hosted actions are external dependencies. Dependabot reduces staleness, while full commit-SHA pinning remains a future hardening option that must preserve maintainability.
- Private real-provider evidence remains outside the public repository and requires separate local controls.

## Options considered

### Option 1 — Documentation only

Keep the current release checks and add a security policy. This has low maintenance cost, but dependency and component drift would remain difficult to detect. We rejected this as insufficient for a public technical showcase.

### Option 2 — Deterministic SBOM and verification gate

Add a closed component inventory, byte-reproducible SBOM, local verifier, Dependabot and CodeQL. This preserves the current standard-library runtime and gives reviewers concrete integrity checks. This is the implemented option.

### Option 3 — Fully attested release pipeline

Add GitHub artifact attestations and release the deterministic SBOM without rewriting `v0.2.0rc1`. The `v0.2.0rc2` pipeline implements this option with job-scoped signing permissions and online verification before publication.

## Recommendation

We should keep Option 2 as the repository baseline and use the rc2 implementation of Option 3 for downloadable release artifacts. Future hardening can pin third-party action revisions more strictly and move the builder into a reviewed reusable workflow if the maintenance tradeoff remains acceptable. Tactical findings from future CodeQL, dependency or manual reviews still require individual validation and fixes; architecture and automation do not close a vulnerability on their own.
