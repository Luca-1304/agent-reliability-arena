# First real-provider pilot candidate

Status: **provider-free review candidate; external execution disabled**

Prepared: 2 August 2026

## Selected model

- Provider: `openai-responses`
- Pinned model ID: `gpt-5-mini-2025-08-07`
- Model version: `2025-08-07`
- Prompt version: `fixture-prompts-v1`
- Controlled scenario: `success`

A pinned snapshot is used instead of a moving alias so the pilot remains attributable to one model version.

## Official capability and price source

OpenAI's model documentation, checked on 2 August 2026, lists `gpt-5-mini-2025-08-07` as a GPT-5 mini snapshot supported by the Responses API. The listed standard text-token prices are USD $0.25 per million input tokens and USD $2.00 per million output tokens.

Source: <https://developers.openai.com/api/docs/models/gpt-5-mini>

This repository does not treat that webpage as measured billing evidence. Actual provider usage belongs in the private transport ledger, and later cost calculation must preserve a dated price source separately.

## Reviewed policy ceiling

The committed review policy permits:

- exactly 8 planned calls;
- at most 2,068 requested output tokens across the call plan;
- a conservative 2,048 total-token reservation per call;
- at most 16,384 reserved total tokens;
- GBP 0.02 reserved per call;
- a hard GBP 0.20 total ceiling;
- no automatic expansion or extra call;
- external execution disabled.

The monetary reservation is intentionally much larger than a simple token-price estimate for the stated token ceiling. It is an operator safety ceiling, not a prediction or statement of actual billing.

## Provider-free preflight

```bash
arena-preflight-pilot \
  --config examples/pilot_experiment.gpt-5-mini-2025-08-07.json \
  --catalog examples/live_prompt_catalog.json \
  --policy examples/pilot_policy.gpt-5-mini-2025-08-07.review.json
```

Acceptance conditions before preparing a private enabled copy:

- command exits successfully;
- `provider_called` is `false`;
- `external_execution_enabled` is `false`;
- provider and pinned model fields match exactly;
- planned call ceiling is 8;
- scenario list contains only `success`;
- reserved total tokens are 16,384 or lower;
- reserved cost is 16 pence or lower;
- maximum cost is exactly 20 pence;
- all policy, configuration, contract, prompt-catalogue and manifest digests are present.

## Deliberate execution boundary

The committed policy must never be edited in place to enable execution. After the preflight is reviewed, create a private copy outside the repository, change only `external_execution_enabled` to `true`, rerun preflight, review the new policy digest, and use a fresh private run directory.

`OPENAI_API_KEY` must be supplied through the local process environment only. Do not put it in GitHub Actions, source, JSON, screenshots, issues, pull requests, logs or command arguments.

The operator must still supply both explicit approvals required by `scripts/run_private_pilot.py`. Completing one pilot would prove only that this controlled real-provider path executed and preserved evidence. It would not establish general model performance or specialist-system superiority.
