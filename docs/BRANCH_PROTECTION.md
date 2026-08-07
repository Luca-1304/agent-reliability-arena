# Branch protection and merge policy

This document defines the intended merge-control contract for `main` in Agent Reliability Arena. It is an operating specification, not proof that GitHub account-level rules are currently configured.

The repository's workflow policy remains authoritative for what the reliability roles mean. GitHub branch protection or a branch ruleset should enforce the small set of stable role-summary checks rather than duplicating every underlying matrix or specialist job.

## Intended `main` protection

Configure the default branch so that changes reach `main` through a pull request and cannot bypass the repository's required reliability roles.

Recommended controls:

- require a pull request before merging;
- require all three reliability role-summary checks listed below;
- require review conversations to be resolved before merge;
- block force pushes to `main`;
- block deletion of `main`;
- keep bypass access empty or limited to the narrowest audited emergency role available;
- preserve any existing required security/privacy/history checks unless they are deliberately superseded with equivalent evidence;
- do **not** require the Scheduled ecosystem advisory.

This document does not automatically modify GitHub rulesets, branch protection, provider settings, deployment settings or secrets.

## Required reliability checks

GitHub required-status-check names for Actions workflows are job names. The stable merge contract is therefore the three aggregate job names below:

| Required check | Role | What it aggregates |
|---|---|---|
| `Fast — Role evidence summary` | Fast | Python 3.10–3.13 source tests, structural CI-policy verification, privacy/policy checks, wheel build and outside-workspace wheel validation |
| `Specialist — Role evidence summary` | Specialist | reproducible-build, explicit-determinism, clean-room, concurrency-isolation and diagnostic-security jobs |
| `Deep — Role evidence summary` | Deep | both policy-driven Deep variants, Python 3.10 and 3.13, including the 15-pass engine and privacy-safe evidence publication |

Require the summary checks, not every underlying matrix or specialist job. Each summary job is the role boundary and is designed to fail when its required role cannot produce acceptable evidence. This keeps branch protection stable if the internal matrix expands while preserving the role contract.

## Advisory check that must not block merges

The following workflow and summary are intentionally advisory:

- `Scheduled — Ecosystem drift advisory`
- `Scheduled — Advisory evidence summary`

They run on the scheduled/manual ecosystem path rather than the pull-request merge path. Requiring either one would contradict `reliability-policy.json` and could leave a pull request waiting for a check that is not supposed to run on that event.

A Scheduled failure is a maintenance signal. It should create follow-up work when meaningful, not rewrite a previously verified pull-request result retroactively.

## Up-to-date branch policy

Do not enable **Require branches to be up to date before merging** by default yet.

Reason:

- Deep verification is intentionally expensive;
- forcing every already-green pull request to rerun after an unrelated `main` movement can multiply CI cost without adding proportional evidence in a low-contention, single-owner repository;
- runtime performance is currently observational by policy, so there is not yet evidence for treating repeated base-update runs as an acceptable permanent cost.

This is a conscious `loose` required-check policy, not permission to ignore base drift. Rebase or update the pull request before merge when:

- the base changed in files or behavior relevant to the pull request;
- Git reports a conflict;
- another merge changed reliability policy, workflow structure, dependencies, build metadata, public evidence or the same implementation area;
- the exact tested head is no longer the revision intended for merge.

Reconsider strict mode when there is enough measured history to show that concurrent merges or base drift are a material source of defects. If contention becomes routine, evaluate a merge queue before accepting repeated full Deep reruns as the only solution.

## Safe ruleset activation sequence

Do not turn on required checks by guessing their names. Use this order:

1. Open a pull request whose changed paths trigger Fast, Specialist and Deep.
2. Confirm the exact three summary job names appear on that pull request and complete successfully.
3. Create or edit the `main` branch ruleset/protection rule.
4. Add exactly:
   - `Fast — Role evidence summary`
   - `Specialist — Role evidence summary`
   - `Deep — Role evidence summary`
5. Keep Scheduled absent from the required-check list.
6. Preserve already-required independent security/privacy/history checks unless their replacement is separately verified.
7. Activate the ruleset only after the check names have been observed on a real pull request.
8. Verify with a subsequent pull request that GitHub actually blocks merge while a required summary is pending or failed and permits merge only after the required summaries pass.

If GitHub allows selecting an expected source for a required check, prefer the repository's GitHub Actions application/source rather than accepting an unrelated producer with the same status name.

## Check-renaming protocol

A required status check is an external dependency on a literal job name. Renaming a job carelessly can deadlock merges.

When a required summary name must change:

1. Add the new job name in workflow code while the old required name can still run.
2. Merge or otherwise deploy the workflow change through a path that does not strand `main`.
3. Observe the new check name successfully on a real pull request.
4. Add the new check name to the ruleset.
5. Remove the old check requirement only after the new requirement is proven.
6. Remove or rename the old workflow job last.

Never remove a required job from workflow code before removing or replacing its branch-protection requirement.

## Trigger-surface invariant

A required check is safe only if it is produced for every pull request that can change merge-relevant repository behavior.

The layered workflows therefore include the repository's policy-governed trigger surfaces, including `src/**`, `tests/**`, `scripts/**`, `examples/**`, security/release/reference/web/docs/citation/requirements/schema paths, key root metadata and `.github/workflows/**`.

If a new merge-relevant top-level path is introduced:

1. add it to the reliability policy/trigger contract first;
2. make Fast, Specialist and Deep produce their summaries for that path;
3. verify the path on a pull request;
4. only then rely on the existing three summaries as complete branch-protection evidence for that new surface.

Do not solve a missing required check by weakening branch protection. Fix the trigger contract.

## Existing independent checks

The layered summaries are not substitutes for every other repository control. CodeQL, public-site/privacy validation and repository-history boundary checks serve different purposes.

When configuring the actual GitHub ruleset:

- inspect the current required-check list first;
- retain independent checks that are still current and reliably emitted on relevant pull requests;
- do not add a check merely because it exists somewhere in Actions;
- do not remove an existing security/privacy/history requirement merely because Fast, Deep and Specialist are green.

Exact independent check names should be copied from a recent successful pull request rather than hard-coded into this document from memory.

## Bypass and emergency handling

A bypass is not a normal merge path.

If an emergency bypass is ever used:

- record why the normal required checks could not be used;
- keep the change as small and reversible as possible;
- do not bypass privacy/credential boundaries to save time;
- immediately run the applicable Fast, Specialist and Deep verification on the resulting `main` revision;
- record any missing evidence as an unresolved risk rather than calling the merge fully verified.

Provider outages, quota exhaustion or long CI duration are not by themselves evidence that a failing or missing reliability result should be treated as passing.

## Post-configuration acceptance check

After GitHub rules are configured manually, verify the control plane rather than assuming the settings work:

- a pull request with all three summaries pending cannot merge;
- a deliberately failing required role makes its role summary fail and blocks merge;
- all three passing summaries permit the reliability portion of the merge decision;
- the Scheduled workflow is absent from pull-request required checks and cannot block merge;
- direct force-push/deletion of `main` is denied for normal operation;
- any configured bypass identities are exactly the intended minimum set;
- changing a workflow job name follows the migration protocol above;
- the final ruleset/protection settings are recorded privately with the date and reviewer/operator, without copying credentials or sensitive account material into the public repository.

## Evidence boundary

Branch protection controls merge admission. It does not prove:

- Vercel or another provider deployed the merged commit;
- a provider-side resource was deleted;
- historical provider/GitHub privacy surfaces are erased;
- real-provider model performance;
- the absence of every possible defect or flake.

Keep repository merge assurance, deployment provenance, provider operations and privacy-erasure evidence as separate claims.