# Branch lifecycle audit — 2026-08-08

This is a dated, read-only snapshot of remote branch lifecycle evidence. It is not a deletion plan and does not authorize any ref mutation.

## Evidence identity

- Repository: `Luca-1304/agent-reliability-arena`
- Remote: `origin`
- Default branch: `main`
- Observed default-branch tip: `a46328245d3c1925589d31c9489e8b8bace2b34d`
- Observed lifecycle feature head: `0a43ccad5aa7bf9009aa92c73aef52268892c93e`
- GitHub Actions history run: `31263317929`
- Retained artifact: `branch-lifecycle-report-1`
- Artifact ID: `9023398307`
- Artifact digest: `sha256:1cd00e3075a837533064268772c271845809ed7d8abbdc4f28dbaf8f336ab87a`
- Non-main remote branches observed: **90**
- `destructive_actions_supported`: **false**
- `deletion_authorized`: **false for every branch**

The report was generated only after the history workflow fetched all writable `origin` branches and verified that each descended from the approved clean-history boundary.

## Classification counts

| Lifecycle class | Count | Meaning in this audit |
| --- | ---: | --- |
| `merged-superseded-candidate` | 66 | Tip is already an ancestor of observed `main`; review candidate only. |
| `uncertain` | 14 | Ancestry alone cannot establish lifecycle state, commonly because development was squash/rebase integrated. |
| `temporary-obsolete-candidate` | 5 | Temporary/ref-sync naming plus no stronger retention fact; review candidate only. |
| `historical-evidence-retain` | 3 | Explicitly preserved TDD/development evidence. |
| `release-archive-retain` | 2 | Release/archive policy retains these branches. |

## Explicit historical-evidence retains

These branches are intentionally retained in Branch Lifecycle v1:

- `feature/assurance-router` — preserves the superseded Router TDD/provenance history from PR #97.
- `feature/clean-room-concurrency-specialists` — preserves superseded stacked development evidence from PR #91.
- `feature/git-operations-control-plane` — preserves granular RED/GREEN history from squash-merged PR #100.

## Release/archive retains

- `release/v0.1.0`
- `release/v0.2.0-rc1-hardening`

## Temporary/obsolete review candidates

These are the clearest future cleanup-review candidates in this snapshot. None is deletion-authorized by this audit:

- `temp/inspect-ashby-form`
- `tmp/policy-deep-final`
- `tmp/rebase-policy-driven-deep`
- `tmp/rebase-reliability-evidence`
- `tmp/rebase-reliability-policy`

All five were already ancestors of observed `main` with zero commits ahead at audit time.

## Uncertain branches requiring provenance review

The classifier deliberately refuses to infer their state merely from non-ancestry:

- `ci/future-proof-repeated-verification`
- `ci/reliability-gate-v2`
- `design/layered-reliability-assurance`
- `docs/branch-protection-contract`
- `feature/branch-lifecycle-reporting`
- `feature/clean-room-concurrency-specialists-main`
- `feature/determinism-reproducibility-specialists`
- `feature/layered-reliability-workflows`
- `feature/policy-driven-deep-gate`
- `feature/privacy-safe-diagnostic-scanner`
- `feature/reliability-evidence-contract`
- `feature/reliability-policy-foundation`
- `feature/structural-ci-policy`
- `plan/layered-reliability-assurance`

A later provenance-enrichment pass may use reviewed PR facts to reclassify these without modifying any refs.

## Remaining merged/superseded candidates

The other **66** non-main branches were already ancestors of observed `main` and had zero commits ahead at audit time. This makes them strong lifecycle-review candidates, but ancestry is evidence for integration, not authority to delete. A future destructive phase would still need to re-fetch current refs, confirm no open/active work, preserve required evidence/release branches, and obtain separate reviewed deletion authority.

## Safety conclusion

This audit authorizes **zero deletions**. Its purpose is to replace branch clutter with explicit evidence and to make any later cleanup decision reviewable rather than intuitive. Branch existence, retention, and eventual retirement remain separate from the repository history-boundary guarantee.
