# H2EPR-Bench Gold public interface

This directory contains only the public schema and offline validation
interface for H2EPR-Bench reference EPGs. It contains no real reference EPG,
evidence record, adjudication artifact, access credential, or download client.

Official reference EPG records remain in the manual-gated Hugging Face
companion, `AgenticFinLab/H2EPR-Bench-Gold`. Possessing this schema does not
grant access to those records. Public Draft EPGs are separate FinMycelium
construction artifacts and must not be treated as Gold.

Validate an explicitly supplied local document with:

```bash
python datasets/h2epr_bench_gold/validators/validate_reference_epg.py path/to/document.json
```

The validator performs no network calls and has no default Dataset or Gold
path. Repository tests use only the visibly synthetic fixture in
`synthetic_fixtures/`.

Code in this directory is Apache-2.0. The schema, documentation, and fixture
are CC BY-NC 4.0; see the repository licensing notice.
