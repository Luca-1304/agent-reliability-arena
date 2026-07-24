# Portfolio Conversion and Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real 90-second recruiter skim path, employer-recognisable security architecture, protected-call interaction shell, contact conversion and responsive mobile/tablet behaviour to the existing cinematic portfolio.

**Architecture:** Keep `web/cinematic-plus` intact and add one focused stylesheet and one script. The script injects semantic recruiter, security and contact sections into the existing page; the stylesheet owns responsive layout and interaction states. The phone number is never present in repository files; the client calls a configurable same-origin endpoint and shows honest preview fallback when no endpoint is deployed.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript and an optional serverless JavaScript endpoint contract.

## Global Constraints

- Primary business email: `Lucapanay13@gmail.com`.
- Spare email: `lucapanay@icloud.com`.
- LinkedIn: `https://www.linkedin.com/in/luca-panayiotou-64936b256/`.
- Never commit, embed or log the phone number.
- Never claim deployment-dependent controls are active until verified.
- Keep demos local and deterministic.
- Preserve the cinematic visual language.
- Support 320 px mobile through desktop without horizontal overflow.
- Keep primary touch actions approximately 44 × 44 px or larger.
- Respect `prefers-reduced-motion`.
- Add no analytics, trackers or large dependencies.

---

### Task 1: Conversion layer structure

**Files:**
- Create: `web/cinematic-plus/conversion.css`
- Create: `web/cinematic-plus/conversion.js`
- Modify: `web/cinematic-plus/refine.css`
- Modify: `web/cinematic-plus/app.js`

**Interfaces:**
- Consumes: `.hero`, `.closing`, `.footer-inner`, `[data-open-cv]` and shared design tokens.
- Produces: `installConversionLayer(): void`, `openProtectedCallPanel(): void`, and sections `skim`, `security`, `contact`.

- [ ] Create the conversion stylesheet with recruiter, security, contact and modal component classes.
- [ ] Add responsive rules for compact mobile, large mobile, tablet and small laptop.
- [ ] Add focus, touch-target and reduced-motion rules.
- [ ] Import `conversion.css` from `refine.css`.
- [ ] Create idempotent `conversion.js` without third-party dependencies.
- [ ] Load and call `installConversionLayer()` from `app.js`.
- [ ] Fetch changed files and verify the import and bootstrap.
- [ ] Commit `feat: add recruiter conversion layer`.

### Task 2: 90-second recruiter skim path

**Files:**
- Modify: `web/cinematic-plus/conversion.js`
- Modify: `web/cinematic-plus/conversion.css`

**Interfaces:**
- Produces: `createSkimSection(): HTMLElement`, inserted immediately after `.hero`.

- [ ] Build `Luca in 90 seconds` with roles, capabilities, evidence, technical stack and availability.
- [ ] Use supported terms naturally: Agentic AI, LLM Evaluation, AI Quality Assurance, Human-in-the-Loop, Workflow Automation, AI Governance, Failure-Mode Analysis, Acceptance Testing, Technical Prototyping, Python, JavaScript, Git, Systems Thinking and Technical Operations.
- [ ] Add actions for Gmail, protected call, LinkedIn, capability CV and the full portfolio.
- [ ] Verify external links use `noopener noreferrer` and email actions use Gmail.
- [ ] Commit `feat: add 90-second recruiter skim path`.

### Task 3: Employer-facing security section

**Files:**
- Modify: `web/cinematic-plus/conversion.js`
- Modify: `web/cinematic-plus/conversion.css`
- Create: `web/cinematic-plus/_headers`
- Create: `web/cinematic-plus/security-status.json`

**Interfaces:**
- Produces: `createSecuritySection(): HTMLElement`, inserted before `.closing`.

- [ ] Build `Open source. Closed secrets.` with Public Interface → Validated Request → Protected Endpoint → Private Contact Action.
- [ ] Mark actual controls active: public source, no third-party tracking, local-only demos, isolated external links and bounded claims.
- [ ] Mark environment secret, endpoint, rate limiting, origin allow-list and bot control as `Production deployment required` in preview.
- [ ] Add a deployable `_headers` template with CSP, Referrer-Policy, Permissions-Policy, X-Content-Type-Options and frame protection.
- [ ] Add `security-status.json` with `active`, `designed` and `not_claimed` states.
- [ ] Verify no protected value appears in either file.
- [ ] Commit `feat: add inspectable security architecture`.

### Task 4: Protected call interaction shell

**Files:**
- Modify: `web/cinematic-plus/conversion.js`
- Modify: `web/cinematic-plus/conversion.css`
- Create: `web/cinematic-plus/api/contact/call.example.js`

**Interfaces:**
- Consumes: configurable `data-call-endpoint`, default `/api/contact/call`.
- Produces: `requestProtectedPhone(endpoint: string): Promise<{tel: string}>` and an accessible modal.

- [ ] Add keyboard-accessible call modal with focus management and Escape close.
- [ ] Explain static-scraping protection clearly.
- [ ] POST using same-origin credentials and validate the JSON response.
- [ ] Accept only a returned value beginning with `tel:`.
- [ ] On preview failure, show Gmail and LinkedIn fallback without fake success.
- [ ] Add example serverless handler reading `LUCA_PHONE_E164`, checking method/origin and never logging the value.
- [ ] Verify the actual phone number is absent.
- [ ] Commit `feat: add protected call interaction shell`.

### Task 5: Contact conversion and footer integration

**Files:**
- Modify: `web/cinematic-plus/conversion.js`
- Modify: `web/cinematic-plus/conversion.css`

**Interfaces:**
- Produces: `createContactSection(): HTMLElement` and footer conversion links.

- [ ] Add `Discuss a role, project or test problem.` before the closing section.
- [ ] Make Gmail primary and iCloud a labelled spare address.
- [ ] Add protected Call Luca, LinkedIn and CV actions.
- [ ] Add availability across employment, contract, subcontract and selected projects.
- [ ] Extend the footer without duplicating LinkedIn.
- [ ] Commit `feat: add role and project contact conversion`.

### Task 6: Responsive and accessibility verification

**Files:**
- Modify: `web/cinematic-plus/conversion.css`
- Modify: `web/cinematic-plus/layout-fixes.css`

- [ ] Collapse skim grids to one column on compact mobile and two where tablet width permits.
- [ ] Convert the security flow to a vertical sequence on narrow screens.
- [ ] Stack contact actions and keep them accessible without hover.
- [ ] Fit the call modal inside `100dvh` with internal scrolling.
- [ ] Preserve equal demo tabs and remove oversized demo minimum heights below 820 px.
- [ ] Add reduced-motion handling.
- [ ] Fetch final files, verify links and search additions for forbidden phone digits.
- [ ] Commit `fix: harden responsive portfolio conversion`.

### Task 7: Branch completion review

- [ ] Fetch final conversion assets, app bootstrap and security files.
- [ ] Verify ids, business email, LinkedIn, endpoint contract and status labels.
- [ ] Confirm no phone value is stored in new repository files.
- [ ] Confirm preview is not described as having an active protected endpoint.
- [ ] Provide mutable and immutable branch previews.
