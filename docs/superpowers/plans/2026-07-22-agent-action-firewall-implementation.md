# Agent Action Firewall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and independently verify a standalone deterministic policy compiler and one-time execution-permit firewall that blocks dangerous, unauthorised or scope-expanding agent actions before execution.

**Architecture:** Strict JSON inputs are normalised into content-addressed actions, security descriptors, context and trust registries. A finite policy compiler proves monotonic attenuation and emits a canonical policy bundle. The evaluator produces explainable decisions; enforcement mode authenticates one-time approval grants and permits through separate HMAC keys and atomically prevents replay through SQLite. The external executor receives a frozen verified action but remains outside the firewall package.

**Tech Stack:** Python 3.10–3.13 standard library only at runtime; `unittest`; `dataclasses`; SHA-256 and HMAC-SHA-256; `sqlite3`; `argparse`; HTML5, CSS and vanilla JavaScript; setuptools wheel packaging. No network or paid-model calls in tests.

## Global Constraints

- Trusted core is deterministic and contains no model judge.
- Source JSON may contain ordinary whitespace but rejects duplicate keys, post-NFC duplicates, floats, unsafe integers, lone surrogates and unknown fields.
- Security identities use canonical UTF-8 JSON, NFC strings, sorted keys and domain-separated SHA-256.
- Descriptor display metadata never changes authority.
- Default policy outcome is `DENY`.
- Child policy layers may only attenuate parent authority.
- Approval-authority and permit-issuer keys have different IDs, files, bytes and HMAC domains.
- Approver identity and role come from the current trusted registry, never self-assertion alone.
- One approval grant may issue one permit; one permit may be consumed once.
- SQLite atomicity covers cooperating grant/permit state only, not the external tool side effect.
- Permit verification returns an immutable `VerifiedAction`.
- Authorisation is not evidence of task completion.
- No public claim of legal identity, trusted time, universal safety, certification or realised revenue.

---

## Milestone 1 — Canonical trust inputs

### Task 1: Establish package, public models and stable errors

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_action_firewall/__init__.py`
- Create: `src/agent_action_firewall/models.py`
- Create: `src/agent_action_firewall/errors.py`
- Create: `tests/test_public_api.py`
- Create: `tests/test_errors.py`

**Interfaces:**
- Produces: `Decision`, `ReceiptAssurance`, `ActionRecord`, `DecisionResult`, `VerifiedAction`, `FirewallError` subclasses.

- [ ] **Step 1: Write failing import tests**

```python
# tests/test_public_api.py
import unittest


class PublicApiTests(unittest.TestCase):
    def test_public_types_import(self) -> None:
        from agent_action_firewall import Decision, ReceiptAssurance, VerifiedAction

        self.assertEqual(Decision.DENY.value, "DENY")
        self.assertEqual(ReceiptAssurance.MAC_AUTHENTICATED.value, "MAC_AUTHENTICATED")
        self.assertEqual(VerifiedAction.__name__, "VerifiedAction")
```

- [ ] **Step 2: Run and verify the missing-package failure**

Run:

```bash
python -m unittest tests.test_public_api tests.test_errors -v
```

Expected: `ModuleNotFoundError: No module named 'agent_action_firewall'`.

- [ ] **Step 3: Implement package metadata and exact public types**

`models.py` must define string enums for `ALLOW`, `ALLOW_WITH_CONSTRAINTS`, `REQUIRE_APPROVAL`, `DENY` and receipt assurance values. `VerifiedAction` is a frozen dataclass containing canonical bytes, read-only parsed action, all bound digests, immutable constraints, permit digest and receipt ID.

`errors.py` defines stable codes for canonicalisation, schema, descriptor, resource, policy compilation, policy conflict, authentication, expiry, replay, state, receipt and operational failures.

- [ ] **Step 4: Run focused tests**

```bash
PYTHONPATH=src python -m unittest tests.test_public_api tests.test_errors -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/agent_action_firewall tests/test_public_api.py tests/test_errors.py
git commit -m "feat: establish action firewall package boundary"
```

### Task 2: Implement strict JSON, canonical bytes and immutable values

**Files:**
- Create: `src/agent_action_firewall/canonical.py`
- Create: `src/agent_action_firewall/immutable.py`
- Create: `tests/test_canonical.py`
- Create: `tests/test_immutable.py`

**Interfaces:**
- Produces: `parse_strict_json(data: bytes) -> object`, `canonical_bytes(value: object) -> bytes`, `domain_hash(domain: str, value: object) -> str`, `deep_freeze(value: object) -> object`.

- [ ] **Step 1: Write failing edge-case tests**

```python
# tests/test_canonical.py
import unittest

from agent_action_firewall.canonical import canonical_bytes, parse_strict_json
from agent_action_firewall.errors import CanonicalizationError


class CanonicalTests(unittest.TestCase):
    def test_nfc_and_key_order_are_stable(self) -> None:
        self.assertEqual(canonical_bytes({"b": 1, "a": "e\u0301"}), b'{"a":"\\u00e9","b":1}')

    def test_duplicate_after_nfc_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            parse_strict_json(b'{"\\u00e9":1,"e\\u0301":2}')

    def test_float_and_unsafe_integer_are_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            canonical_bytes({"value": 1.5})
        with self.assertRaises(CanonicalizationError):
            canonical_bytes({"value": 1 << 53})
```

```python
# tests/test_immutable.py
import unittest

from agent_action_firewall.immutable import deep_freeze


class ImmutableTests(unittest.TestCase):
    def test_nested_mapping_cannot_be_changed(self) -> None:
        frozen = deep_freeze({"resource": {"to": ["a@example.com"]}})
        with self.assertRaises(TypeError):
            frozen["resource"]["to"] = ()
```

- [ ] **Step 2: Run and verify missing modules**

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_immutable -v
```

Expected: import failures.

- [ ] **Step 3: Implement bounded canonicalisation and recursive freezing**

Use `json.loads(..., object_pairs_hook=...)`, NFC normalisation, safe integer bounds, maximum depth 32 and maximum canonical size 1 MiB. `deep_freeze` uses `MappingProxyType`, tuples and primitive immutable values.

- [ ] **Step 4: Run focused tests**

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_immutable -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/canonical.py src/agent_action_firewall/immutable.py tests/test_canonical.py tests/test_immutable.py
git commit -m "feat: add canonical identities and immutable values"
```

### Task 3: Implement security descriptors and trust registry

**Files:**
- Create: `src/agent_action_firewall/descriptors.py`
- Create: `src/agent_action_firewall/trust.py`
- Create: `tests/test_descriptors.py`
- Create: `tests/test_trust.py`

**Interfaces:**
- Produces: `DescriptorRegistry.from_object`, `descriptor_security_digest`, `descriptor_artifact_digest`, `TrustRegistry.from_object`, `resolve_approval_authority`, `resolve_permit_issuer`.

- [ ] **Step 1: Write authority-boundary tests**

```python
# tests/test_descriptors.py
import unittest

from agent_action_firewall.descriptors import DescriptorRegistry


class DescriptorTests(unittest.TestCase):
    def test_display_change_preserves_security_digest(self) -> None:
        first = DescriptorRegistry.from_object(self.fixture("Send email"))
        second = DescriptorRegistry.from_object(self.fixture("Transmit message"))
        self.assertEqual(first.get("mail.send").security_digest, second.get("mail.send").security_digest)
        self.assertNotEqual(first.artifact_digest, second.artifact_digest)
```

```python
# tests/test_trust.py
import unittest

from agent_action_firewall.errors import AuthenticationError
from agent_action_firewall.trust import TrustRegistry


class TrustTests(unittest.TestCase):
    def test_self_asserted_owner_is_rejected(self) -> None:
        registry = TrustRegistry.from_object(self.fixture())
        with self.assertRaises(AuthenticationError):
            registry.authorise_approver("unknown-key", "user:luca", "owner", now="2026-07-22T12:00:00Z")
```

- [ ] **Step 2: Run and verify missing modules**

```bash
PYTHONPATH=src python -m unittest tests.test_descriptors tests.test_trust -v
```

Expected: import failures.

- [ ] **Step 3: Implement split descriptor identity and active registry checks**

Security digest covers only descriptor security fields. Artifact digest covers the complete registry. Trust registry validates unique key IDs, active windows, roles, permit issuers and generation. It exposes one canonical registry digest.

- [ ] **Step 4: Run focused tests**

```bash
PYTHONPATH=src python -m unittest tests.test_descriptors tests.test_trust -v
```

Expected: display-only mutation preserves authority; inactive, future, expired and unknown keys fail.

- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/descriptors.py src/agent_action_firewall/trust.py tests/test_descriptors.py tests/test_trust.py
git commit -m "feat: bind descriptors and approvers to trusted registries"
```

### Task 4: Implement typed resource and action normalisation

**Files:**
- Create: `src/agent_action_firewall/resources.py`
- Create: `src/agent_action_firewall/actions.py`
- Create: `tests/test_resources.py`
- Create: `tests/test_actions.py`

**Interfaces:**
- Produces: `normalise_resource`, `ActionNormaliser.normalise(native_action, context) -> ActionRecord`.
- Consumes descriptor and trust registries.

- [ ] **Step 1: Write substitution and path tests**

Tests must prove rejection of POSIX traversal, Windows drive and UNC substitution, URL user-info, display-name email syntax, unsafe Unicode local parts and floats. They must prove `cc`→`bcc`, body digest, payee, amount, capability and descriptor-security changes alter the action digest while display-only descriptor changes do not.

- [ ] **Step 2: Run and verify missing normalisers**

```bash
PYTHONPATH=src python -m unittest tests.test_resources tests.test_actions -v
```

Expected: import failures.

- [ ] **Step 3: Implement trusted derived fields**

Callers supply declared values only. Normaliser derives descriptor security digest, canonical host/domain/path, context digest, trust registry digest, principal digest and final action digest. Caller-supplied derived fields are rejected as unknown fields.

Messaging separates `to`, `cc` and `bcc`. Money uses integer minor units and exact uppercase currency. Network redirects are not automatically followed. Resolver evidence is accepted only from an injected trusted resolver interface.

- [ ] **Step 4: Run Milestone 1 suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all canonical-input tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/resources.py src/agent_action_firewall/actions.py tests/test_resources.py tests/test_actions.py
git commit -m "feat: normalise typed action resources"
```

## Milestone 2 — Policy compiler

### Task 5: Implement constraints, matching and subset proofs

**Files:**
- Create: `src/agent_action_firewall/constraints.py`
- Create: `src/agent_action_firewall/selectors.py`
- Create: `tests/test_constraints.py`
- Create: `tests/test_selectors.py`

**Interfaces:**
- Produces: `intersect_constraints`, `constraints_narrower_or_equal`, `selector_matches`, `selector_is_subset`.

- [ ] **Step 1: Write finite proof tests**

Tests cover finite allowlists, path descendants, label-boundary domains, numeric maxima, TTL, required booleans, data classes, retries, incompatible path styles, empty intersections and cross-currency rejection.

- [ ] **Step 2: Run and confirm missing modules**

```bash
PYTHONPATH=src python -m unittest tests.test_constraints tests.test_selectors -v
```

Expected: import failures.

- [ ] **Step 3: Implement only decidable v0.1 relations**

Unknown selectors or constraints raise `PolicyCompilationError`; the compiler never approximates containment. Constraint objects are canonical and immutable.

- [ ] **Step 4: Run focused tests**

```bash
PYTHONPATH=src python -m unittest tests.test_constraints tests.test_selectors -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/constraints.py src/agent_action_firewall/selectors.py tests/test_constraints.py tests/test_selectors.py
git commit -m "feat: add finite policy containment relations"
```

### Task 6: Implement monotonic policy compilation and atomic publication

**Files:**
- Create: `src/agent_action_firewall/policies.py`
- Create: `src/agent_action_firewall/bundles.py`
- Create: `tests/test_policies.py`
- Create: `tests/test_policy_publication.py`

**Interfaces:**
- Produces: `PolicyCompiler.compile(source, descriptors) -> CompiledPolicy`, `publish_compiled_policy(compiled, output)`.

- [ ] **Step 1: Write widening and determinism tests**

Tests prove:

- child allow selector must be contained by one parent allow-capable rule;
- child cannot reduce effect severity;
- child cannot widen path, recipient, domain, data-class, amount, retry or TTL limits;
- deny may be added anywhere;
- cycles/disconnected layers fail;
- rule/layer reordering preserves compiled digest;
- failed compile publishes no authoritative digest;
- unrelated non-empty target is never replaced.

- [ ] **Step 2: Run and verify missing compiler**

```bash
PYTHONPATH=src python -m unittest tests.test_policies tests.test_policy_publication -v
```

Expected: import failures.

- [ ] **Step 3: Implement topological compilation and transactional bundle output**

Each child allow-capable rule is checked against one rule in its direct parent layer. Compiled rules are semantically sorted. Bundle contains canonical policy, descriptor security registry, diagnostics, manifest and product marker. Output uses temporary siblings and `os.replace`.

- [ ] **Step 4: Run Milestone 2 tests**

```bash
PYTHONPATH=src python -m unittest tests.test_constraints tests.test_selectors tests.test_policies tests.test_policy_publication -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/policies.py src/agent_action_firewall/bundles.py tests/test_policies.py tests/test_policy_publication.py
git commit -m "feat: compile monotonic action policies"
```

### Task 7: Implement `firewall-policy`

**Files:**
- Create: `src/agent_action_firewall/policy_cli.py`
- Create: `tests/test_policy_cli.py`

**Interfaces:**
- Produces installed command `firewall-policy` with `lint` and `compile`.

- [ ] **Step 1: Write subprocess tests for JSON output and exit code 6**
- [ ] **Step 2: Run and verify the missing CLI failure**
- [ ] **Step 3: Implement strict argument parsing, stable JSON diagnostics and no default traceback**
- [ ] **Step 4: Run CLI tests and `--help`**
- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/policy_cli.py tests/test_policy_cli.py pyproject.toml
git commit -m "feat: add firewall policy command"
```

## Milestone 3 — Decisions and explanation

### Task 8: Implement deterministic evaluation and receipts

**Files:**
- Create: `src/agent_action_firewall/evaluator.py`
- Create: `src/agent_action_firewall/receipts.py`
- Create: `src/agent_action_firewall/explain.py`
- Create: `tests/test_evaluator.py`
- Create: `tests/test_receipts.py`
- Create: `tests/test_explain.py`

**Interfaces:**
- Produces: `FirewallEvaluator.evaluate(..., approval=None, enforcement=None) -> DecisionResult`, `verify_receipt`, `explain_receipt`.

- [ ] **Step 1: Write decision-lattice tests**

Tests cover default deny, hard deny precedence, approval challenge, constraint intersection, action-constraint violation, allowed action, post-approval `ALLOW_WITH_CONSTRAINTS`, approval conflict denial and semantic determinism under injected time/nonces.

- [ ] **Step 2: Run and verify missing evaluator**
- [ ] **Step 3: Implement analysis-mode decisions and content-addressed receipts**
- [ ] **Step 4: Run focused tests**
- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/evaluator.py src/agent_action_firewall/receipts.py src/agent_action_firewall/explain.py tests/test_evaluator.py tests/test_receipts.py tests/test_explain.py
git commit -m "feat: evaluate and explain firewall decisions"
```

## Milestone 4 — Approval and one-time enforcement

### Task 9: Implement key resolution, challenges and grants

**Files:**
- Create: `src/agent_action_firewall/keys.py`
- Create: `src/agent_action_firewall/approvals.py`
- Create: `tests/test_keys.py`
- Create: `tests/test_approvals.py`

**Interfaces:**
- Produces: `FileKeyResolver`, `create_challenge`, `issue_grant`, `verify_grant`.

- [ ] **Step 1: Write known-answer and authority tests**

Tests prove regular-file/symlink handling, minimum key length, registry role binding, separate approval/permit key IDs and bytes, HMAC known answer, expiry, altered action/policy/context/registry, constraint widening and hard-deny non-approval.

- [ ] **Step 2: Run and verify missing modules**
- [ ] **Step 3: Implement domain-separated HMAC grant flow**
- [ ] **Step 4: Run focused tests**
- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/keys.py src/agent_action_firewall/approvals.py tests/test_keys.py tests/test_approvals.py
git commit -m "feat: add registry-bound one-time approval grants"
```

### Task 10: Implement SQLite issuance, permits and atomic consumption

**Files:**
- Create: `src/agent_action_firewall/replay_store.py`
- Create: `src/agent_action_firewall/permits.py`
- Modify: `src/agent_action_firewall/evaluator.py`
- Create: `tests/test_replay_store.py`
- Create: `tests/test_permits.py`
- Create: `tests/test_multiprocess_replay.py`

**Interfaces:**
- Produces: `ReplayStore`, `issue_permit`, `PermitVerifier.verify_and_consume(...) -> VerifiedAction`.

- [ ] **Step 1: Write issuance and replay tests**

Tests prove:

- one grant issues one permit;
- correctly MACed but unrecorded permit is rejected;
- changed action, descriptor, policy, context or registry invalidates permit;
- expired permit and clock regression reject;
- exactly one process consumes a shared permit;
- returned action is immutable;
- tool failure after consumption cannot reuse permit.

- [ ] **Step 2: Run and verify missing state modules**
- [ ] **Step 3: Implement versioned SQLite schema and `BEGIN IMMEDIATE` transactions**

Schema has unique grant digest/nonce, permit digest/nonce, issued/consumed status, receipt ID, expiry and last accepted wall clock. Enable foreign keys, bounded busy timeout and rollback on all exceptions.

- [ ] **Step 4: Run permit and multi-process tests repeatedly**

```bash
PYTHONPATH=src python -m unittest tests.test_replay_store tests.test_permits tests.test_multiprocess_replay -v
PYTHONPATH=src python -m unittest tests.test_multiprocess_replay -v
```

Expected: exactly one successful consumer every run.

- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/replay_store.py src/agent_action_firewall/permits.py src/agent_action_firewall/evaluator.py tests/test_replay_store.py tests/test_permits.py tests/test_multiprocess_replay.py
git commit -m "feat: enforce one-time action permits"
```

### Task 11: Implement enforcement CLIs

**Files:**
- Create: `src/agent_action_firewall/evaluate_cli.py`
- Create: `src/agent_action_firewall/approve_cli.py`
- Create: `src/agent_action_firewall/explain_cli.py`
- Create: `tests/test_evaluate_cli.py`
- Create: `tests/test_approve_cli.py`
- Create: `tests/test_explain_cli.py`

**Interfaces:**
- Produces `firewall-evaluate`, `firewall-approve`, `firewall-explain`.

- [ ] **Step 1: Write full compile→evaluate→approve→permit→consume subprocess workflow**
- [ ] **Step 2: Run and confirm missing commands**
- [ ] **Step 3: Implement stable JSON output and exit-code mapping 0/2/3/4/5/6/7/8**
- [ ] **Step 4: Run CLI tests and all four `--help` commands**
- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/*_cli.py tests/test_evaluate_cli.py tests/test_approve_cli.py tests/test_explain_cli.py pyproject.toml
git commit -m "feat: add action firewall enforcement commands"
```

## Milestone 5 — Evidence, integrations and release

### Task 12: Implement portfolio adapters and deterministic corpus

**Files:**
- Create: `src/agent_action_firewall/adapters/contract_compiler.py`
- Create: `src/agent_action_firewall/adapters/evidence_ledger.py`
- Create: `src/agent_action_firewall/adapters/completion_verifier.py`
- Create: `scripts/generate_reference_corpus.py`
- Create: `fixtures/scenarios.json`
- Create: `reference_runs/`
- Create: `tests/test_adapters.py`
- Create: `tests/test_reference_corpus.py`
- Create: `tests/test_corpus_regeneration.py`

**Interfaces:**
- Contract adapter emits restrictive overlays only.
- Ledger adapter emits allowlisted action/decision/grant/permit references.
- Verifier adapter labels permit as precondition evidence only.

- [ ] **Step 1: Write adapter-loss and exact-outcome tests**
- [ ] **Step 2: Run and verify missing corpus**
- [ ] **Step 3: Generate at least the 60 named base/amendment scenarios and exact expected outcomes**
- [ ] **Step 4: Regenerate into a temporary directory and compare every path, byte length and SHA-256**
- [ ] **Step 5: Commit**

```bash
git add src/agent_action_firewall/adapters scripts/generate_reference_corpus.py fixtures reference_runs tests/test_adapters.py tests/test_reference_corpus.py tests/test_corpus_regeneration.py
git commit -m "test: add deterministic firewall evidence corpus"
```

### Task 13: Build static policy workbench

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`
- Create: `web/data/scenarios.json`
- Create: `tests/test_web.py`

- [ ] **Step 1: Write static claim, accessibility and no-external-runtime tests**
- [ ] **Step 2: Run and verify missing web files**
- [ ] **Step 3: Implement six required scenarios and limitation panel**
- [ ] **Step 4: Serve locally and review desktop plus 390 CSS pixel layout**
- [ ] **Step 5: Commit**

```bash
git add web tests/test_web.py
git commit -m "feat: add action firewall policy workbench"
```

### Task 14: Add documentation, release verifier and Python matrix

**Files:**
- Create: `README.md`
- Create: `RESULTS.md`
- Create: `THREAT_MODEL.md`
- Create: `docs/METHODOLOGY.md`
- Create: `docs/CONTRIBUTION.md`
- Create: `docs/DEMO_SCRIPT.md`
- Create: `docs/COMMERCIAL_USE.md`
- Create: `scripts/verify_release.py`
- Create: `scripts/run_installed_tests.py`
- Create: `.github/workflows/tests.yml`
- Create: `.github/workflows/pages.yml`
- Create: `tests/test_documentation.py`
- Create: `tests/test_packaging.py`
- Create: `LICENSE`

- [ ] **Step 1: Write documentation and packaging boundary tests**
- [ ] **Step 2: Run and verify missing release contract**
- [ ] **Step 3: Implement one release verifier**

The verifier compiles source, runs all tests, regenerates corpus/web data, replays every expected outcome, exercises four module CLIs, scans credentials/forbidden claims and verifies manifests.

- [ ] **Step 4: Run complete source gate**

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .
python scripts/verify_release.py
```

Expected: all checks pass without network access.

- [ ] **Step 5: Commit**

```bash
git add README.md RESULTS.md THREAT_MODEL.md docs scripts .github/workflows tests/test_documentation.py tests/test_packaging.py LICENSE
git commit -m "docs: prepare action firewall public release"
```

### Task 15: Independently verify wheel, ZIP and publication

**Files:**
- Modify only defects revealed by verification.
- Produce ZIP, wheel and release evidence outside the repository.

- [ ] **Step 1: Run final source verifier and build wheel without editable fallback**
- [ ] **Step 2: Install wheel into a clean environment outside the source tree and run installed tests, four commands and `pip check`**
- [ ] **Step 3: Create a clean ZIP, extract it elsewhere, rerun source verification, rebuild the wheel and repeat wheel-only tests**
- [ ] **Step 4: Record exact Git commit, test/scenario counts and SHA-256 values**
- [ ] **Step 5: Publish exact verified tree to `Luca-1304/agent-action-firewall` through a reviewed PR, Python 3.10–3.13 matrix and Pages deployment**
- [ ] **Step 6: Tag `v0.1.0` only after merged-code and public viewer verification**

## Plan self-review

### Spec coverage

- Canonical identities, descriptors, trust registry and typed resources: Tasks 1–4.
- Finite attenuation, intersections and transactional compilation: Tasks 5–7.
- Decision lattice, receipts and explanation: Task 8.
- Registry-bound approval, one-time grant, permit issuance and replay: Tasks 9–11.
- Contract/Ledger/Verifier boundaries and adversarial evidence: Task 12.
- Employer-facing workbench: Task 13.
- Claims, commercial boundary, reproducibility and packaging: Tasks 14–15.

### Placeholder scan

No `TBD`, `TODO`, unrestricted “handle edge cases”, unnamed validation step or deferred core feature remains. Each task states files, interfaces, red test purpose, command and commit boundary.

### Type consistency

- Decisions are consistently `ALLOW`, `ALLOW_WITH_CONSTRAINTS`, `REQUIRE_APPROVAL`, `DENY`.
- Security binding consistently uses `descriptor_security_digest`, `compiled_policy_digest`, `context_digest` and `trust_registry_digest`.
- Receipt assurance is consistently `CONTENT_ADDRESSED`, `MAC_AUTHENTICATED`, `INVALID`.
- Approval-authority and permit-issuer key roles stay separate.
- Grant issue, permit issue and permit consumption are three distinct states.
- `VerifiedAction` is always frozen and authorisation remains precondition evidence only.

The plan is approved for inline execution in the stated order.