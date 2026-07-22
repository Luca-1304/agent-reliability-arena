# Disclosure-Safe Public Showcase Release Design

## Goal

Turn the existing public repository and deterministic trace viewer into a credible employer-, collaborator- and research-facing showcase without exposing private operational assets or overstating the evidence.

## Chosen approach

Use the repository itself as the first publication surface. Extend the existing `web/` trace viewer into the landing page, add concise public supporting documents, and define an explicit machine-verifiable showcase inventory. Do not introduce a third-party hosting, analytics, form, tracker, provider call or live execution path.

This approach is preferred over a separate new website because it keeps the showcase reproducible, versioned, reviewable and tied to the exact source commit. It is preferred over publishing only a release note because the interactive trace viewer already demonstrates the core distinction between model claims and independently observed evidence.

## Public package

The exact publication package contains:

- `web/index.html`, `web/styles.css`, `web/app.js` and the existing disclosure-safe fixture data;
- `showcase/publication-manifest.json` describing the version, evidence class, allowed files, claims boundary and source commit placeholder;
- `docs/EMPLOYER_TECHNICAL_SUMMARY.md` explaining the engineering problem, architecture, verified capabilities and limitations;
- `docs/SHOWCASE_DEMO_SCRIPT.md` providing a 60–120 second demonstration script;
- `docs/PUBLICATION_BOUNDARY.md` defining public, private and prohibited material;
- `scripts/verify_showcase_release.py` and `tests/test_showcase_release.py`.

The existing repository documentation remains available, but only the files named by the publication manifest are treated as the compact showcase release bundle.

## Landing-page changes

The existing page keeps the trace explorer and fixture metrics. It gains:

1. a concise “What this proves” section;
2. a system architecture section showing the controlled data flow;
3. a “Built and verified” section covering provider-free live boundaries, private evidence, repeated experiments and disclosure tooling;
4. prominent links to the repository, technical summary, reproduction instructions and claims boundary;
5. authorship and transparent AI-assistance attribution;
6. an explicit statement that no real-provider benchmark or spend has occurred.

No private prompts, raw provider payloads, internal logs, enabled policies, budgets or operational playbooks are embedded.

## Publication manifest

`showcase/publication-manifest.json` is an explicit allow-list. It records:

- schema and showcase version;
- evidence class: `deterministic_and_provider_free_showcase`;
- project and author names;
- allowed public files;
- public metrics and their source classification;
- prohibited content categories;
- claims boundary;
- `comparative_claim_permitted: false`;
- `provider_called: false`;
- a canonical manifest digest.

The manifest does not contain secrets, private source paths or a mutable live policy.

## Verification

The verifier must fail closed when:

- a required showcase file is absent;
- the manifest shape or digest differs;
- an allowed file escapes the repository root or is a symlink;
- an allowed file contains credential-shaped material, local absolute paths, private-evidence paths, raw-provider identifiers, internal-note markers or enabled live-policy markers;
- the landing page omits its evidence classification, limitations or authorship statement;
- fixture metrics differ from the committed public reference data;
- the package claims a real benchmark, representative performance, universal superiority, production safety or measured cost efficiency;
- the publication inventory includes a private or prohibited path.

The scan uses both exact prohibited markers and conservative regular expressions. False positives are resolved by rewriting public copy, not by silently weakening the scanner.

## CI and release proof

The showcase verifier runs in editable and clean-wheel CI beside the existing release, disclosure and repeated-experiment verifiers. The source tests verify positive construction and adversarial rejection cases.

A merge is publication into the already-public repository. A separate GitHub Release, Pages deployment or third-party announcement may follow only from the exact verified bundle and must record its URL, source commit, date and limitations.

## Claims boundary

The showcase may demonstrate engineering discipline, deterministic fairness controls, fail-closed parsing, independent verification, tamper-evident evidence, provider-free orchestration, guarded live boundaries, repeated-experiment infrastructure and disclosure safety.

It must not claim representative hosted-model performance, universal specialist superiority, real-world cost efficiency, arbitrary-tool safety, unattended production readiness or successful paid-provider execution.