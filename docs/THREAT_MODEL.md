# Threat model and trust boundary

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
