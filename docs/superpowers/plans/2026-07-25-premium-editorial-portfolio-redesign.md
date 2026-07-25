# Premium Editorial Portfolio Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the existing three-page portfolio into a shorter, premium editorial presentation that demonstrates broad applied-AI engineering capability through fact-checked evidence, explicit evidence tiers and accessible high-contrast design.

**Architecture:** Keep the current static architecture: three HTML pages, one shared stylesheet, one navigation-only script and one downloadable CV. Replace repeated card grids with page-specific editorial components. Expand the contract test first so every public metric, status label, attribution boundary, link and colour token is checked before visual implementation.

**Tech Stack:** HTML5, CSS, minimal vanilla JavaScript, Python `unittest`, standard-library HTML parsing and WCAG contrast calculation.

## Global Constraints

- Work only on branch `portfolio-canonical-review-v1`; do not merge or publish.
- Keep exactly three canonical pages: `index.html`, `evidence.html`, `interests.html`.
- Keep one shared stylesheet: `portfolio.css`.
- Keep one script: `site.js`; it remains navigation-only.
- All visible wording must be direct HTML and usable without JavaScript.
- Preserve `Luca_Panayiotou_CV.pdf` unchanged.
- Preserve the five main-page section IDs: `hero`, `capabilities`, `evidence`, `fit`, `contact`.
- Verified fixture figures are exactly `2/8 → 6/8`, `3 → 0`, `0 → 4`, `0.25 → 1.00`, `8 → 44`, and `+36` logical calls.
- The deterministic-fixture and no-real-provider boundaries must remain adjacent to results.
- Do not present upstream forks or mirrors as Luca-authored software.
- Do not publish Veritas Trace until an inspectable public artefact exists.
- Every project shown in the proof map must include a written evidence-status label.
- Ordinary text must reach WCAG AA contrast of at least 4.5:1; large display text and essential graphical text must reach at least 3:1.
- Text status may not be communicated by colour alone.

---

## File Map

- `tests/test_lean_portfolio.py` — structural, evidence, privacy, attribution, responsive and colour-contract checks.
- `web/cinematic-plus/index.html` — five-section employer overview and flagship evidence.
- `web/cinematic-plus/evidence.html` — guided technical case study and software proof map.
- `web/cinematic-plus/interests.html` — four paired professional-interest rows and compact personal footer.
- `web/cinematic-plus/portfolio.css` — semantic colour tokens, editorial layouts, responsive behaviour and reduced-motion rules.
- `web/cinematic-plus/site.js` — existing progressive-enhancement mobile navigation only.

---

### Task 1: Expand the Portfolio Contract Before Redesigning

**Files:**
- Modify: `tests/test_lean_portfolio.py`

**Interfaces:**
- Consumes: the three canonical pages, `portfolio.css`, `site.js`, and the CV path.
- Produces: a fail-closed contract for the redesigned structure and semantic colour tokens.

- [ ] **Step 1: Replace old layout assertions with premium-editorial structure assertions**

Keep the existing file/link/privacy helpers and add tests that require:

```python
self.assertIn('class="capability-strip"', index_html)
self.assertIn('class="engineering-range"', index_html)
self.assertIn('class="flagship-layout"', index_html)
self.assertEqual(index_html.count('class="role-lane"'), 3)
self.assertNotIn('class="card-grid"', index_html)
```

Require exactly three hero actions and ensure Interests remains navigation-only:

```python
hero = section_html(index_html, "hero")
self.assertEqual(hero.count('class="button'), 3)
self.assertNotIn('href="interests.html"', hero)
```

- [ ] **Step 2: Add exact evidence and cost assertions**

Require the main page to contain:

```python
for text in ["2/8 → 6/8", "3 → 0", "0 → 4", "+36 logical role calls"]:
    self.assertIn(text, index_html)
self.assertNotIn("0.25 → 1.00", index_html)
```

Require the evidence page to contain all fixture values and limitations:

```python
for text in [
    "2/8 → 6/8",
    "3 → 0",
    "0 → 4",
    "0.25 → 1.00",
    "8 → 44",
    "+36 additional calls",
    "No real-provider benchmark has been executed",
    "not production readiness",
]:
    self.assertIn(text, evidence_html)
```

- [ ] **Step 3: Add capability-range and evidence-tier assertions**

Require the direct-HTML range labels:

```python
for label in [
    "Evaluation",
    "Agent architecture",
    "Python systems",
    "Adversarial testing",
    "AI assurance",
    "Release engineering",
    "Technical interfaces",
]:
    self.assertIn(label, index_html)
```

Require the proof map to show only currently defensible public items:

```python
for name in ["Agent Reliability Arena", "Agent Completion Verifier", "ACE Master Nexus"]:
    self.assertIn(name, evidence_html)
self.assertNotIn("Veritas Trace", evidence_html)
```

Require written status labels:

```python
self.assertGreaterEqual(evidence_html.count("Released and reproducible"), 2)
self.assertIn("Architecture / active research", evidence_html)
```

Reject unqualified upstream attribution:

```python
for upstream in ["gpt-oss", "the_well", "Ruflo", "Graphify", "OpenAgentSkill", "VisionClaw"]:
    self.assertNotIn(upstream, index_html + evidence_html + interests_html)
```

- [ ] **Step 4: Add WCAG contrast helpers and token tests**

Add these helpers:

```python
def css_hex_token(css: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{6}})", css)
    if not match:
        raise AssertionError(f"missing CSS token {name}")
    return match.group(1)


def relative_luminance(value: str) -> float:
    channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    high, low = sorted([relative_luminance(first), relative_luminance(second)], reverse=True)
    return (high + 0.05) / (low + 0.05)
```

Test these token pairs:

```python
pairs = [
    ("--bg", "--text-on-dark-primary", 4.5),
    ("--bg", "--text-on-dark-secondary", 4.5),
    ("--paper", "--text-on-light-primary", 4.5),
    ("--paper", "--text-on-light-secondary", 4.5),
    ("--paper", "--accent-readable-on-light", 4.5),
    ("--bg", "--focus-ring", 3.0),
    ("--paper", "--focus-ring", 3.0),
]
for background, foreground, minimum in pairs:
    self.assertGreaterEqual(
        contrast_ratio(css_hex_token(css, background), css_hex_token(css, foreground)),
        minimum,
        f"{foreground} on {background}",
    )
```

- [ ] **Step 5: Run the focused test and confirm the intended red state**

Run:

```bash
python -m unittest tests.test_lean_portfolio -v
```

Expected: failures for missing editorial classes, new evidence wording, proof statuses and colour tokens; existing privacy and link checks remain green.

- [ ] **Step 6: Commit the red contract**

```bash
git add tests/test_lean_portfolio.py
git commit -m "test: define premium portfolio contract"
```

---

### Task 2: Rebuild the Main Page as a Short Editorial Overview

**Files:**
- Modify: `web/cinematic-plus/index.html`
- Test: `tests/test_lean_portfolio.py`

**Interfaces:**
- Consumes: shared header/footer, CV, evidence page and proof URLs.
- Produces: five concise sections with page-specific classes consumed by `portfolio.css`.

- [ ] **Step 1: Replace the hero with the approved three-action composition**

Use this content structure:

```html
<section id="hero" class="hero-section">
  <div class="shell hero-editorial">
    <div class="hero-copy">
      <p class="eyebrow">AI evaluation · applied AI · technical delivery</p>
      <h1>Luca<br><em>Panayiotou</em></h1>
      <p class="lead">I turn unclear AI capability into testable systems, inspectable evidence and human-controlled delivery.</p>
      <div class="actions">
        <a class="button button-primary" href="evidence.html">View evidence</a>
        <a class="button" href="Luca_Panayiotou_CV.pdf" download>Download CV</a>
        <a class="button" href="mailto:Lucapanay13@gmail.com?subject=Role%20or%20project%20discussion">Contact</a>
      </div>
    </div>
    <div class="evidence-path" aria-label="Claim is checked against evidence before a verdict">
      <span>Claim</span><i aria-hidden="true"></i><span>Evidence</span><i aria-hidden="true"></i><strong>Verdict</strong>
      <small>The actor under test does not grade itself.</small>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Replace capability cards with one strip and range band**

Use four `<article class="capability-item">` entries for Evaluate, Build, Test and Clarify. Add:

```html
<div class="engineering-range" aria-label="AI engineering range">
  <strong>AI Engineering Range</strong>
  <span>Evaluation</span><span>Agent architecture</span><span>Python systems</span><span>Adversarial testing</span><span>AI assurance</span><span>Release engineering</span><span>Technical interfaces</span>
</div>
```

Add one role line and one availability note only.

- [ ] **Step 3: Build the asymmetric flagship result**

Use:

```html
<section id="evidence" class="flagship-section">
  <div class="shell flagship-layout">
    <div class="flagship-result"><span>Independently verified outcomes</span><strong>2/8 <i>→</i> 6/8</strong></div>
    <div class="flagship-support">
      <div><strong>3 → 0</strong><span>False-completion claims</span></div>
      <div><strong>0 → 4</strong><span>Recovered scenarios</span></div>
      <p class="tradeoff">Trade-off: <strong>+36 logical role calls</strong></p>
    </div>
    <div class="flagship-copy">
      <p class="eyebrow">Flagship evidence</p>
      <h2>Completion is a judgement against state—not a confident sentence.</h2>
      <p>The Arena compares one General condition with bounded Specialist orchestration under the same task, tools, sandbox, failure schedule and acceptance contract.</p>
      <p class="boundary">Controlled deterministic software evidence. No real-provider benchmark has been executed; this is not production-performance evidence.</p>
      <a class="text-link" href="evidence.html">Inspect the method, trace and cost →</a>
    </div>
  </div>
</section>
```

- [ ] **Step 4: Replace role cards with three ruled lanes**

Each lane uses one heading, one sentence and one proof cue:

```html
<article class="role-lane">
  <span>01</span>
  <h3>AI evaluation and quality</h3>
  <p>Acceptance contracts, trace review, failure-mode discovery and independently verified outcomes.</p>
  <a href="evidence.html#results">Proof: controlled fixture and replay</a>
</article>
```

The other two lanes point to `evidence.html#software` and the public repository.

- [ ] **Step 5: Compress contact to one closing block**

Retain Email, LinkedIn and CV only. Remove repeated role and project copy.

- [ ] **Step 6: Run main-page contract tests**

Run:

```bash
python -m unittest tests.test_lean_portfolio.LeanPortfolioContract.test_index_has_exact_five_sections -v
python -m unittest tests.test_lean_portfolio -v
```

Expected: main-page tests pass; evidence, interests and CSS-token tests remain red.

- [ ] **Step 7: Commit the main-page redesign**

```bash
git add web/cinematic-plus/index.html tests/test_lean_portfolio.py
git commit -m "feat: shorten premium employer overview"
```

---

### Task 3: Rebuild the Evidence Page as a Guided Technical Story

**Files:**
- Modify: `web/cinematic-plus/evidence.html`
- Test: `tests/test_lean_portfolio.py`

**Interfaces:**
- Consumes: locked fixture metrics, public repository URLs and the status-label vocabulary.
- Produces: sections `summary`, `flow`, `trace`, `results`, `software`, `boundaries`, `next`.

- [ ] **Step 1: Build the short opening and contribution split**

Use a compact introduction that states:

- problem: source-reported success can differ from actual state;
- standard: observable state satisfying a fixed contract is authoritative;
- evidence class: deterministic fixture and provider-free integration;
- Luca/ACE contribution boundary.

- [ ] **Step 2: Replace architecture cards with one six-stage flow**

Use an ordered list:

```html
<ol class="system-flow" aria-label="Completion verification flow">
  <li><span>01</span><strong>Task contract</strong><small>Required state and evidence fixed first</small></li>
  <li><span>02</span><strong>Agent action</strong><small>The actor attempts the task</small></li>
  <li><span>03</span><strong>Raw evidence</strong><small>Source events remain preserved</small></li>
  <li><span>04</span><strong>Independent observation</strong><small>Actual state is checked separately</small></li>
  <li><span>05</span><strong>Verifier</strong><small>Observation is resolved against the contract</small></li>
  <li><span>06</span><strong>Canonical verdict</strong><small>VERIFIED_COMPLETE, PARTIAL, UNVERIFIED or FAILED</small></li>
</ol>
```

- [ ] **Step 3: Keep one representative trace**

Use a four-row table: reported claim, observable state, verifier judgement, canonical state. Keep semantic `<th scope="row">` cells so mobile stacking remains meaningful.

- [ ] **Step 4: Present results with visible orchestration cost**

Require:

```html
<strong>2/8 → 6/8</strong>
<strong>3 → 0</strong>
<strong>0 → 4</strong>
<strong>0.25 → 1.00</strong>
<strong>8 → 44</strong>
<p>+36 additional calls</p>
```

Immediately follow with the deterministic-fixture and no-real-provider boundaries.

- [ ] **Step 5: Add the fact-checked software proof map**

Use exactly three public items:

1. Agent Reliability Arena — `Released and reproducible`; link to the repository and employer review.
2. Agent Completion Verifier — `Released and reproducible`; link to its repository.
3. ACE Master Nexus and adaptive-control architecture — `Architecture / active research`; no outcome metrics and no claim of production deployment.

Do not include Veritas Trace or upstream forks.

- [ ] **Step 6: Add two-column proof boundaries and one next step**

The `boundaries` section contains `What this proves` and `What it does not prove`. The `next` section contains the reviewed live-model sample requirement and actions for GitHub source and portfolio return.

- [ ] **Step 7: Run evidence tests**

```bash
python -m unittest tests.test_lean_portfolio -v
```

Expected: evidence and attribution tests pass; Interests and CSS tests remain red.

- [ ] **Step 8: Commit the evidence page**

```bash
git add web/cinematic-plus/evidence.html tests/test_lean_portfolio.py
git commit -m "feat: guide evidence through proof and cost"
```

---

### Task 4: Compress Interests into Four Paired Editorial Rows

**Files:**
- Modify: `web/cinematic-plus/interests.html`
- Test: `tests/test_lean_portfolio.py`

**Interfaces:**
- Consumes: the eight approved interest labels and existing Physics/Forex boundaries.
- Produces: four `.interest-pair` rows and one `.personal-strip`.

- [ ] **Step 1: Replace eight equal cards with four paired rows**

Each row contains two `<article class="interest-column">` elements. Preserve every approved heading exactly once.

- [ ] **Step 2: Limit each interest to one sentence and two-to-four terms**

Use plain inline term lists rather than pill-heavy tag clouds. Preserve the exact Physics and Forex phrases required by the test.

- [ ] **Step 3: Keep research and advice boundaries adjacent**

Mathematics, Physics and Forex each retain one concise boundary line.

- [ ] **Step 4: Replace four personal cards with one strip**

Use:

```html
<div class="personal-strip">
  <span>AI and future technology</span>
  <span>Visual ideas</span>
  <span>Calisthenics and strength</span>
  <span>Football</span>
  <span>Inventions and unusual questions</span>
</div>
```

- [ ] **Step 5: Run Interests tests and commit**

```bash
python -m unittest tests.test_lean_portfolio -v
git add web/cinematic-plus/interests.html tests/test_lean_portfolio.py
git commit -m "feat: compress interests into paired rows"
```

Expected: only CSS/visual contract tests remain red.

---

### Task 5: Implement the Premium Editorial Visual System and Contrast Tokens

**Files:**
- Modify: `web/cinematic-plus/portfolio.css`
- Test: `tests/test_lean_portfolio.py`

**Interfaces:**
- Consumes: all classes introduced by Tasks 2–4.
- Produces: responsive editorial layouts, WCAG-tested tokens and reduced-motion-safe decoration.

- [ ] **Step 1: Replace the root palette with semantic tokens**

Use these tested values:

```css
:root {
  --bg:#080b11;
  --surface:#101722;
  --surface-raised:#151f2d;
  --paper:#f2f5f8;
  --paper-soft:#e7edf2;
  --text-on-dark-primary:#f7f9fc;
  --text-on-dark-secondary:#b8c4d3;
  --text-on-light-primary:#101927;
  --text-on-light-secondary:#4f5f73;
  --accent-bright:#66ddff;
  --accent-readable-on-light:#006879;
  --focus-ring:#2f80ed;
  --violet-detail:#8f7ae6;
  --status-released:#2a9d72;
  --status-prototype:#a86b00;
  --status-research:#6f5bc7;
  --status-upstream:#667085;
  --line-dark:rgba(255,255,255,.14);
  --line-light:rgba(16,25,39,.16);
  --radius:24px;
  --shell:min(1160px,calc(100% - 40px));
}
```

- [ ] **Step 2: Establish editorial typography**

Use a system serif display stack for `h1` and major `h2` elements and the existing system sans stack for body text. Keep body line length near 68 characters and reduce heading maxima from the current oversized values.

- [ ] **Step 3: Style each page section as a different component**

Implement distinct rules for:

- `.hero-editorial` and `.evidence-path`;
- `.capability-strip` and `.engineering-range`;
- `.flagship-layout`, `.flagship-result`, `.flagship-support` and `.tradeoff`;
- `.role-lanes` and `.role-lane`;
- `.system-flow`;
- `.proof-map` and `.status-label`;
- `.interest-pair` and `.personal-strip`;
- `.proof-boundaries`.

Do not reuse a generic card grid for these components.

- [ ] **Step 4: Add progressive responsive layouts**

At `max-width: 900px`, stack hero and flagship layouts. At `max-width: 720px`, turn system flow vertical, stack proof boundaries and interest pairs, and keep the existing no-JavaScript navigation fallback. Keep the mobile trace table stacked.

- [ ] **Step 5: Add restrained CSS-only motion**

Animate only the evidence-path line or marker with a slow transform/opacity cycle. Do not hide content. Disable animation inside `@media(prefers-reduced-motion:reduce)`.

- [ ] **Step 6: Run contract and contrast tests**

```bash
python -m unittest tests.test_lean_portfolio -v
```

Expected: all portfolio tests pass.

- [ ] **Step 7: Commit the visual system**

```bash
git add web/cinematic-plus/portfolio.css tests/test_lean_portfolio.py
git commit -m "style: add accessible editorial portfolio system"
```

---

### Task 6: Run Full Regression and Browser Review

**Files:**
- Modify only when evidence-based fixes are found: `web/cinematic-plus/*.html`, `web/cinematic-plus/portfolio.css`, `tests/test_lean_portfolio.py`

**Interfaces:**
- Consumes: the completed static portfolio.
- Produces: a review-ready branch with automated and visual evidence.

- [ ] **Step 1: Run the complete repository test suite**

```bash
python -m unittest discover -s tests -v
```

Expected: every existing repository test and every portfolio test passes.

- [ ] **Step 2: Validate direct file loads and JavaScript-disabled navigation**

Open all three pages directly. Disable JavaScript and verify that navigation links remain visible and usable at mobile width.

- [ ] **Step 3: Review three target viewports**

Review:

- 1440 × 900
- 1024 × 768
- 390 × 844

Check hierarchy, reading length, text wrapping, table stacking, keyboard focus, hover states, link identification and horizontal overflow.

- [ ] **Step 4: Verify reduced-motion behaviour**

Enable `prefers-reduced-motion: reduce`. Confirm the evidence path remains understandable and no content depends on animation.

- [ ] **Step 5: Measure page-height reduction**

Compare the new main and Interests page scroll heights against the pre-redesign branch commit. The main page should be materially shorter and Interests should no longer read as eight equal blocks. Record the observed values in the final review summary; do not invent a percentage when the browser cannot measure it.

- [ ] **Step 6: Commit only evidence-based review fixes**

```bash
git add web/cinematic-plus tests/test_lean_portfolio.py
git commit -m "fix: resolve premium portfolio review findings"
```

Skip this commit when no defects are found.

- [ ] **Step 7: Compare branch against main**

Confirm the branch is based on current `main`, has no unexpected files and does not include upstream repository content or private data.

- [ ] **Step 8: Present one canonical preview**

Provide the main, evidence and Interests preview URLs on `portfolio-canonical-review-v1`. Do not create aliases, merge or publish.

---

## Plan Self-Review

- **Spec coverage:** Tasks 2–5 cover the main page, evidence story, proof map, Interests compression, colour rules, motion and responsive design. Task 1 enforces evidence, attribution and contrast before implementation. Task 6 covers repository regression and visual review.
- **Fact-check correction:** Veritas Trace is deliberately omitted because no inspectable public artefact was found. Upstream mirrors and forks are omitted rather than used as authorship evidence.
- **No placeholders:** Every task names exact files, classes, copy, test expectations, commands and commit boundaries.
- **Interface consistency:** All new classes referenced by tests are defined in the HTML tasks and styled in Task 5. Evidence section IDs used by role links are defined in Task 3.
- **Scope:** The work remains one static portfolio redesign. No backend, analytics, framework, external font dependency, upstream code import or publication action is introduced.
