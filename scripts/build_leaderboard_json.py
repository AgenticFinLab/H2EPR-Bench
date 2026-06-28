#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT.parent
    / "EventMycelium"
    / "results"
    / "direct_llm_16model"
    / "tables"
    / "direct_llm_16model_main_results.csv"
)
OUT = ROOT / "data" / "direct_llm_16model_main_results.json"

NUMERIC_FIELDS = {
    "scored_count": int,
    "schema_valid_rate": float,
    "schema_valid_rate_pct": float,
    "QualityScore": float,
    "S_structure": float,
    "S_temporal": float,
    "S_mechanistic": float,
    "S_evidence": float,
}


def convert_row(row):
    converted = {}
    for key, value in row.items():
        if key in NUMERIC_FIELDS:
            converted[key] = NUMERIC_FIELDS[key](value)
        else:
            converted[key] = value
    return converted


def main():
    with SOURCE.open("r", encoding="utf-8", newline="") as f:
        rows = [convert_row(row) for row in csv.DictReader(f)]
    rows.sort(key=lambda row: row["QualityScore"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
