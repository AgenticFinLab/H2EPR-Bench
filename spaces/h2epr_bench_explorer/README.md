---
title: H2EPR-Bench Explorer
colorFrom: gray
colorTo: blue
sdk: docker
pinned: false
license: apache-2.0
---

[![Project Website](https://img.shields.io/badge/Project_Website-Visit-176B70?style=flat-square)](https://agenticfinlab.github.io/H2EPR-Bench/)
[![Public Dataset](https://img.shields.io/badge/Public_Dataset-3%2C000_events-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
[![FinMycelium System](https://img.shields.io/badge/FinMycelium-System-176B70?style=flat-square)](https://github.com/AgenticFinLab/FinMycelium)
[![Reference EPGs (Gated)](https://img.shields.io/badge/Reference_EPGs-Gated-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold)
[![Release Repository](https://img.shields.io/badge/Release_Repository-Source-176B70?style=flat-square)](https://github.com/AgenticFinLab/H2EPR-Bench)

# H²EPR-Bench Explorer

Explore 3,000 real-world event processes without navigating raw Dataset files.
Search by title, domain, category, or keyword; inspect graph statistics and
ordered stages; open an interactive timeline; and preview or download the
public Draft EPG for any event.

## What you can explore

- **3,000 event profiles** spanning six domains and 26 categories
- **8,843 ordered stages** with temporal and graph-level summaries
- **Interactive timelines** for calendar-based and relative-order processes
- **Draft EPG JSON** with participants, actions, outcomes, and typed relations
- **Direct links** to the Dataset and gated reference collection

The Explorer presents the public FinMycelium Draft EPGs. Expert-finalized
reference EPGs for official scoring are available through the
[gated companion](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold).

## Data connection

The app reads five Parquet views from
[AgenticFinLab/H2EPR-Bench](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench):

| Table | Role |
|---|---|
| `event_gallery.parquet` | Lightweight event discovery |
| `event_catalog.parquet` | Complete event registry |
| `event_instances.parquet` | Metadata and artifact access fields |
| `finalcascade_summary.parquet` | Event-level graph and temporal summaries |
| `event_stages.parquet` | Ordered Draft-EPG stages |

Event-level graphs are loaded from
`draft_events/<H2EPR-ID>/draft_epg.json`. Remote reads are pinned to Dataset
commit `4b0f0f4000db3ba9b6e1a720e5b5cfbaae68353c`, and each file is verified
against the release hash registry before display.

## Local development

Point the app at a complete local Dataset tree:

~~~bash
export H2EPR_EXPLORER_LOCAL_DATASET_DIR=/path/to/H2EPR-Bench
streamlit run app.py
~~~

The Explorer source is Apache-2.0. Dataset content displayed by the app is
released under CC BY-NC 4.0.
