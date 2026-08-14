# H2EPR-Bench licensing policy

The repository uses two licenses because software source and benchmark
content have different reuse boundaries.

## Apache License 2.0

Apache-2.0 applies to executable source and configuration, including:

- `scripts/**/*.py`;
- `spaces/**/*.py`, Dockerfiles, requirements, and runtime configuration;
- validator source under `datasets/**/scripts/` and
  `datasets/**/validators/`;
- `tests/**/*.py`;
- `static/**/*.js` and `static/**/*.css`; and
- `.github/workflows/**`.

The full text is in `LICENSES/Apache-2.0.txt`.

## CC BY-NC 4.0

CC BY-NC 4.0 applies to public data, content, and assets, including:

- website HTML and prose;
- Markdown documentation;
- `assets/**` and `data/**`;
- JSON schemas, release contracts, and synthetic fixtures under `datasets/**`;
- citations and other non-executable release metadata; and
- the corresponding released H2EPR-Bench Dataset content unless a file states
  a different license.

The license notice and canonical legal-code link are in
`LICENSES/CC-BY-NC-4.0.md`.

## Mixed and third-party files

For a mixed file, the classification above applies to the repository owner's
copyrightable contribution according to the file's primary role. Third-party
names, facts, software dependencies, fonts, and other material remain subject
to their own rights and licenses. The repository grants only rights the
publisher is authorized to grant.

Real reference EPGs (Gold), evidence packages, and other gated material are
not distributed by this GitHub repository and are not licensed by this notice.
