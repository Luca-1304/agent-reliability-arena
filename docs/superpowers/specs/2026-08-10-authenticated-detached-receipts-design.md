# Authenticated Detached Receipts Design

## Purpose

The repeated-experiment reliability chain now has four provider-free evidence layers:

1. hash-chained transport records inside each trial ledger;
2. a hash-chained root witness for independently verified completed trials;
3. deterministic detached receipts that commit exact witness prefixes outside the experiment root;
4. an immutable private evidence-set index for finalized disclosure-safe evidence.

A detached receipt detects replacement of the experiment root only while at least one trusted receipt copy survives. The next remaining local threat is an actor or failure domain that can rewrite both the experiment root and the detached receipt file. This change adds a deliberately narrow cryptographic authentication layer using HMAC-SHA256 and an independently retained 256-bit operator secret.

This is **not a digital signature and not external notarization**. HMAC uses a shared secret, so anyone who possesses the authentication key can create a valid tag. The gain is that rewriting the experiment root and receipt is no longer enough: a replacement authentication envelope also requires the independently retained secret.

## Chosen approach

Three approaches were considered:

1. **Public-key Ed25519 signature.** Best asymmetric verification model, but Python 3.10–3.13 does not provide Ed25519 in the standard library. Adding a cryptographic runtime dependency or relying on platform-specific OpenSSL/SSH tooling would expand supply-chain and platform assumptions.
2. **Remote timestamp/transparency service.** Strong independent anchoring, but it adds network availability, external trust, identity/credential handling and operational authority before a real provider experiment has even been executed.
3. **Offline HMAC-SHA256 authentication envelope.** Standard-library-only, deterministic, provider-free, cross-platform and materially stronger than an unauthenticated detached receipt when the secret is retained outside the experiment-root failure domain. This is the selected intermediate stage.

A later separately reviewed stage may replace or supplement HMAC with asymmetric signatures or a remote transparency/timestamp anchor.

## Artifact model

The existing detached receipt remains unchanged:

`arena-repeated-experiment-detached-witness-receipt-v1`

Authentication is a separate create-once JSON artifact so existing receipt semantics and verification remain stable.

Authentication envelope schema:

`arena-repeated-experiment-detached-receipt-auth-v1`

Exact fields:

- `schema_version`
- `algorithm`
- `receipt_digest`
- `key_id`
- `auth_tag`

`algorithm` is exactly `hmac-sha256`.

The envelope contains no secret key, experiment path, receipt path, prompt, output, provider payload, credential, operator note, price, timestamp or machine identifier.

## Key model

The authentication key is exactly 32 bytes (256 bits).

Production Python APIs receive the key as `bytes`; they never read global environment state themselves. The module CLI reads the key only from:

`ARENA_RECEIPT_AUTH_KEY_HEX`

The environment value must be exactly 64 hexadecimal characters and decodes to exactly 32 bytes. Uppercase/lowercase hex may be accepted on input, but no key material is ever echoed in normal or error output.

The CLI does not accept the secret as a command-line argument because command arguments may appear in shell history or process listings. The tool does not generate or persist keys. Key creation/storage is an operator responsibility outside this repository.

## Key identifier

The envelope includes a non-secret key identifier so an operator can tell which independently retained secret is needed without exposing it.

Use a domain-separated SHA-256 identifier:

```text
key_id = SHA256(
    b"arena-repeated-receipt-auth-key-id-v1\x00" + key_bytes
)
```

The design requires a uniformly random 256-bit key. The key identifier is not a password-hardening mechanism and must not be used with human-memorable or low-entropy secrets.

## Authentication message

HMAC authenticates the existing canonical `receipt_digest`, not the receipt path or current experiment path.

Use domain separation:

```text
message = b"arena-repeated-receipt-auth-v1\x00" + bytes.fromhex(receipt_digest)
auth_tag = HMAC-SHA256(key_bytes, message)
```

The receipt digest already commits the complete deterministic detached-receipt contents. Authenticating that digest therefore binds the HMAC envelope to the exact receipt while keeping the envelope compact.

## Production interfaces

Create a focused module:

`src/agent_reliability_arena/repeated_receipt_auth.py`

Public constants:

```python
AUTH_SCHEMA = "arena-repeated-experiment-detached-receipt-auth-v1"
AUTH_ALGORITHM = "hmac-sha256"
AUTH_KEY_ENV = "ARENA_RECEIPT_AUTH_KEY_HEX"
```

Public functions:

```python
def write_detached_receipt_auth(
    experiment_root: Path,
    receipt_path: Path,
    auth_path: Path,
    key: bytes,
) -> dict[str, object]


def verify_detached_receipt_auth(
    experiment_root: Path,
    receipt_path: Path,
    auth_path: Path,
    key: bytes,
) -> dict[str, object]
```

Both functions first use the existing `verify_detached_witness_receipt(...)` path so a cryptographically valid envelope cannot make an invalid experiment/receipt pair look valid.

The module may expose:

```text
python -m agent_reliability_arena.repeated_receipt_auth create --experiment-root ROOT --receipt RECEIPT --auth AUTH
python -m agent_reliability_arena.repeated_receipt_auth verify --experiment-root ROOT --receipt RECEIPT --auth AUTH
```

No `pyproject.toml` console-script entry is added.

## Detached-path boundary

The authentication envelope is intended to be retained outside the experiment root, just like the detached receipt.

Creation and verification require:

- experiment root is a regular non-symlink directory;
- receipt already passes the existing detached-receipt outside-root checks;
- auth parent exists and resolves to a directory;
- resolved auth parent is neither the experiment root nor a descendant;
- auth output is create-once and not a symlink;
- no parent directory is auto-created;
- write uses `O_EXCL`, restrictive permissions where supported, flush and `fsync`.

The auth file may live beside the receipt or in a different independently retained location. No same-directory requirement is imposed because separate retention domains may be useful.

## Creation algorithm

1. Validate the 32-byte key without logging it.
2. Call `verify_detached_witness_receipt(experiment_root, receipt_path)`.
3. Parse the receipt independently with duplicate-key/exact-field validation sufficient to obtain its lowercase 64-hex `receipt_digest`.
4. Derive the domain-separated `key_id`.
5. Derive the domain-separated HMAC-SHA256 `auth_tag` over the binary receipt digest.
6. Build the exact authentication envelope.
7. Persist it with exclusive-create durability.
8. Re-read the persisted envelope and verify it against the current experiment, receipt and supplied key before returning.

## Verification algorithm

1. Validate the 32-byte key without logging it.
2. Apply the auth outside-root/non-symlink path boundary.
3. Parse the auth envelope with duplicate-key and exact-field rejection.
4. Require exact schema and algorithm values.
5. Validate all digests as lowercase 64-hex strings.
6. Recompute the envelope key identifier and compare using `hmac.compare_digest`.
7. Call `verify_detached_witness_receipt(...)` to independently reverify the current experiment and committed witness prefix.
8. Require the auth envelope `receipt_digest` to equal the verified detached receipt digest.
9. Recompute the HMAC tag and compare with `hmac.compare_digest`.
10. Return a compact result containing only verification status, algorithm, key ID, receipt digest and existing receipt checkpoint metadata.

## Fail-closed cases

Reject:

- key not exactly 32 bytes;
- missing or malformed environment key in CLI mode;
- auth output inside the experiment root;
- auth target already existing or symlinked;
- auth parent missing or resolving inside the root;
- malformed UTF-8 or JSON;
- duplicate/unknown/missing fields;
- wrong schema or algorithm;
- malformed key ID, receipt digest or auth tag;
- key ID mismatch;
- receipt digest mismatch;
- HMAC mismatch;
- any underlying detached-receipt verification failure;
- any current witness/trial evidence inconsistency detected by the existing receipt verifier.

No failure message may include the secret key or raw environment value.

## Threat boundary

This stage protects against replacement of:

- the experiment root alone;
- the experiment root plus witness;
- the experiment root plus witness plus detached receipt;
- the above plus an unauthenticated replacement auth envelope when the attacker does **not** possess the HMAC key.

It does not protect against:

- compromise/disclosure of the HMAC key;
- an attacker controlling both all evidence copies and the independently retained key;
- malicious key generation using weak/guessable material;
- proof to a third party that does not share/trust the same secret;
- trusted timestamp or transparency-log guarantees.

The HMAC key must therefore be retained outside the same failure/adversary domain as the experiment evidence for the control to add meaningful assurance.

## Testing

Provider-free tests cover:

- exact envelope shape and deterministic HMAC derivation;
- successful creation and immediate verification;
- successful verification after later witness appends that leave the detached receipt valid;
- wrong 32-byte key rejected;
- short/long/non-bytes keys rejected at the Python API;
- malformed/missing CLI environment key rejected without echoing the supplied value;
- auth output inside root/existing/symlink/resolved-parent boundary rejected;
- auth envelope unknown/duplicate/malformed fields rejected;
- receipt replacement rejected even when the new receipt independently verifies against a replacement local history;
- auth-tag tampering rejected;
- key-ID tampering rejected;
- underlying witness/receipt corruption still rejected before HMAC acceptance;
- module CLI create/verify provider-free smoke behavior;
- no packaged command, dependency, workflow permission, provider call or Vercel change.

Existing Tests, Fast, Deep, Specialist, History, CodeQL, Concurrent Evidence Ledger and Pages verification remain the merge authority.

## Documentation and roadmap

Update `docs/REPEATED_EXPERIMENT_RUNBOOK.md` after the detached-receipt section with authenticated receipt usage, key-handling rules and the HMAC-versus-signature distinction.

Update Stage 8 in `ROADMAP.md` to record authenticated detached receipt infrastructure without claiming external notarization, public-key signatures or real-provider evidence.

## Scope and authority

This change adds no:

- provider execution;
- provider credential handling;
- network request;
- runtime dependency;
- Git mutation authority;
- Vercel integration;
- release/publication authority;
- automatic key generation/storage;
- public-key signature claim;
- trusted timestamp claim;
- model-performance claim.
