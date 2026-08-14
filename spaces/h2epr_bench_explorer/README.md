---
title: H2EPR-Bench Explorer
colorFrom: gray
colorTo: blue
sdk: docker
pinned: false
license: apache-2.0
---

# H²EPR-Bench Explorer

H²EPR-Bench Explorer is the interactive browsing layer for the Unified-3000
release of `AgenticFinLab/H2EPR-Bench`. The existing Docker Space runs a
Streamlit interface for searching all 3,000 catalog events, inspecting current
Draft EPG summaries and stage timelines, and previewing or downloading the
2,876 public per-event Draft EPG files.

The other 124 catalog events remain fully browsable and show a neutral local
empty state because no public Draft EPG is available for them in this release.

**Release boundary:** public Draft EPGs are sanitized FinMycelium construction
artifacts. Official benchmark scoring uses expert-adjudicated reference EPGs in
the [manual-gated companion](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold).
The Explorer does not load reference EPGs or frozen evidence packages.

The Explorer source code is Apache-2.0. Dataset content displayed by the app,
including public Draft EPGs, remains CC BY-NC 4.0 under the Dataset release.

## Public data contract

The Explorer loads five Parquet tables from one immutable dataset revision:

| Table | Role |
|---|---|
| `event_catalog.parquet` | Stable event discovery metadata |
| `event_instances.parquet` | Public access-state fields |
| `finalcascade_summary.parquet` | Draft graph counts and event-level temporal summary |
| `draft_availability.parquet` | Per-event Draft EPG availability and integrity metadata |
| `event_stages.parquet` | Ordered stage rows for available drafts |

Selected Draft EPGs are loaded directly from
`draft_events/<H2EPR-ID>/draft_epg.json`. The path is derived only after the
canonical event ID and availability state have been validated. The availability
table's `draft_asset` value identifies the consolidated release asset and is
not used as the selected-event path.

Default dataset revision:

```text
1d01f3649ace0301ac3bbe9ee875eea660347a29
```

## Local development

The app can use the frozen local Unified-3000 release candidate without any
network access:

```bash
export H2EPR_EXPLORER_LOCAL_DATASET_DIR=../../build/hf_unified3000_inplace_upgrade_rc_v3_dataset_card/H2EPR-Bench
streamlit run app.py
```

Without `H2EPR_EXPLORER_LOCAL_DATASET_DIR`, all public table and selected-event
downloads use the pinned revision above. The application exposes no runtime
revision override, so one process cannot mix dataset revisions.
