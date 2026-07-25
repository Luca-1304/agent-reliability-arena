# Premium Editorial Portfolio Redesign — Design Specification

## Purpose

Refine the lean three-page portfolio so it feels premium, distinctive and employer-ready without becoming decorative, dense or technically fragile.

The redesign must shorten the perceived and actual reading length, vary the visual rhythm between sections, and preserve the static, accessible and evidence-led architecture already established.

## Direction

Use a **70% premium editorial / 30% restrained futuristic** visual language.

The site should feel:

- confident rather than loud;
- technically credible rather than dashboard-like;
- visually varied rather than built from repeated cards;
- concise at first glance, with deeper evidence available by choice;
- recognisably Luca's rather than a generic developer template.

Do not add new topics, claims, projects or decorative technology for its own sake.

## Fact-Checked Evidence Boundary

The locked public fixture contains eight deterministic paired scenarios comparing one General condition with one bounded Specialist orchestration.

The verified public figures are:

- independently verified outcomes: **2/8 → 6/8**;
- false-completion claims: **3 → 0**;
- recovered scenarios: **0 → 4**;
- claim precision: **0.25 → 1.00**;
- logical role calls: **8 → 44**;
- additional logical role calls: **36**.

These values validate deterministic software behaviour, evidence separation, recovery, measurement and replay paths. They are not measurements of a hosted model, local model, production system, workforce, provider cost or latency.

The redesigned site must:

- keep the controlled-fixture boundary adjacent to the metrics;
- show the additional 36 logical calls as the visible trade-off;
- state that no real-provider benchmark has been executed;
- avoid universal model-superiority, production-readiness or safety-certification language;
- distinguish deterministic fixture evidence from future real-model empirical evidence.

## Main Portfolio — `web/cinematic-plus/index.html`

The main page remains five sections, but their composition changes so the page does not feel like a sequence of repeated boxes.

### 1. Hero

Use a two-part editorial composition:

- oversized but controlled name and positioning on the left;
- a refined evidence-path visual on the right built around **Claim → Evidence → Verdict**.

The hero copy should be shorter than the current version and communicate:

- AI evaluation;
- applied AI and workflow design;
- evidence and human control.

Primary actions:

1. View evidence
2. Download CV
3. Contact

Interests remains in the main navigation rather than competing in the hero action group.

The evidence-path visual may use subtle CSS motion, but it must remain understandable when motion is disabled and must not depend on JavaScript.

### 2. Capability Strip

Replace the current four large cards with a compact editorial strip containing four verbs:

- **Evaluate** — test claims against observable evidence;
- **Build** — turn unclear workflows into working prototypes;
- **Test** — define acceptance criteria and expose failure modes;
- **Clarify** — make ownership, limitations and next actions visible.

Below the strip, use one concise role-fit line rather than another grid:

`AI evaluation · applied AI · technical operations · implementation support`

Availability becomes a small status note, not a full card.

### 3. Flagship Evidence

Make this the visual centrepiece of the main page.

Use an asymmetrical editorial layout:

- one dominant result panel: **2/8 → 6/8 independently verified outcomes**;
- two supporting metrics: **3 → 0 false completions** and **0 → 4 recovered scenarios**;
- one small trade-off line: **+36 logical role calls**;
- a short problem statement;
- a short method statement;
- the controlled-fixture boundary;
- one clear action to open the full evidence page.

Do not place claim precision on the main page. Keep it on the evidence page where its definition and context can be inspected.

### 4. Role Lanes

Replace the four-card role grid with three editorial lanes:

1. AI evaluation and quality
2. Applied AI and automation
3. Technical operations

Each lane contains:

- one concise capability statement;
- one inspectable proof cue;
- no more than two lines of supporting copy.

Selected public work should appear as a single linked footer line beneath the lanes rather than a fourth card.

### 5. Contact

Use a compact closing section with:

- one direct heading;
- one sentence;
- Email, LinkedIn and Download CV actions.

Do not repeat role lists, availability details or project summaries here.

## Evidence Page — `web/cinematic-plus/evidence.html`

The evidence page becomes a guided technical story rather than a long sequence of generic sections.

### Opening

Show:

- the failure being addressed;
- the fixed evidence standard;
- a compact Luca/ACE contribution split;
- the deterministic-fixture classification.

### System Flow

Replace repeated architecture cards with one horizontal process on desktop and one vertical process on mobile:

1. Task contract
2. Agent action
3. Raw evidence
4. Independent observation
5. Verifier
6. Canonical verdict

The visual must make clear that the actor under test does not grade itself.

### Representative Trace

Keep one representative trace only.

The trace must distinguish:

- source-reported claim;
- observable state;
- verifier judgement;
- final canonical state.

Desktop uses a compact table. Mobile uses stacked evidence records with no horizontal overflow.

### Results and Cost

Use:

- dominant result: **2/8 → 6/8**;
- supporting metrics: **3 → 0**, **0 → 4**, **0.25 → 1.00**;
- explicit cost: **8 → 44 logical role calls / +36 additional calls**.

The section must explain that improved fixture behaviour came with greater orchestration complexity and logical-call overhead.

### What This Proves / What It Does Not Prove

Replace four limitation cards with two editorial columns.

**What this proves:**

- deterministic evaluation plumbing works;
- evidence and self-report are separated;
- bounded recovery paths are exercised;
- public replay and measurement paths are reproducible.

**What it does not prove:**

- real hosted or local model performance;
- representative live reliability;
- provider cost or latency;
- production readiness;
- universal tool safety;
- universal model superiority.

### Next Empirical Step

End with one concise next step:

Run the fixed acceptance contract against a reviewed, representative live-model sample with dated model identity, exact call and spend ceilings, private evidence retention and independent verification.

Provide one primary GitHub source action and one return-to-portfolio action.

## Interests Page — `web/cinematic-plus/interests.html`

The Interests page keeps all eight approved professional interests but reduces repetition.

### Structure

1. concise editorial introduction;
2. four paired rows rather than eight equal cards;
3. compact personal-interest footer;
4. return-to-portfolio action.

### Paired Rows

- AI Reliability + Adaptive Systems
- Mathematics & Modelling + Physics & Materials
- Markets, Forex & Risk + Human–AI Systems
- Truth & Stewardship + Visual Ideas

Each interest retains its own heading and boundary where needed, but uses:

- one short description;
- two to four key terms maximum;
- no repeated introductory language.

Physics retains:

- Fluid dynamics & Navier–Stokes
- Heat transfer
- Material integrity
- Simulation

Forex retains:

- Technical & price-action analysis
- London & New York sessions
- DXY confirmation
- Invalidation & risk control

The mathematical, physics and trading boundaries remain visible.

Personal interests become one compact horizontal list or short editorial footer, not four full cards.

## Shared Visual System — `web/cinematic-plus/portfolio.css`

Preserve one shared stylesheet and one minimal navigation script.

### Typography

- Stronger editorial hierarchy with more restrained maximum heading sizes.
- Short line lengths for explanatory copy.
- Small uppercase labels used sparingly.
- Larger contrast between headline, evidence figure and supporting explanation.

### Layout Rhythm

Avoid using the same two-column card grid for every section.

Use a deliberate mixture of:

- editorial split layouts;
- horizontal strips;
- asymmetric evidence panels;
- ruled role lanes;
- paired interest rows;
- compact closing blocks.

### Colour and Surfaces

Retain the dark graphite foundation, cyan accent and light editorial sections, but use them more purposefully:

- dark hero;
- light capability strip;
- dark flagship evidence centrepiece;
- restrained light role section;
- dark contact close.

Use violet only as a secondary detail. Avoid repeated gradients on every surface.

### Motion

Motion is optional and CSS-only.

Permitted:

- slow evidence-line movement;
- subtle metric reveal on hover/focus;
- restrained background drift.

Not permitted:

- content hidden until animation runs;
- scroll-jacking;
- cursor-following effects;
- continuous high-motion decoration;
- JavaScript content injection.

Respect `prefers-reduced-motion`.

## Technical Constraints

- Keep exactly three canonical employer-facing pages.
- Keep one shared `portfolio.css` and one minimal `site.js`.
- All visible content remains direct HTML.
- JavaScript remains navigation-only.
- Navigation and content work without JavaScript.
- Preserve the privacy-safe public CV.
- Keep the old reviewed-preview path as a redirect only.
- Do not merge into `main` or publish without Luca's explicit visual approval.

## Testing and Review

Update the contract test to verify:

- the main page still has exactly five sections;
- evidence figures match the locked fixture;
- `+36` call overhead appears on the evidence page;
- real-provider and production boundaries are present;
- Interests remain direct HTML;
- Physics and Forex retain their approved key points;
- no runtime content injection appears;
- privacy-forbidden details remain absent;
- mobile trace presentation does not overflow;
- no-JavaScript navigation remains usable.

Perform visual review at approximately:

- 1440 × 900
- 1024 × 768
- 390 × 844

Check reading length, hierarchy, contrast, keyboard focus, reduced motion and overflow before presenting the preview.

## Acceptance Criteria

The redesign is ready for Luca's review when:

1. The main page is visibly shorter and no longer reads as repeated cards.
2. The flagship evidence is the strongest visual section.
3. Every public metric is traceable to the locked fixture.
4. Logical-call overhead is visible beside the improvement.
5. The evidence page clearly separates what is proven from what remains unproven.
6. The Interests page retains all approved substance with less repetition.
7. All automated tests pass.
8. Desktop, tablet, mobile and no-JavaScript reviews are clean.
9. Nothing has been merged or published.
