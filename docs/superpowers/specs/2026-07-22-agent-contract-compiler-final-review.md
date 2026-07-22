# Agent Contract Compiler v0.1.0 — Final Adversarial Review

Date: 2026-07-22  
Base specification: `2026-07-22-agent-contract-compiler-design.md`  
Tracking issue: #5  
Status: Normative corrections; approved for user review

This document records the fresh-eyes protocol review. Where it is more specific than the base specification, this document takes precedence.

## Review conclusion

The selected direction remains correct and has been strengthened rather than expanded:

- deterministic controlled-language compiler;
- typed semantic IR;
- contradiction and reachability analysis;
- proof-obligation graph;
- intent-preservation report;
- weak-contract mutants and near-miss execution witnesses;
- canonical verifier-ready outputs;
- static employer workbench.

No model call, hosted service, arbitrary plugin system, signing infrastructure or general theorem prover belongs in the trusted v0.1.0 core.

## 1. Source aliases are mandatory for referencable declarations

The base examples incorrectly referred to compiler-generated identifiers before compilation. Any declaration that may be referenced must have a unique source alias.

Correct syntax:

```text
REQUIRE pre_target_absent: report ABSENT BEFORE execution
MUST req_create_report: executor CREATE report
MUST req_parse_json: report PARSE_AS json_array
MUST req_exact_count: report ITEM_COUNT EXACTLY 20
MUST_NOT forbid_overwrite: executor OVERWRITE report
ALWAYS inv_confined: report PATH_WITHIN "output"

OUTCOME completed WHEN req_create_report AND req_parse_json AND req_exact_count AND inv_confined
PROVE req_exact_count USING json_parse BY observer RETAIN sha256,size_bytes,observed_value
ANNOTATE req_exact_count STRENGTHENED_FROM "contains records" REASON "requester fixed the count"
```

Rules:

- aliases use lowercase ASCII letters, digits and underscores;
- maximum alias length is 128 characters;
- aliases are unique across all referencable declarations;
- unresolved, duplicate or wrong-kind aliases are blocking diagnostics;
- source aliases exist for readability and source mapping;
- aliases are resolved before canonical emission and do not themselves determine semantic node identity.

## 2. Semantic IDs are content-derived

Sequence-only IDs would make unrelated reordering change identity. Canonical semantic nodes instead receive domain-separated content IDs:

```text
req_<first-16-lowercase-hex-of-sha256>
pro_<first-16-lowercase-hex-of-sha256>
inv_<first-16-lowercase-hex-of-sha256>
out_<first-16-lowercase-hex-of-sha256>
proof_<first-16-lowercase-hex-of-sha256>
```

The digest input contains the canonical semantic node after aliases are resolved but before the node ID is inserted.

If two distinct canonical nodes collide on the displayed 16-hex prefix, the compiler extends both IDs in four-hex increments until unique. Full SHA-256 values remain retained internally.

Consequences:

- renaming a source alias without changing semantics does not change `contract_id`;
- adding an unrelated declaration does not renumber existing semantic nodes;
- semantically irrelevant declaration reordering does not change the compiled bundle;
- changing a semantic requirement changes that node ID and the contract ID.

## 3. Canonical semantic ordering

Declarations are divided into two classes.

Semantically unordered declarations are sorted by kind and full semantic digest:

- actors;
- objects;
- reusable predicates;
- independent requirements, prohibitions and invariants;
- evidence declarations;
- annotations.

Semantically ordered structures preserve declared order:

- conditional branches;
- ordered state transitions;
- outcome expression operands when short-circuit or priority semantics are explicitly requested;
- retry and rollback transition sequences.

Whitespace, comment placement and leading indentation used only for readability do not affect identity. Indentation is accepted but has no block semantics; `THEN` and `END` delimit blocks.

## 4. Numeric and unit semantics

v0.1.0 supports signed integers only. Floating-point and decimal literals are unsupported rather than rounded.

Supported unit families are:

- count: `items`, `records`, `files`;
- bytes: `bytes`, `kibibytes`, `mebibytes`;
- time: `milliseconds`, `seconds`, `minutes`, `hours`;
- exit status: unitless integer;
- percentages: integer basis points, written as `BASIS_POINTS`, only where an explicitly supported predicate permits them.

Canonical representation uses base units:

- bytes;
- milliseconds;
- integer counts;
- integer exit status;
- integer basis points.

Conversions must be exact. An inexact or overflowing conversion is a blocking diagnostic. The JSON interoperable safe-integer range applies after conversion.

## 5. Path-literal rules

File and directory object paths are logical POSIX-relative paths. The compiler performs no filesystem access.

Rejected path literals include:

- absolute paths;
- Windows drive prefixes;
- backslashes;
- NUL bytes;
- empty segments;
- `.` or `..` segments;
- doubled separators;
- trailing separators except the explicit root marker is not supported in v0.1.0.

Canonical paths use `/`. Path confinement is semantic and must later be independently enforced by an execution or verification adapter.

## 6. Outcome expressions

Outcome expressions refer to source aliases and compile to semantic node IDs.

v0.1.0 supports:

- `AND`;
- `OR`;
- `NOT` only over a single named predicate;
- parentheses to depth 16;
- no implicit precedence beyond `NOT`, then `AND`, then `OR`.

The canonical representation is a typed expression tree. Associative operands are sorted only when the operator is declared order-insensitive. Duplicate operands are rejected as likely source mistakes.

Every successful outcome must depend on at least one positive obligation or invariant. A success outcome composed only of prohibitions is rejected as vacuous.

## 7. Proof authority and independence

`BY observer` and `DISTINCT_FROM executor` remain protocol declarations, not cryptographic proof of identity or organisational separation.

The compiled proof plan records:

- required authority label;
- required distinction labels;
- observation timing;
- retained fields;
- target semantic node;
- artifact binding;
- acceptable evidence class.

An adapter may report that it cannot enforce a distinction. Loss of a required distinction is a lossy adaptation and is blocked by default.

## 8. Proof graph cycle rules

The proof graph is a directed typed multigraph.

Cycles are blocking unless every edge in the cycle is an explicitly declared monotonic derivation over a finite acyclic source set. v0.1.0 ships no user-defined recursive derivations, so ordinary source contracts should produce an acyclic graph.

The cycle diagnostic must include the shortest deterministic cycle path, sorted by semantic ID when multiple equal-length cycles exist.

## 9. Two mutation classes

The phrase “contract mutation testing” covers two distinct products and must not conflate them.

### 9.1 Weak-contract mutants

These alter the compiled semantic contract to test whether a requirement matters:

- remove one requirement;
- weaken `EXACTLY` to `AT_LEAST` or `AT_MOST` where valid;
- remove path confinement;
- replace independent evidence with source-reported evidence;
- increase retry budget;
- remove rollback;
- remove one successful-outcome operand.

Each weak-contract mutant receives a new contract identity and a statement of what protection was lost. The compiler never presents a mutant as an approved contract.

### 9.2 Near-miss execution witnesses

These preserve the contract but generate synthetic candidate outcomes/evidence that should fail:

- count minus one or plus one;
- stale observation;
- missing artifact;
- wrong path;
- digest mismatch;
- success receipt with absent postcondition;
- partial rollback;
- exceeded retry budget;
- mutation after observation.

Each witness records expected rejected node IDs and expected terminal classification.

### 9.3 Coverage reporting

The bundle reports separately:

- supported semantic nodes with at least one weak-contract mutant;
- supported proof obligations with at least one near-miss witness;
- unsupported mutation operators;
- no claim of exhaustive adversarial coverage.

## 10. Contract identity boundary

`contract_id` is computed from `contract.json` with its `contract_id` field omitted.

The following do not affect contract identity:

- comments;
- source aliases;
- diagnostics;
- source spans;
- explanation prose;
- intent-preservation display text;
- generated weak-contract mutants;
- near-miss witnesses;
- output file ordering outside canonical rules.

The following do affect contract identity:

- actors and object semantics;
- predicates;
- obligations, prohibitions and invariants;
- outcome expressions;
- retry and rollback policy;
- proof requirements and permitted evidence strength;
- schema version.

## 11. Blocked-compilation outputs

A blocked compilation must never emit an authoritative `contract.json`, `proof_plan.json`, `verification_checklist.json`, manifest or `contract_id`.

It may emit a diagnostic bundle containing:

- compilation state;
- stable diagnostic codes;
- safe source spans;
- original source lines unless `--redact-source` is requested;
- repair suggestions;
- parser version;
- no claim that the source is a valid contract.

Diagnostic output is physically separate from successful compilation output.

## 12. Output transaction rules

Successful compilation writes to a temporary sibling directory, verifies its own canonical outputs and manifest, then atomically renames the directory into place where the platform supports it.

If the final output exists:

- default behaviour is refusal;
- `--replace` is allowed only when the target contains a compatible Agent Contract Compiler manifest;
- replacement first verifies the old manifest and rejects symbolic links or unexpected files;
- unrelated directories are never recursively deleted.

A failed compilation leaves no partially authoritative output directory.

## 13. Determinism and compiler version

Every bundle records:

- source-language schema version;
- canonical-output schema version;
- compiler package version;
- diagnostic catalogue version;
- mutation-operator catalogue version.

Compiler implementation version alone does not affect `contract_id` when semantic output is byte-identical. Schema or semantic changes that alter canonical output necessarily change the contract identity.

## 14. Diagnostic severity and ordering

Severities:

- `ERROR` — blocks compilation;
- `WARNING` — compiles unless `--strict`;
- `INFO` — explanatory only.

Diagnostics are deterministically sorted by:

1. source start byte;
2. source end byte;
3. severity rank;
4. diagnostic code;
5. semantic node ID when available.

A parser failure that prevents reliable later spans may stop subsequent semantic diagnostics. The tool must not invent locations after synchronisation is lost.

## 15. Additional required tests

Add tests proving:

1. alias renaming does not change `contract_id`;
2. semantically irrelevant declaration reordering does not change any canonical output;
3. a semantic edit changes the relevant node ID and contract ID;
4. colliding displayed prefixes are deterministically extended using an injected hash function;
5. comments and indentation do not affect identity;
6. decimal literals are rejected;
7. exact unit conversions reproduce canonical base units;
8. path traversal and Windows path forms are rejected;
9. blocked compilation emits no authoritative contract ID;
10. every weak-contract mutant has a distinct contract ID;
11. every near-miss witness preserves the original contract ID and is rejected by the generated checklist;
12. output failure leaves no authoritative partial bundle;
13. lossy adapters are blocked by default;
14. vacuous success outcomes are rejected;
15. diagnostic ordering is byte-for-byte deterministic.

## 16. Self-review checklist

Confirmed after these corrections:

- no source declaration depends on an identifier that exists only after compilation;
- semantic IDs remain stable under alias renaming and irrelevant reorder;
- integer and unit semantics are exact;
- path semantics are portable and explicit;
- weak-contract mutation is separate from execution near-miss testing;
- blocked source cannot accidentally receive an authoritative identity;
- output publication is transactional;
- proof-authority wording does not imply cryptographic identity;
- canonical identity has a precise inclusion boundary;
- no `TBD`, `TODO` or unresolved product decision remains;
- the design remains one coherent implementation plan rather than multiple products.

The design is approved for implementation planning once Luca reviews the written specification.