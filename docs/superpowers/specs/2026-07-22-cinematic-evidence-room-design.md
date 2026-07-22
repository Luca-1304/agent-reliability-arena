# Cinematic Evidence Room — Design Specification

## Purpose
Create a premium employer-facing portfolio for Luca Panayiotou that presents AI-agent evaluation, reliability engineering and technical operations through evidence, interactive demonstrations and a credible human–AI operating model.

## Positioning
Primary title: **AI Evaluation · Agent Reliability · Technical Operations**

Primary statement: **Turning ambitious AI claims into systems that can prove what happened.**

The site must communicate unusual upside without claiming prior staff, principal, head-of-AI or foundation-model experience.

## Visual Direction
- Dark graphite base, not pure black.
- Large editorial typography and generous negative space.
- Controlled cyan, ultraviolet and warm-gold accents.
- Fine technical lines, quiet motion and restrained glow.
- No generic developer-template cards, hacker styling, cartoon icons or excessive glassmorphism.
- Responsive from 320 px upward and usable with reduced motion.

## Information Architecture
1. Cinematic opening with three actions: enter system, run demos, open capability CV.
2. Luca × ACE command centre showing Luca, ACE, tools, evidence and Nexus responsibilities.
3. Capability CV with expandable capability cases.
4. Demonstration laboratory with five local demos:
   - Completion Verifier
   - Workflow Architect
   - Agent System Designer
   - Evidence Builder
   - Delivery Simulator
5. Hiring case explaining why Luca is differentiated from a conventional applicant.
6. Controlled evidence presenting 2/8 vs 6/8, 3→0 false completions, 0.25→1.00 precision and 44 vs 8 logical calls.
7. Public examples section containing the only GitHub links on the site.
8. Experience and transferability.
9. Printable executive capability CV drawer.
10. Closing statement: **Bring the ambition. We will define what would make it real.**

## Truth Boundaries
- Deterministic fixtures are software-validation evidence, not representative live-model performance.
- External-model trials, latency, token use, cost and production scaling remain unproven.
- No claim of training a foundation model, changing model weights, proprietary model ownership or autonomous operation without human accountability.
- ACE Master Nexus is a developing human-led framework, not completed autonomous infrastructure.
- GitHub appears only inside the Public Examples section.

## Interaction Model
- Every demo is client-side, deterministic and clearly labelled.
- Demo outputs update in place and explain what the result proves and does not prove.
- Capability cases expand without page navigation.
- Command-centre nodes update a central evidence panel.
- The CV opens in an accessible modal and supports browser print/PDF.

## Accessibility
- Semantic landmarks and headings.
- Keyboard-operable buttons and tabs.
- Visible focus states.
- `aria-live` for demo outputs.
- Reduced-motion support.
- High-contrast text and status labels that do not rely on colour alone.
