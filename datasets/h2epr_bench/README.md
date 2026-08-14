# H2EPR-Bench public Dataset release contract

This directory maintains the public source contract and local validator for
the H2EPR-Bench Unified-3000 Dataset release. The released tables and Draft
EPG records remain on Hugging Face and are intentionally not duplicated in
this GitHub repository.

The contract is fixed to public Dataset revision
`1d01f3649ace0301ac3bbe9ee875eea660347a29`. It covers all 3,000 catalog
events, including 2,876 public Draft EPGs and 124 events whose Draft EPG is
unavailable in this release.

## Validate a local release tree

Install the Explorer's declared dependencies, then run:

```bash
python datasets/h2epr_bench/scripts/validate_release.py /path/to/H2EPR-Bench
```

The command is local-only: it takes an explicit Dataset root, performs no
download or upload, and never opens the gated Gold repository. It checks the
six frozen viewer mirrors, joined identity and count invariants, stage-level
closure, direct per-event Draft paths, Draft identities and canonical hashes,
and neutral unavailable markers.

Direct Draft paths are always derived from a validated H2EPR ID:

```text
draft_events/<H2EPR-ID>/draft_epg.json
```

The `draft_asset` metadata field is provenance, not a path resolver.

## Release boundary

A public Draft EPG is a sanitized FinMycelium construction artifact. It is
not a reference EPG (Gold) and must never be presented as one. Official
reference EPG records remain in the manual-gated Hugging Face companion and
are not required by this validator.

Code in this directory is Apache-2.0. The released Dataset, documentation,
and content are CC BY-NC 4.0; see the repository licensing notice.
