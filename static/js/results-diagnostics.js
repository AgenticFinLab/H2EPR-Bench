const modelCardGrid = document.querySelector("#model-card-grid");
const modelDetailPanel = document.querySelector("#model-detail-panel");

let diagnosticsPayload = null;
let selectedSystem = "GLM-5.1";

const scoreMetrics = [
  ["structural_fidelity", "Struct"],
  ["temporal_fidelity", "Temp"],
  ["causal_fidelity", "Causal"],
  ["evidence_fidelity", "Evid"],
];

const failureLabels = [
  ["invalid_json", "Invalid JSON"],
  ["old_schema_invalid", "Schema mismatch"],
  ["unresolved_relation_endpoint", "Unresolved relation endpoint"],
  ["unknown_evidence_source", "Unknown evidence source"],
  ["unsupported_response_envelope", "Unsupported response envelope"],
];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatScore(value, digits = 2) {
  return Number(value).toFixed(digits);
}

function percent(value, digits = 1) {
  return `${Number(value).toFixed(digits)}%`;
}

function bar(metric, label, value, accentVar = "--model-accent") {
  const safeValue = Math.max(0, Math.min(100, Number(value)));
  return `
    <div class="mini-bar">
      <span>${label}</span>
      <span class="mini-bar-track">
        <span class="mini-bar-fill" style="width: ${safeValue}%; background: var(${accentVar}, var(--accent));"></span>
      </span>
      <span>${formatScore(value, 0)}</span>
    </div>
  `;
}

function renderModelCard(model) {
  const active = model.system === selectedSystem ? " is-active" : "";
  return `
    <button class="model-card${active}" type="button" data-system="${escapeHtml(model.system)}" style="--model-accent: ${model.accent};">
      <div class="model-card-top">
        <div>
          <h3>${escapeHtml(model.short_name)}</h3>
          <small>${escapeHtml(model.family)} · ${escapeHtml(model.system)}</small>
        </div>
        <span class="model-rank">#${model.rank}</span>
      </div>
      <div class="model-score-row">
        <div>
          <strong>${formatScore(model.h2epr_score)}</strong>
          <span>H²EPRScore</span>
        </div>
        <div>
          <strong>${percent(model.output_validity_pct)}</strong>
          <span>Valid outputs</span>
        </div>
      </div>
      <div class="mini-bars">
        ${scoreMetrics.map(([key, label]) => bar(key, label, model[key])).join("")}
      </div>
      <span class="model-bottleneck">${escapeHtml(model.bottleneck)}</span>
    </button>
  `;
}

function renderDetail(model) {
  modelDetailPanel.style.setProperty("--detail-accent", model.accent);
  modelDetailPanel.innerHTML = `
    <span class="detail-kicker">Pipeline trace · rank #${model.rank}</span>
    <h3>${escapeHtml(model.system)}</h3>
    <div class="detail-metric-grid">
      <div>
        <strong>${formatScore(model.h2epr_score)}</strong>
        <span>H²EPRScore</span>
      </div>
      <div>
        <strong>${percent(model.output_validity_pct)}</strong>
        <span>Valid outputs</span>
      </div>
      <div>
        <strong>${formatScore(model.absolute_fidelity)}</strong>
        <span>Absolute Fidelity</span>
      </div>
      <div>
        <strong>${formatScore(model.mean_tokens_per_event / 1000, 1)}k</strong>
        <span>Tokens / event</span>
      </div>
    </div>

    <div class="detail-score-bars">
      <h4>Diagnostic score profile</h4>
      ${scoreMetrics.map(([key, label]) => bar(key, label, model[key], "--detail-accent")).join("")}
    </div>

    <div class="failure-list">
      <h4>Failure-mode rates</h4>
      ${failureLabels
        .map(
          ([key, label]) => `
            <div class="failure-row">
              <span>${label}</span>
              <span>${percent(model.failure_modes[key])}</span>
            </div>
          `,
        )
        .join("")}
    </div>

    <div class="results-thesis model-detail-note">
      <strong>95% CI [${formatScore(model.ci95_lower)}, ${formatScore(model.ci95_upper)}]</strong>
      <span>Candidate-output Absolute Fidelity: ${formatScore(model.candidate_terminal_absolute_fidelity)}. Token usage is companion metadata.</span>
    </div>
  `;
}

function bindCards() {
  modelCardGrid.querySelectorAll(".model-card").forEach((card) => {
    card.addEventListener("click", () => {
      const system = card.dataset.system;
      const model = diagnosticsPayload.models.find((item) => item.system === system);
      if (!model) return;
      selectedSystem = model.system;
      modelCardGrid.querySelectorAll(".model-card").forEach((item) => item.classList.remove("is-active"));
      card.classList.add("is-active");
      renderDetail(model);
    });
  });
}

function renderDiagnostics() {
  if (!modelCardGrid || !modelDetailPanel || !diagnosticsPayload) {
    return;
  }

  modelCardGrid.innerHTML = diagnosticsPayload.models.map(renderModelCard).join("");
  const defaultModel =
    diagnosticsPayload.models.find((item) => item.system === selectedSystem) || diagnosticsPayload.models[0];
  selectedSystem = defaultModel.system;
  renderDetail(defaultModel);
  bindCards();
}

async function loadDiagnostics() {
  if (!modelCardGrid || !modelDetailPanel) {
    return;
  }

  try {
    const response = await fetch("data/unified3000_21model_diagnostics.json");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    diagnosticsPayload = await response.json();
    renderDiagnostics();
  } catch (error) {
    modelCardGrid.innerHTML = `<p class="loading-note">Unable to load model diagnostics.</p>`;
    modelDetailPanel.innerHTML = `<p class="loading-note">Unable to load selected-model diagnostics.</p>`;
    console.error("Results diagnostics load failed:", error);
  }
}

loadDiagnostics();
