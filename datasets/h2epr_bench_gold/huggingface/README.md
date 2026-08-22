---
pretty_name: "H²EPR-Bench Reference EPGs"
language:
- en
license: cc-by-nc-4.0
tags:
- event-understanding
- benchmark
- event-process-reconstruction
- evidence-grounded
- graph-structured-data
- gated
- official-scoring-target
size_categories:
- 1K<n<10K
configs:
- config_name: gold_catalog
  data_files:
  - split: gated
    path: data/gold_catalog.parquet
- config_name: gold_reference_summary
  data_files:
  - split: gated
    path: data/gold_reference_summary.parquet
---

[![Website](https://img.shields.io/badge/Website-H2EPR--Bench-0D5159?style=flat-square)](https://agenticfinlab.github.io/H2EPR-Bench/)
[![Code](https://img.shields.io/badge/Code-GitHub-24292F?style=flat-square)](https://github.com/AgenticFinLab/H2EPR-Bench)
[![Public Dataset](https://img.shields.io/badge/Dataset-Unified--3000-D99A20?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
[![Explorer](https://img.shields.io/badge/Explorer-Open-126A70?style=flat-square)](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer)
[![FinMycelium](https://img.shields.io/badge/System-FinMycelium-2A7F62?style=flat-square)](https://github.com/AgenticFinLab/FinMycelium)
[![Gated Gold](https://img.shields.io/badge/Reference_EPGs-Gated_Gold-9A6A16?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold)
[![AgenticFinLab](https://img.shields.io/badge/Lab-AgenticFinLab-51606A?style=flat-square)](https://agenticfinlab.github.io/)
![Paper forthcoming](https://img.shields.io/badge/Paper-forthcoming-87939B?style=flat-square)

# H²EPR-Bench Reference EPGs

This gated companion repository contains all 3,000 medium-granularity reference
EPGs used to score fixed-evidence event-process reconstruction in
H²EPR-Bench. The reference namespace is `H2EPR-0001` through `H2EPR-3000`.

Reference EPGs were constructed from the same frozen evidence packages used in
benchmark evaluation, using FinMycelium draft generation followed by
agent–expert verification, expert adjudication and final sign-off. Public
FinMycelium drafts remain separate intermediate construction artifacts.

## Quick facts

| Item | Value |
|---|---:|
| Reference EPGs | 3,000 |
| Process nodes | 75,454 |
| Evidence nodes | 28,573 |
| Total nodes | 104,027 |
| Relation and mechanism-path records | 27,858 |
| Evidence-support edges | 68,153 |
| Domains / categories | 6 / 26 |
| Access | Gated; available upon request |

## Reference graph composition

The aggregate node distribution is disclosed for benchmark transparency; the
per-event reference graphs remain controlled evaluation targets.

<p align="center">
  <img src="assets/card/reference_node_composition.png" width="980" alt="H²EPR-Bench domain and reference EPG node composition">
</p>

## Contents

| Asset | Role |
|---|---|
| [`gold_catalog.parquet`](data/gold_catalog.parquet) | Gated 3,000-event index |
| [`gold_reference_summary.parquet`](data/gold_reference_summary.parquet) | Viewer-friendly component-count summary |
| [`gold_reference_medium.jsonl`](data/gold_reference_medium.jsonl) | Canonical 3,000-reference JSONL |
| [`gold_events/`](gold_events/) | Per-event reference EPG files |
| [`reference_epg.schema.json`](schemas/reference_epg.schema.json) | Release schema |
| [`validation_report.json`](manifests/validation_report.json) | Release acceptance report |
| [`viewer_quality_report.json`](manifests/viewer_quality_report.json) | Cross-repository Viewer validation |
| [`dataset_card_asset_provenance.json`](manifests/dataset_card_asset_provenance.json) | Display-asset provenance |
| [`SHA256SUMS`](SHA256SUMS) | File-level integrity closure |

## Access and intended use

Request access only when official scoring references are needed for benchmark
evaluation, independent reproduction, or controlled audit of reported
H²EPR-Bench results. The reference repository is not intended for general data
collection, pretraining, benchmark memorization or redistribution.

The reference EPGs are standardized, medium-granularity scoring targets rather
than exhaustive historical truth records. Raw search records, full evidence
text, and internal construction metadata are excluded from this release.

The companion [public repository](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
provides the complete event catalog, sanitized FinMycelium drafts
and representative Gantt previews.

## Loading tabular configs

```python
from datasets import load_dataset

gold_catalog = load_dataset(
    "AgenticFinLab/H2EPR-Bench-Gold", "gold_catalog", split="gated"
)
gold_summary = load_dataset(
    "AgenticFinLab/H2EPR-Bench-Gold", "gold_reference_summary", split="gated"
)
```

Approved users can retrieve controlled files with `huggingface_hub`:

```python
from huggingface_hub import hf_hub_download

gold_jsonl_path = hf_hub_download(
    repo_id="AgenticFinLab/H2EPR-Bench-Gold",
    repo_type="dataset",
    filename="data/gold_reference_medium.jsonl",
)
```

## Validation and integrity

All 3,000 references pass the frozen release's schema, namespace/foreign-key,
evidence-reference, temporal-DAG, causal-DAG and deterministic-replay checks.
The tabular views additionally pass identity, required-value, cross-table, and
CSV/Parquet consistency checks. Detailed results are available in the release
manifests and [`SHA256SUMS`](SHA256SUMS).

## Usage restrictions

Use this repository for research evaluation only. Do not redistribute reference
EPGs, expose reference answers in prompts or public examples, or use them
for model training or fine-tuning unless separately permitted in writing.

See [`TERMS_OF_USE.md`](TERMS_OF_USE.md) and [`LICENSE.md`](LICENSE.md).
Citation metadata is provided in [`CITATION.cff`](CITATION.cff). The historical
Core-1000 state remains preserved under the `core-1000-v1` tag.
