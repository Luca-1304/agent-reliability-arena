# Agent Evidence Ledger — Final Adversarial Review

Date: 2026-07-22  
Base specification: `2026-07-22-agent-evidence-ledger-design.md`  
Tracking issue: #4  
Status: Approved and implementation-ready after the amendments below

This document records the final security, crash-consistency and protocol review. It is normative. Where it is more specific than the base design, this document takes precedence.

## Review conclusion

The selected architecture remains correct for v0.1.0: a local-first, portable, newline-delimited, SHA-256-chained event ledger with typed evidence classes, lifecycle validation, content-addressed artifacts, optional external-root comparison and a read-only disclosure viewer.

No hosted service, signing-key system, database, blockchain, arbitrary agent runner or compliance claim is required for the first release.

The review found no reason to change the product direction. It did identify protocol details that must be explicit before implementation.

## 1. Canonicalisation hardening

The canonical profile additionally requires:

- every object key and string value is normalised to Unicode NFC before validation and hashing;
- duplicate keys are rejected both before and after NFC normalisation;
- lone Unicode surrogate code points are rejected;
- integers are limited to the interoperable JSON safe-integer range `-(2^53 - 1)` through `2^53 - 1`;
- `previous_hash`, `event_hash` and artifact SHA-256 values are exactly 64 lowercase hexadecimal characters;
- decoded nesting depth is at most 32;
- one canonical event line is at most 1 MiB excluding its final newline;
- one event contains at most 128 references;
- event keys are sorted after normalisation;
- the verifier compares each supplied line byte-for-byte with its reconstructed canonical representation.

These limits prevent cross-runtime number ambiguity and bound accidental resource exhaustion without turning v0.1.0 into a general untrusted-data gateway.

## 2. Reference graph rules

Every event reference must:

- name an event in the same ledger;
- point to a strictly earlier sequence number;
- satisfy the exact reference cardinality required by its event type;
- never point to itself or forward in the stream.

Because only prior events are referenceable, the event-reference graph is acyclic by construction.

## 3. Attempt-window rules

One attempt window begins with `tool_attempted` and ends with exactly one `verification_decided`.

Within one attempt window, v0.1.0 permits at most one of each:

- `tool_reported`;
- `observation_recorded`;
- `completion_claimed`;
- `verification_decided`.

`tool_reported`, `observation_recorded` and `completion_claimed` must occur after the attempt and before its decision. A completion claim may occur before or after observation, but never changes the lifecycle state by itself.

Decision requirements are:

- `VERIFIED_COMPLETE` requires a latest relevant independent observation that matches the contract and whose referenced artifacts verify;
- `PARTIAL` requires a relevant independent observation showing only partial contract satisfaction;
- `SECURITY_REJECTED` requires a terminal independent observation;
- `FAILED` requires either a relevant failing observation or a successfully persisted execution error tied to the attempt;
- `UNVERIFIED` is used when the available evidence is insufficient, including when no valid independent observation exists.

A decision closes its attempt window. A new action requires `recovery_authorized`, a new proposal and a new authorisation. Recovery remains illegal after verified completion, security rejection or a terminal observation.

A recoverable decision may either proceed to bounded recovery or close as `aborted`; recovery is not mandatory.

## 4. Error-event boundary

`error_recorded` represents an error that was itself successfully persisted. It may be appended after `request_received` and before closure, and should reference the relevant earlier event when one exists.

A writer failure that prevents persistence cannot truthfully appear inside the ledger. Such a failure is returned by the CLI as an operational error and may be recorded by an external supervisory system.

## 5. Open and sealed verification

The verifier must support both working and final ledgers.

Assurance levels are:

- `OPEN_CHAIN_VALID` — an unsealed ledger is canonical, internally chained and lifecycle-valid so far;
- `INTERNAL_CHAIN_VALID` — a sealed ledger, seal, manifest and referenced artifacts are internally consistent;
- `EXPECTED_ROOT_MATCHED` — internal sealed consistency plus a matching independently retained checkpoint;
- `INVALID` — parsing, integrity, lifecycle, artifact, seal, manifest or checkpoint verification failed.

`ledger-export` requires a sealed ledger except for the explicit diagnostic mode described below.

The verifier is read-only. It creates no lock or metadata file. It records relevant file metadata before and after reading and returns an operational concurrency error when the source changes during verification.

## 6. Cooperative locking

The writer uses a platform-specific operating-system advisory lock on a dedicated `.ledger.lock` regular file:

- `fcntl.flock` on POSIX;
- `msvcrt.locking` on Windows.

The operating system releases the lock if the process exits, avoiding stale lock ownership files. Lock timeout is explicit. Correctness on network filesystems whose locking semantics do not match the local platform is not claimed.

The lock file is excluded from the seal manifest and disclosure output.

## 7. Atomic artifact attachment

Canonical artifact storage is:

```text
artifacts/<64-lowercase-hex-sha256>
```

No extension is used; `media_type` remains metadata in the event reference.

`ledger-record attach` must:

1. acquire the writer lock;
2. reject symbolic links and non-regular sources;
3. stream at most 64 MiB by default into a temporary file inside `artifacts/`;
4. calculate SHA-256 and byte length while copying;
5. flush and `fsync` the temporary file;
6. atomically replace the canonical digest path;
7. `fsync` the artifact directory where supported;
8. return the reference object.

Attachment is idempotent when the canonical path already contains matching bytes. A digest-path collision with different bytes is a hard error.

Every retained artifact must be referenced by at least one event before sealing. Closure refuses unreferenced artifacts. All ledger-controlled paths must be regular files or directories; symbolic links are rejected throughout the source ledger.

## 8. Crash-resumable closure

`ledger-record close` is idempotent and runs under the writer lock.

Closure procedure:

1. verify the open ledger;
2. append and `fsync` `ledger_closed` when it is not already present;
3. derive `seal.json` from the final event;
4. write the seal to a temporary sibling, flush, `fsync` and atomically replace;
5. derive the manifest from `ledger.jsonl`, `seal.json` and every referenced artifact using sorted relative paths;
6. write the manifest to a temporary sibling, flush, `fsync` and atomically replace;
7. `fsync` the ledger directory where supported.

If a crash leaves a valid `ledger_closed` event without one or both metadata files, rerunning `close` reconstructs only the missing or incomplete metadata and does not append another event.

If an existing seal or manifest disagrees with the final event or retained bytes, closure refuses to overwrite it and reports a verification error.

Allowed close reasons are:

- `complete` for `VERIFIED_COMPLETE`;
- `security_rejected` for `SECURITY_REJECTED`;
- `aborted` for `PARTIAL`, `UNVERIFIED` or `FAILED` when no further recovery will occur.

The close payload's final status must exactly match the referenced final decision.

## 9. Manifest rules

`manifest.json` contains sorted entries for:

- `ledger.jsonl`;
- `seal.json`;
- every referenced artifact.

Each entry records relative path, raw-byte SHA-256 and byte length. Temporary files, `.ledger.lock`, disclosure outputs and the manifest itself are excluded.

Unexpected retained files in the sealed source ledger are verification failures rather than silently ignored additions.

## 10. Expected-root checkpoint

`--expected-root <sha256>` remains available for a direct final-hash comparison.

`--expected-root-file` consumes a canonical JSON checkpoint containing:

```json
{
  "schema_version": "1",
  "ledger_id": "led_example",
  "event_count": 12,
  "final_event_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

All checkpoint fields must match. The checkpoint file is retained outside the ledger directory in the demonstration and tests.

## 11. Invalid-ledger diagnostic export

The base rule remains: normal `ledger-export` fails when the source ledger is invalid.

An explicit `--diagnostic-invalid` mode may create a minimal viewer bundle for explaining synthetic tamper fixtures. It exports only:

- `assurance_level: INVALID`;
- parser and verification error codes;
- safe event positions, sequence numbers and event types when recoverable;
- expected and actual non-sensitive digest metadata;
- the claims-boundary warning.

It must not export invalid payload fields or artifact bytes. The viewer labels the bundle `INVALID_SOURCE_DIAGNOSTIC`, never as verified evidence.

This resolves the earlier contradiction between fail-closed public export and the requirement to demonstrate invalid fixtures.

## 12. Observer-independence wording

`independent_observation` is a protocol trust class, not cryptographic proof that an observer was organisationally or physically independent. Actor identifiers remain labels. The public viewer and README must state this near the assurance explanation.

## 13. Secret filtering limits

Secret-like key rejection is recursive and case-insensitive after Unicode normalisation. Separators such as `_`, `-` and spaces are ignored for denylist comparison.

The implementation may also flag common credential-shaped values, but it must describe this as best-effort detection. No claim is made that arbitrary secrets can always be recognised.

## 14. Final review checklist

Confirmed after amendments:

- no `TBD`, `TODO` or unresolved implementation placeholders;
- no claim of signatures, authenticated identity, trusted time, filesystem immutability or legal non-repudiation;
- no contradiction between invalid-fixture demonstration and fail-closed export;
- open-ledger validation is distinct from sealed-ledger assurance;
- every attempt has one unambiguous decision boundary;
- recoverable outcomes may be deliberately aborted;
- closure can resume safely after process interruption;
- canonicalisation is stable across Python 3.10–3.13 and browser-safe for integers;
- artifacts have one canonical path and atomic persistence rules;
- the verifier remains read-only;
- external checkpoints bind ledger identity, count and final hash;
- implementation remains divided into four independently reviewable milestones;
- public claims remain narrower than the evidence.

The design is approved for implementation planning and execution.