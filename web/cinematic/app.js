const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

const escapeHTML = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const siteHeader = $("[data-header]");
const cursorField = $(".cursor-field");
const menuButton = $("[data-menu]");
const primaryNav = $("[data-nav]");

addEventListener("scroll", () => {
  siteHeader?.classList.toggle("scrolled", scrollY > 18);
}, { passive: true });

addEventListener("pointermove", (event) => {
  if (!cursorField) return;
  cursorField.style.left = `${event.clientX}px`;
  cursorField.style.top = `${event.clientY}px`;
}, { passive: true });

menuButton?.addEventListener("click", () => {
  const open = primaryNav?.classList.toggle("open") ?? false;
  menuButton.setAttribute("aria-expanded", String(open));
});

$$("#primary-nav a, #primary-nav button").forEach((control) => {
  control.addEventListener("click", () => {
    primaryNav?.classList.remove("open");
    menuButton?.setAttribute("aria-expanded", "false");
  });
});

const revealObserver = "IntersectionObserver" in window
  ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.1 })
  : null;

$$(".reveal").forEach((element) => {
  if (revealObserver) revealObserver.observe(element);
  else element.classList.add("visible");
});

const commandData = {
  luca: {
    label: "HUMAN DIRECTION",
    status: "ACCOUNTABLE OWNER",
    sigil: "L",
    title: "Define the real objective and what counts as done.",
    description: "Luca separates the surface request from the operational problem, sets the acceptance contract and owns consequential judgement.",
    contributes: "Problem framing, standards, challenge, risk ownership and final acceptance.",
    boundary: "Does not delegate legal, financial, reputational or public accountability to AI.",
    artefacts: "Acceptance contract, risk boundary, decision record and approval state."
  },
  ace: {
    label: "AI ACCELERATION",
    status: "CANDIDATE WORK",
    sigil: "A",
    title: "Expand, compare and translate intent into technical artefacts.",
    description: "ACE accelerates research, code assistance, architecture, testing and documentation while leaving the objective and final judgement human-owned.",
    contributes: "Breadth, synthesis, counterarguments, iteration speed and structured continuity.",
    boundary: "Fluent output is not treated as proof, and ACE does not grant itself authority.",
    artefacts: "Prototype code, test plans, diagrams, specifications and structured analysis."
  },
  tools: {
    label: "OBSERVABLE EXECUTION",
    status: "CONTRACT-BOUNDED",
    sigil: "T",
    title: "Create state changes and artefacts another person can inspect.",
    description: "Tools search, calculate, write, retrieve or change state. Their real contracts define what is possible and what evidence can be collected.",
    contributes: "Repository changes, tests, files, searches, records and bounded workflow actions.",
    boundary: "A tool receipt is evidence only for fields and postconditions it can genuinely support.",
    artefacts: "Logs, test output, files, identifiers, manifests and external-state observations."
  },
  evidence: {
    label: "INDEPENDENT JUDGEMENT",
    status: "CANONICAL LAYER",
    sigil: "E",
    title: "Decide what can be claimed from observable reality.",
    description: "Evidence stays separate from source-reported confidence. Completion is accepted only when every required action and evidence field is satisfied.",
    contributes: "Verification, mismatch detection, replay, falsification and explicit uncertainty.",
    boundary: "The system that performs an action cannot silently redefine the proof standard after acting.",
    artefacts: "Canonical verdict, raw trace, evidence manifest, limitation statement and replay bundle."
  },
  nexus: {
    label: "CONTINUITY & CONTROL",
    status: "DEVELOPING FRAMEWORK",
    sigil: "N",
    title: "Connect objectives, context, actions, outcomes and durable learning.",
    description: "ACE Master Nexus preserves project state and next actions through structured records without pretending every component is autonomous or permanently integrated.",
    contributes: "Project indexing, status discipline, provenance, correction history and reusable patterns.",
    boundary: "Only verified lessons become durable; temporary context and conceptual plans remain labelled.",
    artefacts: "Project record, decision log, evidence links, correction record and next concrete action."
  }
};

function selectCommand(key) {
  const data = commandData[key];
  if (!data) return;

  $$("[data-command-node]").forEach((button) => {
    const selected = button.dataset.commandNode === key;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
  });

  $("#command-label").textContent = data.label;
  $("#command-status").textContent = data.status;
  $("#command-sigil").textContent = data.sigil;
  $("#command-title").textContent = data.title;
  $("#command-description").textContent = data.description;
  $("#command-contributes").textContent = data.contributes;
  $("#command-boundary").textContent = data.boundary;
  $("#command-artefacts").textContent = data.artefacts;
}

$$("[data-command-node]").forEach((button) => {
  button.addEventListener("click", () => selectCommand(button.dataset.commandNode));
});

$$("[data-capability]").forEach((item) => {
  const trigger = $(".capability-trigger", item);
  const body = $(".capability-body", item);

  trigger?.addEventListener("click", () => {
    const willOpen = !item.classList.contains("open");

    $$("[data-capability]").forEach((other) => {
      other.classList.remove("open");
      $(".capability-trigger", other)?.setAttribute("aria-expanded", "false");
      const otherBody = $(".capability-body", other);
      if (otherBody) otherBody.hidden = true;
    });

    if (willOpen) {
      item.classList.add("open");
      trigger.setAttribute("aria-expanded", "true");
      if (body) body.hidden = false;
    }
  });
});

function showLabPanel(key) {
  $$("[data-lab-target]").forEach((tab) => {
    const selected = tab.dataset.labTarget === key;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
  });

  $$("[data-lab-panel]").forEach((panel) => {
    const selected = panel.dataset.labPanel === key;
    panel.classList.toggle("active", selected);
    panel.hidden = !selected;
  });
}

$$("[data-lab-target]").forEach((tab) => {
  tab.addEventListener("click", () => showLabPanel(tab.dataset.labTarget));
});

const verifierInputs = {
  claim: $("#v-claim"),
  success: $("#v-success"),
  message: $("#v-message"),
  recipient: $("#v-recipient"),
  rollback: $("#v-rollback")
};

const verifierPresets = {
  verified: [true, true, true, true, false],
  partial: [true, true, true, false, false],
  unverified: [true, true, false, false, false],
  failed: [true, false, false, false, false],
  rollback: [true, true, true, true, true]
};

function verifierRows(state) {
  return [
    ["01", "Completion claim", state.claim ? "Agent reported success" : "No success claim", state.claim ? "OBSERVED" : "ABSENT"],
    ["02", "Latest action", state.success ? "send_email succeeded" : "send_email failed", state.success ? "PASS" : "FAIL"],
    ["03", "Message identifier", state.message ? "Present" : "Missing", state.message ? "PASS" : "MISSING"],
    ["04", "Recipient evidence", state.recipient ? "Present" : "Missing", state.recipient ? "PASS" : "MISSING"],
    ["05", "Later event", state.rollback ? "Failure or rollback invalidates success" : "No invalidating later event", state.rollback ? "FAIL" : "CLEAR"]
  ];
}

function evaluateVerifier() {
  const state = Object.fromEntries(Object.entries(verifierInputs).map(([key, input]) => [key, Boolean(input?.checked)]));
  let title;
  let copy;
  let color;

  if (state.rollback) {
    title = "FAILED";
    copy = "A later failure or rollback overrides the earlier successful event.";
    color = "var(--red)";
  } else if (!state.success) {
    title = "FAILED";
    copy = "The latest required action is recorded as unsuccessful.";
    color = "var(--red)";
  } else if (state.message && state.recipient) {
    title = "VERIFIED_COMPLETE";
    copy = state.claim
      ? "Every required action and evidence field is present in the latest successful event."
      : "The task is proven complete even though the agent did not announce success.";
    color = "var(--green)";
  } else if (state.message || state.recipient) {
    title = "PARTIAL";
    copy = "The action appears successful, but only part of the required evidence is present.";
    color = "var(--gold)";
  } else {
    title = "UNVERIFIED";
    copy = state.claim
      ? "The agent claims completion, but the acceptance contract is not evidenced."
      : "Nothing is proven and no completion claim was made.";
    color = "var(--violet)";
  }

  $("#verifier-title").textContent = title;
  $("#verifier-copy").textContent = copy;
  $("#verifier-state").textContent = "EVALUATED";
  $("#verifier-state").style.color = color;
  $("#verifier-lamp").style.background = `radial-gradient(circle, ${color}, transparent 70%)`;
  $("#verifier-lamp").style.boxShadow = `0 0 48px ${color}`;

  const trace = $("#verifier-trace");
  trace.replaceChildren();
  verifierRows(state).forEach(([index, label, detail, status]) => {
    const item = document.createElement("li");
    const number = document.createElement("i");
    const body = document.createElement("div");
    const heading = document.createElement("strong");
    const description = document.createElement("p");
    const result = document.createElement("b");
    number.textContent = index;
    heading.textContent = label;
    description.textContent = detail;
    result.textContent = status;
    body.append(heading, description);
    item.append(number, body, result);
    trace.append(item);
  });
}

$$("[data-verifier-preset]").forEach((button) => {
  button.addEventListener("click", () => {
    $$("[data-verifier-preset]").forEach((other) => other.classList.remove("active"));
    button.classList.add("active");
    const values = verifierPresets[button.dataset.verifierPreset];
    Object.values(verifierInputs).forEach((input, index) => {
      if (input) input.checked = values[index];
    });
    evaluateVerifier();
  });
});

$("#run-verifier")?.addEventListener("click", evaluateVerifier);

function renderArchitecture(target, summary, cards, limitation) {
  const output = $(target);
  if (!output) return;

  const summaryCard = `<article class="output-summary"><strong>${escapeHTML(summary)}</strong><p>${escapeHTML(limitation)}</p></article>`;
  const cardMarkup = cards.map((card, index) => `
    <article>
      <span>${String(index + 1).padStart(2, "0")}</span>
      <div><h4>${escapeHTML(card.title)}</h4><p>${escapeHTML(card.description)}</p></div>
      <b>${escapeHTML(card.tag)}</b>
    </article>`).join("");

  output.innerHTML = summaryCard + cardMarkup;
}

function buildWorkflow() {
  const problem = $("#workflow-problem")?.value.trim() || "The process is unclear.";
  const risk = $("#workflow-risk")?.value || "medium";
  const frequency = $("#workflow-frequency")?.value || "daily";

  const approval = risk === "high" ? "Named human approval before every consequential action" : risk === "medium" ? "Human approval before customer-facing state changes" : "Periodic human review with immediate rollback";
  const recovery = risk === "high" ? "Stop, preserve evidence, escalate and require explicit restart" : risk === "medium" ? "Retry once within bounds, then route to a human owner" : "Retry bounded reversible steps and log the correction";
  const cadence = frequency === "continuous" ? "Live event logging and hourly exception review" : frequency === "daily" ? "Per-case trace with daily pattern review" : "Per-run trace with periodic review";

  renderArchitecture(
    "#workflow-output",
    "A six-layer workflow that keeps ownership and proof visible.",
    [
      { title: "Objective contract", description: `Translate “${problem.slice(0, 110)}${problem.length > 110 ? "…" : ""}” into one observable outcome and explicit exclusions.`, tag: "HUMAN" },
      { title: "Intake and state capture", description: "Standardise required inputs, freshness, source and current owner before AI reasoning begins.", tag: "TOOLS" },
      { title: "AI assistance boundary", description: "Use AI for classification, drafting, comparison or preparation—not silent ownership of the final outcome.", tag: "ACE" },
      { title: "Approval gate", description: approval, tag: "CONTROL" },
      { title: "Evidence contract", description: "Record action result, external identifier, actor, timestamp and postcondition required to support completion.", tag: "PROOF" },
      { title: "Recovery and learning", description: `${recovery}. ${cadence}.`, tag: "NEXUS" }
    ],
    "This is a structural diagnostic, not a production workflow or a claim that the organisation has been fully analysed."
  );
}

$("#run-workflow")?.addEventListener("click", buildWorkflow);

const taskRoleSets = {
  research: [
    ["Research Lead", "Decomposes the question and defines competing hypotheses.", "NO ACTION"],
    ["Evidence Scout", "Collects source-tagged candidate evidence and freshness metadata.", "READ ONLY"],
    ["Critic", "Looks for contradictions, missing evidence and alternative explanations.", "NO MUTATION"],
    ["Synthesiser", "Builds a decision-ready answer with uncertainty and next tests.", "DRAFT ONLY"]
  ],
  operations: [
    ["Workflow Strategist", "Defines the objective, handoffs and acceptance contract.", "NO ACTION"],
    ["Operator", "Prepares or executes only the allowed bounded action.", "BOUNDED"],
    ["Auditor", "Compares tool output and observed state against the contract.", "NO MUTATION"],
    ["Recovery", "Attempts the predefined reversible path after verified mismatch.", "CONDITIONAL"],
    ["Synthesiser", "Reports verified, partial, unverified or failed status.", "NO OVERRIDE"]
  ],
  evaluation: [
    ["Case Designer", "Defines representative tasks, failures and acceptance fields.", "NO GRADING"],
    ["Runner", "Executes each condition under controlled inputs.", "SANDBOXED"],
    ["Independent Verifier", "Judges outcomes from raw evidence and postconditions.", "CANONICAL"],
    ["Analyst", "Computes paired metrics and exposes complexity trade-offs.", "READ ONLY"]
  ],
  delivery: [
    ["Requirements Lead", "Extracts the real audience, use case and completion standard.", "NO ACTION"],
    ["Builder", "Creates the requested document, code or interactive artefact.", "DRAFT/BUILD"],
    ["Reviewer", "Checks accuracy, completeness, accessibility and claim boundaries.", "NO MUTATION"],
    ["Release Gate", "Approves only the verified output for delivery.", "HUMAN"]
  ]
};

function designAgentSystem() {
  const task = $("#agent-task")?.value || "operations";
  const risk = $("#agent-risk")?.value || "medium";
  const autonomy = $("#agent-autonomy")?.value || "prepare";
  const baseRoles = taskRoleSets[task];
  const roles = [...baseRoles];

  if (risk === "high") {
    roles.push(["Human Risk Owner", "Approves consequential decisions, exceptions and any expansion of authority.", "FINAL AUTHORITY"]);
  }

  if (autonomy === "execute" && risk !== "low") {
    roles.push(["Policy Gate", "Blocks actions outside the allowed tool, scope, amount, recipient or time window.", "PRE-ACTION"]);
  }

  const autonomyText = autonomy === "assist"
    ? "No external action: AI may analyse and draft only."
    : autonomy === "prepare"
      ? "Actions are prepared for named human approval."
      : risk === "low"
        ? "Only bounded, reversible actions may execute automatically."
        : "Execution requires policy checks and retained human authority.";

  renderArchitecture(
    "#agent-output",
    `${roles.length} roles, added only where separation improves control or evidence.`,
    roles.map(([title, description, tag]) => ({ title, description, tag })),
    `${autonomyText} This is an architecture proposal, not evidence that the system is production-ready.`
  );
}

$("#run-agents")?.addEventListener("click", designAgentSystem);

function buildEvidenceContract() {
  const claim = $("#claim-input")?.value.trim() || "The system performs better.";
  const scope = $("#claim-scope")?.value || "comparative";

  const scopeRequirements = {
    demo: "A deterministic fixture can support a narrow software-behaviour claim.",
    comparative: "Both conditions need identical tasks, tools, evidence rules, mutation limits and paired analysis.",
    production: "Representative live traffic, pre-registered metrics, sufficient sample size, latency, cost, safety and incident data are required."
  };

  const conclusion = scope === "production"
    ? "Current deterministic evidence would be insufficient for this strength of claim."
    : "The claim can be tested if the acceptance and comparison contract is fixed before results are observed.";

  renderArchitecture(
    "#evidence-output",
    `Evidence contract for: “${claim.slice(0, 120)}${claim.length > 120 ? "…" : ""}”`,
    [
      { title: "Operational definition", description: "Replace “better” or “reliable” with a measurable outcome, denominator and observation window.", tag: "DEFINE" },
      { title: "Acceptance contract", description: "Specify required action, evidence fields, latest-event semantics and valid completion states before running cases.", tag: "LOCK" },
      { title: "Independent observation", description: "Preserve raw traces and external postconditions separately from the system’s own report.", tag: "OBSERVE" },
      { title: "Fair comparison", description: scopeRequirements[scope], tag: "CONTROL" },
      { title: "Falsification test", description: "State which result, mismatch, rollback or missing field would force the claim to be weakened or rejected.", tag: "CHALLENGE" },
      { title: "Bounded conclusion", description: conclusion, tag: "REPORT" }
    ],
    "A strong evidence plan can show that a claim is currently unsupported; it does not manufacture the missing evidence."
  );
}

$("#run-evidence")?.addEventListener("click", buildEvidenceContract);

const deliveryTemplates = {
  evaluate: {
    "48h": ["Failure-surface interview", "Initial acceptance contract", "Ten representative cases", "Evidence and risk memo"],
    "2w": ["Evaluation harness prototype", "Structured case suite", "Trace and metric design", "Reproducible findings report"],
    "6w": ["Shadow evaluation pipeline", "Live-model comparison plan", "Reviewer workflow", "Scale / redesign / stop decision"]
  },
  workflow: {
    "48h": ["Process and handoff map", "Automation opportunity screen", "Risk and ownership matrix", "Pilot recommendation"],
    "2w": ["Narrow workflow prototype", "Approval and recovery gates", "Evidence logging", "Operational test plan"],
    "6w": ["Shadow pilot", "Exception monitoring", "Human-review measurement", "Implementation runbook"]
  },
  research: {
    "48h": ["Question decomposition", "Evidence register", "Competing explanations", "Next-test recommendation"],
    "2w": ["Structured literature and source review", "Claim map", "Prototype calculation or simulation", "Decision-ready synthesis"],
    "6w": ["Repeatable research pipeline", "External review loop", "Experiment design", "Validated research roadmap"]
  },
  prototype: {
    "48h": ["Requirements and claim boundary", "Interaction or architecture concept", "Technical feasibility memo", "Build sequence"],
    "2w": ["Working narrow prototype", "Core tests", "Interactive demonstration", "Technical and limitation documentation"],
    "6w": ["Shadow-ready pilot", "Telemetry and failure handling", "Reviewer feedback cycle", "Production-readiness decision"]
  }
};

function buildDeliveryPlan() {
  const goal = $("#delivery-goal")?.value || "prototype";
  const horizon = $("#delivery-horizon")?.value || "2w";
  const team = $("#delivery-team")?.value || "product";
  const items = deliveryTemplates[goal][horizon];

  const teamContext = {
    founder: "Optimise for one decision, fast learning and minimal operational overhead.",
    product: "Integrate product, engineering and reviewer needs with explicit acceptance criteria.",
    operations: "Prioritise ownership, handoffs, exception handling and measurable time saved.",
    governance: "Prioritise provenance, reviewability, policy boundaries and evidence retention."
  }[team];

  const horizonLabel = { "48h": "48-hour diagnostic", "2w": "two-week prototype", "6w": "six-week shadow pilot" }[horizon];

  renderArchitecture(
    "#delivery-output",
    `${horizonLabel}: four concrete outputs and one decision point.`,
    items.map((title, index) => ({
      title,
      description: index === items.length - 1 ? `${teamContext} Finish with a named owner and next decision.` : `${teamContext} Keep claims bounded by the evidence available at this stage.`,
      tag: index === items.length - 1 ? "DECIDE" : `OUTPUT ${index + 1}`
    })),
    "The actual scope would be adjusted after access to the organisation’s systems, data, stakeholders and constraints."
  );
}

$("#run-delivery")?.addEventListener("click", buildDeliveryPlan);

const cvModal = $("[data-cv-modal]");
let previousFocus = null;

function openCV() {
  if (!cvModal) return;
  previousFocus = document.activeElement;
  cvModal.classList.add("open");
  cvModal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  $("[data-close-cv]", cvModal)?.focus();
}

function closeCV() {
  if (!cvModal) return;
  cvModal.classList.remove("open");
  cvModal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  previousFocus?.focus?.();
}

$$('[data-open-cv]').forEach((button) => button.addEventListener("click", openCV));
$$('[data-close-cv]').forEach((button) => button.addEventListener("click", closeCV));
$("#print-cv")?.addEventListener("click", () => print());

addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeCV();
    primaryNav?.classList.remove("open");
    menuButton?.setAttribute("aria-expanded", "false");
  }
});

selectCommand("luca");
evaluateVerifier();
buildWorkflow();
designAgentSystem();
buildEvidenceContract();
buildDeliveryPlan();
