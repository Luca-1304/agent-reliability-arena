# v0.2.0rc2 release checklist

This checklist is evidence-gated. A box is complete only when the candidate tree—not an earlier implementation stage—passes the stated verification.

## Metadata

- [x] `pyproject.toml` version is `0.2.0rc2`.
- [x] `agent_reliability_arena.__version__` is `0.2.0rc2`.
- [x] installed-distribution version is tested.
- [x] README, changelog and project status identify the release candidate accurately.

## Provider-free reproducibility

- [x] deterministic fixture execution requires no credential;
- [x] replay and public export require no credential;
- [x] scripted live orchestration requires no credential;
- [x] pilot preflight requires no credential or transport;
- [x] injected transport tests make no external request;
- [x] the real OpenAI network opener is disabled without explicit approval.

## Pilot controls

- [x] pilot policy schema is exact and rejects credential fields;
- [x] committed example policy has external execution disabled;
- [x] model, model version, prompt version and scenarios must match preflight;
- [x] reviewed policy digest must match exactly;
- [x] external execution requires a separate explicit approval;
- [x] adapter network execution requires explicit approval independently;
- [x] call, requested-output-token, reserved-total-token and monetary ceilings are enforced before calls;
- [x] no automatic retry is included;
- [x] operator runbook defines run-directory, credential and abort rules.

## Evidence and disclosure

- [x] private transport ledger remains tamper-evident and single-writer;
- [x] failed and aborted evidence must be retained;
- [x] private prompts, outputs and credentials are excluded from public export by default;
- [x] disclosure-safe field and redaction boundaries are documented;
- [x] release claims state that no real-model benchmark has been established.

## Candidate verification

- [x] source compilation succeeds on Python 3.10–3.13;
- [x] complete source suite succeeds on Python 3.10–3.13;
- [x] release verifier succeeds on Python 3.10–3.13;
- [x] all installed commands, including `arena-preflight-pilot`, succeed;
- [x] wheel builds and installs in a clean environment on Python 3.10–3.13;
- [x] clean-wheel tests and deterministic reference checks succeed;
- [x] dependency validation succeeds;
- [x] safeguard and release-candidate matrices completed without a provider request;
- [ ] the final documentation-closure head passes the same complete matrix;
- [ ] PR #18 is merged and issue #13 is closed.

## Claims boundary

Passing the technical checks establishes a reviewable release candidate and a controlled path toward a private pilot. It does not establish hosted-model performance, cost efficiency, statistical significance, production readiness or safety for arbitrary tools.
