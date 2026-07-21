# v0.1.0 GitHub CI verification

This documentation-only commit exists to trigger an inspectable pull-request matrix after the permanent workflow became available on `main`.

The runtime source, deterministic reference artifacts, metrics, tests, verifier snapshot and static viewer are unchanged from published commit `a169219bfeff2241d564f671718bee42990c2b64`.

The verification PR must pass Python 3.10, 3.11, 3.12 and 3.13, including source tests, release verification, clean-wheel tests, installed commands, replay, deterministic artifact comparison and dependency checks.
