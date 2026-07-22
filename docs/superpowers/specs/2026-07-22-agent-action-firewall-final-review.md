# Agent Action Firewall — Final Adversarial Review

Date: 2026-07-22  
Base specification: `2026-07-22-agent-action-firewall-design.md`  
Lyra-100 record: `2026-07-22-agent-action-firewall-lyra-100-review.md`  
Status: Normative corrections required before implementation

This review was performed after reading the committed design with fresh eyes. Where this document is more specific than the base specification, this document takes precedence.

## Review conclusion

The strengthened deterministic policy compiler and stateful permit-enforcement architecture remains the correct design. No product-level redesign is needed.

The review found several places where the original text was directionally correct but not yet exact enough to implement or claim publicly.

## 1. Tool descriptor has two identities

A trusted descriptor contains:

- **security fields** used for matching and permit binding;
- **display metadata** used only for human explanation.

The compiler produces:

- `descriptor_security_digest` over capability ID, capability version, operations, resource kinds, side-effect classes, required action fields and resolver requirements;
- `descriptor_artifact_digest` over the complete canonical descriptor including untrusted display metadata.

Action, challenge, approval and permit binding use `descriptor_security_digest`.

Changing only a display name or description changes the artifact digest but does not change authority, invalidate approval or invalidate a permit. Changing any security field does.

This resolves the earlier contradiction between “the descriptor digest covers every field” and the metamorphic requirement that descriptions do not affect authority.

## 2. Canonical action is produced by the trusted normaliser

Callers provide a native proposed action. They do not author authoritative fields such as:

- `normalised_path`;
- resolved filesystem path;
- resolver evidence digest;
- canonical hostname;
- descriptor security digest;
- derived principal digest;
- action digest.

The trusted normaliser constructs those fields from the registered descriptor, native action and trusted deployment adapters. The canonical action digest covers the resulting normalised action.

For filesystem actions, the permit binds both the declared path and trusted resolution result. A caller-supplied resolver claim is untrusted metadata and cannot satisfy a resolver requirement.

## 3. Policy attenuation is finite and decidable

A baseline allow envelope must enumerate finite sets for:

- capability IDs;
- operations;
- principal IDs and/or principal types;
- resource kinds;
- environments;
- side-effect classes.

Child allow-capable selectors must be element-wise subsets of one reachable parent allow envelope. A child deny may target any selector because it only removes authority.

Constraint subset rules are exact:

| Constraint | Child is narrower when |
|---|---|
| finite allowlist | child set is a subset |
| path roots | every child root is equal to or a descendant of a parent root using the same path style |
| domain allowlist | every child domain is equal to or a label-boundary subdomain of a parent domain |
| numeric maximum | child value is less than or equal |
| TTL maximum | child value is less than or equal |
| required boolean control | child may change false to true, never true to false |
| allowed data classes | child set is a subset |
| retry maximum | child value is less than or equal |

A missing constraint means unbounded only where the schema explicitly defines an unbounded parent. Unknown constraint types are compilation errors. The compiler never guesses a subset relation.

## 4. Constraint intersection is explicit

At runtime:

- finite allowlists use set intersection;
- path roots retain the narrower overlapping roots;
- domain allowlists retain the narrower label-boundary domains;
- numeric and TTL maxima use the minimum;
- required booleans use logical OR;
- allowed data classes use set intersection;
- retry maxima use the minimum.

An empty finite intersection, incompatible path styles, non-overlapping roots or unsupported combination yields `DENY` with `POLICY_CONSTRAINT_CONFLICT`.

`ALLOW` is returned only when the effective constraint object is semantically unbounded. Any effective restriction produces `ALLOW_WITH_CONSTRAINTS`.

## 5. Approval challenge binds effective scope

The challenge binds:

- the canonical action digest;
- descriptor security digest;
- compiled policy digest;
- context digest;
- principal digest;
- aggregate matched approval rule IDs;
- the evaluator’s **effective required constraints**;
- required approver roles;
- issue/expiry values;
- nonce.

It does not rely only on caller-requested constraints.

An approval grant may retain or tighten the effective required constraints. It may not widen them.

## 6. Approval and permit keys are separate roles

Two HMAC key purposes exist:

- approval-authority keys authenticate grants;
- firewall-enforcement keys authenticate receipts and permits.

They use different domain separators even when a demonstration intentionally uses the same test bytes.

Production documentation recommends separate key custody. The project does not claim physical separation merely because key IDs differ.

CLI key resolution:

- `firewall-approve` receives one approval key file and declared key ID;
- `firewall-evaluate` receives an approval key directory or injected `ApprovalKeyResolver` that resolves the grant’s `key_id`;
- enforcement mode separately receives one firewall permit key file and key ID;
- `firewall-evaluate verify-permit` receives only the firewall permit key resolver.

Key paths must be regular files, symbolic links are rejected, and key content must be at least 32 bytes. The implementation can validate length but cannot prove randomness; documentation instructs generation from a cryptographically secure random source.

## 7. Approval grants are one-time

A valid grant may mint at most one permit.

The SQLite state store additionally contains consumed approval-grant digests and challenge nonces.

Permit issuance for an approval-required action:

1. re-evaluates current action, descriptor, policy and context;
2. verifies the grant and challenge binding;
3. begins `BEGIN IMMEDIATE`;
4. rejects a previously consumed grant or challenge nonce;
5. records the grant as consumed and the permit digest as issued;
6. updates clock-regression state;
7. commits;
8. atomically writes the permit output.

A crash after database commit but before permit output loses that approval safely; a new approval is required. The system must never roll back grant consumption merely to improve availability.

Non-approval actions do not consume an approval record.

## 8. Permit issue and consume are distinct states

The replay database records:

- consumed approval grant;
- issued permit digest/nonce;
- consumed permit digest/nonce;
- expiry;
- associated decision receipt ID;
- last accepted wall-clock time.

`verify_and_consume` accepts only a permit recorded as issued and not yet consumed. This prevents a correctly MACed but never issued permit object from being accepted when the key is shared across components.

Permit issuance and consumption are separate transactions because execution occurs later. Both use `BEGIN IMMEDIATE`.

## 9. Receipt identity and authenticity are different

A receipt body excludes `receipt_id` and `receipt_mac`. The ID is:

```text
SHA256(RECEIPT_DOMAIN || canonical(receipt_body))
```

Internal ID verification detects accidental corruption and alteration relative to a retained expected ID. An attacker able to rewrite the receipt can also recompute the ID.

In enforcement mode, the firewall adds `receipt_key_id` and `receipt_mac`. A valid HMAC authenticates possession of the configured firewall key.

Public wording must use:

- **content-addressed receipt** for an unhashed/ID-only analysis artifact;
- **HMAC-authenticated receipt** when a valid MAC is present.

The generic phrase “tamper-evident receipt” may be used only when the expected receipt ID is retained independently or an HMAC is verified, and that condition must be stated.

`firewall-explain` verifies internal identity by default. Optional `--expected-receipt-id` or firewall key verification upgrades the assurance. It must display which assurance was achieved.

## 10. Semantic decision determinism is separate from artifact freshness

For identical canonical action, descriptor security fields, compiled policy and context, the semantic decision, matched rules and effective constraints are deterministic.

Challenge nonces, permit nonces, evaluation timestamps and expiry values vary in normal operation. Deterministic fixtures inject clocks and nonce factories.

Documentation must not claim byte-identical challenges or permits across ordinary repeated evaluations.

## 11. Approval does not bypass fresh policy evaluation

Supplying a valid grant does not directly transform `REQUIRE_APPROVAL` into allow.

The evaluator performs a fresh normalisation and policy evaluation. The grant is accepted only when the newly generated aggregate challenge body—excluding fresh nonce and issue time—matches the approved challenge scope and every bound digest remains current.

A current hard deny, missing field, conflict or stricter policy remains denied regardless of the grant.

## 12. State and clock handling

Clock checks and state transitions occur inside the same SQLite transaction used for grant issuance or permit consumption.

The retained wall-clock value detects local regression beyond a configured tolerance. It is not trusted time and cannot defend against a privileged attacker who can rewrite the database and clock.

Analysis mode may evaluate without the state database. Enforcement mode cannot issue or consume permits without a writable state database.

## 13. Atomic output rules

Compiled policy bundles, challenges, grants, receipts, permits and disclosure files use temporary siblings, `flush`, `fsync`, `os.replace` and best-effort directory `fsync`.

Output directories may be replaced only when they contain a matching firewall-generated manifest and product marker. Unrelated directories are never recursively deleted.

Key files and replay databases are never copied into output bundles.

## 14. Revised command details

`firewall-evaluate evaluate` in enforcement mode additionally requires:

```text
--permit-key-id ID
--permit-key-file FILE
--replay-db FILE
```

When an approval grant is supplied, it additionally requires one of:

```text
--approval-key-dir DIR
```

or an injected library key resolver. The directory maps safe key IDs to regular files; traversal, symbolic links and unknown IDs are rejected.

`firewall-evaluate verify-permit` validates the recorded-issued state before consuming the permit.

`firewall-explain` supports:

```text
--expected-receipt-id HASH
--receipt-key-dir DIR
```

as optional assurance upgrades.

## 15. Added adversarial cases

The corpus must also include:

48. descriptor display metadata changes without authority change;
49. descriptor security field changes invalidating approval and permit;
50. approval grant reused to request a second permit;
51. correctly MACed but unrecorded permit;
52. permit output lost after grant consumption;
53. caller-forged resolver evidence;
54. receipt ID recomputed after alteration without a valid MAC;
55. analysis receipt explained as internal-only assurance;
56. approval and permit key IDs confused;
57. key path symbolic-link rejection;
58. child allow selector not contained by one parent envelope;
59. policy rule reorder preserving semantic decision and compiled digest;
60. repeated ordinary evaluation preserving semantic decision but changing nonce-bearing artifacts.

## 16. Final claims boundary

The project may claim that, under its deployment assumptions, it:

- deterministically evaluates canonical proposed actions;
- rejects widening policy overlays;
- binds approval and permits to exact security identities;
- prevents one consumed approval from minting multiple permits;
- rejects unissued, expired, changed or replayed permits;
- returns explainable rule and constraint evidence.

It may not claim that:

- content hashing alone authenticates a receipt;
- descriptor display metadata is security-relevant;
- shared-secret possession proves legal identity;
- local state or time is immune to privileged modification;
- the firewall controls tools that can bypass its gateway;
- authorisation proves successful execution.

## 17. Self-review checklist

Confirmed after these corrections:

- no model is inside the trusted enforcement path;
- policy attenuation and constraint intersection are finite and implementable;
- tool display text cannot silently influence authority;
- approval keys and permit keys have distinct roles;
- an approval grant is one-time;
- permits must have been recorded as issued before consumption;
- caller-forged derived fields cannot satisfy policy;
- receipt identity is not confused with authentication;
- ordinary freshness fields are not confused with semantic determinism;
- all output and state transitions have a fail-closed crash rule;
- commercial and employer claims remain narrower than the design evidence.

The design is ready for user review and, after approval, implementation planning.