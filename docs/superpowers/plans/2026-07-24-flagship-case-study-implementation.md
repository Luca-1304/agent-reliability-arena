# Flagship Case Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cinematic, evidence-backed Agent Completion Verifier case study and the missing proof-and-personality sections to the secure portfolio preview.

**Architecture:** Keep the existing secure preview intact. Load a focused `flagship.js` enhancement from `secure-preview.js`; the enhancement injects semantic case-study, Why Luca, role-coverage, public-work and contact-challenge sections. A separate `flagship.css` owns all cinematic, technical, responsive and reduced-motion styling.

**Tech Stack:** Semantic HTML generated from local JavaScript, CSS/SVG-style visuals, no frameworks, no external model calls, GitHub static preview.

## Global Constraints

- Public demo remains deterministic and makes no external mutations.
- Only the existing verified fixture metrics may be displayed.
- No fabricated testimonial, screenshot, production deployment or novelty claim.
- Phone value remains absent from source and static artefacts.
- 320 px through desktop layouts must avoid horizontal page overflow.
- Touch targets remain approximately 44 × 44 px or larger.
- `prefers-reduced-motion` disables non-essential animation.

---

### Task 1: Load the flagship enhancement

**Files:**
- Modify: `web/cinematic-plus/secure-preview.js`
- Create: `web/cinematic-plus/flagship.js`

**Interfaces:**
- Consumes: existing `#skim`, `#work`, `#security`, `#contact`, `[data-nav]` elements.
- Produces: `#flagship`, `#why-luca`, `#role-coverage`, `#public-work`, accessible technical-layer controls.

- [ ] Append a guarded loader for `flagship.js` to `secure-preview.js`.
- [ ] Inject the flagship and supporting sections at deterministic locations.
- [ ] Implement one-open-at-a-time technical layers on compact viewports.
- [ ] Add URL hash opening for `#flagship` and layer targets.
- [ ] Verify all inserted links and buttons have real destinations or honest preview behaviour.
- [ ] Commit.

### Task 2: Cinematic and responsive styling

**Files:**
- Create: `web/cinematic-plus/flagship.css`

**Interfaces:**
- Consumes: class names emitted by `flagship.js`.
- Produces: cinematic surface, architecture diagram, evidence trace, metric comparison, code excerpt, responsive layouts and reduced-motion handling.

- [ ] Add full-width cinematic stage and evidence-gate visual.
- [ ] Add technical accordion, architecture, trace, metrics, limitations and code styling.
- [ ] Add Why Luca, role coverage and public-work presentation.
- [ ] Implement mobile, tablet and desktop breakpoints.
- [ ] Add visible focus states and reduced-motion override.
- [ ] Commit.

### Task 3: Verification

**Files:**
- Verify: `web/cinematic-plus/secure-preview.js`
- Verify: `web/cinematic-plus/flagship.js`
- Verify: `web/cinematic-plus/flagship.css`

- [ ] Confirm source contains only the approved metrics: `2/8 → 6/8`, `3 → 0`, `0.25 → 1.00`, `4`, `3.10–3.13`.
- [ ] Confirm no phone number is present.
- [ ] Confirm the page remains local-only and no new external mutation code exists.
- [ ] Confirm compact layouts use single-column flow and no fixed cinematic height.
- [ ] Confirm reduced-motion rules exist.
- [ ] Keep the branch isolated for review rather than merging to `main`.
