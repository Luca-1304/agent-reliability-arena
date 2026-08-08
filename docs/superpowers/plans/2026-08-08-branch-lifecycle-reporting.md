# Branch Lifecycle Reporting Implementation Plan

**Goal:** Add a deterministic, report-only classifier for remote branch lifecycle state and produce the first dated repository audit without deleting or modifying refs.

**Architecture:** Standard-library Python + local Git commands only. A closed JSON policy defines non-destructive classification rules. Optional provenance JSON supplies PR/evidence facts that Git ancestry cannot prove after squash merges. The classifier emits machine JSON with `deletion_authorized: false` for every branch.

## Constraints

- No branch deletion, ref update, push, tag mutation or force operation.
- No GitHub settings mutation.
- No provider/network call from the classifier.
- Current historical TDD/evidence branches remain live.
- Temporary branches are candidates for review only.

### Task 1 — RED contracts
- Create `tests/test_branch_lifecycle.py`.
- Require closed policy loading.
- Require exact remote-ref coverage.
- Require retention > active > release > merged/superseded > temporary > uncertain precedence.
- Require squash-like non-ancestor branch to remain uncertain without provenance.
- Require every output row to contain `deletion_authorized: false`.
- Require source to contain no destructive Git command capability.
- Observe expected missing-module RED in PR CI.

### Task 2 — Policy and classifier
- Create `branch-lifecycle-policy.json`.
- Create `scripts/ci/branch_lifecycle.py`.
- Create `scripts/ci/report_branch_lifecycle.py` CLI.
- Use argument-list subprocess calls only.
- Inspect `refs/remotes/<remote>` via `git for-each-ref`.
- Compute ancestry and ahead/behind via `merge-base --is-ancestor` and `rev-list --left-right --count`.
- Accept optional closed provenance snapshot.
- Emit deterministic JSON, sorted by branch.

### Task 3 — Real audit evidence
- Build a provenance snapshot from current GitHub branch/PR evidence outside the classifier.
- Fetch every remote branch in the read-only history workflow environment or equivalent reviewed local Git context.
- Generate `docs/audits/branch-lifecycle-2026-08-08.json` and concise Markdown summary.
- Confirm the report contains every current non-main branch exactly once and authorizes zero deletions.

### Task 4 — CI integration
- Add a source test/verification path that proves the classifier remains non-destructive.
- Do not make a stale dated audit a permanent merge blocker.
- Keep live branch-count auditing operator-invoked until an appropriate fresh-data CI route is separately designed.

### Task 5 — Exact-head acceptance
- Full Python 3.10–3.13 tests and clean wheel checks.
- Fast/Specialist/Deep role summaries green.
- CodeQL/history/Pages/release relevant verification green.
- Public-write jobs skipped on PR.
- Diff contains no ref mutation/deletion capability.
- Merge with expected-head guard only.
