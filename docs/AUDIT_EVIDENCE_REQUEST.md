# AI Agent Reliability Audit — Evidence Request

Provide only evidence relevant to the scoped workflow. Redact or replace sensitive values wherever practical.

## Preferred evidence

- workflow diagram or concise step list;
- exact requested outcome and current success criteria;
- representative tool-call or execution traces;
- final external-state records where available;
- retry, timeout, rollback and failure logs;
- current prompts/instructions relevant to completion handling;
- staging fixtures or deterministic reproductions;
- known incident or manual-cleanup examples;
- current human approval and escalation rules.

## Do not provide

- API keys, passwords or private keys;
- session cookies or authentication headers;
- full environment-variable dumps;
- unrelated customer or employee data;
- unrestricted production credentials;
- secrets embedded in screenshots, logs or exported traces.

## Redaction guidance

Replace sensitive identifiers consistently so relationships remain reviewable. For example:

- customer email → `customer-01@example.invalid`;
- account ID → `ACCOUNT_A`;
- API token → `[REDACTED_SECRET]`;
- internal hostname → `service-a.internal.invalid`.

Do not redact the workflow structure, event ordering, result status, timestamps needed for sequencing, retry counts or fields used to determine completion.

## Evidence manifest

For each supplied item record:

| Item | Source | Time range | Redactions | Integrity/limitations |
|---|---|---|---|---|
| | | | | |

## Transfer and retention

Use only the agreed evidence location. Do not email credentials or upload private evidence to a public repository. Retention, reviewer access and deletion dates must match the written scope.
