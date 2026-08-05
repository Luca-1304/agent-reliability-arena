# Repository history boundary

## Status

On 5 August 2026, the owner-controlled writable history of this repository was rebuilt to remove the historical public-CV lineage from every writable branch.

The current source tree was preserved at the clean boundary commit:

`2fe7d730a688f020e878e24d711d8f153e0cfcbb`

Every new branch and pull request must descend from that commit. Provider-controlled pull-request references, caches, tags and unreachable objects are handled separately through GitHub's privacy and support processes; this repository must not describe that provider-side work as complete until GitHub confirms it.

## Required local recovery procedure

Use a **fresh clone** for all future work. An older local clone may retain removed objects and must not be merged, rebased or force-pushed back into this repository.

When unfinished work exists only in an old clone:

1. create a fresh clone from the current default branch;
2. inspect the old work without adding its history as a remote;
3. export only the necessary text patch or recreate the change manually;
4. inspect the patch for personal information, credentials and obsolete hosting references;
5. apply it to a new branch created from current `main`;
6. run the complete repository verification before opening a pull request.

Do not merge an old branch, push an old tag, use `--mirror`, or resolve divergence by restoring the former ancestry.

## Automated enforcement

`.github/workflows/history-boundary.yml` performs a full-history checkout, fetches all writable origin branches and runs `scripts/verify_history_boundary.py`.

The verifier fails closed unless:

- the approved boundary commit exists;
- it has exactly the approved pre-CV parent;
- it has the approved current-tree identity;
- the checked-out commit descends from the boundary; and
- every fetched writable origin branch descends from the boundary.

This control prevents ordinary pull requests and pushes from silently reintroducing the removed writable ancestry. It does not replace GitHub's provider-side garbage collection or removal of read-only references.