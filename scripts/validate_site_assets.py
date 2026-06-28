#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "index.html",
    "assets/h2epr-overview.png",
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
    "assets/diagnostics/domain-quality-dotplot.png",
    "assets/diagnostics/failure-mode-heatmap.png",
    "data/direct_llm_16model_main_results.json",
]

REQUIRED_TEXT = [
    "H²EPR-Bench",
    "Official scores are computed against gated Gold references.",
    "Dataset summary panel",
    "Example event-process timeline",
    "FinalCascade-derived event timelines across multiple domains.",
    "gantt-hd-gallery",
    "diagnostics-layout",
    "diagnostic-secondary",
    "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench",
    "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold",
    "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer",
    "https://github.com/AgenticFinLab/H2EPR-Bench",
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
    print("site validation passed")


if __name__ == "__main__":
    main()
