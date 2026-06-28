#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "index.html",
    "assets/h2epr-overview.png",
    "assets/usecases/reconstruction.png",
    "assets/usecases/analysis.png",
    "assets/usecases/prediction-simulation.png",
    "assets/usecases/societal-world-model.png",
    "assets/screenshots/explorer.png",
    "assets/release-boundary.png",
    "assets/charts/domain-distribution.png",
    "assets/charts/category-distribution-top12.png",
    "assets/charts/stage-count-distribution.png",
    "assets/summary/dataset-summary-panel.png",
    "assets/gantt/gantt-rajaratnam.png",
    "assets/gantt/gantt-cum-ex.png",
    "assets/gantt/gantt-laiki.png",
    "assets/gantt/hd/P1000-0346_gantt_hd.png",
    "assets/gantt/hd/P1000-0409_gantt_hd.png",
    "assets/gantt/hd/P1000-0536_gantt_hd.png",
    "assets/gantt/hd/P1000-0552_gantt_hd.png",
    "assets/gantt/hd/P1000-0641_gantt_hd.png",
    "assets/gantt/hd/P1000-0901_gantt_hd.png",
    "assets/gantt/hd/P1000-0909_gantt_hd.png",
    "assets/gantt/hd/P1000-0991_gantt_hd.png",
    "assets/gantt/hd/gantt_hd_manifest.csv",
    "assets/diagnostics/evidence-process-gap.png",
    "assets/diagnostics/evidence-process-gap.svg",
    "assets/diagnostics/domain-quality-dotplot.png",
    "assets/diagnostics/failure-mode-heatmap.png",
    "assets/diagnostics/quality-distribution-by-model.png",
    "assets/diagnostics/valid-only-dumbbell.png",
    "assets/diagnostics/token-quality-scatter.png",
    "data/direct_llm_16model_main_results.json",
    "data/direct_llm_16model_diagnostics.json",
    "static/js/results-diagnostics.js",
]

REQUIRED_TEXT = [
    "H²EPR-Bench",
    "Official scores are computed against gated Gold references.",
    "expansion and follow-up studies",
    "Real-world events are not static text objects.",
    "background-primer",
    "background-usecase-switcher",
    "usecase-main-image",
    "data-view=\"reconstruction\"",
    "From simplified event outputs to structured event-process graph reconstruction.",
    "prediction and simulation",
    "Societal world model",
    "Long-term direction: linking structured events into larger market and social-process world models.",
    "Dataset summary panel",
    "Interactive event-process graph browser.",
    "assets/screenshots/explorer.png",
    "Example event-process timeline",
    "FinalCascade-derived event timelines across multiple domains.",
    "gantt-hd-gallery",
    "construction-boundary-figure",
    "evaluation-framework",
    "result-snapshot",
    "model-card-grid",
    "model-detail-panel",
    "diagnostics-layout",
    "diagnostic-secondary",
    "diagnostic-text-card",
    "Valid-only sensitivity",
    "Token use",
    "Full numeric table",
    "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench",
    "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold",
    "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer",
    "https://github.com/AgenticFinLab/H2EPR-Bench",
    "static/js/results-diagnostics.js",
]

FORBIDDEN_TEXT = [
    "EventMycelium-v1_1000",
    "forecasting benchmark",
    "simulation benchmark",
    "RAG benchmark",
    "agent benchmark",
    "They are inspection views, not official scoring references.",
]


def main():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        raise SystemExit(f"missing required files: {missing}")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    missing_text = [text for text in REQUIRED_TEXT if text not in html]
    if missing_text:
        raise SystemExit(f"missing required text: {missing_text}")

    forbidden = [text for text in FORBIDDEN_TEXT if re.search(re.escape(text), html, flags=re.IGNORECASE)]
    if forbidden:
        raise SystemExit(f"forbidden public wording found: {forbidden}")

    rows = json.loads((ROOT / "data/direct_llm_16model_main_results.json").read_text(encoding="utf-8"))
    if len(rows) != 16:
        raise SystemExit(f"expected 16 leaderboard rows, found {len(rows)}")
    diagnostics = json.loads((ROOT / "data/direct_llm_16model_diagnostics.json").read_text(encoding="utf-8"))
    models = diagnostics.get("models", [])
    if diagnostics.get("schema_version") != "h2epr_results_diagnostics_r1":
        raise SystemExit("unexpected diagnostics schema version")
    if len(models) != 16:
        raise SystemExit(f"expected 16 diagnostics models, found {len(models)}")
    required_model_keys = {
        "QualityScore",
        "S_structure",
        "S_temporal",
        "S_mechanistic",
        "S_evidence",
        "failure_modes",
        "evidence_process_gap",
        "valid_only_delta_Q",
        "token_total_k_per_event",
    }
    missing_model_keys = [
        model.get("system", "<unknown>")
        for model in models
        if not required_model_keys.issubset(model)
    ]
    if missing_model_keys:
        raise SystemExit(f"diagnostics models missing required keys: {missing_model_keys}")
    print("site validation passed")


if __name__ == "__main__":
    main()
