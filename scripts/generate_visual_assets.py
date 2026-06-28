#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
AGENTIC_ROOT = ROOT.parent
RESEARCH_ROOT = AGENTIC_ROOT / "EventMycelium-Research"
SUMMARY_DIR = RESEARCH_ROOT / "manifests/v1_1000/release/dataset_card_tables_full1000"
EVENT_CATALOG = RESEARCH_ROOT / "build/hf_release/v1_1000/full1000/data/event_catalog.jsonl"
GANTT_HTML_DIR = (
    RESEARCH_ROOT
    / "build/hf_dataset_repo_staging/eventmycelium-v1_1000-public/visualizations/gantt_full1000_v1/html"
)
PLOTLY_JS = AGENTIC_ROOT / ".venv/lib/python3.12/site-packages/plotly/package_data/plotly.min.js"

SUMMARY_OUTPUT = ROOT / "assets/summary/dataset-summary-panel.png"
GANTT_OUTPUT_DIR = ROOT / "assets/gantt/hd"
GANTT_WORK_DIR = Path("/tmp/h2epr-bench-gantt-export")

WINDOWS_CHROME_CANDIDATES = [
    Path("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path("/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe"),
    Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
]

GANTT_IDS = [
    "P1000-0552",
    "P1000-0346",
    "P1000-0409",
    "P1000-0718",
    "P1000-0536",
    "P1000-0641",
    "P1000-0901",
    "P1000-0909",
    "P1000-0991",
    "P1000-0403",
]

DOMAIN_ALIASES = {
    "Cybersecurity & Tech Governance": "Cyber/Tech",
    "Energy & Environment": "Energy",
    "Finance": "Finance",
    "Military & Geopolitics": "Mil./Geo.",
    "Public Health & Biosecurity": "Health/Bio.",
    "Science & Engineering": "Sci./Eng.",
}

CATEGORY_ALIASES = {
    "Fraud & Financial Misreporting": "Fraud & Misreporting",
    "Institutional Crises & Liquidity Runs": "Institutional Crises",
    "Bubbles & Valuation Collapses": "Bubbles & Valuation",
    "Sovereign, FX & Policy Shocks": "Sovereign FX Stress",
    "Market Manipulation & Trading Disruptions": "Market Manipulation",
    "Corporate Governance, IPOs & M&A": "Corp. Governance",
}

FONT_REGULAR = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")

INK = "#101820"
INK_2 = "#2C3942"
MUTED = "#65717A"
BG = "#F7F9FA"
CARD = "#FFFFFF"
LINE = "#DCE4E6"
ACCENT = "#166B70"
BLUE = "#244E9A"
TEAL = "#1B8A83"
GOLD = "#C28B1D"
CORAL = "#C4583C"
PURPLE = "#6E5AA6"
GREEN = "#4C7A45"
PALETTE = [BLUE, TEAL, GOLD, CORAL, PURPLE, GREEN]
DATE_RE = re.compile(r"(?<!\d)((?:18|19|20)\d{2}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)?)")


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def read_summary(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append((row["value"], int(row["count"])))
    return rows


def read_event_catalog() -> dict[str, dict]:
    events: dict[str, dict] = {}
    for line in EVENT_CATALOG.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        events[row["event_id"]] = row
    return events


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: str,
    max_chars: int,
    line_gap: int = 6,
) -> int:
    x, y = xy
    for line in wrap(text, max_chars):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, radius: int = 18) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 4, y0 + 5, x1 + 4, y1 + 5), radius=radius, fill="#E9EEF2")
    draw.rounded_rectangle(box, radius=radius, fill=CARD, outline=LINE, width=2)


def draw_section_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    draw.text(xy, text.upper(), font=font(17, bold=True), fill=MUTED)


def draw_big_metric(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: str,
    label: str,
    note: str,
    color: str,
) -> None:
    rounded_panel(draw, box)
    x0, y0, _x1, y1 = box
    draw.rectangle((x0, y0, x0 + 10, y1), fill=color)
    draw.text((x0 + 32, y0 + 28), value, font=font(64, bold=True), fill=color)
    draw.text((x0 + 36, y0 + 106), label, font=font(28, bold=True), fill=INK)
    draw_wrapped(draw, (x0 + 36, y0 + 150), note, font(19), MUTED, max_chars=31, line_gap=4)


def draw_tile(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: str,
    label: str,
    color: str,
) -> None:
    rounded_panel(draw, box, radius=15)
    x0, y0, _x1, y1 = box
    draw.rectangle((x0, y0, x0 + 8, y1), fill=color)
    draw.text((x0 + 22, y0 + 13), value, font=font(30, bold=True), fill=color)
    draw_wrapped(draw, (x0 + 22, y0 + 52), label, font(18), INK_2, max_chars=17, line_gap=1)


def draw_domain_donut(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], rows: list[tuple[str, int]]) -> None:
    rounded_panel(draw, box)
    x0, y0, x1, _y1 = box
    draw_section_label(draw, (x0 + 22, y0 + 18), "Domain mix")
    ordered = sorted(rows, key=lambda item: item[1], reverse=True)
    total = sum(count for _, count in ordered)
    cx, cy = x0 + 112, y0 + 142
    radius = 86
    start = -90.0
    for index, (_label, count) in enumerate(ordered):
        extent = 360 * count / total
        draw.pieslice((cx - radius, cy - radius, cx + radius, cy + radius), start, start + extent, fill=PALETTE[index])
        start += extent
    draw.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), fill=CARD, outline=CARD)
    draw.text((cx, cy - 10), "6", font=font(42, bold=True), fill=INK, anchor="mm")
    draw.text((cx, cy + 28), "domains", font=font(17, bold=True), fill=MUTED, anchor="mm")

    lx, ly = x0 + 232, y0 + 65
    for index, (label, count) in enumerate(ordered):
        y = ly + index * 32
        draw.rounded_rectangle((lx, y + 6, lx + 16, y + 22), radius=4, fill=PALETTE[index])
        draw.text((lx + 28, y), DOMAIN_ALIASES.get(label, label), font=font(15, bold=True), fill=INK_2)
        draw.text((x1 - 54, y), str(count), font=font(15), fill=MUTED)


def draw_category_bars(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], rows: list[tuple[str, int]]) -> None:
    rounded_panel(draw, box)
    x0, y0, x1, _y1 = box
    draw_section_label(draw, (x0 + 22, y0 + 18), "Top categories")
    draw.text((x1 - 156, y0 + 18), "26 total", font=font(17, bold=True), fill=CORAL)
    top = sorted(rows, key=lambda item: item[1], reverse=True)[:5]
    max_count = max(count for _, count in top)
    label_x, bar_x = x0 + 24, x0 + 230
    bar_w = x1 - bar_x - 68
    y = y0 + 78
    for index, (label, count) in enumerate(top):
        color = PALETTE[index]
        display = CATEGORY_ALIASES.get(label, label[:23])
        draw.text((label_x, y - 3), display, font=font(16, bold=True), fill=INK_2)
        draw.rounded_rectangle((bar_x, y + 5, bar_x + bar_w, y + 23), radius=8, fill="#E8EDF2")
        fill_w = max(12, int(bar_w * count / max_count))
        draw.rounded_rectangle((bar_x, y + 5, bar_x + fill_w, y + 23), radius=8, fill=color)
        draw.text((bar_x + bar_w + 16, y - 1), str(count), font=font(16, bold=True), fill=MUTED)
        y += 38


def draw_outlet(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=18, fill="#EEF7F6", outline="#CFE1DF", width=2)
    draw.text((x0 + 24, y0 + 18), "Downstream workflows", font=font(19, bold=True), fill=TEAL)
    labels = ["Analysis", "Prediction", "Simulation"]
    widths = [draw.textbbox((0, 0), label, font=font(29, bold=True))[2] for label in labels]
    arrow_w = 62
    total = sum(widths) + arrow_w * 2
    x = x0 + (x1 - x0 - total) // 2
    y = y0 + 72
    cy = y + 18
    for i, label in enumerate(labels):
        draw.text((x, y), label, font=font(29, bold=True), fill=INK)
        x += widths[i]
        if i < len(labels) - 1:
            ax0, ax1 = x + 16, x + arrow_w - 16
            draw.line((ax0, cy, ax1, cy), fill=TEAL, width=4)
            draw.polygon([(ax1, cy), (ax1 - 11, cy - 8), (ax1 - 11, cy + 8)], fill=TEAL)
            x += arrow_w


def generate_summary_panel() -> None:
    domain_rows = read_summary(SUMMARY_DIR / "domain_summary.csv")
    category_rows = read_summary(SUMMARY_DIR / "category_summary.csv")
    canvas = Image.new("RGB", (2400, 920), BG)
    draw = ImageDraw.Draw(canvas)

    draw.text((76, 52), "Core-1000 structured event-process graph release", font=font(52, bold=True), fill=INK)
    draw.text(
        (78, 114),
        "Benchmark-scale event resources for structured reconstruction and downstream event-process research",
        font=font(27),
        fill=MUTED,
    )

    draw_big_metric(
        draw,
        (78, 188, 444, 502),
        "1,000",
        "Event instances",
        "Curated real-world events with fixed evidence contexts and public metadata.",
        BLUE,
    )
    draw_domain_donut(draw, (480, 188, 902, 502), domain_rows)
    draw_category_bars(draw, (938, 188, 1530, 502), category_rows)

    tile_y = 188
    tile_w, tile_h = 190, 106
    tiles = [
        ("3,038", "Stage rows", CORAL),
        ("1,000", "Process graphs", BLUE),
        ("1,000", "Gated Gold refs", TEAL),
        ("16", "LLM baselines", GOLD),
    ]
    tx = 1570
    for i, (value, label, color) in enumerate(tiles):
        draw_tile(draw, (tx + i * (tile_w + 18), tile_y, tx + i * (tile_w + 18) + tile_w, tile_y + tile_h), value, label, color)

    draw_outlet(draw, (1570, 336, 2318, 502))

    lower = (78, 568, 2318, 840)
    rounded_panel(draw, lower)
    draw.text((lower[0] + 32, lower[1] + 28), "Release structure", font=font(25, bold=True), fill=INK)
    columns = [
        ("Public dataset", "Catalog, stage tables, public graph artifacts, Gantt views, schemas, and validation reports.", BLUE),
        ("Gated Gold", "Medium-granularity scoring references for controlled benchmark use.", TEAL),
        ("Explorer", "Interactive browsing for event metadata, stages, timeline views, and public graph summaries.", GOLD),
    ]
    col_w = (lower[2] - lower[0] - 96) // 3
    for i, (title, body, color) in enumerate(columns):
        x0 = lower[0] + 32 + i * (col_w + 32)
        y0 = lower[1] + 86
        draw.rectangle((x0, y0, x0 + 8, y0 + 118), fill=color)
        draw.text((x0 + 24, y0), title, font=font(22, bold=True), fill=color)
        draw_wrapped(draw, (x0 + 24, y0 + 40), body, font(18), INK_2, max_chars=44, line_gap=5)

    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(SUMMARY_OUTPUT)
    print(SUMMARY_OUTPUT)


def wslpath_windows(path: Path) -> str:
    return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()


def find_windows_chrome() -> Path:
    for candidate in WINDOWS_CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No Windows Chrome or Edge executable found under /mnt/c.")


def parse_plotly_datetime(value: str) -> datetime | None:
    candidate = value.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.year < 1800 or parsed.year > 2050:
        return None
    return parsed


def infer_x_range_from_html(html: str) -> tuple[str, str] | None:
    dates = [parsed for match in DATE_RE.finditer(html) if (parsed := parse_plotly_datetime(match.group(1)))]
    if len(dates) < 2:
        return None
    start = min(dates)
    end = max(dates)
    span = end - start
    if span <= timedelta(0):
        span = timedelta(days=30)
    pad = max(span * 0.04, timedelta(days=7))
    pad = min(pad, timedelta(days=180))
    return ((start - pad).isoformat(timespec="seconds"), (end + pad).isoformat(timespec="seconds"))


def prepare_offline_html(source_html: Path, output_html: Path, *, css_width: int, css_height: int) -> tuple[str, str] | None:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLOTLY_JS, output_html.parent / "plotly.min.js")
    html = source_html.read_text(encoding="utf-8")
    x_range = infer_x_range_from_html(html)
    html = html.replace('src="https://cdn.plot.ly/plotly-2.35.2.min.js"', 'src="plotly.min.js"')
    html = html.replace(
        "<head><meta charset=\"utf-8\" /></head>",
        "<head><meta charset=\"utf-8\" /><style>html,body{margin:0;overflow:hidden;background:white;}::-webkit-scrollbar{display:none;}</style></head>",
    )
    html = html.replace(
        'class="plotly-graph-div" style="height:600px; width:100%;"',
        f'class="plotly-graph-div" style="height:{css_height}px; width:{css_width}px;"',
    )
    html = html.replace(
        '<div style="margin-top:12px;padding:8px 0;border-top:1px solid #eee;">',
        '<div style="display:none;margin-top:12px;padding:8px 0;border-top:1px solid #eee;">',
    )
    html = html.replace(
        "<body>",
        f"<body style=\"margin:0; width:{css_width}px; height:{css_height}px; overflow:hidden; background:white;\">",
    )
    html += f"""
<script>
(function stabilizeForExport() {{
  function applyStableSize() {{
    var gd = document.querySelector('.plotly-graph-div');
    if (!gd || !window.Plotly) {{
      window.setTimeout(applyStableSize, 100);
      return;
    }}
    var relayout = {{'width': {css_width}, 'height': {css_height}, 'autosize': false}};
    {"relayout['xaxis.range'] = ['" + x_range[0] + "', '" + x_range[1] + "'];" if x_range else ""}
    Plotly.relayout(gd, relayout).then(function() {{
      gd.style.width = '{css_width}px';
      gd.style.height = '{css_height}px';
      document.body.style.width = '{css_width}px';
      document.body.style.height = '{css_height}px';
    }});
  }}
  if (document.readyState === 'complete') applyStableSize();
  else window.addEventListener('load', applyStableSize);
}})();
</script>
"""
    output_html.write_text(html, encoding="utf-8")
    return x_range


def export_gantt(event_id: str, *, css_width: int, css_height: int, scale_factor: int) -> tuple[Path, tuple[str, str] | None]:
    source = GANTT_HTML_DIR / f"{event_id}_gantt.html"
    if not source.exists():
        raise FileNotFoundError(source)
    work_html = GANTT_WORK_DIR / f"{event_id}_gantt.html"
    x_range = prepare_offline_html(source, work_html, css_width=css_width, css_height=css_height)
    output = GANTT_OUTPUT_DIR / f"{event_id}_gantt_hd.png"
    chrome = find_windows_chrome()
    cmd = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--force-device-scale-factor={scale_factor}",
        f"--window-size={css_width},{css_height}",
        "--virtual-time-budget=7000",
        f"--screenshot={wslpath_windows(output)}",
        wslpath_windows(work_html),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    if x_range:
        print(f"{event_id} export x-range: {x_range[0]} -> {x_range[1]}")
    return output, x_range


def generate_gantt_assets(*, css_width: int, css_height: int, scale_factor: int) -> None:
    events = read_event_catalog()
    metadata: list[dict[str, str | int]] = []
    for event_id in GANTT_IDS:
        output, x_range = export_gantt(event_id, css_width=css_width, css_height=css_height, scale_factor=scale_factor)
        with Image.open(output) as image:
            width, height = image.size
        row = events[event_id]
        metadata.append(
            {
                "event_id": event_id,
                "display_name": row.get("display_name", ""),
                "domain": row.get("domain", ""),
                "event_category": row.get("event_category", ""),
                "source_html": str(GANTT_HTML_DIR / f"{event_id}_gantt.html"),
                "website_file": str(output.relative_to(ROOT)),
                "width": width,
                "height": height,
                "x_range_start": x_range[0] if x_range else "",
                "x_range_end": x_range[1] if x_range else "",
            }
        )
        print(output, width, height)

    manifest = GANTT_OUTPUT_DIR / "gantt_hd_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "event_id",
                "display_name",
                "domain",
                "event_category",
                "source_html",
                "website_file",
                "width",
                "height",
                "x_range_start",
                "x_range_end",
            ],
        )
        writer.writeheader()
        writer.writerows(metadata)
    print(manifest)
    generate_gantt_contact_sheet(metadata)


def generate_gantt_contact_sheet(metadata: list[dict[str, str | int]]) -> None:
    thumb_w, thumb_h = 520, 190
    label_h = 66
    cols = 2
    rows = (len(metadata) + cols - 1) // cols
    pad = 32
    canvas_w = cols * thumb_w + (cols + 1) * pad
    canvas_h = 94 + rows * (thumb_h + label_h + pad) + pad
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 26), "High-resolution Gantt candidates", font=font(34, bold=True), fill=INK)
    draw.text((pad, 65), "Website-ready exports for visual selection", font=font(18), fill=MUTED)

    for index, row in enumerate(metadata):
        col = index % cols
        r = index // cols
        x = pad + col * (thumb_w + pad)
        y = 106 + r * (thumb_h + label_h + pad)
        image_path = ROOT / str(row["website_file"])
        with Image.open(image_path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        draw.rounded_rectangle((x - 2, y - 2, x + thumb_w + 2, y + thumb_h + 2), radius=8, fill="#FFFFFF", outline=LINE, width=2)
        canvas.paste(thumb, (x + (thumb_w - thumb.width) // 2, y + (thumb_h - thumb.height) // 2))
        label_y = y + thumb_h + 10
        draw.text((x, label_y), str(row["event_id"]), font=font(16, bold=True), fill=ACCENT)
        draw_wrapped(draw, (x + 112, label_y), str(row["display_name"]), font(15, bold=True), INK_2, max_chars=46, line_gap=2)

    output = GANTT_OUTPUT_DIR / "gantt_hd_contact_sheet.png"
    canvas.save(output)
    print(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate H2EPR-Bench website visual assets.")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--gantt-only", action="store_true")
    parser.add_argument("--css-width", type=int, default=1800)
    parser.add_argument("--css-height", type=int, default=660)
    parser.add_argument("--scale-factor", type=int, default=2)
    args = parser.parse_args()

    if not args.gantt_only:
        generate_summary_panel()
    if not args.summary_only:
        generate_gantt_assets(css_width=args.css_width, css_height=args.css_height, scale_factor=args.scale_factor)


if __name__ == "__main__":
    main()
