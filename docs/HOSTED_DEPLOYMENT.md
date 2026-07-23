# Hosted deployment readiness

## Verified source

The only approved hosted-site source is the existing public `web/` directory, as verified by:

- `showcase/publication-manifest.json`;
- `arena-verify-showcase --root .`;
- the permanent Python 3.10–3.13 source and clean-wheel matrix.

The site consists of static HTML, CSS, JavaScript and the locked deterministic fixture export. It requires no provider key, server process, database or private evidence directory.

## Current state

**No hosted deployment is claimed live.**

The repository contains deployment-ready static files, but enabling a hosting service changes external repository or platform settings. That action must be performed through an authorised account and confirmed by a public URL.

## Safe deployment sequence

1. Verify the repository checkout:

   ```bash
   python -m pip install --editable .
   arena-verify-showcase --root .
   arena-verify-launch-package --root .
   ```

2. Configure the chosen static host to publish only the `web/` directory.
3. Do not add environment variables, credentials or private artifacts.
4. Confirm that `web/data/fixture-v1.json` loads and the scenario selector works.
5. Re-run the public verifier against the exact source commit used for deployment.
6. Record the public HTTPS URL, source commit and publication date in `showcase/distribution-register.json`.
7. Re-run `arena-verify-launch-package --root .` after updating the register and its pinned manifest digest.

## GitHub Pages route

A suitable repository-owner action is:

- open repository **Settings → Pages**;
- select a GitHub Actions or branch-based static deployment source;
- configure it to publish `web/` only;
- verify the resulting public URL before changing the distribution state from `blocked` or `prepared`.

Repository files alone do not prove that Pages is enabled, so this package does not claim that setting was changed.

## Alternative static hosts

The same `web/` directory can be deployed to another reputable static host. The publication boundary remains identical: only the verified static bundle is allowed, and the host must not receive private prompts, provider records, ledgers, local paths or credentials.

## Rollback

If a deployed site differs from the verified bundle, exposes unintended files or presents unsupported claims:

1. disable or remove the deployment;
2. retain the public URL and incident note in the register;
3. restore the last verified source commit;
4. rerun both public verifiers before republishing.
