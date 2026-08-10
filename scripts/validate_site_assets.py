#!/usr/bin/env python3
"""Validate the self-contained Unified-3000 static website release."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GANTT_IDS = ["H2EPR-0346", "H2EPR-0408", "H2EPR-0535", "H2EPR-0900", "H2EPR-0908", "H2EPR-0990"]

REQUIRED_FILES = [
    "index.html",
    "assets/hero/h2epr-benchmark-overview.png",
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
    "assets/diagnostics/evidence-process-gap.png",
    "assets/diagnostics/score-profile-summary.png",
    "assets/diagnostics/domain-quality-dotplot.png",
    "assets/diagnostics/failure-mode-heatmap.png",
    "assets/diagnostics/quality-distribution-by-model.png",
    "assets/diagnostics/valid-only-dumbbell.png",
    "assets/diagnostics/token-quality-scatter.png",
    "data/unified3000_21model_main_results.json",
    "data/unified3000_21model_diagnostics.json",
    "static/js/leaderboard.js",
    "static/js/results-diagnostics.js",
    *[f"assets/gantt/hd/{event_id}_draft_gantt.png" for event_id in GANTT_IDS],
]

REQUIRED_TEXT = [
    "H²EPR-Bench",
    "3,000",
    "11,333",
    "25,814 verified documents",
    "84,693 candidate source records",
    "21",
    "Unified-3000",
    "Background &amp; Motivation",
    "Benchmark Construction",
    "Interactive Explorer",
    "Prediction / Simulation",
    "Key Findings",
    "Results &amp; Diagnostics",
    "best H²EPRScore",
    "Full numeric table",
    "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench",
    "https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold",
    "https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer",
    "https://github.com/AgenticFinLab/H2EPR-Bench",
    *GANTT_IDS,
]

FORBIDDEN_PUBLIC_TEXT = [
    "Core-1000",
    "P1000-",
    "best QualityScore",
    "16 direct reconstruction",
    "1,000 benchmark events",
]

REQUIRED_MODEL_KEYS = {
    "system_id",
    "system",
    "rank",
    "event_count",
    "output_validity_pct",
    "structural_fidelity",
    "temporal_fidelity",
    "causal_fidelity",
    "evidence_fidelity",
    "absolute_fidelity",
    "relative_capability",
    "h2epr_score",
    "ci95_lower",
    "ci95_upper",
    "failure_modes",
}


def validate_local_references(html: str) -> None:
    references = re.findall(r'(?:src|href)="([^"]+)"', html)
    missing: list[str] = []
    for reference in references:
        if reference.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path = ROOT / reference.split("?", 1)[0]
        if not path.exists():
            missing.append(reference)
    if missing:
        raise SystemExit(f"missing local HTML references: {missing}")


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"missing required files: {missing}")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    missing_text = [text for text in REQUIRED_TEXT if text not in html]
    if missing_text:
        raise SystemExit(f"missing required text: {missing_text}")
    forbidden = [text for text in FORBIDDEN_PUBLIC_TEXT if text.lower() in html.lower()]
    if forbidden:
        raise SystemExit(f"stale public wording found: {forbidden}")
    validate_local_references(html)

    rows = json.loads((ROOT / "data/unified3000_21model_main_results.json").read_text(encoding="utf-8"))
    if len(rows) != 21:
        raise SystemExit(f"expected 21 leaderboard rows, found {len(rows)}")
    if [row["rank"] for row in rows] != list(range(1, 22)):
        raise SystemExit("leaderboard ranks are not the complete ordered range 1..21")
    if any(row["event_count"] != 3000 for row in rows):
        raise SystemExit("not every leaderboard row covers 3,000 events")
    malformed = [row.get("system_id", "<unknown>") for row in rows if not REQUIRED_MODEL_KEYS.issubset(row)]
    if malformed:
        raise SystemExit(f"leaderboard rows missing required keys: {malformed}")
    leader = rows[0]
    if leader["system_id"] != "glm-5-1" or not 52.99 <= leader["h2epr_score"] <= 53.01:
        raise SystemExit("unexpected primary leaderboard leader or score")

    diagnostics = json.loads((ROOT / "data/unified3000_21model_diagnostics.json").read_text(encoding="utf-8"))
    meta = diagnostics.get("meta", {})
    models = diagnostics.get("models", [])
    if meta.get("system_count") != 21 or meta.get("events_per_system") != 3000 or meta.get("evaluation_slots") != 63000:
        raise SystemExit("unexpected Unified-3000 diagnostics metadata")
    if models != rows:
        raise SystemExit("diagnostic and leaderboard model rows differ")

    print("Unified-3000 site validation passed")


if __name__ == "__main__":
    main()
