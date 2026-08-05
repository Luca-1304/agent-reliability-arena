# Vercel hosting status

GitHub Pages is the canonical public hosting path for Agent Reliability Arena.

Two historical Vercel projects remain attached at the account level:

- `agent-reliability-arena`
- `agent-reliability-arena-ytop`

They are decommissioned and must not be treated as canonical production. Repository configuration now sets `git.deploymentEnabled` to `false`, so future Git pushes are not intended to create Vercel production or preview deployments for either project.

The earlier `ignoreCommand: "exit 0"` workaround was removed because it still created a cancelled deployment record for every push. The previous one-time device-authentication deletion workflow was also removed because it could write an encrypted handoff commit from inside a push-triggered job, causing repeated Git and Vercel activity without completing project deletion.

## Safe cleanup boundary

- Do not add another repository workflow that performs interactive Vercel login.
- Do not place Vercel tokens, device codes or authentication responses in source, workflow logs, pull requests or chat.
- Keep Vercel Git deployments disabled while GitHub Pages remains canonical.
- Remove or disconnect the two projects only through authenticated Vercel account controls or a supported private API action.
- Historical cancelled deployments may remain visible as audit history; do not create new pushes solely to clear them.
