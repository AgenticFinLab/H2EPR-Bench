const modelCardGrid = document.querySelector("#model-card-grid");
const modelDetailPanel = document.querySelector("#model-detail-panel");

let diagnosticsPayload = null;
let selectedSystem = "Doubao Seed 2.0 Pro";

const scoreMetrics = [
  ["S_structure", "Struct"],
  ["S_temporal", "Temp"],
  ["S_mechanistic", "Mech"],
  ["S_evidence", "Evid"],
];

const failureLabels = [
  ["schema_invalid", "Schema invalid"],
  ["primary_missing_operation", "Primary operation missing"],
  ["weak_temporal", "Weak temporal"],
  ["weak_mechanistic", "Weak mechanistic"],
  ["weak_evidence", "Weak evidence"],
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
          <strong>${formatScore(model.QualityScore)}</strong>
          <span>QualityScore</span>
        </div>
        <div>
          <strong>${percent(model.schema_valid_rate_pct)}</strong>
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
        <strong>${formatScore(model.QualityScore)}</strong>
        <span>QualityScore</span>
      </div>
      <div>
        <strong>${percent(model.schema_valid_rate_pct)}</strong>
        <span>Valid outputs</span>
      </div>
      <div>
        <strong>${formatScore(model.evidence_process_gap)}</strong>
        <span>Evidence-process gap</span>
      </div>
      <div>
        <strong>${formatScore(model.token_total_k_per_event, 1)}k</strong>
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
      <strong>Valid-only Q ${formatScore(model.valid_only_Q)}</strong>
      <span>Delta over all-instance scoring: +${formatScore(model.valid_only_delta_Q)}. Token usage is companion metadata.</span>
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
    const response = await fetch("data/direct_llm_16model_diagnostics.json");
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
