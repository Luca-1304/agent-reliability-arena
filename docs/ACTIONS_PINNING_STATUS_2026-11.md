# GitHub Actions pinning — current maintenance note

**Observed:** 2026-11-05. **Scope:** current repository workflows, not a historical release attestation.

The earlier supply-chain write-up at `docs/SUPPLY_CHAIN_SECURITY.md` describes full third-party GitHub Actions SHA pinning as future work. This is now stale for the current-worktree workflows inspected here. The tested workflows use full-length immutable action commit references rather than floating version tags.

Representative observed references:

- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` — annotated `v7.0.1`;
- `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97` — annotated `v7`;
- `github/codeql-action/init@5595ccaf912efad79be6eef63a5619ff05969be3` — annotated `v4.37.6`;
- `github/codeql-action/analyze@5595ccaf912efad79be6eef63a5619ff05969be3` — annotated `v4.37.6`;
- `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` — annotated `v7.0.1`.

These values were observed in current `.github/workflows/` source; annotation text is informational, while the commit SHA controls execution. This is a sampled inventory rather than independent cryptographic verification of every upstream action or a complete all-branch audit.

**Maintenance:** Dependabot proposes updates for Python and GitHub Actions dependencies. Its pull requests need exact-diff review and the repository's required CI, policy, history, code-scanning and evidence gates. Updates should not be auto-merged solely because a newer release exists.

**Integrity and historical boundary:** This is a new explanatory note; it does not replace, regenerate or alter the checksum-linked `docs/SUPPLY_CHAIN_SECURITY.md`, `security/supply-chain-manifest.json`, `release/github-prerelease.json` or immutable `v0.2.0rc2` artifacts. A prior attempted direct edit correctly failed a hash-drift verification. Issue #142 tracks a separately reviewed approach for formally updating the attested material.

**Claims:** SHA pinning reduces revision ambiguity, but does not establish that an upstream action is uncompromised, that every workflow has least-privilege permissions, or that there are no vulnerable dependencies. Repo settings, branch protection, provider-account controls and historical secrets need independent review.

There is no real-provider test or Daybreak authorisation implied by this note. The historical Stage 7 privacy-execution hold remains open.
