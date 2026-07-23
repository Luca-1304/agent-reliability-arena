# Agent Reliability Arena — employer review

**Author and project lead:** Luca Panayiotou  
**Current public release:** `v0.2.0rc2`  
**Evidence class:** deterministic fixture and provider-free integration  
**Recommended review time:** five minutes

## 30-second summary

Agent Reliability Arena is a Python evaluation and release system for one narrow engineering question:

> When the task, model configuration, tools, sandbox, failure schedule and completion contract stay fixed, can role-specialised orchestration improve independently verified completion enough to justify its additional calls and complexity?

The comparison is between one General agent and one unified Specialist system with bounded Strategist, Operator, Auditor, Recovery and Synthesiser roles. The central rule is that an agent or tool reporting success is not proof of completion. Final status comes from independently observed state checked against the exact contract.

This repository demonstrates evaluation design, agent authority separation, fail-closed contracts, adversarial testing, reproducible packaging, release provenance, supply-chain verification and explicit claims management.

## Verified evidence

The locked public fixture contains eight deterministic paired scenarios:

| Measure | General | Unified specialists |
|---|---:|---:|
| Independently verified outcomes | **2/8** | **6/8** |
| False completion claims | **3** | **0** |
| Recovered scenarios | **0** | **4** |
| Logical role calls | **8** | **44** |

The Specialist fixture therefore contains four additional verified outcomes and removes three false-completion claims at the cost of **36 additional logical role calls**.

These numbers validate the software, evidence separation, failure handling, measurement and replay paths. They are not measurements of a hosted model, local model, production system or workforce. Token use, provider latency and monetary cost are deliberately unmeasured rather than invented.

The public release also verifies:

- source and clean-wheel execution on Python 3.10, 3.11, 3.12 and 3.13;
- strict parsing for six role-output contracts;
- exact action authorisation before mutation;
- independent post-action observation and completion verification;
- provider-free success, bounded recovery and terminal security paths;
- tamper-evident transport records and preserved abort evidence;
- preregistered repeated trials with safe pause and replay-free continuation;
- disclosure-safe export retaining completed and aborted outcomes;
- checksum-verified release assets, SLSA provenance attestations and CycloneDX attestations.

`provider_called: false`  
`comparative_claim_permitted: false`

## What Luca owned

Luca's contribution is recorded as technical direction and accountable review, not as a claim of unaided code authorship.

He:

- identified false completion as the practical failure mode worth isolating;
- selected the held-constant comparison between a General agent and bounded Specialist orchestration;
- set the acceptance standard that independently observed state outranks agent text and success-shaped tool receipts;
- required planning, mutation, audit, recovery and final synthesis to have separate authority boundaries;
- required exact path/content authorisation, explicit external-execution approvals and hard pre-call reservations;
- required failed and aborted evidence to remain countable rather than disappear from later reporting;
- set the publication boundary separating deterministic software evidence from real-model empirical evidence;
- approved releases only after source, installed-package, clean-wheel and public-evidence verification;
- directed repeated review passes and required discovered defects—including release, fixture, checksum, attestation and compatibility defects—to be repaired and reverified before merge or publication.

Architecture, Python implementation, tests and documentation were produced through **AI-assisted implementation** under Luca's direction, constraints and review. Correctness is grounded in repository tests, reproducible artifacts and independent verifiers rather than either Luca's or the AI's assertion.

See `docs/CONTRIBUTION.md` for the authorship record.

## Review in five minutes

1. **See the failure being solved:** open `web/index.html`, choose the `false_success` scenario and compare the source report with the independently observed state.
2. **Read the engineering conclusion:** open `docs/TECHNICAL_REPORT.md`, especially the evidence taxonomy and threats to validity.
3. **Inspect the core authority separation:** review `src/agent_reliability_arena/live_orchestration.py` with `tests/test_live_orchestration.py`.
4. **Inspect the paid-execution boundary:** review `src/agent_reliability_arena/private_pilot.py` with `tests/test_private_pilot.py`.
5. **Inspect release and supply-chain discipline:** review `src/agent_reliability_arena/github_prerelease.py`, `tests/test_github_prerelease.py`, `src/agent_reliability_arena/supply_chain.py` and `tests/test_supply_chain_security.py`.
6. **Verify the fixture identity:** inspect `reference_runs/fixture-v1/manifest.json` and run the reproduction commands below.
7. **Review limitations before drawing conclusions:** read `docs/PROJECT_STATUS.md`, `docs/PUBLICATION_BOUNDARY.md` and `SECURITY.md`.

## Code-review map

| Path | What it demonstrates | What to inspect |
|---|---|---|
| `src/agent_reliability_arena/live_orchestration.py` | General and Specialist live-path orchestration | role authority, strict parsing, mutation boundary, independent verification and recovery gating |
| `tests/test_live_orchestration.py` | Adversarial orchestration coverage | success, recovery, malformed output and terminal security behaviour |
| `src/agent_reliability_arena/private_pilot.py` | Deliberate private paired execution | exact preflight, fresh-directory rules, evidence retention and abort handling |
| `tests/test_private_pilot.py` | Pilot gate and evidence tests | approval, credential, call-plan, ledger and failure-preservation cases |
| `src/agent_reliability_arena/github_prerelease.py` | Reproducible release construction | exact artifact inventory, source commit, hashes and release-record checks |
| `tests/test_github_prerelease.py` | Release regression coverage | rc2 contract agreement, tamper rejection, bundle contents and checksum behaviour |
| `src/agent_reliability_arena/supply_chain.py` | Deterministic SBOM and security package verification | closed schemas, component identity, path confinement and claim scanning |
| `tests/test_supply_chain_security.py` | Supply-chain adversarial tests | byte-for-byte SBOM regeneration, hidden-component rejection and permission checks |
| `reference_runs/fixture-v1/manifest.json` | Locked fixture identity | file allow-list, sizes and SHA-256 values |
| `web/index.html` | Reviewer-facing trace exploration | source claim, independent observation, audit, recovery and final verifier state |

## Technical decisions and trade-offs

| Decision | Why it was chosen | Cost or limitation kept visible |
|---|---|---|
| Independent observation outranks self-report | A success message does not prove the requested state exists | extra observation and verification steps |
| Separate Strategist, Operator, Auditor, Recovery and Synthesiser authority | prevents one role from planning, mutating and approving its own work | more logical calls and coordination complexity |
| Deterministic fixture before real-model experimentation | makes software and measurement defects reproducible | does not estimate external-model performance |
| One bounded recovery attempt | permits evidence-backed correction without indefinite retry loops | some recoverable tasks may still terminate |
| Private raw evidence with allow-listed public export | preserves provider-shaped evidence while preventing accidental disclosure | public reviewers cannot inspect private payloads |
| Exact call, token and monetary reservations before execution | constrains external work before spend occurs | reservations are conservative ceilings, not measured billing |
| Minimal runtime dependencies and clean-wheel checks | reduces supply-chain surface and packaging ambiguity | more standard-library implementation work |
| Attested prerelease rather than silent asset replacement | preserves exact source and build provenance | fixes require a new release or explicit corrective history |

## Reproduce the public fixture

```bash
python -m venv .venv
. .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .

arena-run \
  --config examples/fixture_experiment.json \
  --output runs/fixture-v1

arena-replay --input runs/fixture-v1
arena-export-web \
  --input runs/fixture-v1 \
  --output /tmp/arena-fixture-public.json

arena-verify-showcase --root .
arena-verify-launch-package --root .
arena-verify-citation-package --root .
arena-verify-supply-chain --root .
```

The preflight and public verifiers require no provider credential and make no model request.

## Role fit

This project provides evidence relevant to:

- **AI reliability or evaluation engineering:** controlled comparisons, authoritative acceptance contracts, false-completion measurement and evidence taxonomy;
- **Agent systems engineering:** bounded role authority, strict outputs, provider-neutral transport, recovery and safe continuation;
- **Python backend engineering:** typed data boundaries, filesystem confinement, deterministic serialization, CLI packaging and standard-library-heavy implementation;
- **Test and release engineering:** adversarial unit/integration coverage, multi-version matrices, clean-wheel verification, immutable release records and checksum validation;
- **AI assurance or safety engineering:** explicit execution approvals, hard resource ceilings, terminal security rejection, private/public evidence separation and conservative claims.

This mapping is based on inspectable repository work. It is not a claim that one project substitutes for production experience across every listed role.

## What remains unproven

The current repository does not establish:

- performance of any real hosted or local model;
- successful execution of the prepared paid-provider pilot;
- comparative reliability from a representative live sample;
- measured provider billing or real-world cost efficiency;
- generalisation beyond the controlled task family;
- safe execution of arbitrary tools;
- concurrent ledger writing;
- unattended operation or production readiness;
- absence of every vulnerability.

Issue #14 remains at the explicit execution boundary: an exact dated model snapshot, scenario, call/token ceilings, worst-case monetary reservation, enabled policy digest and local environment credential must be reviewed before any real-provider request.

## Public evidence and provenance

- Employer-facing technical summary: `docs/EMPLOYER_TECHNICAL_SUMMARY.md`
- Technical report: `docs/TECHNICAL_REPORT.md`
- Reproducibility statement: `docs/REPRODUCIBILITY.md`
- Authorship record: `docs/CONTRIBUTION.md`
- Publication boundary: `docs/PUBLICATION_BOUNDARY.md`
- Security policy: `SECURITY.md`
- CycloneDX SBOM: `security/sbom.cdx.json`
- Citation metadata: `CITATION.cff`
- Public prerelease: `https://github.com/Luca-1304/agent-reliability-arena/releases/tag/v0.2.0rc2`

The repository should be judged by those files, the source/tests above and reproducible outputs—not by promotional wording.