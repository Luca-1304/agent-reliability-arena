# Citation Package Reproducibility

This procedure verifies the public deterministic fixture, provider-free safeguards, showcase, launch package and citation package. It requires no provider credential and makes no external model request.

Expected boundary:

```text
provider_called: false
comparative_claim_permitted: false
```

## Supported environments

The release matrix covers CPython 3.10, 3.11, 3.12 and 3.13 on GitHub Actions. The project has no runtime dependencies outside the Python standard library.

## Setup

```bash
git clone https://github.com/Luca-1304/agent-reliability-arena.git
cd agent-reliability-arena
git checkout main

python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

## Reproduce the deterministic fixture

```bash
arena-run \
  --config examples/fixture_experiment.json \
  --output runs/fixture-v1

arena-replay --input runs/fixture-v1

arena-export-web \
  --input runs/fixture-v1 \
  --output runs/fixture-v1-public.json
```

Expected independently verified fixture counts:

- General: `2/8`
- Unified specialists: `6/8`
- False-completion reduction: `3`
- Additional logical calls: `36`

These are deterministic fixture values, not real-model benchmark measurements.

## Verify provider-free safeguards

```bash
arena-preflight-pilot \
  --config examples/fixture_experiment.json \
  --catalog examples/live_prompt_catalog.json \
  --policy examples/pilot_policy.disabled.json

python scripts/verify_release.py
python scripts/verify_disclosure_release.py
python scripts/verify_repeated_release.py
```

The committed pilot policy keeps external execution disabled. **No real-provider benchmark** is part of this procedure.

## Verify public publication packages

```bash
arena-verify-showcase --root .
arena-verify-launch-package --root .
arena-verify-citation-package --root .
```

Each command is local-only and fail-closed. The citation verifier checks the release metadata, report limitations, reproducibility commands, provenance schema, file digests and prohibited private markers.

## Run the complete suite

```bash
python -m compileall -q src tests scripts
python -m unittest discover -s tests -p "test_*.py" -v
python -m pip check
```

## Interpretation boundary

Successful reproduction verifies software behavior and public provenance. It is not production readiness, a real-provider performance result, a cost comparison, a statistical generalisation or unrestricted-tool safety evidence.
