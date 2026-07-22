# Agent Reliability Arena

> **Same model. Same tools. Same evidence rules. Different orchestration.**

Agent Reliability Arena is a controlled evaluation and demonstration system comparing:

1. one **general agent** that plans, acts, checks and reports alone; and
2. one **unified specialist system** with bounded Strategist, Operator, Auditor, Recovery and Synthesiser roles.

Both conditions receive the same task, model configuration, sandbox, failure scenario, mutation limit and independently observed acceptance contract. The project asks:

> Does role-specialised orchestration improve reliable completion enough to justify its additional calls and complexity?

![Agent Reliability Arena trace viewer](web/arena-preview.png)

## Current evidence status

### Public v0.1.0 fixture

**Deterministic fixture — software validation, not external-model performance.**

The published reference run proves that experiment plumbing, role boundaries, evidence separation, metrics, replay and the trace viewer behave as designed. The fixed policies are not measurements of OpenAI, Anthropic, Gemini, local models, people or production systems.

### v0.2.0rc1 release candidate

The release candidate adds a complete provider-free live-model path and controlled pilot safeguards:

- versioned provider-neutral request and result contracts;
- an HTTPS OpenAI Responses adapter with credential, endpoint and explicit network-approval protections;
- tamper-evident private transport ledgers;
- a source-controlled six-role prompt catalogue;
- deterministic request construction and permission manifests;
- fail-closed role-output parsing;
- provider-neutral general and specialist orchestrators;
- exact contract checks before bounded mutation;
- independent observation, verification, audit, recovery and synthesis;
- a secret-free pilot policy with hard call, token-reservation and monetary-reservation ceilings;
- a provider-free `arena-preflight-pilot` command;
- a second execution gate requiring the exact reviewed policy digest and separate explicit approval.

The release fixtures exercise this path with scripted provider responses. No benchmark request or provider spend is included.

See [Project status](docs/PROJECT_STATUS.md), [Roadmap](ROADMAP.md), [Changelog](CHANGELOG.md), [Private pilot runbook](docs/PRIVATE_PILOT_RUNBOOK.md), [Disclosure boundary](docs/DISCLOSURE_BOUNDARY.md) and [RC checklist](docs/RELEASE_CANDIDATE_CHECKLIST.md).

## Reference fixture results

| Metric | General | Unified specialists |
|---|---:|---:|
| Independently verified outcomes | **2/8** | **6/8** |
| False completion claims | **3** | **0** |
| Claim precision | **0.25** | **1.00** |
| Recovered scenarios | **0** | **4** |
| Logical role calls | **8** | **44** |

The specialist fixture improves four paired outcomes and removes three false-completion cases while requiring **+36 logical role calls**. Token use, latency and monetary cost are deliberately unmeasured rather than invented.

See [RESULTS.md](RESULTS.md), [Methodology](docs/METHODOLOGY.md) and [Threat model](docs/THREAT_MODEL.md).

## Provider-free reproduction

```bash
python -m venv .venv
. .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .

arena-run \
  --config examples/fixture_experiment.json \
  --output runs/fixture-v1

arena-replay --input runs/fixture-v1
arena-export-web \
  --input runs/fixture-v1 \
  --output web/data/fixture-v1.json

arena-preflight-pilot \
  --config examples/fixture_experiment.json \
  --catalog examples/live_prompt_catalog.json \
  --policy examples/pilot_policy.disabled.json
```

The pilot preflight reads local files only, calls no provider, requires no API key and reports `provider_called: false`. The committed policy keeps external execution disabled.

To inspect the deterministic viewer:

```bash
python -m http.server 8000 --directory web
```

Open `http://localhost:8000`.

## Architecture

```text
Experiment config + prompt catalogue + pilot policy
                         │
                         ▼
          Deterministic permission and budget preflight
                         │
                exact reviewed policy digest
                         │
          explicit pilot gate + network approval
                         │
              ┌──────────┴──────────┐
              │                     │
      General condition      Specialist condition
          General          Strategist → Operator
              │                    → Auditor
              │               Recovery if justified
              │                    → Synthesiser
              └──────────┬──────────┘
                         │
              Provider-neutral transport
                         │
              Private tamper-evident ledger
                         │
              Strict role-output contracts
                         │
               Exact contract authorisation
                         │
                Confined file-write sandbox
                         │
               Independent state observation
                         │
              Agent Completion Verifier v0.6.0
                         │
               Evidence-derived final outcome
```

The Arena vendors Agent Completion Verifier v0.6.0 at commit `f65fb3450e3c1d7db17f0192667b854d126cd190`; every vendored Python file is recorded in [vendor_snapshot.json](vendor_snapshot.json).

## Why this is not a normal multi-agent demo

- Strategist and Auditor cannot mutate state.
- Operator cannot approve completion.
- Proposed writes must match the exact configured path and content before execution.
- Recovery runs only after an evidence-backed mismatch and has one attempt.
- Security rejections are terminal.
- Synthesiser cannot claim completion unless the verifier status is `VERIFIED_COMPLETE`.
- Canonical evidence comes from independently observed state, not a success-shaped receipt.
- Provider-shaped calls can be recorded in a private ledger and verified without re-execution.
- Real network execution is disabled unless approved independently at the pilot gate and adapter.

## Commands

| Command | Purpose | External request |
|---|---|---|
| `arena-run` | Execute the deterministic paired fixture and write digest-verified artifacts. | Never |
| `arena-replay` | Verify and summarise an artifact directory without executing tools. | Never |
| `arena-export-web` | Produce a reduced public fixture bundle. | Never |
| `arena-preflight-pilot` | Validate an exact pilot policy and print permission/budget evidence. | Never |

A public live-provider execution command is deliberately absent. Real-provider execution remains a separately gated private experiment tracked in issue #14.

## Release verification

The release gate covers:

- Python 3.10, 3.11, 3.12 and 3.13;
- package and installed-distribution version consistency;
- source compilation and the complete unit/integration suite;
- exact deterministic reference metrics;
- fairness invariants and 64 permitted live request templates;
- all six strict role-output contracts and malformed-output rejection;
- provider response, refusal, incomplete and failure handling;
- disabled-by-default adapter network execution;
- secret-free pilot policy and provider-free preflight;
- exact policy-digest approval and hard pre-call reservations;
- request, result, record and ledger digests;
- tamper, traversal, symlink and unlisted-file rejection;
- three provider-free live orchestration scenarios;
- installed command execution;
- wheel build and clean-wheel verification;
- dependency validation and vendored verifier integrity.

Run locally:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verify_release.py
```

## Repository map

```text
src/agent_reliability_arena/   experiment, live boundaries, pilot controls and replay
src/completion_verifier/       digest-pinned verifier snapshot
examples/                      fixture, prompt catalogue and disabled pilot policy
docs/                          status, methodology, runbook, disclosure and release checks
reference_runs/fixture-v1/     reproducible public fixture evidence
web/                           static trace viewer
web/data/                      reduced verified public fixture export
tests/                         fairness, transport, pilot, ledger, orchestration and UI tests
```

## Next empirical step

After the final release-candidate matrix is green, issue #14 permits one tightly bounded private paired run using one provider, one dated model snapshot, one scenario and the reviewed ceilings. One pilot remains operational evidence only; repeated trials and a disclosure-safe export are required before comparative publication.

No single live-model result should be described as representative.

## Authorship and AI assistance

See [docs/CONTRIBUTION.md](docs/CONTRIBUTION.md). The repository distinguishes Luca Panayiotou's problem framing and acceptance standard from AI-assisted implementation, documentation and testing.

## Licence

MIT. The vendored verifier carries the same licence and remains attributed in [VENDORED_VERIFIER.md](VENDORED_VERIFIER.md).
