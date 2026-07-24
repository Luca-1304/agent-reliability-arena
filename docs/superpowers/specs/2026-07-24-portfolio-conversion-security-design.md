# Portfolio Conversion and Security Design

Date: 2026-07-24
Branch: `cinematic-evidence-room-v1`
Target: `web/cinematic-plus`

## 1. Purpose

Refine the existing cinematic portfolio into a professional conversion surface that supports three forms of promotion through one identity:

1. employment opportunities;
2. contract or subcontract work;
3. selected technical projects and collaborations.

The site must remain visually distinctive while becoming easier for recruiters, technical managers, founders and operations leaders to understand quickly.

## 2. Positioning

Primary public identity:

**Luca Panayiotou**  
AI Evaluation · Agent Reliability · Applied AI · Technical Operations

Public availability statement:

> Open to AI roles, contract work, subcontract delivery and selected technical projects.

The site must not split employment and project work into separate brands. They are different conversion paths from the same capability profile.

## 3. Contact hierarchy

### Public business contact

- Primary business email: `Lucapanay13@gmail.com`
- LinkedIn: `https://www.linkedin.com/in/luca-panayiotou-64936b256/`

### Secondary contact

- Spare email: `lucapanay@icloud.com`
- The spare address may appear inside the capability CV and contact panel but should not compete visually with the primary business address.

### Protected contact

- Phone number value: stored only in a deployment environment secret and intentionally omitted from repository files.
- The phone number must not be committed to the public repository, embedded in client-side JavaScript, exposed in metadata, included in static HTML, or written into public build artefacts.
- The visible action is **Call Luca**.
- The number is retrieved only after a user-initiated protected request.

## 4. Recruiter skim path

Add a compact section immediately below the hero titled:

> Luca in 90 seconds

It must answer six questions without requiring the visitor to open every section:

1. What does Luca do?
2. Which role families fit best?
3. What evidence already exists?
4. Which tools and methods are relevant?
5. What work is Luca open to?
6. How can an employer contact him now?

### Skim content

- Best-fit roles:
  - AI Evaluation / Quality Analyst
  - Applied AI / Automation Specialist
  - Technical Operations Analyst
  - AI Product / Solutions Associate
  - AI Deployment / Implementation Associate
- Strongest capabilities:
  - agent evaluation;
  - false-completion detection;
  - workflow reliability;
  - technical prototyping;
  - evidence-led problem decomposition.
- Evidence highlights:
  - 2/8 versus 6/8 independently verified outcomes in the deterministic reference fixture;
  - false-completion claims reduced from 3 to 0 in that fixture;
  - Python verification across 3.10–3.13.
- Actions:
  - Email Luca;
  - Call Luca;
  - View LinkedIn;
  - Review capability CV;
  - Continue to full portfolio.

## 5. Technical-language layer

Use a restrained set of recognised technical terms naturally in the skim path, capability CV and metadata:

- Agentic AI
- LLM Evaluation
- AI Quality Assurance
- Human-in-the-Loop
- Workflow Automation
- AI Governance
- Failure-Mode Analysis
- Acceptance Testing
- Technical Prototyping
- Python
- JavaScript
- Git
- Systems Thinking
- Technical Operations

These terms must support real sections or examples. They must not be repeated as keyword stuffing or used to imply experience that is not evidenced.

## 6. Security section

Add an employer-facing section titled:

> Open source. Closed secrets.

The section should make the security design inspectable and technically credible without claiming formal certification or complete security.

### Employer-recognisable controls

- Public source repository for inspectable client-side code;
- deployment environment variables for protected values;
- serverless function boundary for the phone action;
- rate limiting by IP and short time window;
- bot challenge or managed anti-abuse control;
- strict input validation;
- allow-listed request origin;
- Content Security Policy;
- Permissions Policy;
- Referrer Policy;
- `noopener` and `noreferrer` for external links;
- secret scanning in repository workflows;
- dependency and static-code checks where supported;
- no unnecessary advertising or behavioural-tracking scripts;
- local-only demo mutations;
- human approval retained for consequential connected actions.

### Public security status panel

Display only controls that are actually implemented. Proposed labels:

- Source visibility: Public
- Runtime secrets: Environment-managed
- Phone action: Protected endpoint
- Contact abuse controls: Rate-limited
- Third-party tracking: Disabled
- Demo external mutations: None
- Human authority: Required
- Production claims: Explicitly bounded

Do not display a control as active until it has been implemented and verified.

## 7. Protected phone flow

Recommended architecture:

1. Visitor clicks **Call Luca**.
2. A contact panel explains that the number is protected from static scraping.
3. A user-initiated request is sent to a serverless endpoint.
4. The endpoint validates origin, request method, abuse controls and rate limit.
5. The endpoint retrieves the phone number from a deployment secret.
6. The browser receives a short-lived response suitable for launching a `tel:` action.
7. The number is not stored in local storage, analytics events, repository files or static build output.

### Accessibility fallback

The contact panel must provide:

- a clearly labelled button;
- keyboard access;
- focus management;
- useful failure text;
- business email and LinkedIn as fallback actions when the protected call action is unavailable.

### Honest limitation

A determined legitimate visitor may still observe a number once it is delivered to their browser. The design protects against static source scraping and casual automated harvesting; it does not make a contact number cryptographically undiscoverable after authorised reveal.

## 8. Contact and conversion section

Add a dedicated contact section near the end of the employer portfolio.

Headline:

> Discuss a role, project or test problem.

Primary actions:

- Email Luca — business Gmail;
- Call Luca — protected action;
- View LinkedIn;
- Review capability CV.

Secondary text may mention the spare iCloud address inside the expanded contact panel or CV.

Do not use a fake contact form. A form is added only when a real delivery endpoint, spam handling and receipt behaviour are implemented.

## 9. Mobile and tablet design requirements

Responsive support is a release requirement, not a later polish task.

### Target viewport classes

- compact mobile: 320–479 px;
- large mobile: 480–767 px;
- tablet portrait: 768–1023 px;
- tablet landscape and small laptop: 1024–1279 px;
- desktop: 1280 px and above.

### Required responsive behaviour

- no horizontal page overflow;
- minimum practical touch target of approximately 44 × 44 px;
- navigation collapses cleanly and remains keyboard accessible;
- hero typography scales without clipping;
- recruiter skim cards become one column on compact screens and two columns where space permits;
- role selector avoids narrow three-column layouts;
- demo category buttons remain equal-sized;
- demo tabs become horizontally scrollable on smaller screens;
- demo panels do not inherit oversized desktop minimum heights on mobile;
- contact actions stack vertically on compact screens;
- modal and contact panels fit within the viewport and support internal scrolling;
- phone, email and LinkedIn actions remain reachable without hover;
- constellation and technical visuals have accessible text alternatives;
- reduced-motion preferences disable non-essential orbit, pulse and reveal animation;
- focus indicators remain visible on dark and paper backgrounds.

### Device-oriented verification

Test at minimum:

- 320 × 568;
- 375 × 667;
- 390 × 844;
- 430 × 932;
- 768 × 1024;
- 820 × 1180;
- 1024 × 768;
- 1280 × 800;
- 1440 × 900.

## 10. Performance and metadata

- Avoid large third-party JavaScript bundles.
- Keep the static page functional without external model calls.
- Use lazy loading for future non-critical media.
- Add a professional Open Graph preview image later.
- Provide accurate page title, description and structured role language.
- Do not publish the protected phone number in schema.org structured data.

## 11. Testing

### Functional checks

- every recruiter skim action opens the expected destination;
- business Gmail is the primary email action;
- LinkedIn uses the approved profile URL;
- protected call flow handles success, rate limit, bot failure and endpoint failure;
- CV modal opens, closes and prints correctly;
- all five demos switch without resizing category buttons;
- all demos remain local and deterministic;
- Interests-page filters continue to work.

### Security checks

- repository search returns no phone number;
- built static files return no phone number;
- source maps and logs contain no protected contact value;
- endpoint rejects unsupported methods and invalid origins;
- response is not broadly cacheable;
- secrets are read from deployment environment only;
- dependency and secret-scanning results are reviewed before release;
- public security status text matches the controls actually deployed.

### Accessibility checks

- keyboard navigation through header, skim path, role selector, demos, contact actions and modals;
- accessible names for icon-only or compact actions;
- focus restoration after closing panels;
- sufficient contrast;
- reduced-motion behaviour;
- screen-reader-friendly error and success messages.

## 12. Non-goals

This release does not claim:

- formal penetration testing;
- ISO 27001, SOC 2 or Cyber Essentials certification;
- zero vulnerabilities;
- complete prevention of contact scraping after authorised reveal;
- production-scale performance of the AI demonstrations;
- autonomous decision authority for ACE.

## 13. Delivery sequence

1. Add recruiter skim path and technical-language strip.
2. Add contact section with Gmail, LinkedIn, CV and protected Call Luca interface.
3. Add security architecture section and honest control-status panel.
4. Implement responsive layouts across mobile, tablet and desktop.
5. Add the serverless protected-phone endpoint and deployment-secret configuration.
6. Add security headers and anti-abuse controls.
7. Run responsive, accessibility, source-secret and functional checks.
8. Publish only after the status panel matches verified implementation.

## 14. Success criteria

The release succeeds when:

- a recruiter can understand Luca's fit in roughly 90 seconds;
- employment, contract and project enquiries share one clear professional identity;
- the primary business Gmail is immediately usable;
- LinkedIn and CV are obvious;
- the phone number is absent from the public repository and static build;
- the Call Luca action works through a protected runtime boundary;
- security claims are concrete, inspectable and non-inflated;
- the site works cleanly on mobile, tablet and desktop;
- the cinematic identity remains recognisable without blocking usability.
