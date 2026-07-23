# External Consumer Verification

This repository includes a read-only workflow that verifies the published `v0.2.0rc2` prerelease from the position of an external consumer.

The workflow downloads the public release rather than trusting local `dist/` output. It verifies the exact 11 release assets, all 10 checksum entries, two provenance attestations and two CycloneDX attestations against the published source commit.

It then creates a fresh virtual environment, installs only the downloaded wheel with `--no-deps`, runs the deterministic fixture, and compares three key outputs byte-for-byte with the locked public reference:

- `aggregate_metrics.json`
- `paired_results.jsonl`
- `report.md`

The public fixture export must also reproduce these locked values:

- general verified complete: `2`
- specialist verified complete: `6`
- additional logical model calls: `36`

## Run it

Open the repository's Actions tab, select **Verify published v0.2.0rc2 release**, and choose **Run workflow**.

The workflow also runs once when the verification files are merged to `main`. It has no recurring schedule.

## Evidence produced

A successful run uploads a disclosure-safe artifact containing:

- `verification.json`
- checksum verification output
- provenance-attestation verification output
- CycloneDX-attestation verification output

The artifact contains no credentials, private prompts, provider payloads, local machine paths, private budgets or ACE internals.

## Claims boundary

This verifies the identity, checksum integrity, signed build provenance and deterministic fixture reproduction of one published release.

It does not prove security, absence of vulnerabilities, production readiness, real-model performance, universal superiority or universal cross-platform reproducibility.
