#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "EventMycelium/results/direct_llm_16model/tables/evidence_vs_process_gap.csv"
OUTPUT = ROOT / "assets/diagnostics/evidence-process-gap.svg"


def read_rows() -> list[dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sx(value: float) -> float:
    return 96 + (value - 15) / (32 - 15) * 724


def sy(value: float) -> float:
    return 438 - (value - 15) / (88 - 15) * 314


def color(score: float) -> str:
    low = (47, 105, 142)
    high = (218, 174, 64)
    t = max(0.0, min(1.0, (score - 18) / (45 - 18)))
    rgb = tuple(round(low[i] + (high[i] - low[i]) * t) for i in range(3))
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def label_for(system: str) -> str:
    replacements = {
        "Doubao Seed 2.0 Pro": "Doubao Seed 2.0 Pro",
        "DeepSeek-V3.2": "DeepSeek V3.2",
        "MiniMax-M2.7": "MiniMax M2.7",
        "GLM-4.7": "GLM 4.7",
        "MiniMax-M2.5": "MiniMax M2.5",
    }
    return replacements.get(system, system)


def main() -> None:
    rows = read_rows()
    points = []
    for row in rows:
        process = float(row["process_score"])
        evidence = float(row["S_evidence"])
        quality = float(row["QualityScore"])
        valid = float(row["schema_valid_rate_pct"])
        points.append(
            {
                "system": row["system"],
                "process": process,
                "evidence": evidence,
                "quality": quality,
                "valid": valid,
                "x": sx(process),
                "y": sy(evidence),
                "r": 8 + max(0, min(1, (valid - 60) / 40)) * 10,
            }
        )

    label_offsets = {
        "DeepSeek-V3.2": (-82, -46),
        "MiniMax-M2.7": (18, 40),
        "GLM-4.7": (24, -22),
        "MiniMax-M2.5": (20, -12),
    }

    circles = []
    labels = []
    for point in points:
        circles.append(
            f'<circle cx="{point["x"]:.1f}" cy="{point["y"]:.1f}" r="{point["r"]:.1f}" '
            f'fill="{color(point["quality"])}" stroke="#ffffff" stroke-width="2.5">'
            f'<title>{point["system"]}: QualityScore {point["quality"]:.2f}</title></circle>'
        )
        if point["system"] in label_offsets:
            dx, dy = label_offsets[point["system"]]
            x2 = point["x"] + dx
            y2 = point["y"] + dy
            labels.append(
                f'<line x1="{point["x"]:.1f}" y1="{point["y"]:.1f}" x2="{x2 - 6:.1f}" y2="{y2 + 5:.1f}" '
                'stroke="#7b858b" stroke-width="1.2"/>'
            )
            labels.append(
                f'<text x="{x2:.1f}" y="{y2:.1f}" class="label">{label_for(point["system"])}</text>'
            )

    x_ticks = [15, 20, 25, 30]
    y_ticks = [20, 40, 60, 80]
    grid = []
    for tick in x_ticks:
        x = sx(tick)
        grid.append(f'<line x1="{x:.1f}" y1="124" x2="{x:.1f}" y2="438" class="grid"/>')
        grid.append(f'<text x="{x:.1f}" y="468" class="tick" text-anchor="middle">{tick}</text>')
    for tick in y_ticks:
        y = sy(tick)
        grid.append(f'<line x1="96" y1="{y:.1f}" x2="820" y2="{y:.1f}" class="grid"/>')
        grid.append(f'<text x="76" y="{y + 5:.1f}" class="tick" text-anchor="end">{tick}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 560" role="img" aria-labelledby="title desc">
  <title id="title">Evidence retention and process organization in direct reconstruction</title>
  <desc id="desc">Scatter plot comparing evidence score and process organization score for 16 direct reconstruction baselines.</desc>
  <defs>
    <style>
      .title {{ font: 700 30px Georgia, serif; fill: #182323; }}
      .subtitle {{ font: 500 14px sans-serif; fill: #536160; }}
      .axis {{ stroke: #202928; stroke-width: 2.2; }}
      .grid {{ stroke: #e7eeeb; stroke-width: 1.2; }}
      .tick {{ font: 13px sans-serif; fill: #596663; }}
      .axis-label {{ font: 700 15px sans-serif; fill: #24302f; }}
      .label {{ font: 700 14px sans-serif; fill: #293333; }}
      .zone-label {{ font: 700 14px sans-serif; fill: #2d6559; }}
      .note {{ font: 500 13px sans-serif; fill: #5a6765; }}
    </style>
  </defs>
  <rect width="960" height="560" fill="#ffffff"/>
  <text x="64" y="48" class="title">Evidence score vs. process organization</text>
  <text x="64" y="74" class="subtitle">Each point is one direct reconstruction baseline; process organization averages temporal and mechanistic scores.</text>
  <rect x="96" y="124" width="724" height="190" fill="#e8f1ee" opacity="0.78"/>
  <text x="116" y="150" class="zone-label">high evidence, lower process organization</text>
  {"".join(grid)}
  <line x1="96" y1="438" x2="820" y2="438" class="axis"/>
  <line x1="96" y1="124" x2="96" y2="438" class="axis"/>
  {"".join(circles)}
  {"".join(labels)}
  <text x="458" y="522" class="axis-label" text-anchor="middle">Process organization score</text>
  <text x="28" y="282" class="axis-label" text-anchor="middle" transform="rotate(-90 28 282)">Evidence score</text>
  <g transform="translate(850 144)">
    <text x="0" y="0" class="note">QualityScore</text>
    <rect x="0" y="16" width="24" height="130" fill="#2f698e"/>
    <rect x="0" y="16" width="24" height="65" fill="#daa940" opacity="0.9"/>
    <text x="34" y="28" class="tick">high</text>
    <text x="34" y="148" class="tick">low</text>
  </g>
  <text x="96" y="500" class="note">Process organization is the mean of temporal and mechanistic scores. Circle size reflects schema-valid output rate.</text>
</svg>
"""
    OUTPUT.write_text(svg, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
