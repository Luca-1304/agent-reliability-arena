# Branch Lifecycle Reporting Design

## Purpose

Add a deterministic, report-only branch lifecycle layer that reduces stale-ref ambiguity without deleting, rewriting, moving, force-updating or publishing any Git ref.

This layer answers a narrower question than the history-boundary verifier: not only “does this branch descend from the approved clean history boundary?”, but “what operational state should this branch be reviewed as?”

## Safety boundary

Branch Lifecycle v1 is deliberately incapable of cleanup.

It must not contain or invoke:

- `git push`;
- `git update-ref`;
- `git branch -D` / remote deletion;
- GitHub ref deletion/update APIs;
- tag creation or deletion;
- force operations;
- automatic branch retirement.

Its outputs are advisory evidence only. A later cleanup phase, if ever approved, must be a separate review and must re-prove branch state immediately before any deletion.

## Inputs

The classifier uses two explicit evidence sources:

1. **Local Git remote refs** — authoritative for branch names, tip commits and ancestry relative to the selected default branch.
2. **Optional provenance snapshot JSON** — operator-supplied metadata for facts Git alone cannot prove after squash merges, such as open/merged/superseded pull-request status or an explicit historical-evidence retention reason.

The tool itself performs no GitHub network calls. This keeps it deterministic, provider-free and usable in local clones, CI checkouts and offline audits.

## Output classes

Every non-default remote branch receives exactly one class:

- `active` — provenance says an open PR or active work exists;
- `historical-evidence-retain` — explicit provenance says the branch is intentionally preserved for TDD, diagnostic or superseded-development evidence;
- `release-archive-retain` — branch matches the reviewed release/archive retention policy;
- `merged-superseded-candidate` — provenance says merged/superseded and Git evidence does not contradict that status;
- `temporary-obsolete-candidate` — temporary/test/ref-sync naming plus no active provenance and no explicit retention;
- `uncertain` — evidence is incomplete, contradictory, or unique work may remain.

The classifier must never emit `safe_to_delete`.

## Git evidence

For each remote branch the report records:

- branch name;
- tip SHA;
- default-branch tip SHA;
- whether the branch tip is an ancestor of default;
- ahead/behind commit counts from `git rev-list --left-right --count`;
- configured lifecycle class;
- reasons/evidence used;
- `deletion_authorized: false`.

A branch that is not an ancestor of `main` is not automatically “unmerged work”: squash merging can preserve content without preserving commit ancestry. Such branches remain `uncertain` unless provenance supplies a stronger reviewed fact.

## Provenance snapshot

Optional JSON records are keyed by exact branch name and use a closed vocabulary:

- `pr_state`: `open`, `merged`, `closed_unmerged`, `none`, `unknown`;
- `superseded_by`: PR number or null;
- `retain_as_evidence`: boolean;
- `retention_reason`: string or null;
- `note`: optional non-authoritative explanation.

Unknown branches in provenance, duplicate keys, malformed SHAs, or unsupported states fail closed.

Provenance may strengthen classification but cannot authorize deletion.

## Policy

A small `branch-lifecycle-policy.json` owns:

- default branch (`main`);
- remote (`origin`);
- release/archive retain prefixes;
- temporary/review prefixes;
- explicit retained branch overrides when a branch name cannot safely be inferred from prefix;
- output schema version;
- `destructive_actions_supported: false`.

The policy is closed and must reject attempts to turn destructive actions on.

## Classification precedence

1. default branch is excluded from non-default lifecycle rows;
2. explicit historical-evidence retention;
3. open PR / active provenance;
4. release/archive retention policy;
5. merged/superseded provenance;
6. temporary/review prefix with no active/retain evidence;
7. ancestor-of-main fallback may produce merged candidate only when provenance does not contradict it;
8. otherwise `uncertain`.

Retention wins over cleanup candidacy.

## Current repository first-generation intent

The first real audit keeps TDD/evidence branches live. Examples already known to require preservation include superseded development branches whose PR descriptions explicitly say they are retained as historical evidence.

Temporary prefixes such as `tmp/` and `temp/` should become high-priority review candidates, not automatic deletions.

Release and verification branches remain retained or uncertain until provenance review says otherwise.

## Lucas Critique

Intended adaptation:
- new work uses branches with clear PR provenance;
- temporary/ref-sync branches become visible quickly;
- evidence branches gain explicit retention reasons.

Gaming adaptation:
- renaming a stale branch to a retained prefix must not by itself make it historical evidence;
- a merged PR must not imply deletion if unique branch commits remain or explicit evidence retention exists;
- squash merges must not be mistaken for unmerged work solely because ancestry differs.

Strategic/unexpected adaptation:
- future tools may supply richer provenance snapshots without changing classifier semantics;
- branch counts can fall later without weakening the clean-history guard;
- GitHub auto-delete should stay off until evidence-retention behavior is explicitly compatible.

Long-term equilibrium:
- branch existence becomes intentional rather than accidental;
- cleanup candidates carry machine-readable reasons;
- destructive actions remain a distinct, auditable control boundary.

Failure signals:
- unclassified provenance branch;
- malformed or contradictory provenance;
- destructive capability appears in code/policy;
- report omits a fetched remote branch;
- branch class changes without evidence change;
- a candidate is described as deletion-authorized.

## Acceptance criteria

1. synthetic tests prove the classifier is report-only and fail closed on malformed provenance/policy;
2. every fetched non-main branch appears exactly once in a report;
3. explicit evidence retention outranks merged/temp classification;
4. open PR outranks cleanup candidacy;
5. squash-like non-ancestor branches remain uncertain without provenance;
6. temporary prefixes produce review candidates, never deletion authority;
7. `deletion_authorized` is always false;
8. no code path contains ref deletion, push or update operations;
9. the first repository audit is committed as dated evidence, not as timeless truth;
10. no branch is deleted or modified during implementation or verification.
