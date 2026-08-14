## Summary

<!-- State the user-visible or release-governance outcome. -->

## Changes

<!-- List the focused code, content, contract, or build changes. -->

## Validation

<!-- Include exact commands, outcomes, and relevant commit/tree/hash receipts. -->

- [ ] Unit and contract tests pass.
- [ ] Website validation passes when website files are affected.
- [ ] Public release boundary and size checks pass.
- [ ] `git diff --check` passes.

## Public release boundary

- [ ] No real reference EPG (Gold), evidence, raw model output, provider trace,
      credential, internal log, absolute local path, or ignored runtime receipt
      is included.
- [ ] Dataset records remain on Hugging Face; GitHub contains only approved
      source, contracts, schemas, validators, documentation, and small
      synthetic fixtures.
- [ ] Public Draft EPGs are described as FinMycelium construction artifacts,
      never as reference EPGs.
- [ ] New files comply with the repository size policy and do not use Git LFS.

## Licensing and provenance

- [ ] New code is compatible with Apache-2.0.
- [ ] New data/content/assets are compatible with CC BY-NC 4.0.
- [ ] Third-party sources and generated assets are identified where needed.

## Downstream impact

<!-- Check every target that may need a separately authorized promotion. -->

- [ ] GitHub Pages
- [ ] Explorer Space
- [ ] Public Dataset
- [ ] Public Gold interface only (never Gold records)
- [ ] No downstream deployment

## Rollback

<!-- Name the prior commit/revision and describe an ordinary revert path. -->

## Commit hygiene

- [ ] Work was developed on a focused branch and will merge through this PR.
- [ ] Commits follow `<type>: <lowercase-verb subject>`.
- [ ] Types are limited to `feat`, `fix`, `polish`, `refactor`, `style`,
      `build`, and `test`.
- [ ] Each commit is one cohesive logical change; no force push or history
      rewrite is required for release.
