# H²EPR-Bench public Dataset contract

[Project Website](https://agenticfinlab.github.io/H2EPR-Bench/) ·
[Event Explorer](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer) ·
[FinMycelium System](https://github.com/AgenticFinLab/FinMycelium) ·
[Reference EPGs (Gated)](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold) ·
[Release Repository](https://github.com/AgenticFinLab/H2EPR-Bench)

This directory maintains the source contract, Dataset Card, and local
validator for the 3,000-event H²EPR-Bench Dataset. Released tables and Draft
EPG records are hosted on Hugging Face.

The contract covers the continuous `H2EPR-0001` through `H2EPR-3000`
namespace. Every event has one public sanitized Draft EPG, and the five viewer
tables cover all 3,000 events and 8,843 ordered stages. `dataset_revision` is
pinned to the immutable Hugging Face commit returned after the exact release
tree was uploaded and independently downloaded and validated.

## Validate a local release tree

Install the Explorer's declared dependencies, then run:

```bash
python datasets/h2epr_bench/scripts/validate_release.py /path/to/H2EPR-Bench
```

The command is local-only: it takes an explicit Dataset root, performs no
download or upload, and never opens the gated Gold repository. It checks the
five frozen viewer mirrors, joined identity and count invariants, stage-level
closure, the 3,000 direct Draft paths, the source-hash registry, the aggregate
JSONL, Draft identities and hashes, and release-tree integrity.

Direct Draft paths are always derived from a validated H2EPR ID:

```text
draft_events/<H2EPR-ID>/draft_epg.json
```

Every path is derived from the validated public event identity; no path is read
from event metadata.

## Draft and reference EPGs

The public Dataset includes one sanitized FinMycelium Draft EPG per event.
Expert-finalized EPGs used for official scoring are available through the
gated Hugging Face companion.

Code in this directory is Apache-2.0. The released Dataset, documentation,
and content are CC BY-NC 4.0; see the repository licensing notice.
