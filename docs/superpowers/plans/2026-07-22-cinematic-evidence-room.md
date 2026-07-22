# Cinematic Evidence Room Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a premium, evidence-led portfolio that demonstrates Luca × ACE capabilities through interactive systems rather than generic claims.

**Architecture:** A static three-file site at `web/cinematic/` with semantic HTML, a focused design-system stylesheet and vanilla JavaScript modules grouped by interaction responsibility. The branch remains isolated until visual review; GitHub links exist only in the Public Examples section.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript, GitHub static hosting, no external runtime dependencies.

## Global Constraints

- Use the exact positioning: `AI Evaluation · Agent Reliability · Technical Operations`.
- Use the primary statement: `Turning ambitious AI claims into systems that can prove what happened.`
- Keep all empirical claims within existing repository evidence.
- Label every demo as local and deterministic.
- GitHub links may appear only in the Public Examples section.
- Support keyboard operation, visible focus and reduced motion.
- Do not overwrite the existing main-branch portfolio during preview development.

---

### Task 1: Semantic page structure

**Files:**
- Create: `web/cinematic/index.html`

**Interfaces:**
- Consumes: approved design specification.
- Produces: stable section IDs and DOM hooks used by `styles.css` and `app.js`.

- [ ] Create the opening, command centre, capability CV, lab, hiring case, evidence, examples, experience, CV modal and closing sections.
- [ ] Ensure only the Public Examples section contains GitHub URLs.
- [ ] Add accessible tab, disclosure and modal attributes.
- [ ] Validate that all IDs referenced by buttons exist once.
- [ ] Commit the semantic shell.

### Task 2: Premium visual system

**Files:**
- Create: `web/cinematic/styles.css`

**Interfaces:**
- Consumes: HTML classes and data-state attributes from Task 1.
- Produces: responsive layout and visible interaction states.

- [ ] Define graphite, cyan, ultraviolet and gold design tokens.
- [ ] Build editorial typography, spacing, navigation and section rhythm.
- [ ] Style the command centre as a responsive system console.
- [ ] Style capability dossiers, demo workbench, evidence comparison and CV modal.
- [ ] Add restrained animation and reduced-motion overrides.
- [ ] Verify at 1440 px, 1024 px, 768 px and 375 px layout breakpoints.
- [ ] Commit the visual system.

### Task 3: Command centre and capability interactions

**Files:**
- Create: `web/cinematic/app.js`

**Interfaces:**
- Consumes: `[data-command-node]`, `[data-capability]`, `#command-output` and capability panel hooks.
- Produces: selected-node state, expanded capability cases and accessible output updates.

- [ ] Implement command-node selection with role, responsibility, boundary and artefact output.
- [ ] Implement one-open-at-a-time capability disclosures.
- [ ] Add navigation state, mobile menu and scroll reveals.
- [ ] Verify keyboard and pointer interactions.
- [ ] Commit core interactions.

### Task 4: Demonstration laboratory

**Files:**
- Modify: `web/cinematic/index.html`
- Modify: `web/cinematic/app.js`

**Interfaces:**
- Produces five local deterministic demos with labelled outputs.

- [ ] Implement Completion Verifier with verified, partial, unverified and failed states.
- [ ] Implement Workflow Architect that maps objective, handoffs, approvals, evidence and recovery.
- [ ] Implement Agent System Designer that assigns bounded roles and permissions.
- [ ] Implement Evidence Builder that converts a claim into requirements, observations and invalidation tests.
- [ ] Implement Delivery Simulator for 48-hour, two-week and six-week deliverables.
- [ ] Add `aria-live` output regions and honest limitation notices.
- [ ] Commit the laboratory.

### Task 5: Hiring case, evidence and executive CV

**Files:**
- Modify: `web/cinematic/index.html`
- Modify: `web/cinematic/styles.css`
- Modify: `web/cinematic/app.js`

**Interfaces:**
- Produces employer-facing differentiation, evidence boundaries and printable CV.

- [ ] Present Luca's operational judgement, problem finding, evidence discipline and AI-assisted delivery as the hiring thesis.
- [ ] Show controlled metrics with complexity and unproven areas beside them.
- [ ] Build a printable executive CV separating Luca and ACE contributions.
- [ ] Implement modal open, close, Escape and print actions.
- [ ] Verify no unsupported seniority or model-training claims appear.
- [ ] Commit employer-facing content.

### Task 6: Final verification and preview

**Files:**
- Verify: `web/cinematic/index.html`
- Verify: `web/cinematic/styles.css`
- Verify: `web/cinematic/app.js`

**Interfaces:**
- Produces: reviewable branch preview URL.

- [ ] Confirm every HTML-referenced CSS and JavaScript file exists on the branch.
- [ ] Confirm GitHub URLs occur only within `#examples`.
- [ ] Confirm all five demo buttons have matching panels and handlers.
- [ ] Confirm responsive and print rules are present.
- [ ] Fetch all files from GitHub after commit and inspect the final source.
- [ ] Provide the immutable commit preview and branch preview URLs.
