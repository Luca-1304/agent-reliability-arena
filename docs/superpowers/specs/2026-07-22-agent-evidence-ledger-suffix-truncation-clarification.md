# Agent Evidence Ledger — Suffix Truncation Clarification

Date: 2026-07-22  
Status: Normative correction discovered during red-first implementation

A chained open stream cannot prove that no valid suffix once existed. Removing an interior event breaks sequence, references or hashes, but removing one or more final events from an unsealed ledger can produce a different internally valid earlier lifecycle state.

Therefore:

- `OPEN_CHAIN_VALID` proves internal consistency only for the supplied open prefix;
- open-ledger suffix truncation is detectable only when compared with an independently retained checkpoint for a later event count/root;
- a sealed ledger detects suffix deletion through the final `ledger_closed` event, seal event count, manifest and optional external checkpoint;
- public claims of deletion detection must say **interior deletion in any supplied chain, and suffix deletion in sealed or externally checkpointed ledgers**;
- deterministic mutation tests for an open ledger remove every non-final event and expect invalidity;
- a separate test removes the final open event, expects a valid earlier prefix with a different root, and documents the limitation;
- sealed-ledger mutation tests remove every event including the final event and expect invalidity.

This correction narrows the public claim to what SHA-256 chaining and the available checkpoints actually prove.