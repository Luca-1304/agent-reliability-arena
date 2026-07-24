# Flagship Case Study Design

Date: 2026-07-24
Branch: `cinematic-evidence-room-v1`
Target: `web/cinematic-plus/secure-preview.html`

## 1. Purpose

Add the missing proof-and-personality layer to the portfolio by turning the Agent Completion Verifier into the memorable centrepiece of the site.

The section must feel cinematic at first glance, then become progressively more technical as the visitor explores it. Every visual claim must resolve into architecture, evidence, traces, limitations or inspectable code.

## 2. Primary experience

The flagship section appears directly after **Luca in 90 seconds** and before the wider demo gallery.

Public story:

> Most AI systems can say they finished. Far fewer can prove that the required external state actually exists.

Primary case-study title:

> Agent Completion Verifier

Primary promise:

> A model-agnostic evaluator that separates an agent's completion claim from independently observable evidence.

## 3. Cinematic surface

The first screen of the case study uses a dark full-width stage with a restrained moving trace visual.

Visual sequence:

1. an agent emits **TASK COMPLETE**;
2. the completion claim travels through an evidence gate;
3. required fields illuminate or remain missing;
4. a later event can invalidate an earlier success;
5. the canonical verdict resolves to `VERIFIED_COMPLETE`, `PARTIAL`, `UNVERIFIED` or `FAILED`.

The animation must be CSS/SVG-based, lightweight, keyboard-independent and disabled when `prefers-reduced-motion` is active.

The cinematic surface includes:

- a large statement;
- the live verdict visual;
- three evidence metrics;
- a **See the technical evidence** action;
- an **Open interactive verifier** action;
- an honest note that the public demonstration uses controlled deterministic fixtures.

## 4. Technical underneath

The case study expands into six inspectable layers.

### Layer 1: The operational problem

Explain the failure mode:

- an agent can report success while required evidence is absent;
- a successful tool receipt may not prove the full requested outcome;
- partial evidence can be mistaken for completion;
- a later rollback or invalidating event can make an earlier success stale.

### Layer 2: The original design insight

State the core insight clearly:

> Completion must be judged against a fixed acceptance contract and independently observable state, not the system's own confidence or wording.

Do not overclaim novelty beyond the public implementation. Present this as Luca's applied design principle for the system.

### Layer 3: Architecture

Show a visual architecture with these components:

1. Task contract
2. Agent or workflow under test
3. Raw execution trace
4. Evidence normaliser
5. Independent verifier
6. Canonical verdict
7. Replay and limitation record

Each component opens a short technical explanation covering inputs, outputs and boundaries.

### Layer 4: Evidence trace

Display a representative trace with rows for:

- completion claim;
- latest required action;
- message or artefact identifier;
- recipient or destination evidence;
- later rollback or invalidating event;
- resulting verdict.

The trace must visually distinguish:

- observed;
- missing;
- failed;
- stale or invalidated;
- canonical judgement.

### Layer 5: Controlled results

Use only the verified public fixture results already present in the portfolio:

- independently verified outcomes: `2/8 → 6/8`;
- false-completion claims: `3 → 0`;
- claim precision: `0.25 → 1.00`;
- recovered scenarios: `4`;
- Python verification range: `3.10–3.13`.

Every metric includes a tooltip or visible note explaining the denominator, fixture boundary and deterministic nature of the comparison.

### Layer 6: Limitations and next test

Include a visible limitations panel:

- deterministic fixture, not production traffic;
- no claim of universal model performance;
- no live external mutations in the public demonstration;
- organisational impact requires representative tasks and real operational data;
- additional specialist roles increase logical role-call complexity.

End with the next empirical step:

> Run the same acceptance contract against representative live-model traces and organisation-specific postconditions.

## 5. Why Luca

Add a short section immediately after the flagship case study.

Recommended copy direction:

> I did not enter AI through a conventional software-engineering ladder. I came through insurance operations, safety-critical work, customer consequence and practical delivery. That background makes me naturally suspicious of systems that look complete but fail in reality.

Support this with four concise links between background and current capability:

- insurance operations → information accuracy and customer consequence;
- fire safety → procedure, escalation and evidence;
- practical delivery → changing conditions and accountability;
- AI-assisted system building → rapid experimentation with explicit boundaries.

The section must avoid presenting unrelated past roles as equivalent to senior AI engineering experience.

## 6. Visible artefacts

The flagship section should expose real objects rather than rely only on prose:

- architecture diagram;
- evidence-state visual;
- representative trace table;
- before-and-after metric comparison;
- short code excerpt showing verdict-state handling;
- link to the public repository;
- downloadable case-study report when a genuine report file exists.

No fabricated screenshot, testimonial, external review or production deployment claim may be used.

## 7. Revised page order

The secure preview becomes:

1. Hero
2. Luca in 90 seconds
3. Flagship case study — Agent Completion Verifier
4. Why Luca
5. Interactive demos
6. Role coverage
7. Public work and GitHub
8. Security
9. Interests and ACE
10. Contact challenge

The security section remains technically credible but becomes visually shorter than the flagship case study.

## 8. Final contact challenge

Replace the generic closing emphasis with:

> Give me a problem your team has not been able to make measurable.

Supporting line:

> I will help separate the real objective, the evidence standard, the failure surface and the smallest useful test.

Keep these conversion routes:

- Discuss a role or project;
- Email Luca;
- Call Luca securely;
- View LinkedIn;
- Review capability CV.

## 9. Interaction model

The flagship section uses progressive disclosure rather than a separate page by default.

- The cinematic summary is always visible.
- Technical layers expand through accessible controls.
- Only one technical layer opens at a time on compact screens.
- Desktop may show architecture and trace side by side.
- All important information remains available without hover.
- URL hash targets may open the case study or a specific technical layer.

## 10. Mobile and tablet behaviour

The case study must be intentionally responsive.

- 320–479 px: single-column story, horizontally scrollable metric strip, stacked trace rows, no fixed-height cinematic stage.
- 480–767 px: single-column story with two-column metric cards where space permits.
- 768–1023 px: architecture and explanation may use two columns; trace remains full width.
- 1024 px and above: cinematic stage and verdict visual may sit side by side; technical architecture and trace may form a split layout.
- Touch targets remain approximately 44 × 44 px or larger.
- No horizontal page overflow.
- Text and diagrams remain legible without pinch zoom.
- Reduced-motion mode removes non-essential motion while preserving state changes.

## 11. Accessibility

- Semantic headings preserve a logical hierarchy.
- Interactive layers use buttons with `aria-expanded` and controlled regions.
- Trace states are communicated with text and symbols, not colour alone.
- Diagrams receive concise accessible descriptions.
- Keyboard users can open, close and move through technical layers.
- Focus remains visible on dark and light surfaces.

## 12. Performance

- Use HTML, CSS, inline SVG and existing local JavaScript only.
- Do not add a heavy animation or charting library.
- Keep the page functional without external model calls.
- Avoid autoplay video.
- Defer non-critical visual effects until after first content paint.

## 13. Testing

Functional checks:

- flagship actions open the correct technical layer or demo;
- every metric matches the public controlled fixture;
- architecture controls expose the correct descriptions;
- trace state labels remain accurate;
- limitations remain visible and cannot be hidden behind a decorative interaction;
- contact challenge actions work;
- no private phone value enters HTML, JavaScript, metadata or repository history.

Responsive checks:

- 320 × 568;
- 375 × 667;
- 390 × 844;
- 430 × 932;
- 768 × 1024;
- 820 × 1180;
- 1024 × 768;
- 1280 × 800;
- 1440 × 900.

## 14. Success criteria

A recruiter or technical manager should leave the section able to answer:

1. What problem did Luca identify?
2. What did he build?
3. How does it work?
4. What evidence supports it?
5. What are the limitations?
6. Why does Luca's background make this kind of problem a credible fit?
7. What should they contact him about?
