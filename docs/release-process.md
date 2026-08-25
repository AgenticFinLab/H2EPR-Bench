# Public release process

This document defines how reviewed source moves from the H2EPR-Bench GitHub
monorepo to its public endpoints. Validation and publishing are deliberately
separate operations.

## 1. Pull Request gate

Significant work begins on a focused branch and reaches `main` only through a
reviewed Pull Request. PR CI is read-only and credential-free. It may download
the minimal public test subset from the fixed Dataset revision, but it never
uses a Gold credential or deploys any target.

Acceptance requires:

- unit and negative contract tests;
- the complete Explorer contract against pinned public tables;
- static website validation;
- public-boundary, secret, local-path, payload, fixture, and size checks;
- deterministic receipts where applicable; and
- an exact changed-path, commit, tree, and rollback record.

## 2. GitHub Pages

The existing website stays at the repository root to preserve the project-site
URL. A reviewed merge to `main` is the source event for the existing Pages
publication configuration. After merge, verify the deployed commit, all local
assets, external release links, desktop/mobile layout, and browser console.
Failure is corrected with an ordinary revert or follow-up commit through the
same review process.

## 3. Explorer Space

The deployable source is `spaces/h2epr_bench_explorer/`. Promotion must:

1. start from an exact reviewed Git commit, never an unfrozen worktree;
2. record the source subtree manifest and resulting Space commit/tree;
3. keep the immutable Dataset revision in the release contract and Explorer source identical;
4. use an isolated canary/staging target when available;
5. validate build/runtime logs, health, desktop/mobile behavior, deep links,
   filters/reset, both calendar and relative-order timeline modes, all-event
   Draft asset/path/hash closure, and sampled Draft preview/download behavior,
   external links, console errors, and page errors;
6. create a rollback reference before production promotion; and
7. update production only with an ordinary non-force operation after explicit
   deployment authorization.

A broken promotion is reverted with a new ordinary commit restoring the prior
tree. Canary deletion and production promotion are separate lifecycle actions.

## 4. Public Dataset

The GitHub contract fixes the currently accepted public revision, but merging
source does not publish Dataset records. A Dataset release has an independent
manual gate that validates a sanitized staging tree, five mirror schemas and
hashes, all cardinalities and joins, all 3,000 direct Draft EPGs, aggregate and
source-hash closure, the Dataset card, and the CC BY-NC 4.0 boundary.

Only the public Dataset repository is read or written by this flow. A new
revision requires an explicit release record and a coordinated source update
that pins the new immutable revision.

An unpublished candidate keeps `dataset_revision` set to `null` and is frozen
and reviewed locally; it is not pushed as a GitHub PR tip. The exact Dataset
tree is uploaded first, its resulting immutable 40-hex commit is written into
the contract and Explorer source, and all published gates are rerun before the
pinned source branch is pushed for review. CI deliberately rejects an unbound
candidate.

The public Dataset Card source is tracked at
`datasets/h2epr_bench/huggingface/README.md`. A card-only promotion still
requires a remote-HEAD check and records the prior/resulting Dataset revision;
it does not modify or re-upload Dataset records.

## 5. Gold companion

The public monorepo publishes no Gold-record workflow. It maintains only the
already-public reference schema, a local document validator, boundary
documentation, and visibly synthetic tests. Real reference EPGs, evidence,
adjudication artifacts, access review, and gated publication remain in a
separate protected process.

The already-public Gold Card source is tracked at
`datasets/h2epr_bench_gold/huggingface/README.md`. Updating that README must not
read, download, validate, or rewrite any gated record.

## 6. Release receipt

Every downstream promotion records:

- GitHub PR, merge commit, and tree;
- affected source subtree and per-file hashes;
- Dataset/Space prior and resulting immutable revisions;
- test, build, runtime, browser, and boundary results;
- licensing/provenance confirmation;
- rollback references; and
- outstanding canary/staging cleanup.

No release step uses force push, history rewrite, hidden reconstruction from a
developer worktree, or automatic access to gated records.
