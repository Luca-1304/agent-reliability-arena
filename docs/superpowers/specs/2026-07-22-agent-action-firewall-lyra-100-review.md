# Agent Action Firewall — Lyra-100 Review

Date: 2026-07-22  
Status: Completed design review  
Method: 100 structured checks across ten independent review lanes

## Method boundary

“Lyra-100” is used here as Luca’s repeated self-checking and cross-checking review method. It is not a separate model, external benchmark, certification, or claim that 100 independent humans reviewed the design.

The review asked whether each proposed feature materially improves correctness, containment, auditability, integration value or commercial credibility. Changes that only added terminology or surface complexity were rejected.

## Result

The original deterministic policy-compiler and runtime direction remains the correct foundation. The review materially strengthened it in these areas:

1. policies attenuate capability instead of allowing child layers to widen authority;
2. approval grants bind to exact canonical action, policy, context and tool-descriptor digests;
3. an execution permit is distinct from a decision receipt and must be checked immediately before execution;
4. replay protection uses an atomic local state store rather than timestamps alone;
5. misleading natural-language tool descriptions are excluded from trusted matching;
6. resource normalisation is typed by filesystem path, network destination, recipient and money target;
7. unresolved policy conflicts fail closed during compilation;
8. missing security-relevant action fields deny rather than default;
9. policy or context drift invalidates prior approval and permits;
10. public claims explicitly depend on complete gateway adoption and permit enforcement.

## Lane 1 — Threat model and bypass resistance

1. **Direct tool bypass:** required an explicit deployment assumption that all mutating actions pass through the firewall. Adopted.
2. **Executor ignores decision:** added a separately verifiable execution permit. Adopted.
3. **Action changed after evaluation:** permit binds to canonical action digest. Adopted.
4. **Tool schema changed after approval:** bind to trusted tool-descriptor digest. Adopted.
5. **Policy changed after approval:** bind to compiled policy digest. Adopted.
6. **Context changed after approval:** bind to context digest and expiry. Adopted.
7. **Replay of valid approval:** add one-time nonce consumption in an atomic state store. Adopted.
8. **Bypass through misleading tool name:** match registered capability identity, not display text. Adopted.
9. **Unknown operation:** default deny. Adopted.
10. **Side-channel execution outside gateway:** documented as outside the enforcement guarantee. Adopted as a claims boundary.

## Lane 2 — Policy semantics and precedence

11. **Implicit allow:** rejected; default is deny.
12. **Child layer widens parent:** compiler rejects non-monotonic inheritance. Adopted.
13. **Deny overridden by approval:** rejected; hard deny is not approvable.
14. **Conflicting allow and deny:** deny dominates.
15. **Conflicting constraints:** intersect when compatible; compilation fails when the intersection is empty or undefined.
16. **Rule order changes result:** rejected; resolution is order-independent after canonical compilation.
17. **Specificity games:** rejected as a safety mechanism; explicit layers and effect lattice are used instead.
18. **Missing matching allow:** deny with `NO_MATCHING_ALLOW`.
19. **Session policy weakens project policy:** rejected by attenuation checks.
20. **Approval as general wildcard:** rejected; grants are challenge-specific.

## Lane 3 — Canonicalisation and identity

21. **JSON key reordering:** canonical encoding makes identity stable.
22. **Unicode confusables:** security-sensitive identifiers use restricted normal forms and reject unsafe characters.
23. **Floating money values:** rejected; integer minor units only.
24. **Duplicate keys after normalisation:** rejected before hashing.
25. **Unsafe integer range:** restricted to interoperable JSON safe integers.
26. **Hash-domain confusion:** separate domains for action, policy, context, challenge, grant, receipt and permit.
27. **Missing newline or alternate encoding:** canonical UTF-8 JSON only.
28. **Action ID supplied by caller:** treated as metadata; security identity is content-derived.
29. **Tool description included in digest:** retained as untrusted metadata but excluded from permission matching.
30. **Non-deterministic timestamps in fixture identity:** clocks are injected for deterministic tests.

## Lane 4 — Approval security

31. **Approval not bound to exact request:** challenge includes action, policy, context and descriptor digests.
32. **Approver expands requested scope:** grant constraints must be equal to or narrower than the challenge.
33. **Approval expires after evaluation but before use:** permit verification checks current expiry.
34. **Approval token copied between actors:** actor/principal digest is included.
35. **Approval token copied between environments:** environment context is included.
36. **Approver role not authorised:** policy declares exact approver roles.
37. **Approval authorises hard deny:** prohibited.
38. **Key material appears in output:** prohibited; only key ID and HMAC are retained.
39. **HMAC described as a signature:** prohibited; documentation calls it an authenticated MAC.
40. **Poor key custody proves human identity:** rejected claim; v0.1 cannot prove who physically controlled a shared secret.

## Lane 5 — Runtime and time-of-check/time-of-use

41. **Decision receipt used as execution authority:** rejected; only a valid permit authorises execution.
42. **Permit action parameters differ:** verification fails.
43. **Permit tool descriptor differs:** verification fails.
44. **Permit policy differs:** verification fails.
45. **Permit context differs:** verification fails.
46. **Permit constraints not checked by executor:** integration contract requires pre-execution verification and constraint enforcement.
47. **Permit used twice:** atomic nonce consumption rejects replay.
48. **Permit used after expiry:** rejected.
49. **System clock rollback:** state store retains last accepted wall-clock value and rejects material regression; monotonic time is used within one process.
50. **Executor starts after permit verification but mutates parameters:** executor adapter must pass the exact verified canonical action object, not reconstruct it.

## Lane 6 — Typed resource normalisation

51. **Filesystem `..` traversal:** rejected during canonicalisation.
52. **Absolute path outside approved root:** denied.
53. **Windows drive/UNC ambiguity:** parsed separately and rejected unless policy explicitly supports the same root type.
54. **Symbolic-link escape:** lexical policy evaluation is insufficient; resolver evidence is required for write/delete/execute operations.
55. **Recipient display-name substitution:** display names are untrusted; canonical address is evaluated.
56. **Unicode email/domain lookalike:** restricted canonical form and IDNA domain comparison.
57. **Subdomain suffix confusion:** label-boundary matching, not raw string suffix.
58. **URL user-info hides destination:** rejected.
59. **Money decimal ambiguity:** integer minor units and exact uppercase currency.
60. **Hidden data egress in attachment:** action schema declares data classes and attachment digests; omissions deny.

## Lane 7 — Failure, recovery and availability

61. **Policy parser error:** fail closed with deterministic diagnostics.
62. **State database unavailable:** elevated action denies; stateless non-approval evaluation may continue only when policy allows it.
63. **HMAC key unavailable:** approval-required action remains `REQUIRE_APPROVAL`; no permit is issued.
64. **Clock unavailable:** expiring grant/permit verification fails closed.
65. **Context provider unavailable:** rules requiring that context deny.
66. **Descriptor registry unavailable:** unknown capability denies.
67. **Partial receipt write:** atomic temporary sibling plus replace.
68. **Replay-state crash:** SQLite transaction ensures consume-or-not-consume behaviour.
69. **Duplicate evaluation:** deterministic receipt identity, but evaluation itself does not consume approval until permit issuance/use.
70. **Recovery weakens policy:** prohibited; retries re-evaluate against current policy and context.

## Lane 8 — Privacy, secrets and evidence safety

71. **Raw secrets in action parameters:** secret-like fields rejected or represented by opaque references.
72. **Message body copied into receipt:** receipt stores digest and classification, not unrestricted content.
73. **Approval key recorded:** prohibited.
74. **Sensitive recipient retained publicly:** disclosure adapter supports redaction/allowlisting.
75. **Policy contains credentials:** lint rejects secret-like keys and common credential-shaped values on a best-effort basis.
76. **Error traceback leaks values:** stable error codes by default; tracebacks require explicit developer mode.
77. **Replay database leaks full actions:** stores digests, nonce, status and expiry only.
78. **Workbench executes policies:** rejected; static viewer is read-only.
79. **Telemetry or external assets:** rejected from v0.1 workbench.
80. **Evidence implies truth of context:** rejected claim; digests prove binding, not truth.

## Lane 9 — Portfolio integrations

81. **Contract Compiler adapter widens authority:** rejected; contract output becomes an additional restrictive overlay.
82. **Evidence Ledger records firewall decision:** adopted through typed action/decision/permit references.
83. **Completion Verifier treats permit as proof of completion:** rejected; permit proves precondition authorisation only.
84. **Reliability Arena compares policy modes:** adopted as a later experiment, not v0.1 core.
85. **Provider-specific action schemas:** rejected from trusted core; adapters normalise into one envelope.
86. **Tool runner embedded in firewall:** rejected; firewall evaluates and permits but does not become a general executor.
87. **Remote policy service required:** rejected; local-first compiled policies remain portable.
88. **Existing verifier code copied wholesale:** rejected; adapters use public artifact formats.
89. **Ledger required for basic evaluation:** rejected; integration is optional.
90. **Commercial integration needs API boundary:** adopted through small pure-Python services plus CLIs.

## Lane 10 — Employer and commercial credibility

91. **Single risk score:** rejected; decisions expose matched rules and typed constraints.
92. **Vague “AI safety” claim:** replaced with concrete pre-execution authorisation and scope containment.
93. **Pretend production certification:** prohibited.
94. **Revenue claim before customers:** prohibited.
95. **Only happy-path examples:** rejected; adversarial corpus is mandatory.
96. **No cost of safety shown:** workbench shows approval friction and blocked/allowed trade-offs.
97. **Unreadable policy engine:** rule resolution and receipts must be explainable without source inspection.
98. **No deployment story:** include sidecar/library/gateway integration patterns and their guarantees.
99. **No proof of packaging quality:** Python 3.10–3.13, source, wheel and archive gates required.
100. **Portfolio overlap:** scope remains pre-execution containment, distinct from contract compilation, evidence retention, postcondition verification and orchestration evaluation.

## Adopted v0.1 architecture after Lyra-100

```text
Registered tool capability + Proposed action + Context snapshot
                         │
                         ▼
                Canonical normaliser
                         │
                         ▼
Compiled monotonic policy layers ──► Deterministic evaluator
                         │                    │
                         │                    ├── DENY
                         │                    ├── REQUIRE_APPROVAL → challenge
                         │                    ├── ALLOW_WITH_CONSTRAINTS
                         │                    └── ALLOW
                         │
Approval grant + atomic replay store
                         │
                         ▼
              Short-lived execution permit
                         │
                         ▼
          Executor verifies exact permit binding
                         │
                         ▼
        Tool action outside the firewall package
```

## Rejected additions

The review rejected these from v0.1 because they would add surface area without strengthening the trusted core:

- model-based policy judging;
- a hosted control plane;
- general tool execution;
- regex-based rule matching;
- public-key infrastructure and certificate management;
- a universal risk score;
- organisation or multi-tenant administration;
- browser-based policy editing;
- automated policy generation from unrestricted natural language;
- compliance or legal-certification language.

## Conclusion

Lyra-100 materially improves the original design. The project should continue with the strengthened deterministic firewall rather than reverting to the initial outline. The trusted core remains local, explicit, reproducible and narrow enough for a standalone v0.1.0 release.