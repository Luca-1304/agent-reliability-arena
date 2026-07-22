const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

const header = $('.site-header');
const menuButton = $('.menu-toggle');
const primaryNav = $('#primary-nav');
const cursorGlow = $('.cursor-glow');

addEventListener('scroll', () => header?.classList.toggle('is-scrolled', scrollY > 18), { passive: true });
addEventListener('pointermove', event => {
  if (!cursorGlow) return;
  cursorGlow.style.left = `${event.clientX}px`;
  cursorGlow.style.top = `${event.clientY}px`;
}, { passive: true });

menuButton?.addEventListener('click', () => {
  const open = primaryNav.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(open));
});
$$('#primary-nav a, #primary-nav button').forEach(item => item.addEventListener('click', () => {
  primaryNav.classList.remove('open');
  menuButton?.setAttribute('aria-expanded', 'false');
}));

const revealObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    }), { threshold: .12 })
  : null;
$$('.reveal').forEach(element => revealObserver ? revealObserver.observe(element) : element.classList.add('is-visible'));

const stageDetails = {
  human: 'Luca owns the objective, acceptance standard, risk boundary and final judgement. This prevents the system from optimising for a polished answer instead of the real outcome.',
  ai: 'ACE uses advanced AI capabilities for breadth, comparison, synthesis, code assistance, documentation and rapid iteration. It accelerates the work without becoming the accountable party.',
  tools: 'Tools turn reasoning into observable artefacts: repository changes, tests, documents, searches, structured records and workflow actions. Each tool is limited by its real contract.',
  proof: 'The verifier separates a success claim from independent evidence. Completion is accepted only when every required action and evidence field is satisfied.'
};
$$('[data-stage]').forEach(button => button.addEventListener('click', () => {
  $$('[data-stage]').forEach(node => node.classList.remove('active'));
  button.classList.add('active');
  $('#stage-detail').textContent = stageDetails[button.dataset.stage];
}));

const capabilityDetails = {
  agent: {
    title: 'Evaluate AI agents',
    text: 'Define acceptance contracts, failure cases, evidence fields and recovery rules; build a deterministic evaluation harness; preserve raw traces separately from derived judgements; and produce a reviewable result bundle.'
  },
  workflow: {
    title: 'Design safer AI workflows',
    text: 'Map the real process, allocate human and AI responsibilities, identify irreversible or high-blast-radius actions, create approval gates and test the workflow in shadow mode before expanding autonomy.'
  },
  research: {
    title: 'Decompose difficult research',
    text: 'Reduce a broad question into decision-relevant sub-claims, identify the smallest evidence that would change each claim, compare competing explanations and deliver a calibrated recommendation with visible weak points.'
  },
  prototype: {
    title: 'Build credible prototypes',
    text: 'Translate an idea into a working Python harness, interactive web demonstration, test suite, architecture map or technical specification—while clearly separating the prototype from production claims.'
  },
  operations: {
    title: 'Improve operations',
    text: 'Find information loss, repeated manual work, unclear ownership and broken handoffs; redesign the flow around structured inputs, explicit outcomes and measurable checkpoints rather than adding AI for appearance.'
  },
  governance: {
    title: 'Make AI decisions reviewable',
    text: 'Record sources, assumptions, decisions, actions, outcomes, errors and corrections so that another person can understand what happened, why it happened and what still remains uncertain.'
  }
};
$$('[data-capability]').forEach(button => button.addEventListener('click', () => {
  $$('[data-capability]').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  const detail = capabilityDetails[button.dataset.capability];
  $('#capability-detail').innerHTML = `<strong>${detail.title}</strong><p>${detail.text}</p>`;
}));

const labPresets = {
  completion: 'An AI agent says a task is finished, but we cannot prove the external action happened.',
  operations: 'A business process is slow, information is lost between teams and nobody owns the end-to-end outcome.',
  research: 'A technical research question has too many connected possibilities and no clear path to a decision.',
  adoption: 'We want to use AI in the company but do not know where it creates real value without adding unnecessary risk.'
};
const labOutputs = {
  completion: [
    ['Objective', 'Prove the required external state—not the agent’s confidence.', 'List every action that must be true for the task to count as complete.'],
    ['Acceptance', 'Create an independent completion contract.', 'Define required actions, latest-event rules, evidence fields, retries, rollback and partial outcomes.'],
    ['Evidence', 'Use observable state or trusted event sources.', 'Keep source reports separate from canonical evidence and reject missing or empty proof fields.'],
    ['Design', 'Insert a model-agnostic verification step.', 'The agent may report; the verifier decides whether the claim is verified, partial, unverified or failed.'],
    ['Verification', 'Inject controlled failure cases.', 'Test false success, partial execution, recovery, later regression, rollback and silent verified completion.'],
    ['Delivery', 'Ship a replayable evaluation bundle.', 'Provide cases, raw traces, derived evaluations, metrics, integrity manifest and a concise review view.']
  ],
  operations: [
    ['Objective', 'Reduce cycle time and information loss.', 'Name the process owner and define the measurable start and end states.'],
    ['Acceptance', 'Define what a healthy handoff looks like.', 'Specify required fields, responsibility, timing and the conditions that block progression.'],
    ['Evidence', 'Observe real cases before redesigning.', 'Sample timestamps, artefacts, rework, failure reasons and the people carrying hidden manual load.'],
    ['Design', 'Use AI only where it improves the flow.', 'Automate classification, synthesis or drafting while preserving human approval for consequential decisions.'],
    ['Verification', 'Run a shadow-mode pilot.', 'Compare the proposed workflow against the current baseline without letting unmeasured automation affect customers.'],
    ['Delivery', 'Produce a process map and pilot plan.', 'Leave owners, checkpoints, risk controls, success measures and the smallest next implementation step.']
  ],
  research: [
    ['Objective', 'Turn the question into a decision.', 'Write the decision, time horizon and what evidence would make the answer useful.'],
    ['Acceptance', 'Define a calibrated output.', 'Require sub-claims, sources, confidence, contrary evidence and explicit unresolved questions.'],
    ['Evidence', 'Rank information by decision value.', 'Gather the smallest evidence that could materially change the top assumptions.'],
    ['Design', 'Explore several explanatory paths.', 'Use AI for breadth and comparison, then narrow with source quality and falsifiability.'],
    ['Verification', 'Attack the preferred explanation.', 'Search for contradictions, boundary cases, hidden variables and assumptions that were smuggled into the framing.'],
    ['Delivery', 'Create a decision-ready research map.', 'Provide the claim tree, evidence log, uncertainties, recommendation and next experiment.']
  ],
  adoption: [
    ['Objective', 'Find a valuable problem before choosing AI.', 'Identify repeated work, decision bottlenecks, information overload or quality failures with an accountable owner.'],
    ['Acceptance', 'Define value and acceptable failure.', 'Set baseline time, quality, review load, risk class and a condition for stopping the experiment.'],
    ['Evidence', 'Use representative historical examples.', 'Collect real inputs, expected outputs and a failure taxonomy instead of demo-only prompts.'],
    ['Design', 'Choose the narrowest useful AI role.', 'Start with research, drafting, triage or decision support before granting consequential action authority.'],
    ['Verification', 'Measure in shadow mode.', 'Track edits, reviewer effort, error severity, recovery and operational cost before deployment.'],
    ['Delivery', 'Produce an adoption roadmap.', 'Prioritise use cases by value, feasibility, reversibility and evidence readiness.']
  ]
};

let selectedPreset = 'completion';
$$('[data-preset]').forEach(button => button.addEventListener('click', () => {
  $$('[data-preset]').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  selectedPreset = button.dataset.preset;
  $('#challenge-input').value = labPresets[selectedPreset];
}));

function inferPreset(text) {
  const value = text.toLowerCase();
  if (/(done|complete|finished|prove|evidence|agent)/.test(value)) return 'completion';
  if (/(process|handoff|slow|team|operations|onboarding|workflow)/.test(value)) return 'operations';
  if (/(research|question|theory|technical|science|unknown)/.test(value)) return 'research';
  if (/(adopt|use ai|company|opportunity|automate|value)/.test(value)) return 'adoption';
  return selectedPreset;
}

function renderLabSteps(type, challenge) {
  const output = labOutputs[type];
  const list = $('#lab-steps');
  list.innerHTML = output.map((step, index) => `
    <li>
      <i>${String(index + 1).padStart(2, '0')}</i>
      <div><small>${step[0]}</small><strong>${step[1]}</strong><p>${step[2]}</p></div>
    </li>`).join('');
  $('#lab-state').textContent = 'PROCESSING';
  const items = $$('#lab-steps li');
  items.forEach((item, index) => setTimeout(() => {
    item.classList.add('active');
    if (index === items.length - 1) $('#lab-state').textContent = 'STRUCTURED';
  }, 180 * (index + 1)));
  if (challenge.trim()) $('#lab-state').setAttribute('title', `Structured from: ${challenge.trim()}`);
}

$('#run-lab')?.addEventListener('click', () => {
  const challenge = $('#challenge-input').value.trim();
  const type = inferPreset(challenge);
  selectedPreset = type;
  $$('[data-preset]').forEach(button => button.classList.toggle('active', button.dataset.preset === type));
  renderLabSteps(type, challenge);
});

const projectDetails = {
  verifier: {
    title: 'Agent Completion Verifier — contribution split',
    body: `
      <p class="status status-verified">Public implementation</p>
      <h2 id="project-modal-title">Problem framing became executable verification.</h2>
      <h3>Luca’s contribution</h3>
      <p>The practical failure mode, evidence-grounded acceptance standard, outcome categories, recovery rules and case direction were developed through sustained testing of long-running AI workflows. The core requirement was simple but strict: completion must be grounded in observable evidence, not confident language.</p>
      <h3>AI contribution</h3>
      <p>AI assistance helped translate the requirements into Python, documentation, schemas, tests, adapters and release automation. Those artefacts were then checked through the test suite, package verification and example evaluation.</p>
      <h3>Current evidence boundary</h3>
      <p>The repository evaluates structured cases, transforms strict traces and independently observes a narrow local file postcondition. It does not prove arbitrary remote state, identity, authorisation or causal attribution.</p>`
  },
  arena: {
    title: 'Agent Reliability Arena — contribution split',
    body: `
      <p class="status status-prototype">Controlled deterministic comparison</p>
      <h2 id="project-modal-title">Same conditions. Different orchestration.</h2>
      <h3>Luca’s contribution</h3>
      <p>Luca defined the narrow comparison question, fairness requirement, evidence-first acceptance standard and insistence that the specialist system could not grade itself. The design exposes reliability gains and the additional call complexity rather than hiding the trade-off.</p>
      <h3>AI contribution</h3>
      <p>AI assistance supported implementation of the experiment runner, bounded roles, replay artifacts, web trace viewer, documentation and verification suite under the stated constraints.</p>
      <h3>Current evidence boundary</h3>
      <p>The reference results validate deterministic fixture policies and experiment plumbing. They are not presented as representative OpenAI, Anthropic, Gemini, local-model or human performance.</p>`
  }
};

const projectModal = $('#project-modal');
$$('[data-project-detail]').forEach(button => button.addEventListener('click', () => {
  const detail = projectDetails[button.dataset.projectDetail];
  $('#project-modal-content').innerHTML = detail.body;
  projectModal.classList.add('open');
  projectModal.setAttribute('aria-hidden', 'false');
}));
function closeProjectModal() {
  projectModal.classList.remove('open');
  projectModal.setAttribute('aria-hidden', 'true');
}
$$('[data-close-modal]').forEach(button => button.addEventListener('click', closeProjectModal));

const nexusViews = {
  flow: {
    title: 'Operating flow',
    text: 'The Nexus routes a problem through objective, context, AI reasoning, tools, validation, output and outcome review before anything becomes durable learning.',
    bullets: ['Human objective and constraints lead the flow', 'Tool contracts are treated as real limits', 'Validation occurs before consequential action', 'Outcomes and errors feed the next iteration']
  },
  record: {
    title: 'Continuous Learning Record',
    text: 'A proposed durable record prevents decisions and failure lessons from disappearing when a chat or work session ends.',
    bullets: ['Observation · Decision · Action · Outcome', 'Error · Correction · Confidence', 'Provenance · Reusable pattern · Next action', 'Temporary session state remains separate from durable knowledge']
  },
  status: {
    title: 'Capability status discipline',
    text: 'Every component is labelled by what currently exists instead of being marketed as though the full architecture is already operational.',
    bullets: ['Verified practice: repeated use with observable artefacts', 'Prototype: working demonstration, not production hardened', 'Framework: structured design guiding work', 'Planned: intentional next step, not implemented']
  }
};
function setNexusView(view) {
  const detail = nexusViews[view];
  $('#nexus-detail').innerHTML = `<h3>${detail.title}</h3><p>${detail.text}</p><ul>${detail.bullets.map(item => `<li>${item}</li>`).join('')}</ul>`;
  $$('[data-nexus-view]').forEach(button => button.classList.toggle('active', button.dataset.nexusView === view));
}
setNexusView('flow');
$$('[data-nexus-view]').forEach(button => button.addEventListener('click', () => setNexusView(button.dataset.nexusView)));

const nodeDetails = {
  objective: ['Human Objective & Constraints', 'What outcome matters, what is off-limits, who owns the decision and how completion will be judged.'],
  context: ['Context & Knowledge', 'Source-tagged inputs, prior decisions, freshness, uncertainty and the limits of what the system is allowed to use.'],
  reasoning: ['AI Reasoning', 'Options, analysis, comparison and generation—treated as candidate work requiring validation, not automatic truth.'],
  tools: ['Tools & Actions', 'The real mechanisms that search, calculate, write, send, change or retrieve. Their contracts define what is actually possible.'],
  validation: ['Validation & Risk', 'Evidence checks, failure taxonomy, human approval, reversibility and blast-radius review before action is accepted.'],
  outputs: ['Outputs & Delivery', 'Documents, code, prototypes, decisions or actions that can be inspected and used by someone else.'],
  outcomes: ['Outcomes & Feedback', 'What actually happened compared with what was expected, including errors, corrections and stakeholder response.'],
  patterns: ['Patterns & Continuity', 'Reusable methods and failure lessons preserved only after repeated evidence—not abstracted prematurely.']
};
$$('.nexus-node').forEach(node => {
  node.setAttribute('tabindex', '0');
  node.setAttribute('role', 'button');
  const activate = () => {
    $$('.nexus-node').forEach(item => item.classList.remove('active'));
    node.classList.add('active');
    const [title, text] = nodeDetails[node.dataset.node];
    $('#nexus-detail').innerHTML = `<h3>${title}</h3><p>${text}</p><p><span class="status status-framework">Framework node</span></p>`;
  };
  node.addEventListener('click', activate);
  node.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      activate();
    }
  });
});

const cvModal = $('#cv-modal');
function openCV() {
  cvModal.classList.add('open');
  cvModal.setAttribute('aria-hidden', 'false');
}
function closeCV() {
  cvModal.classList.remove('open');
  cvModal.setAttribute('aria-hidden', 'true');
}
$$('[data-open-cv]').forEach(button => button.addEventListener('click', openCV));
$$('[data-close-cv]').forEach(button => button.addEventListener('click', closeCV));
$('#print-cv')?.addEventListener('click', () => print());

addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    closeCV();
    closeProjectModal();
    primaryNav?.classList.remove('open');
    menuButton?.setAttribute('aria-expanded', 'false');
  }
});

// Give the page a useful first state without pretending a live model was called.
$('[data-preset="completion"]')?.classList.add('active');
$('#challenge-input').value = labPresets.completion;
