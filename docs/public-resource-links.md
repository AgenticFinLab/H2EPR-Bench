# Public resource links and button contract

Date verified: 2026-08-22

`manifests/public_resource_links.json` is the machine-readable authority for
the public H2EPR-Bench resource identities. Visible links may use shorter
labels, but they must resolve to the exact URLs in that manifest.

## Information hierarchy

The canonical reader-facing names are:

1. `Project Website` for the project overview;
2. `Event Explorer` (or the action label `Explore Events`) for interactive browsing;
3. `Public Dataset` for the 3,000-event distribution;
4. `FinMycelium System` for the multi-agent reconstruction system;
5. `Reference EPGs (Gated)` for the controlled scoring references; and
6. `Release Repository` for the canonical public source monorepo.

`Code` and `GitHub` are not used as standalone labels for the release
repository because that repository is not the FinMycelium implementation or an
experimental-code release. `Gold` is not used as an unqualified public button
label. FinMycelium must be described as the multi-agent event reconstruction
system that produced public Draft EPG construction artifacts; it must never be
described as a source of reference records.

Each surface omits its own destination from its resource group. The
AgenticFinLab organization website is attribution rather than a project
resource and may appear as a quiet footer or prose link, not as a resource
button.

The H2EPR-Bench paper has no verified public URL at this gate. The forthcoming
status may appear in citation prose, but it is not presented as a badge or
button. No paper or arXiv link may be created until the manifest records a
reviewed URL.

## Surface rules

- The website prioritizes `Explore Events`, `Public Dataset`, and `Benchmark
  Results`, then presents the three supporting resources. Buttons use one
  transparent outline treatment, one icon size and one stroke weight; meaning
  is not encoded through unrelated fill colors.
- GitHub and Hugging Face README files use one compact flat-square badge style
  and one color. Badge alternative text remains the complete destination name.
- The Explorer sidebar uses full-width native Streamlit link buttons. Dataset
  and system links precede the controlled reference-access and release-source
  links.
- External links use descriptive accessible names. A destination must not be
  mislabeled; in particular, the monorepo is `Release Repository`, not `Code`,
  `GitHub`, or `Website`.
- Mobile layouts may wrap or stack buttons, but may not hide a required public
  resource.

## Resource roles

Public Dataset links may point at the stable repository landing page for
discovery. Reproducibility and runtime data-loading links use the same
immutable Dataset revision recorded in the release contract and Explorer
source. Publication is blocked while that revision is unbound.

The Hugging Face card sources tracked in this monorepo are public metadata
only. The Gold card source contains no Gold record and creates no mechanism for
accessing gated content.
