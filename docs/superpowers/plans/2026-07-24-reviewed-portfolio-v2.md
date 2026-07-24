# Reviewed Portfolio V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a second real portfolio preview that applies the review: static flagship content, explicit Luca/ACE ownership, reduced card density, employer-use scenarios, demos before role coverage, a genuine downloadable CV, and email-first conversion.

**Architecture:** Create an isolated `reviewed-preview.html` page using the existing secure visual foundation while placing all flagship case-study markup directly in the document. Add focused CSS and JavaScript files for progressive disclosure, responsive behaviour, protected-call preview handling, and client-side delivery of a verified PDF CV.

**Tech Stack:** Semantic HTML, CSS, vanilla JavaScript, ReportLab-generated PDF embedded as a downloadable browser asset, GitHub branch preview.

## Global Constraints

- Preserve honest deterministic-fixture boundaries and existing verified metrics only.
- Present Luca as the accountable human owner and ACE as an AI copilot, not an autonomous legal actor.
- Keep the phone number out of public HTML, JavaScript, metadata, source history and static page content.
- Make business Gmail the dominant contact action; secure calling remains secondary until deployed.
- Support mobile, tablet and desktop without horizontal page overflow.
- Preserve reduced-motion support and keyboard-accessible controls.
- Do not fabricate testimonials, production deployments, certifications or external reviews.

---

### Task 1: Static reviewed preview

**Files:**
- Create: `web/cinematic-plus/reviewed-preview.html`

- [ ] Build the full page in this order: hero, 90-second skim, static flagship case study, contribution split, where-it-matters, why Luca, demos, role coverage, public artefacts, security, contact challenge.
- [ ] Link the existing secure visual foundation plus V2 CSS and JavaScript directly in the document head.
- [ ] Make all core flagship content present in initial HTML without JavaScript injection.
- [ ] Commit the page.

### Task 2: Visual refinement and responsive behaviour

**Files:**
- Create: `web/cinematic-plus/reviewed-preview.css`

- [ ] Reduce bordered-card density by using open typography, horizontal timelines and full-width diagrams.
- [ ] Style the Luca/ACE contribution split and employer-use scenarios.
- [ ] Keep demo tabs equal-sized and horizontally scrollable on compact screens.
- [ ] Add tablet-specific layout rules and reduced-motion behaviour.
- [ ] Commit the stylesheet.

### Task 3: Interaction layer

**Files:**
- Create: `web/cinematic-plus/reviewed-preview.js`

- [ ] Implement menu, demo switching, technical-layer accordion, protected-call preview modal and keyboard Escape handling.
- [ ] Keep only one technical layer open on compact screens while allowing deliberate desktop exploration.
- [ ] Ensure business-email actions remain primary when the call endpoint is unavailable.
- [ ] Commit the script.

### Task 4: Downloadable capability CV

**Files:**
- Create: `web/cinematic-plus/cv-download.js`

- [ ] Generate and visually verify `Luca_Panayiotou_CV.pdf` using ReportLab.
- [ ] Embed the verified PDF bytes as a base64 browser download asset.
- [ ] Connect all `data-download-cv` controls to a direct PDF download named `Luca_Panayiotou_CV.pdf`.
- [ ] Commit the download asset.

### Task 5: Verification

- [ ] Confirm static source contains the flagship, contribution split, employer-use section, demos-before-roles order and security boundaries.
- [ ] Confirm no phone number is present in the new public files.
- [ ] Confirm responsive CSS includes compact mobile, tablet and desktop rules.
- [ ] Confirm reduced-motion handling and keyboard controls exist.
- [ ] Publish only as a branch preview; do not merge to `main`.
