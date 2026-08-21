---
pretty_name: "H²EPR-Bench"
language:
- en
license: cc-by-nc-4.0
task_categories:
- text-generation
- other
tags:
- event-understanding
- benchmark
- event-process-reconstruction
- evidence-grounded
- graph-structured-data
- temporal-reasoning
- causal-reasoning
- llm-evaluation
size_categories:
- 1K<n<10K
configs:
- config_name: event_gallery
  data_files:
  - split: benchmark
    path: data/viewer_mirrors/event_gallery.parquet
- config_name: event_catalog
  data_files:
  - split: benchmark
    path: data/viewer_mirrors/event_catalog.parquet
- config_name: event_instances
  data_files:
  - split: benchmark
    path: data/viewer_mirrors/event_instances.parquet
- config_name: event_stages
  data_files:
  - split: benchmark
    path: data/viewer_mirrors/event_stages.parquet
- config_name: finalcascade_summary
  data_files:
  - split: benchmark
    path: data/viewer_mirrors/finalcascade_summary.parquet
- config_name: draft_availability
  data_files:
  - split: benchmark
    path: data/viewer_mirrors/draft_availability.parquet
---

[![Website](https://img.shields.io/badge/Website-H2EPR--Bench-0D5159?style=flat-square)](https://agenticfinlab.github.io/H2EPR-Bench/)
[![Code](https://img.shields.io/badge/Code-GitHub-24292F?style=flat-square)](https://github.com/AgenticFinLab/H2EPR-Bench)
[![Public Dataset](https://img.shields.io/badge/Dataset-Unified--3000-D99A20?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
[![Explorer](https://img.shields.io/badge/Explorer-Open-126A70?style=flat-square)](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer)
[![FinMycelium](https://img.shields.io/badge/System-FinMycelium-2A7F62?style=flat-square)](https://github.com/AgenticFinLab/FinMycelium)
[![Gated Gold](https://img.shields.io/badge/Reference_EPGs-Gated_Gold-9A6A16?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold)
[![AgenticFinLab](https://img.shields.io/badge/Lab-AgenticFinLab-51606A?style=flat-square)](https://agenticfinlab.github.io/)
![Paper forthcoming](https://img.shields.io/badge/Paper-forthcoming-87939B?style=flat-square)

# H²EPR-Bench

**An Evidence-Traceable Benchmark for Event-Process Reconstruction**

H²EPR-Bench evaluates whether a model can reconstruct how a bounded real-world
event unfolds from fixed multi-source evidence. Each event is represented as a
hierarchical heterogeneous event-process graph (EPG) that couples macro-level
stages, meso-level episodes, and micro-level participants, actions, outcomes,
and relations with an explicit evidence-support layer.

<p align="center">
  <img src="assets/card/h2epr_epg_overview.png" width="940" alt="H²EPR-Bench event-process reconstruction overview">
</p>

## Benchmark task

For each event, a model receives an event specification and a frozen evidence
package, then reconstructs the event as an EPG. The same evidence package is
used to construct the hidden, medium-granularity reference EPG. This controlled
setting separates evidence retrieval from event-process organization and lets
the evaluator measure structural, temporal, causal, and evidence fidelity.

The accompanying study evaluates 21 LLMs and finds that current models recover
salient elements and coarse stages more reliably than the causal and
mechanistic links that organize them into complete event processes.

## Quick facts

| Item | Value |
|---|---:|
| Real-world event instances | 3,000 |
| Temporal coverage | 1629–2025 |
| Domains / categories | 6 / 26 |
| Retrieved source records | 84,693 |
| Verified documents used to form frozen evidence packages | 25,814 |
| Mean verified documents per event | 8.60 |
| Mean evidence-package length | 26,151 characters |
| Expert-finalized reference EPGs | 3,000 (gated companion repository) |

Full evidence text is not redistributed in this public repository.

## Benchmark profile

The benchmark spans six domains and 26 event categories. The profile below
summarizes domain coverage, frozen-evidence size, and reference-process
complexity.

<p align="center">
  <img src="assets/card/unified3000_benchmark_profile.png" width="980" alt="H²EPR-Bench composition and instance scale">
</p>

## What is released here

| Asset class | Coverage | Access | Interpretation |
|---|---:|---|---|
| Event catalog and normalized metadata | 3,000 | Public | Event identity, scope, domain, and category |
| Sanitized FinMycelium FinalCascade drafts | 2,876 | Public | High-granularity construction artifacts, not scoring references |
| Representative Gantt previews | 30 | Public | Visualizations derived from FinMycelium drafts |
| Frozen evidence packages | 3,000 | Not included in this release | Benchmark input boundary described in the paper |
| Reference EPGs | 3,000 | [Gated companion repository](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold) | Official scoring references |

FinMycelium drafts are intermediate construction artifacts and must not be used
as scoring references.

## Dataset distribution

Source tables and the chart-generation script are included for reproducibility.

### Domains

![H²EPR-Bench domain distribution](assets/charts/unified3000_domain_distribution.png)

Source: [`domain_distribution.csv`](data/statistics/domain_distribution.csv)

### Categories

![H²EPR-Bench category distribution](assets/charts/unified3000_category_distribution.png)

Source: [`category_distribution.csv`](data/statistics/category_distribution.csv)

### Draft process depth

![H²EPR-Bench draft stage-count distribution](assets/charts/unified3000_draft_stage_distribution.png)

Source: [`finalcascade_summary.parquet`](data/viewer_mirrors/finalcascade_summary.parquet)

The chart generator is included at
[`scripts/generate_dataset_card_charts.py`](scripts/generate_dataset_card_charts.py).

## Data access

| Config | Rows | Purpose |
|---|---:|---|
| [`event_gallery`](data/viewer_mirrors/event_gallery.parquet) | 3,000 | Concise event browsing |
| [`event_catalog`](data/viewer_mirrors/event_catalog.parquet) | 3,000 | Complete benchmark event registry |
| [`event_instances`](data/viewer_mirrors/event_instances.parquet) | 3,000 | Normalized metadata and access state |
| [`event_stages`](data/viewer_mirrors/event_stages.parquet) | 8,500 | Ordered stage rows from available drafts |
| [`finalcascade_summary`](data/viewer_mirrors/finalcascade_summary.parquet) | 3,000 | Draft graph-size and temporal summary |
| [`draft_availability`](data/viewer_mirrors/draft_availability.parquet) | 3,000 | Per-event draft asset status |

CSV and Parquet mirrors are row- and cell-equivalent. Field types,
requiredness and conditional-null rules are documented in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

```python
from datasets import load_dataset

gallery = load_dataset(
    "AgenticFinLab/H2EPR-Bench", "event_gallery", split="benchmark"
)
catalog = load_dataset(
    "AgenticFinLab/H2EPR-Bench", "event_catalog", split="benchmark"
)
```

## Representative events

| Event | Domain | Category | Draft | Gantt |
|---|---|---|---|---|
| `H2EPR-0408` Cum-Ex Tax Scandal | Finance | Compliance, AML & Tax Evasion | [`JSON`](draft_events/H2EPR-0408/draft_epg.json) | [`PNG`](assets/gantt_previews/03_H2EPR-0408_gantt.png) |
| `H2EPR-0900` Crimean War | Military & Geopolitics | War Outbreaks & Escalation | [`JSON`](draft_events/H2EPR-0900/draft_epg.json) | [`PNG`](assets/gantt_previews/07_H2EPR-0900_gantt.png) |
| `H2EPR-1453` Reddit API Pricing and Moderator Protest | Cybersecurity & Tech Governance | Platform Governance, Surveillance & Influence | [`JSON`](draft_events/H2EPR-1453/draft_epg.json) | [`PNG`](assets/gantt_previews/10_H2EPR-1453_gantt.png) |
| `H2EPR-2784` Kuwaiti Oil Fires Environmental Crisis | Energy & Environment | Industrial & Environmental Disasters | [`JSON`](draft_events/H2EPR-2784/draft_epg.json) | [`PNG`](assets/gantt_previews/13_H2EPR-2784_gantt.png) |
| `H2EPR-0552` Samoa Measles Outbreak of 2019 | Public Health & Biosecurity | Regional Epidemics & Biosecurity | [`JSON`](draft_events/H2EPR-0552/draft_epg.json) | [`PNG`](assets/gantt_previews/24_H2EPR-0552_gantt.png) |
| `H2EPR-1353` Jon Sudbø Cancer Research Fraud | Science & Engineering | Scientific Fraud & Research Integrity | [`JSON`](draft_events/H2EPR-1353/draft_epg.json) | [`PNG`](assets/gantt_previews/30_H2EPR-1353_gantt.png) |

## FinMycelium draft visualizations

These examples expose the stage/episode organization and participant-relation
structure of FinMycelium-generated drafts. They are visualizations of
construction artifacts, not reference answers.

**2019 Samoa Measles Outbreak (`H2EPR-0552`)**

![Samoa measles event-process Gantt](assets/gantt_previews/24_H2EPR-0552_gantt.png)

**Kuwaiti Oil Fires Environmental Crisis (`H2EPR-2784`)**

![Kuwaiti oil fires event-process Gantt](assets/gantt_previews/13_H2EPR-2784_gantt.png)

**Reddit API Pricing and Moderator Protest (`H2EPR-1453`)**

![Reddit API protest event-process Gantt](assets/gantt_previews/10_H2EPR-1453_gantt.png)

All 30 selected previews are available under
[`assets/gantt_previews/`](assets/gantt_previews/), with their registry in
[`representative_events_30.csv`](data/catalog/representative_events_30.csv).

## Machine-readable assets and integrity

| Asset | Role |
|---|---|
| [`finmycelium_finalcascade_public.jsonl`](data/finmycelium_finalcascade_public.jsonl) | Consolidated sanitized draft EPGs |
| [`draft_events/`](draft_events/) | Event-local draft assets and status records |
| [`benchmark_totals.json`](data/statistics/benchmark_totals.json) | Frozen release totals |
| [`draft_graph_summary.csv`](data/statistics/draft_graph_summary.csv) | Aggregate draft graph statistics |
| [`validation_report.json`](manifests/validation_report.json) | Release acceptance report |
| [`viewer_quality_report.json`](manifests/viewer_quality_report.json) | Cross-repository Viewer validation |
| [`dataset_card_asset_provenance.json`](manifests/dataset_card_asset_provenance.json) | Figure and chart provenance |
| [`SHA256SUMS`](SHA256SUMS) | File-level integrity closure |

The release passes schema, identity, cross-table, ordering, and CSV/Parquet
consistency checks. Detailed results are available in the validation reports
and file-level checksum manifest above.

## Scope, ethics and citation

H²EPR-Bench references are structured evaluation targets, not exhaustive or
error-free historical truth records. Users should review
[`DATA_STATEMENT.md`](DATA_STATEMENT.md),
[`ETHICS_AND_LIMITATIONS.md`](ETHICS_AND_LIMITATIONS.md), and
[`TERMS_OF_USE.md`](TERMS_OF_USE.md) before reuse.

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). The previous
Core-1000 release remains preserved under the `core-1000-v1` tag; the default
3,000-event release uses only the `H2EPR-0001` through `H2EPR-3000` namespace.
