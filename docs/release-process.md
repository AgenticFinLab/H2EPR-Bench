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
3. keep Dataset revision `1d01f3649ace0301ac3bbe9ee875eea660347a29` fixed;
4. use an isolated canary/staging target when available;
5. validate build/runtime logs, health, desktop/mobile behavior, deep links,
   filters/reset, three timeline modes, Draft preview/download, unavailable
   state, external links, console errors, and page errors;
6. create a rollback reference before production promotion; and
7. update production only with an ordinary non-force operation after explicit
   deployment authorization.

A broken promotion is reverted with a new ordinary commit restoring the prior
tree. Canary deletion and production promotion are separate lifecycle actions.

## 4. Public Dataset

The GitHub contract fixes the currently accepted public revision, but merging
source does not publish Dataset records. A Dataset release has an independent
manual gate that validates a sanitized staging tree, six mirror schemas and
hashes, all cardinalities and joins, 2,876 direct Draft EPGs, 124 unavailable
markers, content hashes, the Dataset card, and the CC BY-NC 4.0 boundary.

Only the public Dataset repository is read or written by this flow. A new
revision requires an explicit release record and a coordinated source update
that pins the new immutable revision.

## 5. Gold companion

The public monorepo publishes no Gold-record workflow. It maintains only the
already-public reference schema, a local document validator, boundary
documentation, and visibly synthetic tests. Real reference EPGs, evidence,
adjudication artifacts, access review, and gated publication remain in a
separate protected process.

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
