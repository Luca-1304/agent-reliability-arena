# Vercel hosting status

GitHub Pages is the canonical public hosting path for Agent Reliability Arena.

Two historical Vercel projects remain attached at the account level:

- `agent-reliability-arena`
- `agent-reliability-arena-ytop`

They are decommissioned and must not be treated as canonical production. Their Git-triggered deployments are intentionally ignored/cancelled until the projects can be removed or disconnected through Vercel account controls.

The previous one-time device-authentication deletion workflow was removed because it could write an encrypted handoff commit from inside a push-triggered job, causing repeated Git and Vercel activity without completing project deletion.

## Safe cleanup boundary

- Do not add another repository workflow that performs interactive Vercel login.
- Do not place Vercel tokens, device codes or authentication responses in source, workflow logs, pull requests or chat.
- Remove or disconnect the two projects only through authenticated Vercel account controls or a supported private API action.
- Until then, avoid unnecessary pushes solely to clear historical cancelled deployment entries.
