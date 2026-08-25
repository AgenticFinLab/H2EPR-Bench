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

[![Project Website](https://img.shields.io/badge/Project_Website-Visit-176B70?style=flat-square)](https://agenticfinlab.github.io/H2EPR-Bench/)
[![Public Dataset](https://img.shields.io/badge/Public_Dataset-3%2C000_events-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
[![Event Explorer](https://img.shields.io/badge/Event_Explorer-Browse-176B70?style=flat-square)](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer)
[![FinMycelium System](https://img.shields.io/badge/FinMycelium-System-176B70?style=flat-square)](https://github.com/AgenticFinLab/FinMycelium)
[![Release Repository](https://img.shields.io/badge/Release_Repository-Source-176B70?style=flat-square)](https://github.com/AgenticFinLab/H2EPR-Bench)

# H²EPR-Bench Reference EPGs

This gated companion contains the 3,000 expert-finalized reference EPGs used
for official H²EPR-Bench scoring. Together, they provide a consistent
medium-granularity view of every benchmark event.

Each reference EPG was constructed from the same fixed evidence package used
in benchmark evaluation. FinMycelium draft generation was followed by
agent–expert verification, expert adjudication, and final sign-off.

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

The collection contains 104,027 nodes and 68,153 evidence-support edges,
capturing both process structure and source-level traceability.

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

Request access for benchmark scoring, independent reproduction, or controlled
audit of reported H²EPR-Bench results. The
[public Dataset](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
and [Event Explorer](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer)
provide the event catalog, public Draft EPGs, stage views, and representative
timelines for open exploration.

Access is reviewed manually to preserve the benchmark's evaluation setting.

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

Use this repository for research evaluation. Redistribution, model training,
and public disclosure of reference answers require separate written permission.

See [`TERMS_OF_USE.md`](TERMS_OF_USE.md) and [`LICENSE.md`](LICENSE.md).
Citation metadata is provided in [`CITATION.cff`](CITATION.cff).
