# Results & Diagnostics R1 Design and Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the website Results & Diagnostics section so it communicates the benchmark's evaluation protocol, 16-model direct reconstruction behavior, and diagnostic findings rather than presenting only a leaderboard and static figures.

**Architecture:** R1 keeps the website static and client-side. A small build script merges release-safe aggregate CSVs into one diagnostics JSON file; the page renders framework steps, summary statistics, 16 model trace cards, a selected-model detail panel, diagnostics figures, and the existing sortable leaderboard.

**Tech Stack:** Static HTML/CSS/JavaScript, Python standard library for data preparation, existing PNG assets from release-safe aggregate result folders.

---

## Design Principles

- Results should read as a benchmark diagnostic module, not a generic ranking table.
- Official scoring remains based on the gated Gold references and deterministic graph-matching evaluator.
- Main score diagnostics are QualityScore, schema-valid rate, structure, temporal, mechanistic, evidence, evidence-process gap, valid-only sensitivity, and failure-mode rates.
- Token usage is companion metadata only. It can appear in a secondary panel, but not as a benchmark score.
- The section should take visual inspiration from PortBench-style evaluation traces without copying its layout or language.

## R1 User Experience

### 1. Evaluation Framework

Show a compact horizontal evaluation pipeline:

`Fixed evidence input -> Model graph output -> Schema gate -> Graph matching -> Diagnostic profile`

Each step should have a short label and one sentence. This replaces vague descriptive prose with a concrete evaluation flow.

### 2. Direct Reconstruction Snapshot

Show four metric tiles:

- 16 direct LLM systems.
- 1,000 events per system.
- Best QualityScore = 44.29.
- 13 / 16 systems have schema-valid rate >= 90%.

The accompanying sentence should state the key result: high schema validity does not remove the temporal and mechanistic reconstruction gap.

### 3. Model Trace Cards

Render 16 compact model cards from `data/direct_llm_16model_diagnostics.json`.

Each card includes:

- model name and rank.
- QualityScore.
- schema-valid output rate.
- four mini bars for structure, temporal, mechanistic, and evidence.
- a bottleneck tag based on the lowest process subscore.

Cards should use restrained family accents:

- Doubao: blue.
- DeepSeek: teal.
- GLM: violet.
- Hunyuan / HY / Hy3: green.
- MiniMax: amber.

Clicking a card updates a selected-model detail panel.

### 4. Selected Model Detail Panel

The detail panel should show:

- QualityScore, schema-valid rate, evidence-process gap, and token/event companion value.
- four score bars.
- failure rates for schema invalid, missing primary operation layer, weak temporal, weak mechanistic, and weak evidence.
- valid-only QualityScore delta.

The default selected model should be `Doubao Seed 2.0 Pro`; the panel must also support `DeepSeek-V4-Flash` and all other systems.

### 5. Diagnostic Figures

Reorganize existing figures into three tiers:

- Lead diagnostic: evidence-process gap.
- Paired diagnostics: domain quality dotplot and failure-mode heatmap.
- Companion diagnostics: per-instance quality distribution, valid-only sensitivity, and token-quality scatter.

These figures are not interactive in R1; later versions can add tabs or model-linked figure filtering.

### 6. Full Leaderboard

Keep the existing sortable leaderboard but move it below the model trace and diagnostics. It should serve as the full numeric table, not the primary visual entry point.

## Data Sources

R1 may read only release-safe aggregate assets:

- `EventMycelium/results/direct_llm_16model/tables/direct_llm_16model_main_results.csv`
- `EventMycelium/results/direct_llm_16model/tables/failure_mode_breakdown_16model.csv`
- `EventMycelium/results/direct_llm_16model/tables/evidence_vs_process_gap.csv`
- `EventMycelium/results/direct_llm_16model/tables/valid_only_direct_llm_16model_results.csv`
- `Dataset/freeze905_v1/analysis/full1000/direct_llm_16model_assets/tables/token_quality_scatter_source.csv`

R1 copies only public-safe aggregate PNG figures into website assets:

- `fig_quality_distribution_by_model.png`
- `fig_valid_only_dumbbell.png`
- `fig_token_quality_scatter.png`

No Gold references, raw model outputs, provider traces, internal evidence text, or per-event hidden scoring files should be exposed.

## Implementation Tasks

### Task 1: Data Builder

- [ ] Create `scripts/build_results_diagnostics_data.py`.
- [ ] Merge the release-safe CSV sources above by `system`.
- [ ] Write `data/direct_llm_16model_diagnostics.json`.
- [ ] Include `summary`, `models`, and `source_notes`.
- [ ] Validate that exactly 16 systems are emitted and that every model has main score, failure mode, evidence gap, valid-only, and token companion fields.

### Task 2: Figure Assets

- [ ] Copy the three additional PNG diagnostics into `assets/diagnostics/`.
- [ ] Keep filenames website-facing and descriptive:
  - `quality-distribution-by-model.png`
  - `valid-only-dumbbell.png`
  - `token-quality-scatter.png`

### Task 3: HTML Structure

- [ ] Replace the current Results section with:
  - evaluation framework.
  - snapshot tiles.
  - model trace cards and selected-model detail panel.
  - diagnostics figure grid.
  - full leaderboard.
- [ ] Move `assets/release-boundary.png` back to Benchmark Construction.
- [ ] Remove the Access-section boundary figure.

### Task 4: Styling

- [ ] Add CSS for framework steps, metric tiles, model cards, score bars, detail panel, and balanced diagnostics grid.
- [ ] Keep the section visually consistent with the current refined PortBench-inspired website style.
- [ ] Avoid crowded tables above the fold.

### Task 5: Interaction

- [ ] Create `static/js/results-diagnostics.js`.
- [ ] Fetch `data/direct_llm_16model_diagnostics.json`.
- [ ] Render 16 model cards.
- [ ] Update the detail panel on click.
- [ ] Use accessible button states and no framework dependency.

### Task 6: Validation

- [ ] Update `scripts/validate_site_assets.py` to require the new data file, images, and core Results markup.
- [ ] Run:
  - `python3 scripts/build_results_diagnostics_data.py`
  - `python3 scripts/validate_site_assets.py`
  - `node --check static/js/site.js`
  - `node --check static/js/leaderboard.js`
  - `node --check static/js/results-diagnostics.js`
  - `git diff --check`
- [ ] Start a local server and capture desktop/mobile screenshots for visual review.

## R1 Acceptance Criteria

- Results opens with evaluation logic, not a table.
- Sixteen model cards render from data, not hand-written HTML.
- The selected-model panel updates correctly for at least `Doubao Seed 2.0 Pro`, `DeepSeek-V4-Flash`, `GLM-4.7`, and `MiniMax-M2.5`.
- The release-boundary figure appears in Benchmark Construction.
- Access focuses on links and does not repeat the boundary diagram.
- Validation commands pass.
