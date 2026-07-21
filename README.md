# Agent Reliability Arena

> **Same model. Same tools. Same evidence rules. Different orchestration.**

Agent Reliability Arena is a controlled evaluation and demonstration system for comparing:

1. one **general agent** that plans, acts, checks and reports alone; and
2. one **unified specialist system** with bounded Strategist, Operator, Auditor, Recovery and Synthesiser roles.

Both conditions receive the same task, fixture-model label, sandbox, failure scenario, mutation limit and independently observed acceptance contract. The project asks a narrow engineering question:

> Does role-specialised orchestration improve reliable completion enough to justify its additional calls and complexity?

![Agent Reliability Arena trace viewer](web/arena-preview.png)

## Evidence status

**Deterministic fixture — software validation, not external-model performance.**

This v0.1.0 release proves that the experiment plumbing, role boundaries, evidence separation, metrics, replay and employer-facing trace viewer behave as designed. The fixed fixture policies are not presented as OpenAI, Anthropic, Gemini, local-model or human performance.

## Reference fixture results

| Metric | General | Unified specialists |
|---|---:|---:|
| Independently verified outcomes | **2/8** | **6/8** |
| False completion claims | **3** | **0** |
| Claim precision | **0.25** | **1.00** |
| Recovered scenarios | **0** | **4** |
| Logical role calls | **8** | **44** |

The specialist fixture improves four paired outcomes and removes three false-completion cases, while requiring **+36 logical role calls**. Token use, latency and monetary cost are deliberately left unmeasured rather than invented.

See [RESULTS.md](RESULTS.md) for scenario-level detail, [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for the comparison rules, and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the trust boundary.

## Two-minute local reproduction

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

python -m http.server 8000 --directory web
```

Open `http://localhost:8000` to inspect the paired trace viewer.

## What the viewer shows

- identical task and contract metadata;
- general and specialist traces side by side;
- source-reported success separated from independent observation;
- Auditor and Recovery decisions;
- exact status, claim and logical-call differences;
- the SHA-256-backed evidence used by the verifier;
- the cost side of the reliability improvement.

The web application is static, read-only and dependency-free. It executes no model and mutates no state.

## Architecture

```text
Experiment config
      │
      ├───────────────┬─────────────────────────┐
      │               │                         │
General condition     │              Specialist condition
one policy call       │        Strategist → Operator → Auditor
      │               │                      │
      │               │              Recovery when justified
      │               │                      │
      └───────────────┴──────────────┬───────┘
                                     │
                        Confined file-write sandbox
                                     │
                        Independent state observation
                                     │
                     Agent Completion Verifier v0.6.0
                                     │
                       Paired metrics + replay bundle
```

The Arena vendors the published Agent Completion Verifier v0.6.0 source at commit `f65fb3450e3c1d7db17f0192667b854d126cd190`. Every vendored Python file is recorded in [vendor_snapshot.json](vendor_snapshot.json).

## Why this is not a normal multi-agent demo

The specialist condition cannot grade itself:

- Strategist and Auditor cannot mutate state.
- Operator cannot approve completion.
- Recovery runs only after an evidence-backed mismatch and has one attempt.
- Security rejections are terminal.
- Synthesiser cannot claim completion unless the verifier status is `VERIFIED_COMPLETE`.
- Canonical evidence comes from independently observed local state, never from a success-shaped receipt.

## Commands

| Command | Purpose |
|---|---|
| `arena-run` | Execute the deterministic paired fixture and write digest-verified artifacts. |
| `arena-replay` | Verify and summarise an existing artifact directory without executing tools. |
| `arena-export-web` | Produce a reduced, non-sensitive data bundle for the static viewer. |

## Verification

The release gate covers:

- Python 3.10, 3.11, 3.12 and 3.13;
- source compilation and the complete unit suite;
- exact reference metrics;
- fairness invariants and bounded role permissions;
- artifact determinism and SHA-256 manifests;
- tamper and unlisted-file rejection;
- read-only replay;
- clean-wheel installation and command execution;
- static-viewer accessibility, local-data and no-external-runtime checks;
- vendored verifier integrity.

Run locally:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verify_release.py
```

## Repository map

```text
src/agent_reliability_arena/   experiment, orchestration, metrics and replay
src/completion_verifier/       digest-pinned v0.6.0 verifier snapshot
examples/                      source-controlled fixture configuration
reference_runs/fixture-v1/     reproducible evidence bundle
web/                           static employer-facing trace viewer
web/data/                      reduced verified public export
tests/                         fairness, reliability, artifact and UI tests
docs/                          methodology, contribution and demo narrative
```

## Next empirical phase

A later release can replace deterministic role policies with a versioned real-model transport. Comparative claims will require:

- explicit model snapshots and prompt versions;
- repeated paired runs on the same scenario seeds;
- measured token usage, latency and dated prices;
- uncertainty intervals and absolute counts;
- provider failures separated from orchestration failures;
- public disclosure bundles derived from replayable raw artifacts.

No real-model result should be described as representative from a single run.

## Authorship and AI assistance

See [docs/CONTRIBUTION.md](docs/CONTRIBUTION.md). The repository distinguishes Luca Panayiotou's problem framing and acceptance standard from AI-assisted implementation, documentation and testing.

## Licence

MIT. The vendored verifier carries the same licence and remains attributed in [VENDORED_VERIFIER.md](VENDORED_VERIFIER.md).
