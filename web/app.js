"use strict";

const byId = (id) => document.getElementById(id);

function boolLabel(value) {
  return value ? "Yes" : "No";
}

function statusClass(status) {
  return status === "VERIFIED_COMPLETE" ? "verified" : "failed";
}

function createStep(index, title, description) {
  const row = document.createElement("div");
  row.className = "trace-step";
  const marker = document.createElement("span");
  marker.className = "trace-step-index";
  marker.textContent = String(index).padStart(2, "0");
  const copy = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = title;
  const paragraph = document.createElement("p");
  paragraph.textContent = description;
  copy.append(heading, paragraph);
  row.append(marker, copy);
  return row;
}

function setStatus(element, status) {
  element.textContent = status === "VERIFIED_COMPLETE" ? "Verified" : "Not verified";
  element.className = `status-chip ${statusClass(status)}`;
}

function renderGeneralTrace(data) {
  const target = byId("general-trace");
  target.replaceChildren();
  target.append(createStep(1, "General agent acts", `Injected scenario: ${data.attempts[0].injected_scenario}`));
  target.append(createStep(2, "Source report", data.attempts[0].source_report.reported_success ? "The tool-shaped source reported success." : "The source did not report success."));
  target.append(createStep(3, "Independent observation", data.attempts[0].observation.matches_contract ? "Observed state matches the exact contract." : "Observed state does not match the exact contract."));
  target.append(createStep(4, "Final claim", data.completion_claimed ? "The general condition claims completion." : "The general condition does not claim completion."));
}

function renderSpecialistTrace(data) {
  const target = byId("specialist-trace");
  target.replaceChildren();
  target.append(createStep(1, "Strategist", data.strategy.required_postcondition));
  target.append(createStep(2, "Operator", `Executed ${data.attempts.length} bounded mutation attempt${data.attempts.length === 1 ? "" : "s"}.`));
  const firstAudit = data.audit_records[0];
  target.append(createStep(3, "Auditor", `${firstAudit.decision.toUpperCase()}: ${firstAudit.observation_assessment}`));
  if (data.recovery) {
    target.append(createStep(4, "Recovery", `${data.recovery.failure_class}: one exact retry was justified.`));
  } else {
    target.append(createStep(4, "Recovery", "No retry was justified or required."));
  }
  target.append(createStep(5, "Synthesiser", data.synthesis.summary));
}

function evidenceCard(label, value) {
  const card = document.createElement("article");
  card.className = "evidence-card";
  const name = document.createElement("span");
  name.textContent = label;
  const content = document.createElement("strong");
  content.textContent = value;
  card.append(name, content);
  return card;
}

function renderEvidence(scenario) {
  const target = byId("evidence-grid");
  target.replaceChildren();
  const finalAttempt = scenario.specialist.attempts.at(-1);
  target.append(evidenceCard("Trust basis", finalAttempt.evidence.trust_basis));
  target.append(evidenceCard("Observed path", finalAttempt.evidence.path));
  target.append(evidenceCard("Observed SHA-256", finalAttempt.evidence.sha256 || "No matching file digest"));
  target.append(evidenceCard("Content match", boolLabel(finalAttempt.evidence.matches_content)));
  target.append(evidenceCard("Security confined", boolLabel(finalAttempt.evidence.confined)));
  target.append(evidenceCard("Final verifier status", scenario.specialist.status));
}

function renderScenario(scenario) {
  const general = scenario.general;
  const specialist = scenario.specialist;
  byId("scenario-summary").textContent = `${scenario.scenario_id.replaceAll("_", " ")}: general ${general.status.toLowerCase().replaceAll("_", " ")}; specialist ${specialist.status.toLowerCase().replaceAll("_", " ")}.`;
  setStatus(byId("general-status"), general.status);
  setStatus(byId("specialist-status"), specialist.status);
  byId("general-claim").textContent = boolLabel(general.completion_claimed);
  byId("specialist-claim").textContent = boolLabel(specialist.completion_claimed);
  byId("general-calls").textContent = String(general.logical_model_calls);
  byId("specialist-calls").textContent = String(specialist.logical_model_calls);
  renderGeneralTrace(general);
  renderSpecialistTrace(specialist);
  renderEvidence(scenario);
}

function renderPage(data) {
  const general = data.metrics.conditions.general;
  const specialist = data.metrics.conditions.specialist;
  byId("general-verified").textContent = `${general.verified_complete}/${general.total_runs}`;
  byId("specialist-verified").textContent = `${specialist.verified_complete}/${specialist.total_runs}`;
  byId("false-reduction").textContent = String(data.metrics.paired.false_completion_reduction);
  byId("extra-calls").textContent = `+${data.metrics.paired.additional_logical_model_calls}`;
  byId("model-control").textContent = `${data.experiment.model_id}, version ${data.experiment.model_version}.`;
  byId("contract-control").textContent = `${data.experiment.contract.path}; exact UTF-8 content required.`;
  byId("seed-control").textContent = `Seed ${data.experiment.seed}; identical eight-scenario schedule.`;
  byId("claims-boundary").textContent = data.claims_boundary;

  const select = byId("scenario-select");
  data.scenarios.forEach((scenario) => {
    const option = document.createElement("option");
    option.value = scenario.scenario_id;
    option.textContent = scenario.scenario_id.replaceAll("_", " ");
    select.append(option);
  });
  const preferred = data.scenarios.find((item) => item.scenario_id === "false_success") || data.scenarios[0];
  select.value = preferred.scenario_id;
  renderScenario(preferred);
  select.addEventListener("change", () => {
    const selected = data.scenarios.find((item) => item.scenario_id === select.value);
    if (selected) renderScenario(selected);
  });
}

fetch("data/fixture-v1.json")
  .then((response) => {
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    return response.json();
  })
  .then(renderPage)
  .catch((error) => {
    byId("scenario-summary").textContent = `Unable to load verified fixture data: ${error.message}`;
  });
