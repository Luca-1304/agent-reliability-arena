# Agent Reliability Arena — launch package

Agent Reliability Arena is an evidence-first engineering project by **Luca Panayiotou**. It compares one general agent with a same-model specialist workflow while holding the task, tools, sandbox, failure schedule and completion contract constant.

The project is designed around a simple rule:

> A completion claim is not accepted until independently observed state satisfies the exact contract.

## Verified public evidence

The public showcase is a **deterministic fixture for software and measurement validation**. It is not a test of a commercial or open model.

In the locked eight-scenario fixture:

- the General condition reached **2/8 independently verified outcomes**;
- the Specialist condition reached **6/8 independently verified outcomes**;
- the Specialist path removed **three false-completion claims**;
- the Specialist path required **36 additional logical role calls**.

Those values are reconstructed by the public verifier from the committed fixture. Token use, latency and monetary cost are not invented.

Start here:

- [Public showcase](SHOWCASE.md)
- [Interactive trace viewer](web/index.html)
- [Employer technical summary](docs/EMPLOYER_TECHNICAL_SUMMARY.md)
- [Publication boundary](docs/PUBLICATION_BOUNDARY.md)
- [Launch-package verification](showcase/launch-package-manifest.json)

## What the engineering demonstrates

- deterministic experiment and fairness controls;
- bounded Strategist, Operator, Auditor, Recovery and Synthesiser responsibilities;
- exact contract authorisation before mutation;
- independent observation rather than success-shaped receipts;
- tamper-evident evidence and replay;
- provider-free live-path rehearsal;
- controlled pause, continuation and terminal abort handling;
- disclosure-safe public evidence generation;
- cross-version source, wheel and clean-install verification.

## Use this package

- [CV project entry](docs/CV_PROJECT_ENTRY.md)
- [Portfolio project entry](docs/PORTFOLIO_PROJECT_ENTRY.md)
- [Recruiter outreach](docs/RECRUITER_OUTREACH.md)
- [Public launch posts](docs/LAUNCH_POSTS.md)
- [Technical-community submission copy](docs/COMMUNITY_SUBMISSIONS.md)
- [Hosted deployment readiness](docs/HOSTED_DEPLOYMENT.md)
- [Distribution register](showcase/distribution-register.json)

Verify the exact package locally:

```bash
python -m pip install --editable .
arena-verify-showcase --root .
arena-verify-launch-package --root .
```

Both commands read local public files only and make no provider request.

## Authorship and assistance

**Luca Panayiotou** set the problem direction, acceptance standard, publication boundary and approval to release the showcase. The repository records **AI-assisted implementation**, testing and documentation transparently.

## Evidence boundary

This package demonstrates the design and verification of the evaluation system. It does not turn the deterministic fixture into evidence about external models, deployed systems or real operating costs. Real-provider work remains a separate, deliberately approved stage.
