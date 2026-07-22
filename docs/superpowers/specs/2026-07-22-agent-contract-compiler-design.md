# Agent Contract Compiler v0.1.0 — Design Specification

Date: 2026-07-22  
Status: Approved direction, pending written-spec review  
Tracking issue: #5

## 1. Public question

**Can a human-readable request be converted into an explicit, internally consistent and machine-verifiable completion contract before an agent begins acting?**

Agent Contract Compiler turns a constrained requirements document into:

- a canonical completion contract;
- a proof-obligation graph;
- a verification checklist;
- diagnostics for ambiguity, contradiction and unverifiable language;
- an intent-preservation report;
- a deterministic suite of near-miss contract mutations;
- a stable SHA-256 contract identity.

The core principle is:

> Compile proof obligations before permitting completion claims.

## 2. Why this is a separate project

The existing reliability projects address later stages:

- Agent Completion Verifier determines whether evidence satisfies a declared contract;
- Agent Evidence Ledger preserves an auditable execution history;
- Agent Reliability Arena compares reliability policies and roles;
- controlled failure-injection work tests behaviour under faults.

The missing front-end boundary is contract formation. A verifier cannot rescue a vague requirement such as “make sure the report is correct” because neither “correct” nor the required proof has been defined.

Agent Contract Compiler owns that boundary and remains independently useful.

## 3. Claims boundary

v0.1.0 may demonstrate that, under its supported language:

- a contract is syntactically valid;
- obligations and prohibitions are structurally explicit;
- references resolve;
- supported constraints are internally consistent;
- required evidence is mapped to each success condition;
- circular, self-reported or insufficient proof is diagnosed;
- canonical outputs reproduce byte-for-byte;
- deterministic mutation cases distinguish complete from near-complete outcomes.

v0.1.0 does **not** prove:

- that the compiler recovered unstated human intention;
- that the user's original request was wise, lawful or safe;
- that an actor or observer has a cryptographically authenticated identity;
- that a named independent observer is organisationally independent;
- that an observation is true merely because it is labelled independent;
- that an external AI model will execute the contract correctly;
- legal compliance or legal enforceability;
- completeness for arbitrary natural language.

The README and viewer must place these limits beside the primary claims.

## 4. Recommended architecture

### 4.1 Trusted deterministic core

The trusted core contains no model call and no network dependency.

```text
Controlled requirement document
        ↓
Lexer and parser
        ↓
Typed requirement IR
        ↓
Semantic analyser
        ↓
Proof planner
        ↓
Mutation generator
        ↓
Canonical emitter + contract hash
```

### 4.2 Optional interpretation adapters

Future adapters may convert free-form natural language into the controlled source language. They are explicitly outside the trusted compiler core.

An adapter output must be reviewed or accepted as source text before deterministic compilation. The compiler never treats model-generated interpretation as authoritative merely because it was generated automatically.

### 4.3 No hidden inference

The compiler may perform only declared, lossless normalisations, such as:

- Unicode NFC normalisation;
- canonical unit representation for supported units;
- singular/plural identifier normalisation where unambiguous;
- stable ordering of declarations;
- expansion of named reusable predicates.

It must not silently invent:

- thresholds;
- deadlines;
- file paths;
- actors;
- retry counts;
- tolerances;
- evidence authorities;
- rollback behaviour;
- definitions for subjective adjectives.

Any non-lossless interpretation is emitted as an unresolved diagnostic or an explicit compiler suggestion that requires source modification.

## 5. Input language

### 5.1 Source format

The canonical source format is UTF-8 plain text with one declaration per line and indentation-free blocks delimited by explicit keywords.

Comments begin with `#` and do not affect the compiled contract identity.

The language is intentionally smaller than general English. It is designed to be readable without permitting silent ambiguity.

### 5.2 Required header

```text
CONTRACT report_generation VERSION 1
ACTOR requester TYPE user
ACTOR executor TYPE agent
ACTOR observer TYPE independent_observer
OBJECT report TYPE file PATH "output/report.json"
```

Identifiers use lowercase ASCII letters, digits and underscores. Display labels may contain Unicode.

### 5.3 Supported declaration classes

#### Preconditions

```text
REQUIRE report ABSENT BEFORE execution
REQUIRE input_records COUNT EXACTLY 20
```

#### Obligations

```text
MUST executor CREATE report
MUST report PARSE_AS json_array
MUST report ITEM_COUNT EXACTLY 20
```

#### Prohibitions

```text
MUST_NOT executor OVERWRITE report
MUST_NOT report CONTAIN_FIELD "secret"
```

#### Invariants

```text
ALWAYS report PATH_WITHIN "output"
```

#### Conditional behaviour

```text
WHEN report EXISTS BEFORE execution THEN
  MUST executor TERMINATE_WITH existing_target
  MUST_NOT executor MUTATE report
END
```

#### Terminal outcomes

```text
OUTCOME completed WHEN requirement_1 AND requirement_2 AND requirement_3
OUTCOME existing_target WHEN precondition_existing_target
OUTCOME failed WHEN unrecoverable_error
```

Every contract declares at least one successful or safely terminal outcome.

#### Retry and rollback

```text
RETRY MAX_ATTEMPTS 2
RETRY ONLY_WHEN transient_failure
ROLLBACK REQUIRED_WHEN partial_mutation
```

Unbounded retry is forbidden.

#### Evidence requirements

```text
PROVE requirement_3 USING filesystem_read BY observer
PROVE requirement_4 USING json_parse BY observer
PROVE prohibition_1 USING before_after_digest BY observer
```

Evidence declarations may include:

```text
FRESH_WITHIN 30 seconds
DISTINCT_FROM executor
RETAIN sha256,size_bytes,observed_value
```

### 5.4 Supported predicate families

v0.1.0 supports a deliberately bounded set:

- existence and absence;
- equality and inequality;
- exact, minimum and maximum counts;
- regular-file and directory type;
- path confinement;
- byte length;
- SHA-256 digest;
- UTF-8 validity;
- JSON parse/type/field/count predicates;
- text contains/does-not-contain predicates;
- command exit status;
- ordered state transition;
- before/after mutation comparison;
- temporal freshness relative to an explicitly named event;
- all/any/none quantification over a declared finite collection.

Unsupported predicates produce `UNSUPPORTED_PREDICATE`, never an approximate compilation.

## 6. Typed intermediate representation

The parser produces a typed, immutable requirement IR before semantic analysis.

Core records:

```text
ContractSource
ActorDeclaration
ObjectDeclaration
PredicateDeclaration
Requirement
Prohibition
Invariant
ConditionalBlock
Outcome
RetryPolicy
RollbackPolicy
EvidenceDeclaration
SourceSpan
```

Each semantic node retains:

- a stable source span;
- original source text;
- normalised form;
- compiler-generated identifier;
- whether the node was copied, normalised, expanded or rejected.

Stable IDs use content-derived prefixes plus deterministic sequence allocation, for example:

```text
req_0001
prohibition_0001
outcome_0001
proof_0001
```

IDs are stable when unrelated later declarations are appended, but reordering semantically ordered declarations may change the canonical contract.

## 7. Semantic analysis

### 7.1 Symbol resolution

The analyser rejects:

- duplicate actor or object identifiers;
- unresolved identifiers;
- identifier/type mismatches;
- references to an outcome as though it were an object;
- evidence declarations that target no requirement;
- predicates applied to unsupported object types.

### 7.2 Ambiguity diagnostics

The compiler rejects or blocks compilation for:

- subjective adjectives without predicates: `correct`, `proper`, `good`, `secure`, `high quality`, `reasonable`;
- implicit pronouns;
- omitted actor for an action;
- omitted object identity;
- relative time without an anchor;
- unspecified units;
- open-ended collections;
- undefined success terms;
- “etc.”, “and similar”, “as needed” or equivalent open sets;
- unbounded retry or recovery;
- evidence requirements that merely repeat an agent claim.

Diagnostics include source span, stable code, explanation and a concrete repair suggestion.

### 7.3 Contradiction analysis

The analyser detects supported contradictions such as:

- `MUST CREATE report` with `MUST_NOT MUTATE report` on the same path and outcome;
- count exactly 20 and at most 10;
- object required both present and absent at the same lifecycle point;
- terminal outcome requiring mutually exclusive predicates;
- rollback both required and forbidden for the same failure class;
- retry maximum lower than a required minimum attempt count;
- freshness windows that cannot be satisfied under declared event ordering;
- success depending on a declared failure outcome.

The solver is rule-based and finite-domain for supported predicate families. v0.1.0 does not claim general theorem proving.

### 7.4 Reachability analysis

Each terminal outcome must be reachable under at least one supported state assignment unless it is explicitly declared as a defensive impossible-state sentinel.

The compiler reports:

- unreachable outcome;
- success with no satisfiable path;
- branch with no terminal outcome;
- recovery loop with no decreasing retry budget;
- rollback path that cannot restore a declared invariant.

## 8. Proof-obligation graph

### 8.1 Purpose

Compilation does not stop at requirements. It produces the proof structure required to establish completion.

Graph node classes:

- requirement;
- prohibition;
- invariant;
- outcome;
- observation operation;
- retained artifact;
- evidence authority;
- temporal anchor;
- derived decision.

Graph edges include:

- `SATISFIES`;
- `PROVES`;
- `DEPENDS_ON`;
- `OBSERVED_BY`;
- `FRESH_RELATIVE_TO`;
- `DISTINCT_FROM`;
- `INVALIDATES`;
- `REQUIRES_ARTIFACT`.

### 8.2 Proof completeness

Every predicate contributing to a successful outcome must have at least one proof path to retained evidence.

A proof path is incomplete when it ends in:

- an unretained transient value;
- the executor's completion claim alone;
- a source report without independent observation where independence was required;
- an observation made before the relevant action;
- a digest with no retained byte count or path identity when those are needed;
- a parser result without binding it to the observed artifact digest;
- an authority that is not permitted for that proof obligation.

### 8.3 Circular evidence detection

The graph must be acyclic after collapsing explicit derivation groups.

Rejected circular forms include:

```text
completion is true because status=complete
status=complete because completion is true
```

and:

```text
agent says file exists
file existence is proven by agent success receipt
```

when the contract requires independent filesystem observation.

### 8.4 Evidence strength

Each proof obligation receives a deterministic grade:

- `DIRECT_INDEPENDENT`;
- `DIRECT_SOURCE_REPORTED`;
- `DERIVED_INDEPENDENT`;
- `DERIVED_MIXED`;
- `UNPROVEN`.

Compilation may succeed with source-reported evidence only when the source explicitly permits it. The preservation report must highlight that weaker trust choice.

## 9. Intent-preservation report

The compiler creates `intent_preservation.json` and a human-readable explanation.

Every source declaration is classified as:

- `PRESERVED_EXACTLY`;
- `NORMALISED_LOSSLESSLY`;
- `EXPANDED_FROM_DEFINITION`;
- `STRENGTHENED_EXPLICITLY`;
- `WEAKENED_EXPLICITLY`;
- `UNRESOLVED`;
- `REJECTED`.

The deterministic compiler itself may only emit the first three without an explicit source annotation. Strengthening or weakening requires a declaration such as:

```text
ANNOTATE requirement_3 STRENGTHENED_FROM "contains records" REASON "count fixed by requester"
```

The report shows:

- source span;
- original text;
- compiled node IDs;
- normalisation details;
- omitted comments;
- unresolved diagnostics;
- proof-strength changes;
- whether compilation was blocked.

This makes interpretation drift visible instead of hiding it in generated JSON.

## 10. Contract mutation testing

### 10.1 Purpose

A structurally valid contract may still be too weak. Mutation testing asks whether near-miss outcomes would incorrectly satisfy it.

### 10.2 Deterministic mutation operators

For supported requirements, the compiler generates relevant mutations such as:

- exact count minus one and plus one;
- missing required artifact;
- wrong object type;
- stale evidence;
- self-reported evidence replacing independent evidence;
- path outside confinement;
- digest mismatch;
- prohibited field inserted;
- mutation after verification observation;
- successful tool receipt with absent postcondition;
- partial rollback;
- retry budget exceeded;
- wrong terminal status;
- reordered required state transition.

### 10.3 Expected result

Each mutation includes:

- changed predicate or evidence edge;
- expected rejected requirement IDs;
- expected terminal status;
- explanation;
- deterministic fixture seed derived from the contract hash and operator ID.

The release fixture suite must prove that every generated mutation is rejected by the generated verification checklist or compatible verifier adapter.

The compiler does not claim complete adversarial coverage. It reports mutation coverage only for supported predicates.

## 11. Canonical outputs

A successful compilation produces:

```text
contract.json
proof_plan.json
verification_checklist.json
intent_preservation.json
mutation_suite.json
diagnostics.json
explanation.md
manifest.json
```

### 11.1 Canonical JSON profile

JSON outputs use:

- UTF-8;
- Unicode NFC normalisation;
- sorted object keys;
- compact separators;
- no floats;
- integers within the JSON interoperable safe range;
- final newline;
- rejection of duplicate keys after normalisation;
- explicit schema version.

### 11.2 Contract identity

`contract_id` is:

```text
sha256("agent-contract-compiler:contract:v1\n" + canonical_contract_bytes)
```

The source comments, diagnostics, explanation and generated mutations do not affect `contract_id` unless their semantics are represented inside `contract.json`.

### 11.3 Manifest

`manifest.json` records relative path, byte length and SHA-256 for every output except itself, sorted by path.

Recompiling the same semantic source with the same compiler/schema version must reproduce every output byte-for-byte except an explicitly requested non-deterministic display export, which is out of scope for v0.1.0.

## 12. Compilation states

The compiler returns one of:

- `COMPILED` — no blocking diagnostics and complete proof plan;
- `COMPILED_WITH_WARNINGS` — no blocking diagnostics, but explicitly permitted weaker evidence or non-blocking risk remains;
- `NEEDS_CLARIFICATION` — ambiguity or missing objective definition blocks canonical compilation;
- `CONTRADICTORY` — supported constraints cannot be satisfied together;
- `UNVERIFIABLE` — a required success predicate has no permitted proof path;
- `UNSUPPORTED` — source requests semantics outside v0.1.0;
- `MALFORMED` — syntax, encoding or schema failure.

Partial outputs for blocked compilations include diagnostics and a safe source map, but no authoritative `contract_id`.

## 13. Commands

### 13.1 `contract-compile`

```text
contract-compile SOURCE --output DIRECTORY [--format json|text]
```

Produces the full output bundle only when compilation reaches `COMPILED` or `COMPILED_WITH_WARNINGS`.

Blocked compilations produce a separate diagnostics directory when requested.

### 13.2 `contract-lint`

```text
contract-lint SOURCE [--format json|text] [--strict]
```

Performs syntax, semantic, contradiction, reachability and proof-completeness analysis without writing a contract bundle.

`--strict` promotes warnings about weak evidence to blocking diagnostics.

### 13.3 `contract-explain`

```text
contract-explain CONTRACT_OR_SOURCE [--requirement ID] [--format json|text|markdown]
```

Explains:

- what the contract requires;
- what would prove it;
- what would not prove it;
- terminal outcomes;
- retry and rollback behaviour;
- intent-preservation classifications;
- generated near-miss mutations.

### 13.4 Stable exit codes

- `0`: compiled or lint-clean;
- `1`: compiled/linted with warnings when not strict;
- `2`: needs clarification;
- `3`: contradictory;
- `4`: unverifiable;
- `5`: unsupported semantics;
- `6`: malformed input;
- `7`: operational failure.

No unrestricted traceback is printed by default.

## 14. Integration boundaries

### 14.1 Completion Verifier adapter

A dependency-free adapter may emit a verifier-ready task case containing:

- contract ID;
- required predicates;
- expected evidence classes;
- artifact bindings;
- accepted terminal outcomes;
- retry/rollback constraints.

The compiler must not import the existing verifier package at runtime.

### 14.2 Evidence Ledger adapter

A second adapter may emit a declaration template for:

- `contract_declared` payload;
- proof obligation IDs;
- permitted observer labels;
- expected retained artifacts;
- maximum attempts.

The adapter records compatibility, not cryptographic linkage to an execution ledger.

### 14.3 Versioning

Every adapter declares:

- source compiler schema version;
- target schema name/version;
- unsupported or weakened semantics;
- whether the adapter output is lossless.

Lossy adapter output is blocked by default.

## 15. Security and resource limits

v0.1.0 treats source files as untrusted structured input but does not claim hostile multi-tenant isolation.

Limits:

- source file: 2 MiB;
- declarations: 10,000;
- actors: 128;
- objects: 1,024;
- requirements/prohibitions/invariants: 4,096 total;
- outcomes: 128;
- proof graph nodes: 20,000;
- generated mutations: 10,000;
- nesting: conditional depth at most 16;
- identifier length: 128 ASCII characters;
- display string length: 16 KiB;
- no file inclusion, shell execution, environment expansion or network access;
- output confined beneath an explicitly supplied directory;
- symbolic-link output traversal rejected;
- atomic temporary-file writes and replacement;
- existing non-empty output refused unless `--replace` is explicitly supplied and the directory contains a compatible compiler manifest.

The parser must terminate deterministically within configured bounds.

## 16. Deterministic reference corpus

The release includes source-controlled examples covering:

### Valid

1. exact JSON report creation;
2. existing-target no-overwrite behaviour;
3. directory synchronisation with digest verification;
4. command execution with exit/output proof;
5. bounded retry and rollback;
6. multi-artifact success requiring all observations;
7. explicit source-reported evidence permitted by contract;
8. independently observed evidence required.

### Needs clarification

1. “make it correct”;
2. “save it somewhere safe”;
3. “retry if needed”;
4. relative deadline with no anchor;
5. unspecified count or unit;
6. pronoun with multiple possible objects.

### Contradictory

1. create and never mutate the same absent object;
2. exactly 20 and at most 10;
3. required present and absent at the same state;
4. rollback both required and forbidden;
5. unreachable success outcome.

### Unverifiable

1. success proven only by the completion claim;
2. independent proof required but no observer operation exists;
3. evidence observed before the action;
4. circular derived proof;
5. digest proof not bound to the target artifact.

### Unsupported

1. arbitrary subjective quality scoring;
2. unbounded natural-language quantification;
3. legal-compliance assertion;
4. probabilistic threshold requiring floating-point semantics;
5. external web truth without an adapter.

Every fixture records exact expected compilation state, diagnostics, hashes and mutation outcomes.

## 17. Testing strategy

### 17.1 Unit tests

- lexer and parser spans;
- Unicode normalisation and duplicate identifiers;
- canonical JSON bytes;
- symbol resolution;
- every supported predicate/type pairing;
- ambiguity diagnostics;
- contradiction rules;
- reachability;
- proof graph creation;
- circular evidence detection;
- intent-preservation classifications;
- mutation operators;
- exit-code mapping;
- output confinement and atomic writes.

### 17.2 Property-style deterministic tests

Without adding a runtime property-testing dependency, generated loops must test:

- declaration reordering where order is semantically irrelevant;
- comment changes not affecting contract identity;
- every requirement deletion altering contract identity;
- every proof edge deletion causing incomplete proof or changed identity;
- every generated near-miss mutation being rejected;
- repeated compilation producing byte-identical bundles;
- every manifest entry matching retained bytes.

### 17.3 Source and wheel verification

The release gate must pass:

- source tests;
- installed editable commands;
- wheel build;
- tests from outside the source tree against the wheel only;
- all three installed commands;
- deterministic reference regeneration;
- `pip check`;
- downloadable archive source and rebuilt-wheel clarification passes.

### 17.4 Python matrix

GitHub Actions runs Python 3.10, 3.11, 3.12 and 3.13 with no network or model calls during tests.

## 18. Employer-facing workbench

A dependency-free static viewer demonstrates the compiler without requiring installation.

Primary experience:

1. select a source contract;
2. view syntax-highlighted controlled requirements;
3. inspect compilation state and diagnostics;
4. compare source declarations with compiled nodes;
5. explore the proof-obligation graph;
6. switch among complete and near-miss outcomes;
7. see exactly which proof obligation rejects each mutation;
8. inspect the intent-preservation report;
9. copy local reproduction commands.

Required visual distinctions:

- requirement;
- prohibition;
- invariant;
- outcome;
- source report;
- independent observation;
- derived decision;
- unresolved or weak proof.

Accessibility:

- semantic HTML;
- keyboard-operable scenario and graph navigation;
- visible focus;
- reduced motion;
- no colour-only state communication;
- meaningful initial and no-script content;
- no external assets or telemetry;
- no horizontal overflow at 390 CSS pixels.

## 19. Public positioning

Recommended headline:

> Turn intent into proof obligations before an agent acts.

Recommended supporting line:

> Agent Contract Compiler converts constrained human-readable requirements into deterministic completion contracts, evidence plans and near-miss tests—while showing exactly what it could not infer.

The public demonstration must lead with an actual ambiguous request, the blocked diagnostic, the repaired source and the compiled proof plan. This is more credible than leading with architecture diagrams.

## 20. Authorship and evidence

Public documentation must distinguish:

- Luca Panayiotou as repository owner and product collaborator;
- AI-assisted design and implementation;
- deterministic software fixtures;
- no external-model benchmark unless a separately reproducible run is later added;
- exact source, wheel, archive and CI verification evidence.

No fabricated employment, organisational adoption or production deployment claim is permitted.

## 21. Release milestones

### Milestone 1 — Language and canonical contract

- lexer/parser;
- typed IR;
- canonical emitter and contract identity;
- syntax/schema diagnostics.

### Milestone 2 — Semantic and proof analysis

- symbol/type checking;
- ambiguity and contradiction analysis;
- reachability;
- proof-obligation graph;
- circular/insufficient evidence detection.

### Milestone 3 — Preservation, mutations and commands

- intent-preservation report;
- deterministic mutation suite;
- compile/lint/explain commands;
- verifier and ledger adapters.

### Milestone 4 — Evidence corpus and public release

- deterministic fixtures;
- employer workbench;
- documentation and threat model;
- source/wheel/archive verification;
- Python 3.10–3.13 CI;
- standalone repository and Pages release.

## 22. Acceptance criteria

v0.1.0 is complete only when:

- supported source compiles deterministically;
- blocked source never receives an authoritative contract ID;
- every successful outcome predicate has a permitted proof path;
- circular proof is rejected;
- intent-preservation covers every semantic source declaration;
- mutation fixtures demonstrate rejection of supported near misses;
- all retained artifacts match the manifest;
- source and clean-wheel tests pass independently;
- the downloadable archive passes source and rebuilt-wheel verification;
- Python 3.10–3.13 CI passes;
- the workbench is usable at desktop and 390-pixel width;
- public claims remain within this specification.

## 23. Design decision

Proceed with the deterministic controlled-language compiler, proof-obligation graph, intent-preservation report and contract mutation testing as one coherent v0.1.0 product.

Do not add a model-dependent free-form interpreter, hosted service, database, signing system or arbitrary plugin execution to the trusted core.