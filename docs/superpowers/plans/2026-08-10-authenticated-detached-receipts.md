# Authenticated Detached Receipts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add standard-library-only HMAC-SHA256 authentication envelopes for detached repeated-experiment receipts using an independently retained 256-bit operator secret.

**Architecture:** Keep `repeated_receipt.py` unchanged. Add a focused `repeated_receipt_auth.py` module that verifies the existing detached receipt first, authenticates its canonical `receipt_digest` with a domain-separated HMAC-SHA256 tag, writes a separate create-once envelope, and verifies it with constant-time comparisons. Production functions accept raw key bytes; only the module CLI reads `ARENA_RECEIPT_AUTH_KEY_HEX`.

**Tech Stack:** Python 3.10–3.13 standard library (`hashlib`, `hmac`, `json`, `os`, `argparse`), existing detached receipt verifier, `unittest`, existing GitHub Actions reliability gates.

## Global Constraints

- No provider execution or provider credential handling.
- No network request or paid action.
- No runtime dependency.
- No Git mutation, Vercel integration, publication or release authority.
- Authentication key is exactly 32 bytes and is never stored or echoed.
- CLI secret input is only `ARENA_RECEIPT_AUTH_KEY_HEX`; there is no secret CLI argument.
- Envelope output resolves outside the experiment root and is exclusive-create/no-overwrite.
- Envelope stores no secret, path, prompt, output, provider payload, operator note, price, timestamp or machine identifier.
- This is HMAC authentication, not a public-key digital signature or external notarization.
- Merge only an unchanged exact PR head after all triggered reliability workflow families succeed.

---

### Task 1: Lock the authentication contract with tests

**Files:**
- Create: `tests/test_repeated_receipt_auth.py`

**Interfaces:**
- Planned: `AUTH_SCHEMA`, `AUTH_ALGORITHM`, `AUTH_KEY_ENV`, `write_detached_receipt_auth(...)`, `verify_detached_receipt_auth(...)`, `main(...)`.
- Reuse existing detached-receipt fixtures and witness helpers.

- [ ] Create a fixture with a valid experiment, detached receipt, separate auth directory and fixed 32-byte test key.
- [ ] Require exact five-field envelope shape, algorithm/schema values, domain-separated key ID and deterministic HMAC tag.
- [ ] Require successful immediate verification and successful verification after later witness appends that leave the receipt valid.
- [ ] Reject wrong keys, short/long/non-bytes Python keys, existing/symlink/inside-root auth paths and parent symlinks resolving inside the root.
- [ ] Reject malformed/duplicate/unknown envelope fields, wrong schema/algorithm, changed receipt digest, key ID and auth tag.
- [ ] Replace root plus receipt with a different internally valid local history and prove the old authenticated envelope cannot be replaced without the key.
- [ ] Test CLI create/verify with `ARENA_RECEIPT_AUTH_KEY_HEX`; reject missing/malformed values without echoing secret material.

### Task 2: Implement the focused authentication module

**Files:**
- Create: `src/agent_reliability_arena/repeated_receipt_auth.py`
- Test: `tests/test_repeated_receipt_auth.py`

**Interfaces:**

```python
AUTH_SCHEMA = "arena-repeated-experiment-detached-receipt-auth-v1"
AUTH_ALGORITHM = "hmac-sha256"
AUTH_KEY_ENV = "ARENA_RECEIPT_AUTH_KEY_HEX"

write_detached_receipt_auth(
    experiment_root: Path,
    receipt_path: Path,
    auth_path: Path,
    key: bytes,
) -> dict[str, object]

verify_detached_receipt_auth(
    experiment_root: Path,
    receipt_path: Path,
    auth_path: Path,
    key: bytes,
) -> dict[str, object]
```

- [ ] Validate key type and exact 32-byte length without logging key bytes.
- [ ] Parse the detached receipt with duplicate-key and exact shape validation sufficient to obtain `receipt_digest`.
- [ ] Call existing `verify_detached_witness_receipt(...)` before accepting or authenticating a receipt.
- [ ] Compute `key_id = SHA256(b"arena-repeated-receipt-auth-key-id-v1\x00" + key)`.
- [ ] Compute `auth_tag = HMAC-SHA256(key, b"arena-repeated-receipt-auth-v1\x00" + bytes.fromhex(receipt_digest))`.
- [ ] Write exact envelope `{schema_version, algorithm, receipt_digest, key_id, auth_tag}` with `O_EXCL`, `O_NOFOLLOW` where available, `0o600`, flush and `fsync`.
- [ ] Verify schema/algorithm/digests, compare key ID and tag with `hmac.compare_digest`, require envelope receipt digest to equal the independently verified current detached receipt.
- [ ] Add module CLI `create|verify`; read only `ARENA_RECEIPT_AUTH_KEY_HEX`, never add a `pyproject.toml` script entry.

### Task 3: Document the new trust boundary

**Files:**
- Modify: `docs/REPEATED_EXPERIMENT_RUNBOOK.md`
- Modify: `ROADMAP.md`

- [ ] Add authenticated detached receipt commands and environment-key rules to the runbook.
- [ ] State clearly that HMAC is shared-secret authentication, not a digital signature, trusted timestamp or public proof.
- [ ] Record the new Stage 8 infrastructure while retaining `real repeated execution not performed` and `comparative_claim_permitted: false`.

### Task 4: Full verification and guarded integration

**Files:**
- Review all changed files.

- [ ] Compare against `main`: require behind count 0, expected files only, no workflow/dependency/permission/release/Vercel changes.
- [ ] Open one focused PR documenting the exact threat improvement and remaining key-compromise boundary.
- [ ] Freeze the PR head and require all triggered Tests, Fast, Deep, Specialist, History, CodeQL, Concurrent Evidence Ledger and Pages verification jobs to succeed.
- [ ] Require no unresolved review threads, mergeable PR and branch 0 behind `main`.
- [ ] Squash-merge with `expected_head_sha` equal to the exact verified head; preserve the branch.
- [ ] Confirm merge SHA is identical to `main`, no open PR remains and no retired Vercel deployment was triggered. Do not create ongoing monitoring.
