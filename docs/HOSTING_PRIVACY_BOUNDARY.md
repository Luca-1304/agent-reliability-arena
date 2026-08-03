# Hosting and privacy boundary

Last verified: 3 August 2026

## Canonical public route

GitHub Pages is the only supported public hosting route for the portfolio, downloadable public CV, audit page and Arena viewer.

The Pages workflow must continue to:

- build from reviewed `main` only;
- stage an exact allow-list;
- reject symlinks and unexpected files;
- verify the source PDF before staging;
- verify the staged PDF before upload;
- verify the live PDF after deployment;
- allow only the deliberately public contact email;
- reject private personal, referee and credential-shaped content.

## Vercel decommissioning

Vercel is not a supported publication route for this repository.

The repository-root `vercel.json` intentionally keeps future Vercel Git builds fail-closed with `ignoreCommand: "exit 0"` while the two historical Vercel projects and their immutable deployments are removed by Vercel.

Do not restore Vercel deployment, preview or production checks. Do not publish a Vercel URL in repository files, pull-request descriptions, issues or portfolio copy.

## Historical incident boundary

Older Git and Vercel objects contained a CV version with unnecessary personal and third-party information. The current public CV is sanitised and guarded by generic privacy checks. Historical GitHub objects and immutable Vercel deployments are subject to platform-level removal requests.

The historical material must not be reused, linked, mirrored, copied into a new repository or treated as a professional document.

## Execution gate

No real-provider pilot, disclosure export based on real-provider evidence, or new third-party hosting migration should take priority over closing the historical privacy incident.

Provider-free tests, documentation improvements, dependency maintenance and GitHub Pages privacy verification may continue. External execution remains disabled unless separately reviewed after the incident is closed.

## Closure criteria

The incident is closed only when all of the following are verified:

1. affected immutable Vercel deployment URLs return `404` or `410`;
2. both redundant Vercel projects are deleted or confirmed removed by Vercel;
3. GitHub confirms removal of affected historical blobs, pull-request references and cached views;
4. the canonical GitHub Pages CV still passes the source, staged and live privacy verifier;
5. no tracked public file contains a Vercel deployment URL or private contact value.
