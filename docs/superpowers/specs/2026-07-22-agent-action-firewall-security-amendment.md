# Agent Action Firewall — Security Amendment

Date: 2026-07-22  
Applies to: the base design, Lyra-100 review and final adversarial review  
Tracking issue: #6  
Status: Normative; closes remaining pre-implementation gaps

This amendment takes precedence where earlier documents are less specific.

## 1. Trusted approver registry

### Remaining defect

The final adversarial review separated approval and permit key purposes, but a grant still carried caller-supplied `approver_id` and `approver_role`. A MAC proves possession of a key; without a trusted key-to-authority registry it does not prove that the key is authorised for the asserted identity or role.

### Required registry

Enforcement mode requires a canonical approver registry maintained outside the proposing agent’s control:

```json
{
  "schema_version": "1",
  "registry_generation": 3,
  "approval_keys": [
    {
      "key_id": "owner-key-1",
      "approver_ids": ["user:luca"],
      "approver_roles": ["owner"],
      "status": "active",
      "not_before": "2026-07-22T00:00:00Z",
      "not_after": "2027-07-22T00:00:00Z"
    }
  ],
  "permit_issuers": [
    {
      "key_id": "firewall-permit-1",
      "issuer_id": "service:agent-action-firewall",
      "status": "active",
      "not_before": "2026-07-22T00:00:00Z",
      "not_after": "2027-07-22T00:00:00Z"
    }
  ]
}
```

The registry contains metadata only, never key bytes.

The canonical `trust_registry_digest` is bound into:

- context;
- decision receipt;
- approval challenge;
- approval grant body;
- execution permit.

Grant validation derives allowed IDs and roles from the current active registry entry. Caller-supplied identity fields must exactly match that entry. Unknown, inactive, future, expired or removed keys fail authentication.

The demonstration registry binds Luca as the sole `owner`. Generic library users may explicitly define other principals.

Registry rotation changes the digest and invalidates stale challenges, grants and permits.

## 2. Approval and permit key separation is enforced

Approval-authority and permit-issuer keys must use:

- different key IDs;
- different key files;
- different key bytes;
- different HMAC domain separators.

Policy/configuration lint compares the loaded key bytes when both are supplied and rejects reuse. Fixed public test keys are synthetic and remain separate.

This supersedes the earlier allowance that demonstration keys could share bytes.

## 3. Immutable verified action

`PermitVerifier.verify_and_consume` returns a frozen `VerifiedAction`, not a mutable dictionary.

It contains:

- exact canonical action bytes;
- a recursively immutable parsed representation using frozen dataclasses, tuples and read-only mappings;
- action digest;
- descriptor security digest;
- compiled policy digest;
- context digest;
- trust registry digest;
- immutable effective constraints;
- permit digest;
- decision receipt ID.

The supported executor adapter consumes the canonical bytes or immutable representation returned by verification. It must not reconstruct arguments from the unverified input.

This prevents accidental mutation inside the supported path. It does not make a deliberately dishonest external executor trustworthy.

## 4. Atomicity claim is narrowed

SQLite transactions atomically prevent two cooperating processes from consuming the same grant or permit. Permit consumption is not atomic with the external tool side effect.

Required public wording:

> The firewall atomically prevents replay of one-time grants and permits. The tool side effect remains a separate executor operation.

A scheduling or process boundary remains after verification. Eliminating that final gap would require integration inside the tool implementation and is outside v0.1.0.

## 5. Exact post-approval decision

Without a grant, a matched approval rule returns `REQUIRE_APPROVAL` and a challenge.

With a valid current one-time grant:

1. the action is freshly normalised;
2. current descriptor, policy, context and trust registry digests are recomputed;
3. hard denies and conflicts are evaluated first;
4. the grant is validated against the aggregate current approval scope;
5. approval-rule constraints and grant constraints are intersected;
6. an empty or undefined intersection returns `DENY` with `APPROVAL_CONSTRAINT_CONFLICT`;
7. otherwise the final decision is `ALLOW_WITH_CONSTRAINTS` when any restriction remains, or `ALLOW` only when semantically unbounded.

The receipt records:

```json
{
  "preapproval_decision": "REQUIRE_APPROVAL",
  "approval_satisfied": true
}
```

A grant is never a wildcard and never overrides a hard deny.

## 6. Receipt assurance labels

Receipt assurance is explicit:

- `CONTENT_ADDRESSED` — body matches its content-derived receipt ID;
- `MAC_AUTHENTICATED` — body and ID also verify under an active permit-issuer key in the current trust registry;
- `INVALID` — identity, registry or MAC verification failed.

A content ID alone is not authenticated evidence because an attacker able to rewrite the receipt can recompute it.

## 7. Resolver, redirect and destination limits

### Filesystem

Resolver evidence must be produced by a trusted registered resolver, not accepted merely because a caller supplied a digest. The resolver identity and evidence digest are bound into context and permit.

Lexical and resolver checks do not universally eliminate post-check path replacement. High-assurance executors should operate through a handle obtained during trusted resolution. A universal cross-platform handle-based executor is outside v0.1.0.

### Network

Policy authorises canonical scheme, hostname, port and path class. Hostname policy alone does not prevent DNS rebinding.

Deployments requiring address-level containment must provide registered resolver evidence and bind the resolved addresses to the permit.

Every redirect is a new destination and requires fresh firewall evaluation. Following an unverified redirect is outside the supported guarantee.

### Messaging

Recipients are represented as separate canonical `to`, `cc` and `bcc` sets. Adding an address or moving it between sets changes the action digest and requires re-evaluation. The local part is preserved exactly; only the domain is lower-cased and IDNA-normalised.

### Financial

Numeric limits compare only when exact currency identifiers match. v0.1.0 performs no exchange-rate conversion. Cross-currency comparison is a deterministic denial or compilation conflict, never an approximation.

## 8. Policy publication is transactional

`firewall-policy compile`:

1. parses ordinary strict UTF-8 JSON;
2. rejects duplicate and post-NFC duplicate keys, floats, unsafe integers, surrogates and unsupported fields;
3. compiles canonical semantic objects;
4. writes to a temporary sibling directory;
5. verifies every digest and manifest entry;
6. flushes files;
7. atomically replaces a prior firewall-generated target where supported.

It refuses to replace an unrelated non-empty directory. Failed compilation writes diagnostics only and publishes no authoritative policy digest.

Whitespace and object-key order do not affect security identity. Rule and layer arrays are sorted semantically so harmless source reordering preserves the compiled-policy digest.

## 9. Additional required adversarial tests

Add tests proving:

1. self-asserted `owner` role is rejected without a matching active registry entry;
2. inactive, future, expired and removed approval keys are rejected;
3. registry rotation invalidates stale grant and permit;
4. approval and permit key byte reuse is rejected;
5. one grant cannot issue two permits;
6. a security descriptor change invalidates permit while display-only change preserves authority;
7. source action mutation cannot alter returned `VerifiedAction`;
8. recomputed receipt ID without a valid MAC is not authenticated;
9. approval-constraint conflict denies;
10. redirect destination requires fresh evaluation;
11. moving a recipient from `cc` to `bcc` changes action identity;
12. cross-currency limits are not compared;
13. exactly one process consumes a shared permit.

## 10. Final claims boundary

The project may claim deterministic policy resolution, monotonic attenuation, authenticated one-time capabilities and atomic replay prevention inside the cooperating SQLite-backed enforcement path.

It must also state that:

- registry metadata and HMAC prove configured authority, not legal identity;
- state atomicity is separate from the tool side effect;
- gateway adoption and executor compliance are required;
- local time is not trusted time;
- resolver evidence narrows but does not universally remove TOCTOU or DNS risks;
- authorisation is not proof of successful execution;
- deterministic fixtures are not certification or a production penetration test.

With this amendment, the design is ready for implementation planning.