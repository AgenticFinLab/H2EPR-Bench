# H2EPR-Bench Website Repository Identity

Date: 2026-06-28

This document records the local and remote identity of the H2EPR-Bench static
website repository.

## Canonical Mapping

| Role | Value |
|---|---|
| Local repository path | `/home/lenovo/projects/AgenticFinLab/H2EPR-Bench.github.io` |
| Local branch | `main` |
| Git remote name | `origin` |
| Git remote URL | `https://github.com/AgenticFinLab/H2EPR-Bench.git` |
| GitHub repository | `AgenticFinLab/H2EPR-Bench` |
| GitHub Pages URL | `https://agenticfinlab.github.io/H2EPR-Bench/` |

## Naming Decision

The local directory remains named `H2EPR-Bench.github.io` because the website
work started as a local GitHub Pages project directory. The public remote
repository is intentionally named `AgenticFinLab/H2EPR-Bench`, not
`AgenticFinLab/H2EPR-Bench.github.io`, so that the deployed project-site URL is
concise:

```text
https://agenticfinlab.github.io/H2EPR-Bench/
```

This is a GitHub project site, not a user or organization root site.

## Push Policy

For this website repository, the intended push target is:

```bash
git push origin main
```

where `origin` resolves to:

```text
https://github.com/AgenticFinLab/H2EPR-Bench.git
```

Do not create or push to `AgenticFinLab/H2EPR-Bench.github.io` for this project
unless a future governance decision explicitly changes the website repository
strategy. A read-only check on 2026-06-28 found no accessible repository at
`https://github.com/AgenticFinLab/H2EPR-Bench.github.io.git`.

## Related Release Repositories

- Public dataset: `https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench`
- Gated Gold companion: `https://huggingface.co/datasets/AgenticFinLab/H2EPR-Bench-Gold`
- Explorer Space: `https://huggingface.co/spaces/AgenticFinLab/H2EPR-Bench-Explorer`

