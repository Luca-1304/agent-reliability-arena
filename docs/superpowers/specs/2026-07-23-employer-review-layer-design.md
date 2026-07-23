# Employer Review Layer Design

## Purpose

Make Agent Reliability Arena understandable and technically credible to a recruiter, hiring manager or senior engineer within five minutes, without weakening the evidence boundary or duplicating the locked public showcase package.

## Audience

The primary audience is employers evaluating Luca Panayiotou for work involving AI reliability, agent systems, Python engineering, evaluation infrastructure, test/release engineering or AI assurance.

## Success criteria

A reviewer should be able to determine, quickly and from linked evidence:

1. the engineering problem Luca identified;
2. the system Luca directed and shipped;
3. what the repository proves;
4. what remains deliberately unproven;
5. Luca's concrete ownership and review contribution;
6. the most valuable source and test files to inspect;
7. the main architectural trade-offs;
8. the exact commands required to reproduce the public fixture;
9. the public release, citation, security and supply-chain evidence;
10. the kinds of engineering roles for which the work is relevant.

## Design

### 1. Five-minute employer route

Create a root-level `EMPLOYER_REVIEW.md` as the single employer-facing entry point. It will contain:

- a 30-second project summary;
- verified public results and evidence classification;
- a precise `What Luca owned` section;
- a five-minute review route;
- an architecture and code-review map with exact repository paths;
- key technical decisions and trade-offs;
- reproducibility commands;
- role-fit mapping based on demonstrated work;
- current limitations and the pending empirical boundary.

It must not claim real-model performance, production readiness, universal superiority, unrestricted-tool safety or measured provider economics.

### 2. README entrance

Improve only the opening portion of `README.md` so a new reviewer sees:

- current release `v0.2.0rc2`;
- evidence class: deterministic fixture plus provider-free integration;
- direct links to `EMPLOYER_REVIEW.md`, the trace viewer, technical report and release;
- concise proof points;
- test, CodeQL, release and licence badges;
- an explicit statement that no real-provider benchmark has run.

The detailed technical README body remains intact.

### 3. Ownership clarity

Expand `docs/CONTRIBUTION.md` to distinguish:

- Luca's problem identification and experiment question;
- acceptance standard and claims boundary;
- architecture and authority constraints he required;
- approval, review and defect-correction decisions;
- AI-assisted implementation, documentation and testing;
- the evidence used to verify behaviour independently of either Luca's or the AI's claims.

This must remain transparent and must not imply unaided authorship of generated implementation.

### 4. Current status accuracy

Update `docs/PROJECT_STATUS.md` so its verified date and release-publication state reflect 23 July 2026. Preserve the distinction between completed provider-free engineering and the still-unrun real-provider pilot.

### 5. Automated employer-facing contract

Add `tests/test_employer_review.py` to fail closed when:

- the employer review route is missing required sections;
- linked code or test paths do not exist;
- README first-contact information is missing or stale;
- ownership wording loses the AI-assistance disclosure;
- project status becomes stale;
- prohibited claims appear in the employer layer.

## Files

Create:

- `EMPLOYER_REVIEW.md`
- `tests/test_employer_review.py`

Modify:

- `README.md`
- `docs/CONTRIBUTION.md`
- `docs/PROJECT_STATUS.md`

Temporary process files under `docs/superpowers/specs/` and `docs/superpowers/plans/` will be removed before merge so the public repository gains only durable employer-facing material.

## Non-goals

- No new runtime package, command, workflow or dependency.
- No modification to the seven-file locked showcase package or its publication manifest.
- No change to release assets, rc2 attestations, citation provenance or supply-chain hashes.
- No real-provider call or empirical claim.
- No generic personal-brand language, inflated title claims or unsupported performance language.
- No full portfolio-site rebuild in this change.

## Verification

The final exact branch head must pass:

- `python -m unittest tests.test_employer_review -v`;
- the complete Python 3.10–3.13 repository matrix;
- existing showcase, launch, citation, supply-chain and release verifiers;
- clean-wheel installation and tests;
- CodeQL and release rehearsal where triggered.
