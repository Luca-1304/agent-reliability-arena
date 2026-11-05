# Threat model and trust boundary — baseline plus current scope

## Protected claim

A task may be reported complete only when independently observed local state satisfies the exact file contract.

## Untrusted inputs

- deterministic role-policy output;
- source tool reports and success-shaped receipts;
- attempted paths and content;
- role handoff text;
- public-export consumers.

## Trusted components in v0.1

- source-controlled experiment configuration;
- `SafeFileSandbox` path confinement;
- independent file observation;
- Agent Completion Verifier v0.6.0 evaluation rules;
- SHA-256 artifact manifests;
- release tests and clean-wheel verification.

## Threats covered

- fabricated success without mutation;
- partial or wrong content;
- rollback after apparent success;
- timeout before and after mutation;
- path traversal;
- symlink escape;
- orchestration claiming completion over a failed verifier status;
- duplicate or mismatched experiment pairs;
- modified or unlisted evidence artifacts;
- public viewer receiving data outside the verified export.

## Threats not covered

- hostile native code or kernel-level attacks;
- remote-system identity and authorization;
- compromised Python runtime or operating system;
- SHA-256 collision attacks;
- confidentiality of arbitrary secrets placed in fixture content;
- external-model prompt injection, because no external model runs in this release;
- production-grade sandbox isolation.

The local sandbox is an evaluation boundary for controlled fixtures, not a containment claim for adversarial code.


## Current scope: v0.2.0rc2 and subsequent provider-free Stage 7 hardening

The sections above document the **v0.1.0 deterministic fixture baseline**. The current codebase also contains a versioned provider-neutral request interface, an HTTPS Responses transport, role-based orchestrators, private evidence ledgers, disclosure-safe export, repeated-experiment planning and an explicitly gated local real-provider pilot path. The existence of these interfaces does **not** mean a live provider experiment was performed. The current published comparative evidence remains scripted/deterministic.

### Additional assets and trust boundaries

- **Operator authority and cost:** an exact reviewed execution policy, preflight call plan, explicit operator approval, local token/monetary reservation limits and external-network approval are separate gates; these controls limit intended execution, not downstream provider billing or third-party compromise.
- **Credential and provider identity:** credentials are supplied explicitly to the private runtime; provider-reported model identity must be present and match the requested model before results enter orchestration. A provider API response is still an external trust boundary.
- **Data provenance:** immutable private run indexes, hash-chained transport records and independent local observations protect consistency against detected modification. SHA-256 commitments alone do not provide independent external notarization or hardware-backed nonrepudiation.
- **Output and mutation:** six strict role schemas, exact file contracts, bounded writes and terminal security failure handling restrict source-reported success. The local sandbox is not OS-grade isolation for hostile executable code.
- **Public disclosure:** public evidence is derived from verified private records through an allow-list exporter; raw prompts, outputs, credentials, provider IDs and local machine details remain private. Public bundles must not include selective omission of failed/aborted runs.
- **Privacy execution hold:** the historical hosting/privacy closure described in `docs/HOSTING_PRIVACY_BOUNDARY.md` and tracked in issue #14 is an independent release/execution condition. The source-controlled Stage 7 privacy gate is open and prevents real-provider pilot execution. Do not bypass or close it until all closure criteria are independently evidenced and the focused change is reviewed.

### Additional threats under test, but not conclusively eliminated

- prompt-injection or malicious content influencing provider outputs;
- contradictory, missing, stale or forged provider messages and response identities;
- cost overrun, duplicate paid calls or execution after an abort;
- inadvertent disclosure through logs, diagnostics, public evidence or GitHub workflow artifacts;
- selection bias, statistical overclaiming and changing provider models/prices;
- tampering of local private evidence when attacker and verifier share the same machine or trust domain;
- stale credentials, compromised runners or upstream service failures;
- accidental execution or publication while the historical privacy incident remains unresolved.

### Security conclusion and remaining work

Provider-free tests establish behaviour for the specific synthetic scenarios covered by the test suite. They do not prove that provider-side systems, GitHub, Vercel, operating systems, users or supply-chain dependencies are trustworthy, nor that every prompt injection, privacy leak, symlink race or concurrency attack is prevented. A complete historical secret scan, attack-surface audit and independent review of all deployed artifacts remain separate work.

A live pilot or production rollout requires independent closure of the privacy gate, explicit scope/spend approval, current model/price confirmation, private credentials and fresh evidence. Neither this document nor passing CI authorises it. See `docs/PROJECT_STATUS.md`, `docs/PRIVATE_PILOT_RUNBOOK.md`, `docs/DISCLOSURE_BOUNDARY.md` and `SECURITY.md` for the authoritative status and operational limits.
