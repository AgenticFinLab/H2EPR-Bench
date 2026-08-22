# Public resource links and button contract

Date verified: 2026-08-22

`manifests/public_resource_links.json` is the machine-readable authority for
the public H2EPR-Bench resource identities. Visible links may use shorter
labels, but they must resolve to the exact URLs in that manifest.

## Information hierarchy

Primary resources are presented in this order:

1. Public Dataset;
2. Explorer;
3. FinMycelium;
4. Code; and
5. Website when the current surface is not the website itself.

The manual-gated Gold companion and the AgenticFinLab organization website are
secondary resources. Gold must always be labeled `Gated Gold` or otherwise
identify that access is controlled. FinMycelium must be described as the
multi-agent event reconstruction system that produced public Draft EPG
construction artifacts; it must never be described as a source of Gold
records.

The H2EPR-Bench paper has no verified public URL at this gate. Surfaces may show
the non-interactive label `Paper forthcoming`, but must not create a paper or
arXiv link until the manifest records a reviewed URL.

## Surface rules

- The website uses compact text chips in the header and hero, descriptive rows
  in Access, and low-emphasis footer links.
- GitHub and Hugging Face README files use the same compact flat-square badge
  row, followed by ordinary text links so the destinations remain readable
  when badge images are blocked.
- The Explorer sidebar uses full-width native Streamlit link buttons. Dataset
  and project links precede the controlled Gold-access link.
- External links use descriptive accessible names. A destination must not be
  mislabeled; in particular, a GitHub link is `Code`, not `Website`.
- Mobile layouts may wrap or stack buttons, but may not hide a required public
  resource.

## Release boundary

Public Dataset links may point at the stable repository landing page for
discovery. Reproducibility and runtime data-loading links retain the immutable
Dataset revision `1d01f3649ace0301ac3bbe9ee875eea660347a29`.

The Hugging Face card sources tracked in this monorepo are public metadata
only. The Gold card source contains no Gold record and creates no mechanism for
accessing gated content.
