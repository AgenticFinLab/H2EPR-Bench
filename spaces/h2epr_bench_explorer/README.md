---
title: H2EPR-Bench Explorer
colorFrom: gray
colorTo: blue
sdk: docker
pinned: false
license: apache-2.0
---

[![Project Website](https://img.shields.io/badge/Project_Website-Visit-176B70?style=flat-square)](https://agenticfinlab.github.io/H2EPR-Bench/)
[![Public Dataset](https://img.shields.io/badge/Public_Dataset-Unified--3000-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
[![FinMycelium System](https://img.shields.io/badge/FinMycelium-System-176B70?style=flat-square)](https://github.com/AgenticFinLab/FinMycelium)
[![Reference EPGs (Gated)](https://img.shields.io/badge/Reference_EPGs-Gated-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold)
[![Release Repository](https://img.shields.io/badge/Release_Repository-Source-176B70?style=flat-square)](https://github.com/AgenticFinLab/H2EPR-Bench)

# H²EPR-Bench Explorer

H²EPR-Bench Explorer is the interactive browsing layer for the Unified-3000
release of `AgenticFinLab/H2EPR-Bench`. The existing Docker Space runs a
Streamlit interface for searching all 3,000 catalog events, inspecting current
Draft EPG summaries and stage timelines, and previewing or downloading the
public per-event Draft EPG for every event.

**Release boundary:** public Draft EPGs are sanitized FinMycelium construction
artifacts. Official benchmark scoring uses expert-adjudicated reference EPGs in
the [manual-gated companion](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold).
The Explorer does not load reference EPGs or frozen evidence packages.

The Explorer source code is Apache-2.0. Dataset content displayed by the app,
including public Draft EPGs, remains CC BY-NC 4.0 under the Dataset release.

## Public data contract

The Explorer validates five Parquet tables from one release identity:

| Table | Role |
|---|---|
| `event_gallery.parquet` | Lightweight event discovery metadata |
| `event_catalog.parquet` | Stable event discovery metadata |
| `event_instances.parquet` | Public artifact-access fields |
| `finalcascade_summary.parquet` | Draft graph counts and event-level temporal summary |
| `event_stages.parquet` | Ordered stage rows for every Draft EPG |

Selected Draft EPGs are loaded directly from
`draft_events/<H2EPR-ID>/draft_epg.json`. The path is derived only after the
canonical event ID has been validated. `manifests/draft_source_hashes.csv`
binds every direct file to its canonical source-payload digest and sanitized
record digest; the Explorer verifies both identities and the canonical JSON
digest before displaying a graph.

This release-candidate branch intentionally has no remote dataset revision.
Remote reads and immutable per-file links fail closed until the publication
workflow pins the resulting Hugging Face commit. It never falls back to a
floating branch.

## Local development

The app can use the frozen local Unified-3000 release candidate without any
network access:

```bash
export H2EPR_EXPLORER_LOCAL_DATASET_DIR=/path/to/H2EPR-Bench
streamlit run app.py
```

During release-candidate verification,
`H2EPR_EXPLORER_LOCAL_DATASET_DIR` is required. After publication, the source
constant is updated once to the immutable dataset revision; the application
exposes no runtime revision override, so one process cannot mix releases.
