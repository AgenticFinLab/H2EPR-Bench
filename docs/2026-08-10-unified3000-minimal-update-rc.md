# Unified-3000 Minimal Website Update RC

Date: 2026-08-10
Branch: `website-unified3000-minimal-rc`

## Scope

This release candidate updates the existing project website to the Unified-3000
benchmark while preserving its established role as a project-facing showcase.
It is intentionally not a reproduction of the AAAI paper.

Updated surfaces:

- benchmark scale, time span, domain/category counts, source counts, and graph statistics;
- the direct-reconstruction Results snapshot, leaderboard, and diagnostic plots for 21 systems;
- public Hugging Face, Gold, Explorer, and repository links where displayed;
- the Gantt gallery, using six Unified-3000 FinMycelium draft-EPG timelines;
- small responsive text-fitting and validation improvements.

Preserved surfaces:

- overall information architecture, layout, visual identity, and navigation;
- Background & Motivation;
- Benchmark Construction narrative and established overview graphics;
- Findings section and its presentation;
- Interactive Explorer presentation;
- prediction and simulation framing and use-case placement.

## Frozen Public Facts

- 3,000 events, spanning 1629--2025;
- 6 domains and 26 categories;
- 84,693 candidate source records and 25,814 verified documents;
- 11,333 reference stages;
- 21 direct-LLM systems and 63,000 model-event slots;
- primary v7 result: GLM-5.1 with a Discriminative H2EPRScore of 53.00;
- 14 of 21 systems with output validity at or above 90%.

## Result Sources

The deterministic builder `scripts/build_unified3000_site_release.py` reads the
following frozen aggregate inputs from an operator-supplied `--source-root`.
The source root is private and is never embedded in generated public assets:

| Source | SHA-256 |
|---|---|
| `paper/AAAI_assets/02_主实验结果/表/system_summary_v7.csv` | `a45afe8fea48813006b8918b63a1177a245a536fb3a145d478b0b6639574c6bf` |
| `paper/supplementary_aaai27/code_data_package/h2epr_bench_anonymous/data/results/main/event_level_scores.csv` | `4d6bafc6a247964a280f22a18ec56ea318d12e514fa4798ae98bb66af3d5f461` |
| `paper/AAAI_assets/02_主实验结果/表/domain_summary_v7.csv` | `e908227372675c82c156c05a42d6d4b07fd1f3b637764e9b0efa1c315489cd54` |
| `paper/AAAI_assets/01_基准与Gold统计/表/domain_distribution_v1.csv` | `11ebaf05367afff7d5a85f0fecd4b5b75e4e5b123fc856e3024337dfd7d3d16e` |
| `paper/AAAI_assets/01_基准与Gold统计/表/category_distribution_v1.csv` | `c6fb3ff4620647d95df2240b4197f35bd12058beafcd9a1805618f785831cf5d` |
| `paper/AAAI_assets/09_补充源表/event_features_v1.csv` | `7b9abb1509961b5341395efd64963f2b9fce78cce83575a0da41cdef66fd7481` |
| `paper/AAAI_assets/08_成本效率与失败分析/表/directllm_system_resource_summary_v1.csv` | `0d0ba880ca6b7c1dfec2b3df1c96851d2f2084902200ff3890f990be39363117` |
| `paper/AAAI_assets/08_成本效率与失败分析/表/adaptation_failures_by_system_v1.csv` | `9d1acd810ab068c6401aaad6e1b65cc34b32ea0026bc4c154e8f9374fa05347d` |

## Gantt Gallery

The six displayed events are `H2EPR-0346`, `H2EPR-0408`, `H2EPR-0535`,
`H2EPR-0900`, `H2EPR-0908`, and `H2EPR-0990`. These images visualize
FinMycelium draft EPGs; they are not reference EPGs or scoring targets.

## Validation

- deterministic rebuild produced byte-identical generated JSON and PNG assets;
- `scripts/validate_site_assets.py` passed;
- Python compilation and JavaScript syntax checks passed;
- all referenced local website assets returned successfully in the local HTTP check;
- the rendered page loaded 21 leaderboard rows, 21 diagnostic model controls,
  and 6 Gantt controls without application errors;
- desktop and constrained-width visual checks were completed;
- `git diff --check` passed.

The only local HTTP 404 was the browser's implicit `/favicon.ico` request; no
site content references that path.

## Publication Boundary

This is a local release candidate only. No remote branch, `main`, GitHub Pages,
Hugging Face repository, or Explorer asset was modified by this task. Remote
publication requires a separate explicit authorization and final readback.
