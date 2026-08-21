# H2EPR-Bench repository identity

Date: 2026-08-14

## Canonical public source

| Role | Identity |
| --- | --- |
| GitHub source monorepo | `AgenticFinLab/H2EPR-Bench` |
| Protected integration branch | `main` |
| GitHub Pages project site | `https://agenticfinlab.github.io/H2EPR-Bench/` |
| Public Dataset distribution | `AgenticFinLab/H2EPR-Bench` on Hugging Face |
| Manual-gated reference distribution | `AgenticFinLab/H2EPR-Bench-Gold` on Hugging Face |
| Explorer runtime distribution | `AgenticFinLab/H2EPR-Bench-Explorer` on Hugging Face |
| Multi-agent reconstruction system | `AgenticFinLab/FinMycelium` on GitHub |
| Research group website | `https://agenticfinlab.github.io/` |

The same short name is intentionally used for the GitHub source monorepo and
the public Hugging Face Dataset. Their host and repository type distinguish
them. GitHub is the public source/review system; Hugging Face is the versioned
Dataset and runtime distribution system.

The exact public URLs, display roles, surface order, card-source paths and
current downstream baselines are machine-readable in
`manifests/public_resource_links.json`. No public paper URL is asserted while
the paper remains forthcoming.

## Source-of-truth boundaries

- GitHub owns public website source, Explorer source, public release
  contracts/validators, and public-safe reference schema/interface source.
- The public Hugging Face Dataset owns the released tables and Draft EPG
  artifacts. Source code fixes do not silently create a new Dataset revision.
- The gated Hugging Face companion owns real reference EPGs. No real Gold or
  evidence record is copied into this repository or ordinary CI.
- The Explorer Space runs an explicitly reviewed subtree promoted from this
  monorepo only after separate deployment authorization and runtime testing.
- Private construction inputs, adjudication material, evidence, and provider
  outputs remain outside the public release system.

## Change flow

Significant changes use a focused feature branch. `main` changes only through
a Pull Request following the AgenticFin Lab commit and review guidance. A PR
may validate deployable content but does not itself publish to Hugging Face.
Downstream promotion records the exact reviewed Git commit, subtree, Dataset
revision, and rollback point.

No force push or history rewrite is part of the release process. Failed public
changes are corrected with ordinary follow-up or revert commits.
