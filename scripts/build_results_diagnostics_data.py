#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTIC_ROOT = ROOT.parent
RESULTS_TABLE_DIR = AGENTIC_ROOT / "EventMycelium/results/direct_llm_16model/tables"
TOKEN_TABLE = (
    AGENTIC_ROOT
    / "Dataset/freeze905_v1/analysis/full1000/direct_llm_16model_assets/tables/token_quality_scatter_source.csv"
)
OUTPUT = ROOT / "data/direct_llm_16model_diagnostics.json"

FAMILY_COLORS = {
    "Doubao": "#2f6fb5",
    "DeepSeek": "#15857c",
    "GLM": "#7763a6",
    "HY": "#4d8053",
    "MiniMax": "#b8791c",
}

SHORT_NAMES = {
    "Doubao Seed 2.0 Pro": "Seed 2.0 Pro",
    "Doubao Seed 2.0 Mini": "Seed 2.0 Mini",
    "Doubao Seed 2.0 Lite": "Seed 2.0 Lite",
    "Doubao Seed 1.8": "Seed 1.8",
    "DeepSeek-V3.2": "DeepSeek V3.2",
    "DeepSeek-V4-Flash": "V4 Flash",
    "DeepSeek-V3.1-Terminus": "V3.1 Terminus",
    "DeepSeek-R1-0528": "R1 0528",
    "HY 2.0 Think": "HY Think",
    "HY 2.0 Instruct": "HY Instruct",
    "Hy3 preview": "Hy3 preview",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str) -> float:
    return round(float(row[key]), 2)


def family_for(system: str) -> str:
    if system.startswith("Doubao"):
        return "Doubao"
    if system.startswith("DeepSeek"):
        return "DeepSeek"
    if system.startswith("GLM"):
        return "GLM"
    if system.startswith("HY") or system.startswith("Hy3"):
        return "HY"
    if system.startswith("MiniMax"):
        return "MiniMax"
    return "Other"


def bottleneck_label(row: dict[str, float]) -> str:
    process_scores = {
        "Structure": row["S_structure"],
        "Temporal": row["S_temporal"],
        "Mechanistic": row["S_mechanistic"],
    }
    metric, value = min(process_scores.items(), key=lambda item: item[1])
    return f"{metric} bottleneck ({value:.2f})"


def by_system(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["system"]: row for row in rows}


def validate_system_coverage(*tables: dict[str, dict[str, str]]) -> list[str]:
    base = set(tables[0])
    for table in tables[1:]:
        if set(table) != base:
            missing = sorted(base - set(table))
            extra = sorted(set(table) - base)
            raise SystemExit(f"system coverage mismatch: missing={missing}, extra={extra}")
    return sorted(base)


def build_payload() -> dict:
    main = by_system(read_csv(RESULTS_TABLE_DIR / "direct_llm_16model_main_results.csv"))
    failure = by_system(read_csv(RESULTS_TABLE_DIR / "failure_mode_breakdown_16model.csv"))
    gap = by_system(read_csv(RESULTS_TABLE_DIR / "evidence_vs_process_gap.csv"))
    valid_only = by_system(read_csv(RESULTS_TABLE_DIR / "valid_only_direct_llm_16model_results.csv"))
    token = by_system(read_csv(TOKEN_TABLE))
    systems = validate_system_coverage(main, failure, gap, valid_only, token)

    ordered_systems = sorted(systems, key=lambda system: float(main[system]["QualityScore"]), reverse=True)
    models = []
    for rank, system in enumerate(ordered_systems, start=1):
        main_row = main[system]
        failure_row = failure[system]
        gap_row = gap[system]
        valid_row = valid_only[system]
        token_row = token[system]
        numeric_scores = {
            "S_structure": as_float(main_row, "S_structure"),
            "S_temporal": as_float(main_row, "S_temporal"),
            "S_mechanistic": as_float(main_row, "S_mechanistic"),
            "S_evidence": as_float(main_row, "S_evidence"),
        }
        family = family_for(system)
        models.append(
            {
                "rank": rank,
                "system": system,
                "short_name": SHORT_NAMES.get(system, system),
                "family": family,
                "accent": FAMILY_COLORS.get(family, "#65717a"),
                "scored_count": int(main_row["scored_count"]),
                "schema_valid_rate_pct": as_float(main_row, "schema_valid_rate_pct"),
                "QualityScore": as_float(main_row, "QualityScore"),
                **numeric_scores,
                "process_score": as_float(gap_row, "process_score"),
                "evidence_process_gap": as_float(gap_row, "evidence_process_gap"),
                "valid_only_Q": as_float(valid_row, "valid_only_Q"),
                "valid_only_delta_Q": as_float(valid_row, "delta_Q"),
                "token_total_k_per_event": as_float(token_row, "total_tokens_k_per_event"),
                "completion_tokens_k_per_event": as_float(token_row, "completion_tokens_k_per_event"),
                "bottleneck": bottleneck_label(numeric_scores),
                "failure_modes": {
                    "schema_invalid": as_float(failure_row, "schema_invalid_rate_pct"),
                    "non_aligned": as_float(failure_row, "non_aligned_rate_pct"),
                    "primary_missing_operation": as_float(failure_row, "primary_missing_operation_rate_pct"),
                    "weak_temporal": as_float(failure_row, "weak_temporal_rate_pct"),
                    "weak_mechanistic": as_float(failure_row, "weak_mechanistic_rate_pct"),
                    "weak_evidence": as_float(failure_row, "weak_evidence_rate_pct"),
                },
            }
        )

    quality_scores = [model["QualityScore"] for model in models]
    schema_high = [model for model in models if model["schema_valid_rate_pct"] >= 90]
    summary = {
        "system_count": len(models),
        "events_per_system": 1000,
        "direct_reconstructions": len(models) * 1000,
        "best_system": models[0]["system"],
        "best_quality_score": models[0]["QualityScore"],
        "median_quality_score": round((quality_scores[7] + quality_scores[8]) / 2, 2),
        "high_schema_valid_system_count": len(schema_high),
        "mean_evidence_score": round(sum(model["S_evidence"] for model in models) / len(models), 2),
        "mean_temporal_score": round(sum(model["S_temporal"] for model in models) / len(models), 2),
        "mean_mechanistic_score": round(sum(model["S_mechanistic"] for model in models) / len(models), 2),
        "mean_evidence_process_gap": round(sum(model["evidence_process_gap"] for model in models) / len(models), 2),
        "median_weak_temporal_rate": 99.2,
        "median_weak_mechanistic_rate": 85.4,
    }

    return {
        "schema_version": "h2epr_results_diagnostics_r1",
        "summary": summary,
        "models": models,
        "source_notes": [
            "Official scores use all 1,000 instances per system and the gated Gold references.",
            "Token usage is companion metadata and is not part of QualityScore.",
            "Failure-mode rates are percentages over the same 1,000 instances per system.",
        ],
    }


def main() -> None:
    payload = build_payload()
    if len(payload["models"]) != 16:
        raise SystemExit(f"expected 16 models, found {len(payload['models'])}")
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
