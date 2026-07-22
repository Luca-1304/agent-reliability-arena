# Agent Action Firewall v0.1.0 — Design Specification

Date: 2026-07-22  
Status: Proposed written specification after user approval and Lyra-100 review  
Tracking issue: #6  
Future standalone repository: `Luca-1304/agent-action-firewall`

## 1. Public question

> Can dangerous, unauthorised or scope-expanding agent actions be blocked before execution while every allowed action remains explainable and auditable?

## 2. Product decision

Build a deterministic, local-first policy compiler and enforcement runtime that evaluates one canonical proposed tool action before execution.

The trusted core does not use a language model. Provider or agent adapters may translate their native tool calls into the canonical action envelope, but policy resolution, approval validation, replay prevention and permit verification remain deterministic.

The firewall returns one of four decisions:

- `ALLOW`;
- `ALLOW_WITH_CONSTRAINTS`;
- `REQUIRE_APPROVAL`;
- `DENY`.

A decision receipt explains the result. A separate short-lived execution permit is required for enforcement. A receipt is evidence of a decision; it is not itself permission to execute.

## 3. Why this is a distinct portfolio product

The project owns the pre-execution containment boundary:

```text
Human intent
    ↓
Agent Contract Compiler — what counts as acceptable completion?
    ↓
Agent Action Firewall — may this exact action execute now?
    ↓
Tool execution
    ↓
Agent Evidence Ledger — what was recorded?
    ↓
Agent Completion Verifier — did the required postcondition exist?
    ↓
Agent Reliability Arena — which orchestration behaves more reliably?
```

The firewall does not compile unrestricted natural-language intent, execute arbitrary tools, retain a complete evidence history, prove task completion or benchmark model intelligence.

## 4. Approaches considered

### 4.1 Simple denylist

A denylist is quick to implement but cannot express ownership scope, bounded approval, typed resources, policy drift or exact permit binding. It is too easy to bypass through unknown operations or renamed tools.

Rejected as the product foundation.

### 4.2 Deterministic policy compiler and runtime

Strict action schemas, monotonic policy layers, typed constraints, explicit approval challenges, authenticated permits and replay state produce reproducible decisions and a credible enforcement boundary.

Selected.

### 4.3 Model-based safety judge

A model can help humans draft policies or classify unknown requests, but a probabilistic judge is unsuitable as the final enforcement authority and would weaken reproducibility.

Allowed only as a future untrusted advisory adapter.

## 5. Deployment guarantee and assumptions

The firewall can prevent an action only when all of the following are true:

1. every relevant tool action passes through the firewall;
2. trusted tool descriptors are registered outside agent control;
3. the evaluator receives the security-relevant fields needed by policy;
4. the executor verifies and atomically consumes the permit immediately before execution;
5. the executor uses the exact canonical action object returned by permit verification;
6. HMAC keys and replay-state storage are not controlled by the proposing agent;
7. side channels cannot call the tool directly.

The firewall does not prove that context claims, actor labels or tool descriptors are true merely because they were hashed. It proves that a decision or permit was bound to the supplied canonical values.

## 6. Scope

### 6.1 Included in v0.1.0

- strict canonical action envelopes;
- trusted tool capability descriptors;
- JSON policy source and canonical compiled policy bundles;
- monotonic policy layering and capability attenuation;
- deterministic rule matching and conflict resolution;
- typed filesystem, network, messaging and financial resources;
- four decision outcomes;
- exact matched-rule and constraint explanations;
- approval challenges and HMAC-authenticated approval grants;
- short-lived HMAC-authenticated execution permits;
- SQLite-backed one-time replay protection;
- optional local filesystem resolver evidence;
- tamper-evident decision receipts;
- adapters for the Contract Compiler, Evidence Ledger and Completion Verifier;
- deterministic adversarial corpus;
- dependency-free static policy workbench;
- Python 3.10–3.13, source, clean-wheel and archive verification.

### 6.2 Explicit non-goals

- unrestricted natural-language policy generation;
- general tool execution;
- hosted control plane;
- multi-tenant administration;
- public-key infrastructure or certificates;
- proof of human identity;
- legal non-repudiation;
- trusted-time claims;
- automatic compliance certification;
- universal numerical risk score;
- regex policy expressions;
- external-model performance claims;
- revenue claims before real customers or contracts exist.

## 7. High-level architecture

```text
Tool registry ──────────────┐
                            │
Proposed native tool call ──┼──► Adapter / canonical normaliser
                            │               │
Context provider ───────────┘               ▼
                                      Canonical action
                                             │
Policy sources ─► compiler ─► compiled policy│
                                             ▼
                                    Deterministic evaluator
                         ┌───────────┬────────┼───────────────┐
                         │           │        │               │
                       DENY       REQUIRE   ALLOW WITH      ALLOW
                                   APPROVAL  CONSTRAINTS
                                     │        │               │
                                     ▼        └───────┬───────┘
                              Approval challenge      │
                                     │                │
                              Authenticated grant     │
                                     └───────┬────────┘
                                             ▼
                               Short-lived execution permit
                                             │
                                  Atomic verify-and-consume
                                             │
                                             ▼
                               Exact canonical action object
                                             │
                                             ▼
                               External executor / tool runner
```

## 8. Package boundaries

```text
src/agent_action_firewall/
  canonical.py             strict canonical JSON and domain hashing
  models.py                typed public records
  descriptors.py           trusted tool capability registry
  resources.py             typed resource normalisation
  policies.py              source schema and policy compiler
  attenuation.py           monotonic overlay validation
  evaluator.py             deterministic rule aggregation
  approvals.py             challenge and approval-grant handling
  permits.py               permit issue, verify and consume
  replay_store.py          SQLite replay and clock-regression state
  receipts.py              decision receipt construction and validation
  explain.py               human-readable explanation model
  adapters/
    contract_compiler.py
    evidence_ledger.py
    completion_verifier.py
  policy_cli.py
  evaluate_cli.py
  approve_cli.py
  explain_cli.py
```

Each module must have one public responsibility. The firewall package does not import or copy another portfolio project’s implementation.

## 9. Canonical data profile

All security identities use one bounded canonical JSON profile:

- UTF-8 input and output;
- JSON objects, arrays, strings, booleans, null and integers only;
- no floats, NaN or infinity;
- integers limited to `-(2^53 - 1)` through `2^53 - 1`;
- all keys and string values normalised to Unicode NFC;
- duplicate keys rejected before and after normalisation;
- lone Unicode surrogates rejected;
- sorted object keys;
- compact separators;
- maximum nesting depth 32;
- maximum canonical object size 1 MiB unless an artifact is represented by digest;
- canonical bytes compared exactly during verification.

Separate SHA-256 domains are used for:

- `action`;
- `descriptor`;
- `policy-source`;
- `compiled-policy`;
- `context`;
- `challenge`;
- `approval-grant`;
- `decision-receipt`;
- `execution-permit`.

A caller-provided action ID is metadata. The security identity is the content-derived action digest.

## 10. Trusted tool descriptors

A tool descriptor is registered outside the proposing agent’s control:

```json
{
  "schema_version": "1",
  "capability_id": "mail.send",
  "capability_version": "1",
  "operations": ["send"],
  "resource_kinds": ["message"],
  "side_effect_classes": ["external_mutation", "data_egress"],
  "required_action_fields": [
    "principal",
    "operation",
    "resource.recipients",
    "resource.body_digest",
    "resource.data_classes"
  ],
  "resolver_requirements": [],
  "untrusted_display_name": "Send email"
}
```

The descriptor digest covers every field. Human-readable tool descriptions may appear in the workbench but never determine authority.

Unknown capability IDs, unsupported versions, unsupported operations or missing required fields deny.

## 11. Canonical action envelope

```json
{
  "schema_version": "1",
  "principal": {
    "principal_id": "user:luca",
    "principal_type": "user",
    "owner_id": "user:luca"
  },
  "tool": {
    "capability_id": "mail.send",
    "descriptor_digest": "64-lowercase-hex"
  },
  "operation": "send",
  "resource": {
    "kind": "message",
    "recipients": ["client@example.com"],
    "body_digest": "64-lowercase-hex",
    "attachment_digests": [],
    "data_classes": ["internal"]
  },
  "opaque_parameters_digest": "64-lowercase-hex",
  "contract_digest": "64-lowercase-hex-or-null",
  "context_digest": "64-lowercase-hex",
  "requested_constraints": {
    "max_cost_minor": 0,
    "currency": null,
    "retry_number": 0
  },
  "client_nonce": "caller-generated-opaque-nonce"
}
```

The full private action may remain with the executor. The envelope contains every field policy needs plus digests binding hidden content.

The action digest covers the complete canonical envelope.

## 12. Context snapshot

Context is canonical and content-addressed. Supported v0.1 fields are:

- environment: `development`, `test`, `staging`, `production`;
- owner ID;
- project ID;
- session ID;
- contract digest;
- current policy-generation ID;
- data-classification declarations;
- local wall-clock timestamp;
- optional resolver evidence digests.

The evaluator hashes context but does not claim the context source is truthful. Deployments must decide which process is allowed to construct it.

## 13. Typed resource normalisation

### 13.1 Filesystem resources

Filesystem actions use:

```json
{
  "kind": "filesystem",
  "path_style": "posix|windows",
  "declared_path": "workspace/report.json",
  "normalised_path": "workspace/report.json",
  "root_id": "workspace",
  "resolver_evidence_digest": "64-lowercase-hex-or-null"
}
```

Rules:

- NUL, empty segments, `.` and `..` are rejected;
- POSIX absolute paths, Windows drive paths and UNC paths are distinct forms;
- policy roots must use the same path style;
- high-risk write, delete and execute operations require resolver evidence when policy says so;
- lexical normalisation alone never claims to defeat symbolic-link escape;
- the optional local resolver rejects symbolic links, non-regular roots and resolution outside the registered root.

### 13.2 Network resources

Network destinations contain canonical scheme, IDNA ASCII hostname, explicit or default port and path class. User-info in URLs is rejected. Domain matching uses label boundaries, so `evil-example.com` does not match `example.com`.

### 13.3 Messaging resources

Recipients are canonical addresses without display names. Domains are lower-case IDNA ASCII. Unsafe Unicode local parts and ambiguous display-name syntax are rejected in v0.1. Message bodies and attachments are represented by digest, byte count and declared data classes.

### 13.4 Financial resources

Amounts use integer minor units and exact uppercase currency identifiers. Payee identity is a typed opaque identifier. Floats and formatted currency strings are rejected.

## 14. Policy source model

Policies are strict JSON. A source bundle contains one baseline and zero or more overlays:

```json
{
  "schema_version": "1",
  "bundle_name": "example-policy",
  "layers": [
    {
      "layer_id": "baseline",
      "layer_type": "baseline",
      "parent_layer_id": null,
      "rules": []
    },
    {
      "layer_id": "project-alpha",
      "layer_type": "project",
      "parent_layer_id": "baseline",
      "rules": []
    }
  ]
}
```

Allowed layer types are:

- `baseline`;
- `owner`;
- `project`;
- `contract`;
- `session`.

There is exactly one baseline. Every other layer has one parent. Cycles, duplicate IDs and disconnected layers are rejected.

## 15. Rule model

```json
{
  "rule_id": "mail-send-approved-client",
  "effect": "REQUIRE_APPROVAL",
  "selector": {
    "capability_ids": ["mail.send"],
    "operations": ["send"],
    "principal_ids": ["user:luca"],
    "principal_types": ["user"],
    "resource_kinds": ["message"],
    "environments": ["production"],
    "side_effect_classes": ["external_mutation", "data_egress"]
  },
  "constraints": {
    "recipient_allowlist": ["client@example.com"],
    "allowed_data_classes": ["public", "internal"],
    "max_attachment_bytes": 10485760,
    "max_cost_minor": 0,
    "max_retry_number": 1,
    "permit_ttl_seconds": 120
  },
  "approval": {
    "required_roles": ["owner"],
    "challenge_ttl_seconds": 600
  },
  "reason_code": "EXTERNAL_MESSAGE_REQUIRES_OWNER_APPROVAL"
}
```

Selectors are finite sets and exact typed fields. Regex and arbitrary code are forbidden.

Empty selector fields mean “no additional filter” only when the schema explicitly permits it. Missing security-relevant fields never act as a wildcard.

## 16. Policy compilation and capability attenuation

The compiler:

1. validates canonical source;
2. validates descriptor references;
3. resolves the layer graph;
4. computes each parent’s effective capability envelope;
5. proves every child rule is equal to or narrower than its parent envelope;
6. intersects compatible constraints;
7. rejects empty, contradictory or undefined intersections;
8. sorts rules by stable semantic identity;
9. writes one canonical compiled bundle with a content-derived policy digest.

A child may:

- add a deny;
- convert allow to constraints;
- convert allow or constraints to approval;
- tighten path roots, recipient/domain sets, data classes, amounts, sizes, retry counts or TTLs.

A child may not:

- remove a parent deny;
- convert approval to allow;
- add a capability or operation absent from the parent envelope;
- widen a resource root or allowlist;
- increase a numeric limit or TTL;
- remove a resolver requirement;
- authorise a new principal.

A Contract Compiler adapter produces an additional restrictive `contract` overlay. It can never create authority absent from the baseline/owner/project policy.

## 17. Rule resolution

All matching rules are evaluated. Source order has no semantic effect.

Decision severity is:

```text
DENY > REQUIRE_APPROVAL > ALLOW_WITH_CONSTRAINTS > ALLOW
```

Rules:

- any matching deny produces `DENY`;
- otherwise any matching approval rule produces `REQUIRE_APPROVAL` until a valid grant is supplied;
- otherwise effective constraints are the intersection of every matching constraint;
- an empty or undefined intersection produces `DENY` with `POLICY_CONSTRAINT_CONFLICT`;
- at least one matching allow-capable rule is required;
- no matching allow produces `DENY` with `NO_MATCHING_ALLOW`;
- missing required action, descriptor or context fields produce `DENY` rather than an evaluation exception.

Policy compilation errors are separate from runtime denials and block policy publication.

## 18. Decisions and receipts

A decision receipt contains:

```json
{
  "schema_version": "1",
  "decision": "ALLOW_WITH_CONSTRAINTS",
  "reason_codes": ["PROJECT_PATH_LIMIT"],
  "action_digest": "...",
  "descriptor_digest": "...",
  "compiled_policy_digest": "...",
  "context_digest": "...",
  "matched_rule_ids": ["..."],
  "effective_constraints": {},
  "approval_challenge_digest": null,
  "evaluated_at": "2026-07-22T15:00:00Z",
  "receipt_id": "content-derived-after-body-hash"
}
```

The receipt is tamper-evident through its content-derived ID. In enforcement mode it may additionally carry an HMAC and key ID. Documentation calls this an authenticated MAC, not a digital signature.

Receipts never contain HMAC key material or unrestricted message/file contents.

## 19. Approval challenge

When approval is required, the evaluator returns a canonical challenge bound to:

- action digest;
- descriptor digest;
- compiled policy digest;
- context digest;
- principal digest;
- exact requested constraints;
- required approver roles;
- issue and expiry time;
- one random nonce;
- challenge digest.

Any action, policy, context, descriptor, principal or constraint change requires a new challenge.

## 20. Approval grant

`firewall-approve` reads a regular local key file and creates:

```json
{
  "schema_version": "1",
  "challenge_digest": "...",
  "approver": {
    "approver_id": "user:luca",
    "approver_role": "owner"
  },
  "approved_constraints": {},
  "issued_at": "...",
  "expires_at": "...",
  "grant_nonce": "...",
  "key_id": "owner-key-1",
  "grant_mac": "64-lowercase-hex"
}
```

The grant uses HMAC-SHA-256 with a dedicated domain. Keys must contain at least 32 random bytes. Key bytes never enter artifacts, logs or errors.

Approved constraints must be equal to or narrower than the challenge. An approval cannot override `DENY`.

Shared-secret authentication proves possession of the configured key, not the physical or legal identity of a human approver.

## 21. Execution permits

Every allowed enforcement-mode action receives a short-lived permit. The permit binds:

- decision receipt ID;
- action digest;
- descriptor digest;
- compiled policy digest;
- context digest;
- principal digest;
- effective constraints;
- issue and expiry time;
- one-time permit nonce;
- key ID;
- HMAC-SHA-256 permit MAC.

A permit is never created from a stale approval. The evaluator re-runs the action against the current descriptor, policy and context before issuing it.

## 22. Atomic verify-and-consume

`PermitVerifier.verify_and_consume(action, permit)`:

1. canonicalises the supplied action again;
2. verifies descriptor, policy and context digests supplied by the deployment;
3. verifies HMAC and key ID;
4. checks expiry and local clock-regression state;
5. checks that effective constraints still hold;
6. begins one SQLite immediate transaction;
7. rejects an already consumed permit nonce;
8. records digest, nonce, expiry and consumption time;
9. commits;
10. returns the exact canonical action object and effective constraints to the executor.

The executor must use that returned object. It must not reconstruct parameters after verification.

Consuming a permit before a failed tool call is safe: a retry requires a fresh evaluation and permit.

## 23. Replay and clock state

SQLite is used because it provides cross-process atomicity in the Python standard library.

The database stores only:

- permit digest;
- permit nonce digest;
- consumed timestamp;
- expiry timestamp;
- optional decision receipt ID;
- last accepted wall-clock timestamp.

It does not store full actions, bodies, file contents or HMAC keys.

The verifier uses monotonic time inside one process and rejects material wall-clock regression relative to the retained last accepted timestamp. This limits accidental rollback but does not create trusted time.

## 24. Operating modes

### 24.1 Analysis mode

- no key or replay database required;
- returns decisions, constraints, challenges and receipts;
- never emits an enforceable permit;
- used by linting, fixtures and the workbench.

### 24.2 Enforcement mode

- requires a permit HMAC key and replay database;
- may require an approval key depending on policy;
- emits permits for allowed actions;
- supports atomic verify-and-consume;
- fails closed when required key, clock, descriptor, context or replay state is unavailable.

## 25. Command-line interfaces

### 25.1 `firewall-policy`

```text
firewall-policy lint --source policy.json --descriptors descriptors.json
firewall-policy compile --source policy.json --descriptors descriptors.json --output compiled/
```

Outputs canonical diagnostics and a manifested compiled bundle.

### 25.2 `firewall-evaluate`

```text
firewall-evaluate evaluate \
  --policy compiled/policy.json \
  --descriptors compiled/descriptors.json \
  --action action.json \
  --context context.json \
  [--approval grant.json] \
  [--enforcement-key-file permit.key] \
  [--replay-db state.sqlite]

firewall-evaluate verify-permit \
  --permit permit.json \
  --action action.json \
  --policy compiled/policy.json \
  --descriptors compiled/descriptors.json \
  --context context.json \
  --key-file permit.key \
  --replay-db state.sqlite
```

### 25.3 `firewall-approve`

```text
firewall-approve issue \
  --challenge challenge.json \
  --approver-id user:luca \
  --approver-role owner \
  --key-id owner-key-1 \
  --key-file owner.key \
  --output grant.json
```

The command name `issue` means issue an approval grant, not issue a firewall challenge.

### 25.4 `firewall-explain`

```text
firewall-explain --receipt receipt.json [--format text|json]
```

It verifies the receipt’s content identity before explaining it.

## 26. Stable errors and exit codes

Default command output is JSON. Tracebacks require explicit developer mode.

Exit codes:

- `0` — successful command, including a legitimate `DENY` decision returned as data;
- `2` — invalid or tampered artifact;
- `3` — malformed input;
- `4` — unsupported schema or capability version;
- `5` — operational failure such as unavailable state/key/clock;
- `6` — policy compilation conflict;
- `7` — approval or permit authentication failure;
- `8` — replay or expiry rejection.

A denied action is not a process failure. Automation reads the `decision` field.

## 27. Privacy and secret handling

- policy/action/context keys matching secret-like names are recursively rejected unless represented as an explicit opaque secret reference;
- common credential-shaped values are flagged on a best-effort basis;
- key paths may be passed to CLIs, but key bytes are never printed;
- receipt disclosure uses allowlisted fields and digests;
- workbench data is synthetic;
- replay storage contains only non-sensitive digests and timing metadata;
- static viewer uses no telemetry, cookies, external fonts, CDNs or remote assets.

Best-effort filtering does not guarantee detection of every secret.

## 28. Adversarial reference corpus

The deterministic corpus must include at least:

### Allowed and constrained

1. workspace read allowed;
2. exact report write allowed with path and byte constraints;
3. production message requires approval;
4. approved message receives a permit;
5. reversible staging mutation allowed with constraints.

### Policy denials

6. no matching allow;
7. explicit hard deny;
8. unknown capability;
9. unsupported operation;
10. missing security field;
11. child policy widens path root;
12. child increases amount limit;
13. empty constraint intersection;
14. missing resolver evidence;
15. forbidden data class.

### Normalisation and substitution attacks

16. POSIX traversal;
17. Windows drive substitution;
18. UNC substitution;
19. symlink escape from local resolver;
20. recipient substitution;
21. display-name deception;
22. domain suffix deception;
23. URL user-info deception;
24. hidden attachment digest;
25. changed body digest;
26. money amount expansion;
27. payee substitution;
28. misleading tool description with unchanged capability ID;
29. capability ID substitution;
30. descriptor version drift.

### Approval, permit and replay

31. expired challenge;
32. wrong approver role;
33. approval widens constraints;
34. approval for different action;
35. stale policy approval;
36. stale context approval;
37. invalid grant MAC;
38. missing enforcement key;
39. permit for changed action;
40. permit for changed descriptor;
41. permit for changed policy;
42. permit for changed context;
43. expired permit;
44. replayed permit;
45. local clock regression;
46. state database unavailable;
47. tool call failure after permit consumption requires fresh permit.

Every scenario records exact expected decision, reason codes, matched rules, constraints, challenge/permit presence and exit code.

## 29. Mutation and metamorphic testing

Beyond named fixtures, tests generate mutations for:

- every action digest field;
- every approval-binding digest;
- every permit-binding digest;
- every path segment;
- every recipient;
- every domain label;
- every numeric limit boundary;
- every policy layer edge;
- rule-order permutations;
- descriptor display-name changes;
- repeated permit consumption.

Required metamorphic properties:

- rule source reordering does not change the compiled policy digest;
- human-readable descriptions do not change authority;
- tightening a policy cannot make a previously denied action allowed;
- changing any permit-bound security field invalidates the permit;
- an approval grant can never transform a hard deny into allow;
- analysis and enforcement modes produce the same underlying policy decision before permit handling.

## 30. Portfolio adapters

### 30.1 Agent Contract Compiler

Converts compiled contract permissions and limits into a restrictive contract overlay. Lossy conversion blocks publication.

### 30.2 Agent Evidence Ledger

Exports typed records for:

- `action_proposed`;
- firewall decision receipt;
- approval grant reference;
- execution permit reference;
- permit consumption result.

The ledger stores digests and allowlisted metadata, not HMAC keys.

### 30.3 Agent Completion Verifier

Consumes the permit and receipt only as precondition evidence. It must not treat firewall authorisation as proof that the postcondition occurred.

## 31. Static policy workbench

Headline:

> **Stop the action before it becomes an incident.**

The workbench is read-only and dependency-free. It shows:

- canonical action;
- trusted descriptor identity;
- active policy layers;
- matched rules;
- decision severity;
- effective constraint intersection;
- approval challenge binding;
- permit binding and expiry;
- replay result;
- a concise limitation panel.

Required scenarios:

1. safe workspace read;
2. constrained file write;
3. recipient substitution denied;
4. production delete requiring approval;
5. stale approval rejected after policy change;
6. replayed permit rejected.

The page must be keyboard-operable, responsive at 390 CSS pixels, reduced-motion aware and usable without JavaScript through meaningful initial content.

## 32. Documentation and claims boundary

README must place these limits beside the headline results:

- enforcement depends on complete gateway adoption;
- hashes prove binding, not truth of context;
- HMAC proves possession of configured key, not legal identity;
- local clock expiry is not trusted time;
- filesystem escape claims require local resolver evidence;
- authorisation does not prove successful execution;
- deterministic fixtures are software tests, not external-model or production-security results.

The project may be described as:

- deterministic pre-execution authorisation;
- capability attenuation;
- exact action/policy/context binding;
- one-time permit enforcement;
- explainable policy resolution;
- local-first agent-control infrastructure.

It may not be described as:

- unbypassable;
- universally safe;
- legally immutable;
- cryptographic proof of human identity;
- compliant or certified without an actual assessment;
- revenue-generating before real commercial evidence exists.

## 33. Commercial use without fabricated claims

The release can credibly support:

- fixed-scope agent action-surface audits;
- policy design and integration pilots;
- approval and permit workflow implementation;
- pre-execution controls for internal AI automations;
- portfolio evidence for AI systems, safety, infrastructure and agent-engineering roles.

Commercial material must distinguish a reusable open-source asset from a completed paid engagement.

## 34. Testing and release gates

Minimum release gates:

- Python 3.10, 3.11, 3.12 and 3.13;
- strict source compilation;
- complete unit and adversarial suite;
- deterministic corpus regeneration and byte comparison;
- policy-order metamorphic tests;
- HMAC known-answer tests;
- SQLite multi-process replay tests;
- local filesystem resolver tests on supported platforms;
- all four installed commands;
- clean-wheel installation tested outside the source tree;
- `pip check`;
- clean ZIP extraction, source verification, rebuilt wheel and second wheel-only pass;
- static workbench accessibility, local-data and no-external-runtime checks;
- credential and forbidden-claim scan;
- no network or paid-model calls in tests.

A target test count may guide coverage but is not itself release evidence. The release report records exact passed tests and scenario counts only after execution.

## 35. Implementation milestones

### Milestone 1 — Canonical core

- models and errors;
- canonical JSON and domain hashing;
- descriptor registry;
- typed resource normalisation;
- action/context identity.

### Milestone 2 — Policy compiler

- policy schema;
- layer graph;
- attenuation proof;
- constraint intersection;
- deterministic compiled bundle;
- lint and compile command.

### Milestone 3 — Evaluation and explanation

- rule matching;
- decision lattice;
- receipts;
- analysis mode;
- explanation model;
- adversarial policy/action fixtures.

### Milestone 4 — Approval and enforcement

- challenge;
- HMAC grant;
- permit;
- SQLite replay state;
- verify-and-consume;
- enforcement-mode CLI.

### Milestone 5 — Integrations and public release

- portfolio adapters;
- deterministic corpus;
- static workbench;
- methodology, threat model, results and authorship documents;
- release verifier;
- Python matrix, wheel, archive and Pages publication.

## 36. Acceptance criteria

v0.1.0 is complete only when:

1. the policy compiler rejects widening overlays and unresolved conflicts;
2. unknown or incomplete actions deny deterministically;
3. named allowed, constrained, approval and deny fixtures reproduce exact outcomes;
4. approval is bound to the exact action, descriptor, policy, context, principal and constraints;
5. hard deny cannot be approved;
6. permits are short-lived, authenticated and one-time;
7. changing any bound security field invalidates the permit;
8. replay is rejected atomically across processes;
9. receipts explain matched rules and effective constraints;
10. adapters preserve the distinction between authorisation and completion;
11. workbench claims remain inside the threat model;
12. source, Python matrix, clean wheel, archive and rebuilt wheel all pass independently;
13. a standalone public repository and static viewer contain no temporary transfer mechanisms;
14. release evidence records exact commit and artifact hashes.

## 37. Conclusion

The Lyra-100 review improves the original design enough to adopt the strengthened architecture. Agent Action Firewall v0.1.0 should be implemented as a deterministic policy compiler plus stateful permit-enforcement layer, not as a denylist or model-based judge.