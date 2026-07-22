# Agent Evidence Ledger — Approval Record

Date: 2026-07-22

Luca approved the complete Agent Evidence Ledger direction and requested an additional self-review before implementation.

The final review is complete. The approved implementation contract consists of:

1. `2026-07-22-agent-evidence-ledger-design.md`;
2. `2026-07-22-agent-evidence-ledger-final-review.md`;
3. `../plans/2026-07-22-agent-evidence-ledger-implementation.md`;
4. `../plans/2026-07-22-agent-evidence-ledger-retry-budget-amendment.md`.

The later, more specific document takes precedence if wording conflicts.

Confirmed corrections before implementation:

- disclosure output is separate from sealed source ledgers;
- invalid fixtures use an explicit payload-free diagnostic export;
- open and sealed assurance levels are distinct;
- canonicalisation rejects post-NFC duplicate keys, unsafe integers and lone surrogates;
- references are prior-only and acyclic;
- proposal, authorisation, attempt and decision boundaries are mandatory;
- retry count is derived from `contract_declared.max_attempts` and cannot be reset;
- recoverable decisions may close as aborted;
- artifact attachment and closure are atomic and crash-resumable;
- the verifier is read-only;
- actor and observer independence remain protocol labels rather than cryptographic claims;
- public claims stay narrower than the evidence.

Status: approved for implementation and release execution.