# H²EPR-Bench reference EPG interface

[Project Website](https://agenticfinlab.github.io/H2EPR-Bench/) ·
[Public Dataset](https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench) ·
[Event Explorer](https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer) ·
[FinMycelium System](https://github.com/AgenticFinLab/FinMycelium) ·
[Release Repository](https://github.com/AgenticFinLab/H2EPR-Bench)

This directory provides the public schema and offline document validator for
H²EPR-Bench reference EPGs. The expert-finalized collection is hosted in the
manual-gated Hugging Face companion,
`AgenticFinLab/H2EPR-Bench-Gold`; the included synthetic fixture demonstrates
the interface without reproducing a benchmark record.

Validate an explicitly supplied local document with:

```bash
python datasets/h2epr_bench_gold/validators/validate_reference_epg.py path/to/document.json
```

The validator runs locally against the path supplied by the user. Repository
tests use the synthetic fixture in `synthetic_fixtures/`.

Code in this directory is Apache-2.0. The schema, documentation, and fixture
are CC BY-NC 4.0; see the repository licensing notice.
