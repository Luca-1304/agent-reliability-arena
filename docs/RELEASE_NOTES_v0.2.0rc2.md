# Agent Reliability Arena v0.2.0rc2

This prerelease adds verifiable software-supply-chain provenance to the existing evidence-first evaluation system. The deterministic fixture and provider-free orchestration evidence remain unchanged; rc2 improves how downloadable artifacts are identified, checked and linked to their source workflow.

## Added in rc2

- deterministic CycloneDX SBOM published as a first-class release asset;
- supply-chain manifest linking package, citation, showcase and launch evidence;
- GitHub artifact attestation for the wheel and source distribution;
- separate SLSA provenance and CycloneDX SBOM attestation predicates;
- online attestation verification before release publication;
- job-scoped OIDC, attestation and artifact-metadata permissions;
- citation metadata and package version aligned on `0.2.0rc2`;
- complete SHA-256 inventory and exact source-commit release record;
- preservation of the immutable `v0.2.0rc1` release and notes.

## Verify downloads

Verify the checksum inventory after downloading the release assets:

```bash
sha256sum --check SHA256SUMS
```

Verify SLSA build provenance for the wheel or source archive:

```bash
gh attestation verify agent_reliability_arena-0.2.0rc2-py3-none-any.whl \
  -R Luca-1304/agent-reliability-arena \
  --signer-workflow Luca-1304/agent-reliability-arena/.github/workflows/release.yml
```

Verify the CycloneDX SBOM attestation:

```bash
gh attestation verify agent_reliability_arena-0.2.0rc2-py3-none-any.whl \
  -R Luca-1304/agent-reliability-arena \
  --signer-workflow Luca-1304/agent-reliability-arena/.github/workflows/release.yml \
  --predicate-type https://cyclonedx.org/bom
```

The same commands can be used with `agent_reliability_arena-0.2.0rc2.tar.gz`.

## Evidence boundary

The public result remains deterministic fixture and provider-free integration evidence. **No real-provider benchmark** was executed for this prerelease. Artifact attestation links bytes to a source repository, commit and workflow identity; it does not prove that the software is secure, free of vulnerabilities or suitable for production.

This prerelease is **not production readiness**, representative real-model performance, unrestricted-tool safety, statistical generality or measured real-world cost efficiency.

```text
provider_called: false
comparative_claim_permitted: false
```
