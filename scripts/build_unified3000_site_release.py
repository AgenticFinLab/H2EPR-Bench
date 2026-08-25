#!/usr/bin/env python3
"""Build the H²EPR-Bench data and chart assets used by the static website."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/h2epr-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_SUMMARY: Path
EVENT_SCORES: Path
DOMAIN_RESULTS: Path
DOMAIN_DISTRIBUTION: Path
CATEGORY_DISTRIBUTION: Path
EVENT_FEATURES: Path
RESOURCE_SUMMARY: Path
ADAPTATION_FAILURES: Path

DATA_DIR = ROOT / "data"
CHART_DIR = ROOT / "assets/charts"
DIAGNOSTIC_DIR = ROOT / "assets/diagnostics"
SUMMARY_OUTPUT = ROOT / "assets/summary/dataset-summary-panel.png"

MATPLOTLIB_FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_REGULAR = MATPLOTLIB_FONTS / "DejaVuSans.ttf"
FONT_BOLD = MATPLOTLIB_FONTS / "DejaVuSans-Bold.ttf"

INK = "#152323"
INK_2 = "#30403F"
MUTED = "#687674"
BG = "#F7F9FA"
CARD = "#FFFFFF"
LINE = "#DCE4E6"
BLUE = "#2F698E"
TEAL = "#1A7F72"
GOLD = "#C28B1D"
CORAL = "#C4583C"
PURPLE = "#7557A6"
GREEN = "#4C7A45"
PALETTE = [BLUE, TEAL, GOLD, CORAL, PURPLE, GREEN]


def configure_source_root(source_root: Path) -> None:
    """Bind the approved private aggregate source tree named by the operator."""

    resolved = source_root.expanduser().resolve()
    paper_assets = resolved / "paper" / "AAAI_assets"
    supplement = (
        resolved
        / "paper"
        / "supplementary_aaai27"
        / "code_data_package"
        / "h2epr_bench_anonymous"
        / "data"
    )
    sources = {
        "SYSTEM_SUMMARY": paper_assets / "02_主实验结果/表/system_summary_v7.csv",
        "EVENT_SCORES": supplement / "results/main/event_level_scores.csv",
        "DOMAIN_RESULTS": paper_assets / "02_主实验结果/表/domain_summary_v7.csv",
        "DOMAIN_DISTRIBUTION": paper_assets / "01_基准与Gold统计/表/domain_distribution_v1.csv",
        "CATEGORY_DISTRIBUTION": paper_assets
        / "01_基准与Gold统计/表/category_distribution_v1.csv",
        "EVENT_FEATURES": paper_assets / "09_补充源表/event_features_v1.csv",
        "RESOURCE_SUMMARY": paper_assets
        / "08_成本效率与失败分析/表/directllm_system_resource_summary_v1.csv",
        "ADAPTATION_FAILURES": paper_assets
        / "08_成本效率与失败分析/表/adaptation_failures_by_system_v1.csv",
    }
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise SystemExit(f"approved source root is missing required aggregate inputs: {missing}")
    globals().update(sources)

DISPLAY_NAMES = {
    "deepseek-v3-2": "DeepSeek V3.2",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-v4-pro-202606": "DeepSeek V4 Pro",
    "doubao-seed-1-8": "Doubao Seed 1.8",
    "doubao-seed-2-0-lite": "Doubao Seed 2.0 Lite",
    "doubao-seed-2-0-mini": "Doubao Seed 2.0 Mini",
    "doubao-seed-2-0-pro": "Doubao Seed 2.0 Pro",
    "doubao-seed-2-1-pro": "Doubao Seed 2.1 Pro",
    "doubao-seed-2-1-turbo": "Doubao Seed 2.1 Turbo",
    "glm-4-7": "GLM-4.7",
    "glm-5": "GLM-5",
    "glm-5-1": "GLM-5.1",
    "glm-5-2": "GLM-5.2",
    "hy3": "Hunyuan 3",
    "hy3-preview": "Hunyuan 3 Preview",
    "kimi-k3": "Kimi K3",
    "minimax-m2-5": "MiniMax M2.5",
    "minimax-m2-7": "MiniMax M2.7",
    "minimax-m3": "MiniMax M3",
    "qwen3-5-flash": "Qwen 3.5 Flash",
    "qwen3-5-plus": "Qwen 3.5 Plus",
}

FAMILY_NAMES = {
    "deepseek": "DeepSeek",
    "doubao": "Doubao",
    "glm": "GLM",
    "hy3": "Hunyuan",
    "kimi": "Kimi",
    "minimax": "MiniMax",
    "qwen": "Qwen",
}

FAMILY_COLORS = {
    "DeepSeek": BLUE,
    "Doubao": CORAL,
    "GLM": TEAL,
    "Hunyuan": GREEN,
    "Kimi": PURPLE,
    "MiniMax": GOLD,
    "Qwen": "#3A77B8",
}

DOMAIN_ALIASES = {
    "Cybersecurity & Tech Governance": "Cybersecurity & Tech",
    "Energy & Environment": "Energy & Environment",
    "Finance": "Finance",
    "Military & Geopolitics": "Military & Geopolitics",
    "Public Health & Biosecurity": "Public Health & Biosecurity",
    "Science & Engineering": "Science & Engineering",
}

SUMMARY_DOMAIN_ALIASES = {
    "Cybersecurity & Tech Governance": "Cyber/Tech",
    "Energy & Environment": "Energy/Env.",
    "Finance": "Finance",
    "Military & Geopolitics": "Military/Geo.",
    "Public Health & Biosecurity": "Health/Bio.",
    "Science & Engineering": "Science/Eng.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def family_for(system_id: str) -> str:
    for prefix, family in FAMILY_NAMES.items():
        if system_id.startswith(prefix):
            return family
    return "Other"


def number(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    return float(value) if value not in {"", None} else default


def build_result_data() -> list[dict[str, object]]:
    resources = {row["system_id"]: row for row in read_csv(RESOURCE_SUMMARY)}
    failures: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv(ADAPTATION_FAILURES):
        failures[row["system_id"]][row["failure_code"]] = 100 * float(row["rate_within_system"])

    rows: list[dict[str, object]] = []
    for source in sorted(read_csv(SYSTEM_SUMMARY), key=lambda item: int(item["rank"])):
        system_id = source["system_id"]
        family = family_for(system_id)
        resource = resources.get(system_id, {})
        dimensions = {
            "structural_fidelity": number(source, "structural_fidelity"),
            "temporal_fidelity": number(source, "temporal_fidelity"),
            "causal_fidelity": number(source, "causal_fidelity"),
            "evidence_fidelity": number(source, "evidence_fidelity"),
        }
        bottleneck_key = min(dimensions, key=dimensions.get)
        bottleneck_label = {
            "structural_fidelity": "Structural",
            "temporal_fidelity": "Temporal",
            "causal_fidelity": "Causal",
            "evidence_fidelity": "Evidence",
        }[bottleneck_key]
        process_mean = np.mean(
            [dimensions["structural_fidelity"], dimensions["temporal_fidelity"], dimensions["causal_fidelity"]]
        )
        rows.append(
            {
                "system_id": system_id,
                "system": DISPLAY_NAMES.get(system_id, system_id),
                "short_name": DISPLAY_NAMES.get(system_id, system_id),
                "family": family,
                "accent": FAMILY_COLORS.get(family, BLUE),
                "rank": int(source["rank"]),
                "event_count": int(source["event_count"]),
                "candidate_terminal_count": int(source["candidate_terminal_count"]),
                "output_validity_pct": 100 * number(source, "output_validity"),
                "evaluator_valid_graph_count": int(source["evaluator_valid_graph_count"]),
                **dimensions,
                "absolute_fidelity": number(source, "Absolute_Fidelity"),
                "relative_capability": number(source, "Relative_Capability"),
                "h2epr_score": number(source, "Discriminative_H2EPRScore"),
                "candidate_terminal_absolute_fidelity": number(source, "Candidate_Terminal_Absolute_Fidelity"),
                "ci95_lower": number(source, "H2EPRScore_ci95_lower"),
                "ci95_upper": number(source, "H2EPRScore_ci95_upper"),
                "process_organization": float(process_mean),
                "evidence_process_gap": dimensions["evidence_fidelity"] - float(process_mean),
                "mean_tokens_per_event": number(resource, "mean_total_tokens_observed_slot"),
                "bottleneck": f"{bottleneck_label} bottleneck ({dimensions[bottleneck_key]:.1f})",
                "failure_modes": {
                    key: failures[system_id].get(key, 0.0)
                    for key in [
                        "invalid_json",
                        "old_schema_invalid",
                        "unresolved_relation_endpoint",
                        "unknown_evidence_source",
                        "unsupported_response_envelope",
                    ]
                },
            }
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "unified3000_21model_main_results.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    nonempty = [row for row in rows if row["candidate_terminal_count"]]
    payload = {
        "meta": {
            "release": "H²EPR-Bench",
            "system_count": 21,
            "events_per_system": 3000,
            "evaluation_slots": 63000,
            "primary_threshold": 0.18,
            "score": "H²EPRScore",
            "nonempty_system_count": len(nonempty),
        },
        "models": rows,
        "notes": [
            "All 63,000 model-event slots remain in the official results.",
            "Output validity is reported separately from reconstruction fidelity.",
            "H2EPRScore combines absolute fidelity with roster-conditional relative capability.",
        ],
    }
    (DATA_DIR / "unified3000_21model_diagnostics.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return rows


def plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#283836",
            "axes.labelcolor": "#283836",
            "axes.titlecolor": INK,
            "xtick.color": "#536160",
            "ytick.color": "#536160",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.grid": True,
            "grid.color": "#E4ECE9",
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
        }
    )


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close()


def build_dataset_charts() -> None:
    plot_style()
    domains = sorted(read_csv(DOMAIN_DISTRIBUTION), key=lambda row: int(row["event_count"]))
    labels = [DOMAIN_ALIASES[row["domain"]] for row in domains]
    values = [int(row["event_count"]) for row in domains]
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    bars = ax.barh(labels, values, color=PALETTE[: len(values)])
    ax.set_title("H²EPR-Bench domain distribution", loc="left", fontsize=17, fontweight="bold")
    ax.set_xlabel("Events")
    ax.bar_label(bars, padding=5, fontsize=10)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", visible=False)
    save_figure(CHART_DIR / "domain-distribution.png")

    categories = sorted(read_csv(CATEGORY_DISTRIBUTION), key=lambda row: int(row["event_count"]), reverse=True)[:12]
    categories.reverse()
    labels = [row["category"] for row in categories]
    values = [int(row["event_count"]) for row in categories]
    fig, ax = plt.subplots(figsize=(10.2, 6.3))
    bars = ax.barh(labels, values, color=TEAL)
    ax.set_title("Largest event categories", loc="left", fontsize=17, fontweight="bold")
    ax.set_xlabel("Events (top 12 of 26 categories)")
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", visible=False)
    save_figure(CHART_DIR / "category-distribution-top12.png")

    features = read_csv(EVENT_FEATURES)
    stage_counts = [int(row["stage_count"]) for row in features]
    bins = np.arange(0.5, max(stage_counts) + 1.5, 1)
    fig, ax = plt.subplots(figsize=(8.3, 4.8))
    counts, _, patches = ax.hist(stage_counts, bins=bins, color=BLUE, rwidth=0.82)
    ax.set_title("Reference EPG stage counts", loc="left", fontsize=17, fontweight="bold")
    ax.set_xlabel("Stages per event")
    ax.set_ylabel("Events")
    ax.set_xticks(range(1, max(stage_counts) + 1))
    for count, patch in zip(counts, patches):
        if count:
            ax.text(patch.get_x() + patch.get_width() / 2, count + max(counts) * 0.015, f"{int(count)}", ha="center", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(CHART_DIR / "stage-count-distribution.png")


def build_diagnostic_charts(rows: list[dict[str, object]]) -> None:
    plot_style()
    by_system = {str(row["system_id"]): row for row in rows}
    system_order = [str(row["system_id"]) for row in rows]

    event_scores: dict[str, list[float]] = defaultdict(list)
    for row in read_csv(EVENT_SCORES):
        event_scores[row["system_id"]].append(float(row["absolute_event_fidelity"]))
    fig, ax = plt.subplots(figsize=(12.3, 14.2))
    for index, system_id in enumerate(system_order):
        values = np.sort(np.asarray(event_scores[system_id], dtype=float))
        y = np.full_like(values, index, dtype=float) + np.linspace(-0.25, 0.25, len(values))
        ax.plot(values, y, color=str(by_system[system_id]["accent"]), alpha=0.72, linewidth=1.1)
        ax.scatter([np.mean(values)], [index], color=INK, s=17, zorder=3)
    ax.set_yticks(range(len(system_order)), [str(by_system[key]["short_name"]) for key in system_order])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Event-level Absolute Fidelity")
    ax.set_title("Reconstruction fidelity across 3,000 events", loc="left", fontsize=18, fontweight="bold")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    save_figure(DIAGNOSTIC_DIR / "quality-distribution-by-model.png")

    nonempty = [row for row in rows if int(row["candidate_terminal_count"]) > 0]
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    for row in nonempty:
        size = 35 + float(row["output_validity_pct"]) * 0.9
        ax.scatter(
            float(row["process_organization"]),
            float(row["evidence_fidelity"]),
            s=size,
            color=str(row["accent"]),
            alpha=0.82,
            edgecolor="white",
            linewidth=1.1,
        )
        if int(row["rank"]) <= 5:
            ax.annotate(str(row["short_name"]), (float(row["process_organization"]), float(row["evidence_fidelity"])), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Process organization (mean structural, temporal, causal fidelity)")
    ax.set_ylabel("Evidence fidelity")
    ax.set_title("Evidence retention vs. process organization", loc="left", fontsize=17, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(DIAGNOSTIC_DIR / "evidence-process-gap.png")

    dimensions = [
        ("Evidence", "evidence_fidelity", BLUE),
        ("Temporal", "temporal_fidelity", PURPLE),
        ("Structural", "structural_fidelity", TEAL),
        ("Causal", "causal_fidelity", GOLD),
    ]
    means = [np.mean([float(row[key]) for row in nonempty]) for _, key, _ in dimensions]
    fig, ax = plt.subplots(figsize=(8.9, 4.6))
    bars = ax.barh([label for label, _, _ in dimensions], means, color=[color for _, _, color in dimensions])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Mean fidelity across 20 systems with valid graph output")
    ax.set_title("Average diagnostic profile", loc="left", fontsize=17, fontweight="bold")
    ax.bar_label(bars, fmt="%.1f", padding=5)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", visible=False)
    save_figure(DIAGNOSTIC_DIR / "score-profile-summary.png")

    domain_rows = read_csv(DOMAIN_RESULTS)
    domains = list(dict.fromkeys(row["domain"] for row in domain_rows))
    fig, ax = plt.subplots(figsize=(11.0, 6.0))
    rng = np.random.default_rng(7)
    for index, domain in enumerate(domains):
        values = [float(row["Discriminative_H2EPRScore"]) for row in domain_rows if row["domain"] == domain]
        jitter = rng.uniform(-0.13, 0.13, len(values))
        ax.scatter(np.full(len(values), index) + jitter, values, color=PALETTE[index], alpha=0.65, s=24)
        ax.scatter([index], [np.mean(values)], color=INK, marker="D", s=48, zorder=3)
    ax.set_xticks(range(len(domains)), [DOMAIN_ALIASES[domain] for domain in domains], rotation=18, ha="right")
    ax.set_ylabel("Discriminative H2EPRScore")
    ax.set_title("System performance across domains", loc="left", fontsize=17, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(DIAGNOSTIC_DIR / "domain-quality-dotplot.png")

    failure_keys = [
        "invalid_json",
        "old_schema_invalid",
        "unresolved_relation_endpoint",
        "unknown_evidence_source",
        "unsupported_response_envelope",
    ]
    failure_labels = ["Invalid JSON", "Schema mismatch", "Relation endpoint", "Evidence source", "Response envelope"]
    matrix = np.array([[float(row["failure_modes"][key]) for key in failure_keys] for row in rows])
    fig, ax = plt.subplots(figsize=(12.6, 9.6))
    image = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=max(25, np.percentile(matrix, 95)))
    ax.set_xticks(range(len(failure_labels)), failure_labels, rotation=20, ha="right")
    ax.set_yticks(range(len(rows)), [str(row["short_name"]) for row in rows])
    ax.set_title("Output adaptation failure rates", loc="left", fontsize=17, fontweight="bold")
    cbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Rate within system (%)")
    ax.grid(False)
    save_figure(DIAGNOSTIC_DIR / "failure-mode-heatmap.png")

    fig, ax = plt.subplots(figsize=(11.7, 9.0))
    y = np.arange(len(rows))
    absolute = np.array([float(row["absolute_fidelity"]) for row in rows])
    candidate = np.array([float(row["candidate_terminal_absolute_fidelity"]) for row in rows])
    for index in range(len(rows)):
        ax.plot([absolute[index], candidate[index]], [index, index], color="#B7C4C1", linewidth=2)
    ax.scatter(absolute, y, color=BLUE, label="All 3,000 slots", s=36)
    ax.scatter(candidate, y, color=GOLD, label="Candidate-output fidelity", s=36)
    ax.set_yticks(y, [str(row["short_name"]) for row in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Absolute Fidelity")
    ax.set_title("All-slot and candidate-output fidelity", loc="left", fontsize=17, fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", visible=False)
    save_figure(DIAGNOSTIC_DIR / "valid-only-dumbbell.png")

    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    for row in rows:
        ax.scatter(
            float(row["mean_tokens_per_event"]) / 1000,
            float(row["h2epr_score"]),
            color=str(row["accent"]),
            s=55,
            alpha=0.82,
            edgecolor="white",
        )
        if int(row["rank"]) <= 5 or str(row["system_id"]) == "minimax-m3":
            ax.annotate(str(row["short_name"]), (float(row["mean_tokens_per_event"]) / 1000, float(row["h2epr_score"])), xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Observed tokens per event (thousands)")
    ax.set_ylabel("Discriminative H2EPRScore")
    ax.set_title("Token use and reconstruction performance", loc="left", fontsize=17, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(DIAGNOSTIC_DIR / "token-quality-scatter.png")


def image_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int = 18) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 4, y0 + 5, x1 + 4, y1 + 5), radius=radius, fill="#E9EEF2")
    draw.rounded_rectangle(box, radius=radius, fill=CARD, outline=LINE, width=2)


def build_summary_panel() -> None:
    domains = sorted(read_csv(DOMAIN_DISTRIBUTION), key=lambda row: int(row["event_count"]), reverse=True)
    categories = sorted(read_csv(CATEGORY_DISTRIBUTION), key=lambda row: int(row["event_count"]), reverse=True)[:5]
    canvas = Image.new("RGB", (2400, 920), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((76, 52), "H²EPR-Bench", font=image_font(52, bold=True), fill=INK)
    draw.text((78, 116), "Evidence-traceable evaluation of how complex events unfold", font=image_font(27), fill=MUTED)

    rounded_panel(draw, (78, 188, 444, 502))
    draw.rectangle((78, 188, 88, 502), fill=BLUE)
    draw.text((112, 220), "3,000", font=image_font(64, bold=True), fill=BLUE)
    draw.text((116, 302), "Event instances", font=image_font(28, bold=True), fill=INK)
    draw.multiline_text((116, 352), "Real-world events with fixed\nevidence contexts and\ncanonical public IDs.", font=image_font(19), fill=MUTED, spacing=6)

    rounded_panel(draw, (480, 188, 902, 502))
    draw.text((504, 210), "DOMAIN MIX", font=image_font(17, bold=True), fill=MUTED)
    total = sum(int(row["event_count"]) for row in domains)
    cx, cy, radius, start = 592, 342, 84, -90
    for index, row in enumerate(domains):
        extent = 360 * int(row["event_count"]) / total
        draw.pieslice((cx - radius, cy - radius, cx + radius, cy + radius), start, start + extent, fill=PALETTE[index])
        start += extent
    draw.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), fill=CARD)
    draw.text((cx, cy - 10), "6", font=image_font(42, bold=True), fill=INK, anchor="mm")
    draw.text((cx, cy + 28), "domains", font=image_font(17, bold=True), fill=MUTED, anchor="mm")
    for index, row in enumerate(domains):
        y = 256 + index * 34
        draw.rounded_rectangle((704, y + 4, 720, y + 20), radius=4, fill=PALETTE[index])
        label = SUMMARY_DOMAIN_ALIASES[row["domain"]]
        draw.text((732, y), label, font=image_font(14, bold=True), fill=INK_2)
        draw.text((878, y), row["event_count"], font=image_font(14), fill=MUTED, anchor="ra")

    rounded_panel(draw, (938, 188, 1530, 502))
    draw.text((962, 210), "TOP CATEGORIES", font=image_font(17, bold=True), fill=MUTED)
    draw.text((1382, 210), "26 total", font=image_font(17, bold=True), fill=CORAL)
    max_count = max(int(row["event_count"]) for row in categories)
    for index, row in enumerate(categories):
        y = 270 + index * 42
        label = row["category"]
        if len(label) > 25:
            label = label[:23] + "…"
        draw.text((962, y), label, font=image_font(15, bold=True), fill=INK_2)
        x0, width = 1230, 220
        draw.rounded_rectangle((x0, y + 4, x0 + width, y + 20), radius=8, fill="#E8EDF2")
        fill = max(12, int(width * int(row["event_count"]) / max_count))
        draw.rounded_rectangle((x0, y + 4, x0 + fill, y + 20), radius=8, fill=PALETTE[index])
        draw.text((1472, y), row["event_count"], font=image_font(15), fill=MUTED)

    tiles = [
        ("11,333", "Stages", CORAL),
        ("104,027", "Graph nodes", BLUE),
        ("3,000", "Reference EPGs", TEAL),
        ("21", "LLM systems", GOLD),
    ]
    for index, (value, label, color) in enumerate(tiles):
        x = 1570 + index * 208
        rounded_panel(draw, (x, 188, x + 190, 294), radius=15)
        draw.rectangle((x, 188, x + 8, 294), fill=color)
        draw.text((x + 22, 202), value, font=image_font(30, bold=True), fill=color)
        draw.text((x + 22, 252), label, font=image_font(17, bold=True), fill=INK_2)

    rounded_panel(draw, (1570, 336, 2318, 502))
    draw.text((1594, 354), "Research directions", font=image_font(19, bold=True), fill=TEAL)
    draw.text((1700, 418), "Analysis  →  Prediction  →  Simulation", font=image_font(29, bold=True), fill=INK)

    rounded_panel(draw, (78, 568, 2318, 840))
    draw.text((110, 596), "Benchmark ecosystem", font=image_font(25, bold=True), fill=INK)
    columns = [
        ("Public Dataset", "Catalog, 3,000 Draft EPGs, stage views, timelines, schemas, and manifests.", BLUE),
        ("Reference EPGs", "3,000 expert-finalized graphs for official benchmark scoring.", TEAL),
        ("Event Explorer", "Interactive browsing for event metadata, timelines, and graph summaries.", GOLD),
    ]
    for index, (title, body, color) in enumerate(columns):
        x = 110 + index * 736
        draw.rectangle((x, 654, x + 8, 778), fill=color)
        draw.text((x + 24, 654), title, font=image_font(22, bold=True), fill=color)
        words, lines, current = body.split(), [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 48:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
        draw.multiline_text((x + 24, 700), "\n".join(lines), font=image_font(18), fill=INK_2, spacing=6)

    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(SUMMARY_OUTPUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="approved source tree containing the public aggregate release inputs",
    )
    args = parser.parse_args()
    configure_source_root(args.source_root)
    for path in [DATA_DIR, CHART_DIR, DIAGNOSTIC_DIR, SUMMARY_OUTPUT.parent]:
        path.mkdir(parents=True, exist_ok=True)
    rows = build_result_data()
    build_dataset_charts()
    build_diagnostic_charts(rows)
    build_summary_panel()
    print("Built H²EPR-Bench website data and visual assets.")


if __name__ == "__main__":
    main()
