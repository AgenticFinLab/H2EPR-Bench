# H²EPR-Bench Website

This repository contains the static GitHub Pages website for H²EPR-Bench.

The current website release presents the Unified-3000 benchmark and the
21-system direct reconstruction evaluation while retaining the project's
broader analysis, prediction, and simulation use-case framing.

Repository identity note: this local folder is named
`H2EPR-Bench.github.io`, but it deploys to the project-site repository
`AgenticFinLab/H2EPR-Bench`, whose Pages URL is
https://agenticfinlab.github.io/H2EPR-Bench/. See
`docs/repository-identity.md` for the canonical local/remote mapping.

Public benchmark links:

- Public dataset: https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench
- Gated Gold companion: https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold
- Explorer Space: https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer

The website previews public benchmark assets and routes users to the official release repositories. It does not include gated Gold references, raw evidence text, raw model outputs, provider traces, or internal construction logs.

Rebuild and validate the Unified-3000 website data assets from the sibling
research repository with:

```bash
python scripts/build_unified3000_site_release.py
python scripts/validate_site_assets.py
```
