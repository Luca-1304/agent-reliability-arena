# Security Policy

Agent Reliability Arena is an alpha-stage research and engineering project. Security reports are welcome, but this repository and its release evidence provide **no guarantee** that the software is vulnerability-free, production-ready or safe for unrestricted tools. The published hardening work is **not an exhaustive security audit**.

## Supported versions

| Version | Security support |
|---|---|
| Current `main` branch | Best-effort fixes and review |
| `v0.2.0rc1` prerelease | Critical disclosure review; fixes may land on `main` first |
| Older snapshots | Not actively supported |

## Private vulnerability reporting

Use **GitHub private vulnerability reporting** from the repository **Security** tab and choose **Report a vulnerability**. This keeps exploit details out of public issues and pull requests while a report is assessed.

Please include, when safely available:

- the affected commit, tag or file;
- the security boundary or invariant involved;
- reproduction steps using inert test data;
- expected and observed behaviour;
- likely impact and prerequisites;
- suggested mitigations, if known.

**Do not include credentials**, API keys, access tokens, private prompts, raw provider payloads, private ledgers, personal information or third-party secrets. Revoke any accidentally exposed credential before continuing the report.

If private reporting is unavailable, open a minimal public issue requesting a private channel. Do not include exploit instructions or sensitive evidence in that issue.

## Coordinated disclosure

Please allow reasonable time for triage, reproduction and a fix before public disclosure. The project will use best efforts to acknowledge valid reports, preserve reporter credit when requested and publish accurate remediation notes. No fixed response or remediation deadline is promised.

Good-faith research should avoid:

- accessing data that is not yours;
- executing real provider requests without the account owner's approval;
- increasing spend or consuming another person's quota;
- disrupting repository, CI, hosting or third-party services;
- publishing credentials, private evidence or weaponised exploit details.

## Scope notes

The repository contains provider adapters, private-run safeguards, bounded file mutation and disclosure tooling. Real external execution remains disabled by default and is subject to separate approvals. A passing test suite, CodeQL result, SBOM verification or release checksum is evidence for a specific control only; it is not a general security certification.

For public architecture and limitations, see `docs/THREAT_MODEL.md`, `docs/SUPPLY_CHAIN_SECURITY.md` and `docs/TECHNICAL_REPORT.md`.
