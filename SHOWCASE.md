# Agent Reliability Arena — public showcase

**Showcase version:** `0.2.0rc1-public-showcase-1`  
**Evidence class:** deterministic fixture and provider-free integration  
**Author and project lead:** Luca Panayiotou

This is the compact public route through Agent Reliability Arena. It presents the engineering question, controlled trace viewer, architecture, verified capabilities and limitations without exposing private operational evidence.

## Start here

1. Open [`web/index.html`](web/index.html) through a local static server.
2. Select the `false_success` scenario in the paired trace explorer.
3. Compare the source report with the independently observed state.
4. Read the [employer-facing technical summary](docs/EMPLOYER_TECHNICAL_SUMMARY.md).
5. Review the [publication boundary](docs/PUBLICATION_BOUNDARY.md).
6. Use the [90-second demonstration script](docs/SHOWCASE_DEMO_SCRIPT.md).
7. Open the [launch and career conversion package](LAUNCH.md) for CV, portfolio, outreach and distribution material.
8. Read the [citation-ready technical report](docs/TECHNICAL_REPORT.md).
9. Follow the [provider-free reproducibility statement](docs/REPRODUCIBILITY.md).
10. Review the [security policy](SECURITY.md) and [supply-chain hardening note](docs/SUPPLY_CHAIN_SECURITY.md).

```bash
python -m http.server 8000 --directory web
```

Open `http://localhost:8000`.

## Verify the exact public package

```bash
python -m pip install --editable .
arena-verify-showcase --root .
```

The verifier checks:

- the exact seven-file allow-list;
- canonical manifest and file SHA-256 values;
- path confinement and symlink rejection;
- deterministic reference metrics;
- required attribution and limitations;
- secret-shaped material, private evidence markers, local paths, raw provider identifiers and internal-note markers;
- unsupported performance, cost, safety or production claims.

The locked package is recorded in [`showcase/publication-manifest.json`](showcase/publication-manifest.json).

## Citation and technical review

GitHub can render [`CITATION.cff`](CITATION.cff) through its repository citation interface. The technical report separates deterministic fixture evidence, provider-free integration evidence and the still-unrun real-provider stage.

```bash
arena-verify-citation-package --root .
```

The citation verifier independently checks release metadata, report limitations, provider-free commands, the closed provenance schema and pinned source hashes. The machine-readable record is [`citation/provenance.json`](citation/provenance.json).

## Security and supply-chain review

The root [`SECURITY.md`](SECURITY.md) provides private-reporting and coordinated-disclosure guidance. The deterministic CycloneDX inventory is [`security/sbom.cdx.json`](security/sbom.cdx.json), linked through [`security/supply-chain-manifest.json`](security/supply-chain-manifest.json).

```bash
arena-verify-supply-chain --root .
```

The verifier regenerates the SBOM byte-for-byte, checks the project and vendored-verifier identities, verifies five pinned public files, and enforces the CodeQL, Dependabot and least-privilege workflow boundaries. A successful result is not an exhaustive security audit or a guarantee that no vulnerability exists.

## Career and distribution package

The separate [launch package](LAUNCH.md) converts the verified showcase into reusable CV, portfolio, recruiter, professional-social and technical-community copy without modifying the locked evidence bundle.

```bash
arena-verify-launch-package --root .
```

Its manifest is recorded in [`showcase/launch-package-manifest.json`](showcase/launch-package-manifest.json), and its evidence-backed publication states are recorded in [`showcase/distribution-register.json`](showcase/distribution-register.json).

Prepared external actions remain explicitly unsubmitted until a public URL and date exist.

## Public evidence

The deterministic eight-scenario fixture reports:

| Metric | General | Unified specialists |
|---|---:|---:|
| Independently verified outcomes | 2/8 | 6/8 |
| False completion claims | 3 | 0 |
| Logical role calls | 8 | 44 |

The paired difference is four additional verified outcomes and three fewer false-completion claims, with 36 additional logical role calls.

These are deterministic software-fixture results. They are not measurements of a hosted or local model.

## Publication boundary

The showcase publishes architecture, deterministic outcomes, provider-free reproductions, verification instructions, limitations and transparent authorship attribution.

It does not publish credentials, complete private prompts, raw provider payloads, provider request metadata, private ledgers, operator notes, machine-local paths, enabled live policies, private budgets or unpublished ACE operating patterns.

No real-provider benchmark request or provider spend has been executed. `comparative_claim_permitted` remains `false`.
