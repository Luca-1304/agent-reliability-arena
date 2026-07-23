# Launch and career conversion package design

Date: 2026-07-23
Status: approved by Luca's instruction to proceed

## Purpose

Turn the already verified Agent Reliability Arena showcase into reusable public-facing material for CVs, portfolios, recruiters, professional social posts and selective technical-community submissions.

The package must improve discoverability and conversion without altering the locked seven-file showcase proof or exposing private operational assets.

## Architecture

The package is a second, separate public layer:

1. **Evidence layer — unchanged**
   - `showcase/publication-manifest.json`
   - the seven byte-pinned showcase files;
   - `arena-verify-showcase`;
   - deterministic fixture metrics and the existing claims boundary.

2. **Conversion layer — new**
   - audience-specific CV, portfolio, recruiter, social and community copy;
   - deployment-readiness guidance;
   - a machine-readable distribution register;
   - a separate digest-pinned launch-package manifest;
   - `arena-verify-launch-package`.

The conversion layer may cite the evidence layer but may not modify or reinterpret it.

## Public files

- `LAUNCH.md` — repository-level entry point.
- `docs/CV_PROJECT_ENTRY.md` — short and expanded CV versions.
- `docs/PORTFOLIO_PROJECT_ENTRY.md` — portfolio presentation and technical highlights.
- `docs/RECRUITER_OUTREACH.md` — initial message and follow-up templates.
- `docs/LAUNCH_POSTS.md` — LinkedIn and short-form public launch copy.
- `docs/COMMUNITY_SUBMISSIONS.md` — neutral technical-community submission copy.
- `docs/HOSTED_DEPLOYMENT.md` — safe deployment path using only the verified `web/` bundle.
- `showcase/distribution-register.json` — target, state, public URL and claims-boundary record.
- `showcase/launch-package-manifest.json` — exact public allow-list and SHA-256 inventory.

## Verification rules

The verifier must fail closed when:

- the manifest schema or digest changes unexpectedly;
- a listed file is missing, changed, symlinked, private or escapes the repository;
- credentials, authentication material, local paths, raw provider identifiers, private evidence markers, enabled live-policy markers or internal notes appear;
- copy claims representative external-model performance, universal superiority, production readiness, arbitrary-tool safety or measured real-world cost efficiency;
- fixture metrics are mentioned without deterministic-fixture qualification;
- a distribution entry says an external submission is complete without a recorded public URL and date;
- authorship or AI-assistance attribution is removed;
- the package claims GitHub Pages or another hosted deployment is live when only readiness material exists.

## Distribution states

Allowed states:

- `published_repository` — material is publicly present in this repository;
- `prepared` — copy is ready but no external account action has occurred;
- `submitted` — external submission occurred and has URL/date evidence;
- `declined` — deliberately not used;
- `blocked` — unavailable because an account, setting or external action is required.

Initial external entries must remain `prepared` or `blocked`; the repository publication entry may be `published_repository`.

## Claims boundary

The package may state that the project demonstrates deterministic reliability testing, evidence preservation, provider-free integration, controlled failure injection, reproducible release engineering and explicit trade-off measurement.

It may quote the locked fixture values—General 2/8 verified, Specialist 6/8 verified, three false completions removed and 36 additional logical calls—only when clearly labelled as deterministic fixture results rather than external-model evidence.

## Authorship

Luca Panayiotou is credited for the project direction, problem framing, acceptance standard and publication approval. AI assistance is disclosed for implementation, testing and documentation. The copy must not imply that an external employer, provider or research institution endorsed the work.

## Out of scope

- sending recruiter emails without a selected recipient;
- posting through Luca's LinkedIn or other identity-bearing accounts;
- enabling GitHub Pages repository settings;
- publishing a real-provider benchmark;
- adding private ACE architecture or private pilot evidence;
- fabricating external reception, user counts or performance outcomes.
