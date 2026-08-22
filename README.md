# H²EPR-Bench

[![Project Website](https://img.shields.io/badge/Project_Website-Visit-176B70?style=flat-square)](https://agenticfinlab.github.io/H2EPR-Bench/)
[![Public Dataset](https://img.shields.io/badge/Public_Dataset-Unified--3000-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench)
[![Event Explorer](https://img.shields.io/badge/Event_Explorer-Browse-176B70?style=flat-square)](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer)
[![FinMycelium System](https://img.shields.io/badge/FinMycelium-System-176B70?style=flat-square)](https://github.com/AgenticFinLab/FinMycelium)
[![Reference EPGs (Gated)](https://img.shields.io/badge/Reference_EPGs-Gated-176B70?style=flat-square)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold)

This is the canonical public source monorepo for the H²EPR-Bench release. It
maintains the GitHub Pages website, the deployable Explorer source, the public
Unified-3000 Dataset contract and validator, and only the public-safe schema
and offline interface for the gated Gold companion.

The released data records remain on Hugging Face. This repository does not
duplicate the 3,000-event tables, public Draft EPG files, or any real reference
EPG (Gold), evidence package, raw model output, provider trace, credential, or
internal construction log.

## Repository map

| Path | Public role |
| --- | --- |
| `index.html`, `assets/`, `data/`, `static/` | Existing GitHub Pages website and aggregate public presentation assets |
| `spaces/h2epr_bench_explorer/` | Complete Docker Space source for the Unified-3000 Explorer |
| `datasets/h2epr_bench/` | Public Dataset contract, card source, schema, local-only validator, and release identity |
| `datasets/h2epr_bench_gold/` | Public Gold card source, reference-EPG schema, local-only interface, and synthetic tests only |
| `scripts/` | Website and repository validation/build tools |
| `tests/` | Credential-free public verification suite |

Canonical public destinations and their required surface order are maintained
in `manifests/public_resource_links.json`.

## Release endpoints

- Project Website: https://agenticfinlab.github.io/H2EPR-Bench/
- Release Repository: https://github.com/AgenticFinLab/H2EPR-Bench
- Public Dataset: https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench
- Event Explorer: https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer
- FinMycelium System: https://github.com/AgenticFinLab/FinMycelium
- Reference EPGs (Gated): https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold
- Paper: forthcoming; no public URL is asserted yet.

The public Dataset contract is fixed to revision
`1d01f3649ace0301ac3bbe9ee875eea660347a29`. It covers all 3,000 events,
including 2,876 public Draft EPGs and 124 neutral Draft-unavailable states.
Draft EPGs are sanitized FinMycelium construction artifacts; they are not the
reference EPGs used for official scoring.

## Local validation

Run the credential-free tests that need no released records:

```bash
python -m unittest tests/test_public_dataset_release.py tests/test_public_gold_interface.py
python scripts/validate_site_assets.py
python scripts/check_public_release_boundary.py
```

Explorer integration tests require only public files from the pinned Dataset
revision. Prepare an ignored local cache and run them with:

```bash
python scripts/prepare_public_dataset_test_cache.py --output .cache/h2epr-public-dataset
H2EPR_TEST_DATASET_DIR=.cache/h2epr-public-dataset \
  python -m unittest tests/test_h2epr_explorer_space.py
```

To validate a complete local public Dataset release tree, see
`datasets/h2epr_bench/README.md`.

## Contribution and release policy

Significant work is developed on a focused branch and merged to `main` only
through a reviewed Pull Request. Commit messages follow
`<type>: <lowercase-verb subject>` with the lab-approved types documented in
the repository PR template. Pull-request CI is read-only and credential-free.
Publishing to GitHub Pages or Hugging Face is a separate, manually authorized
release operation; validation workflows do not deploy.

See `docs/repository-identity.md` and `docs/release-process.md` for the
source-of-truth and downstream promotion model.

## Licensing

Source code is licensed under Apache License 2.0. Released data, website and
documentation content, schemas, and visual assets are licensed under CC BY-NC
4.0. See `LICENSE` and `LICENSES/README.md` for the path-level policy and
third-party limitations.
