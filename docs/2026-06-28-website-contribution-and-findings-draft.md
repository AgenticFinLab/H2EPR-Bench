# H2EPR-Bench Website Contribution and Findings Draft

Date: 2026-06-28

Status: partially adopted. The hero overview image, hero summary, teaser contribution line, and `Key Findings` section have been adopted into `index.html`. This document remains the rationale and wording record for later review.

## Current Status Summary

The website layout issues have been resolved for the current pass. The current stable page has:

- A project-site identity aligned with `AgenticFinLab/H2EPR-Bench`.
- A polished hero with primary links, release-scale facts, and a new overview image published from `assets/hero/h2epr-benchmark-overview.png`.
- A Background & Motivation section with use-case switching and the world-model vision.
- Benchmark Construction, Dataset Overview, Interactive Explorer, Representative Event Processes, and Results & Diagnostics sections.
- A 2-by-2 diagnostics figure grid whose image frames and captions have been normalized.
- A `Key Findings` section between Results & Diagnostics and Access.
- Access links for the public dataset, gated Gold companion, and Explorer Space.

## Adopted Wording

The following wording has been adopted into the page.

Hero summary:

> H²EPR-Bench evaluates real-world event understanding across summarization, event-process reconstruction, prediction, and simulation from fixed evidence contexts.

Hero teaser:

> H²EPR-Bench maps real-world events into hierarchical heterogeneous Event-Process Graphs for reconstruction, analysis, prediction, and simulation.

Findings section title:

> Key Findings

Placement:

> Between `Results & Diagnostics` and `Access`.

The remaining issue addressed by this document was contribution framing. The previous hero sentence was method-centered:

> H²EPR-Bench evaluates whether models can reconstruct hierarchical heterogeneous Event-Process Graphs from fixed evidence contexts.

This is accurate but too abstract for the website opening. It describes the representation and benchmark mechanism, not the direct contribution or use value. The website should make the contribution obvious before introducing the graph representation.

## Contribution Framing Principle

The opening should first say what H²EPR-Bench enables, then explain how it does so. The hierarchical heterogeneous Event-Process Graph is the representation and benchmark target; the contribution is the new resource and evaluation setting it makes possible.

Recommended order:

1. State the direct benchmark value: evaluating real-world event understanding, reconstruction, prediction, and simulation.
2. State the release asset: 1,000 real-world events, fixed evidence contexts, structured event-process data, gated Gold references, public inspection artifacts, and baseline diagnostics.
3. State the method/representation: hierarchical heterogeneous Event-Process Graphs.
4. State the broader use: model evaluation, agent-system evaluation, event analysis, continuation prediction, and simulation.

## Candidate Hero Summary

Recommended candidate:

> H²EPR-Bench evaluates whether models and agent systems can understand real-world events: summarizing evidence, reconstructing event processes, predicting plausible continuations, and supporting simulation from fixed evidence contexts.

More compact candidate:

> H²EPR-Bench evaluates real-world event understanding across summarization, event-process reconstruction, prediction, and simulation from fixed evidence contexts.

Stronger release-focused candidate:

> H²EPR-Bench is a benchmark and data resource for evaluating how models and agent systems analyze, reconstruct, and extend real-world events from fixed evidence.

Preferred adoption note:

- Use the recommended candidate if the hero should foreground capability breadth.
- Use the compact candidate if the hero must stay close to benchmark language.
- Use the release-focused candidate if the site should read more like a public data-resource page.

## Candidate Teaser / Contribution Line

Current line:

> The benchmark targets structured process understanding: stage progression, actor actions, temporal order, action-result logic, and evidence traceability.

Problem: This is technically correct, but it reads like a metric description rather than a contribution claim.

Adopted replacement:

> H²EPR-Bench maps real-world events into hierarchical heterogeneous Event-Process Graphs for reconstruction, analysis, prediction, and simulation.

Alternative assertive candidate:

> H²EPR-Bench turns real-world event understanding into a measurable benchmark, pairing fixed evidence with structured process data, gated Gold references, diagnostic scoring, and public exploration assets.

More application-facing candidate:

> Built from real-world events, H²EPR-Bench provides the data foundation for evaluating event reconstruction, stress-testing predictive reasoning, and building event-driven simulation workflows.

Preferred adoption note:

The adopted line follows the overview figure directly: real-world events are represented as hierarchical heterogeneous Event-Process Graphs and used for reconstruction, analysis, prediction, and simulation. It avoids listing implementation assets in the hero.

## Contribution Blocks

These can be used as a compact contribution strip near the hero or as a short section before Background & Motivation.

### 1. Real-World Event Resource

> H²EPR-Bench organizes 1,000 real-world events across six domains and 26 categories into a benchmark-scale event resource, with canonical event IDs, metadata, stage records, and public inspection artifacts.

Role: establishes that the work is a dataset/resource, not only a scoring protocol.

### 2. Evidence-Grounded Evaluation Setting

> Each event is tied to fixed evidence contexts, allowing systems to be evaluated on what they can recover from the same information rather than on open-ended generation alone.

Role: clarifies the fixed-evidence setting without overloading the hero.

### 3. Event-Process Reconstruction

> The benchmark evaluates whether models can reconstruct how an event unfolds, including stages, actors, actions, temporal order, action-result links, and supporting evidence.

Role: explains the main benchmark task in direct terms.

### 4. Gold References and Public Artifacts

> Gated Gold references support official scoring, while public FinalCascade graphs, stage tables, Gantt views, and the Explorer make the resource inspectable and reusable.

Role: resolves the public/gated split and gives confidence in the release.

### 5. Baselines and Diagnostics

> Sixteen direct LLM baselines expose where current systems fail, separating schema validity, structural fidelity, temporal consistency, mechanistic reasoning, and evidence use.

Role: positions the results section as part of the contribution, not only an appendix.

### 6. Prediction and Simulation Substrate

> Beyond leaderboard evaluation, the structured event processes can support continuation prediction, agent-system evaluation, event-driven simulation, and future work on linked social and market-process models.

Role: supports the broader project-application narrative while keeping it as an enabled direction rather than claiming it is fully solved in the current release.

## Findings Section Placement

Recommended placement: between `Results & Diagnostics` and `Access`.

Reason:

- It should summarize what the benchmark reveals after the results section.
- It should appear before Access so visitors understand why they should open the dataset, Gold repository, or Explorer.
- It should not be placed after Citation, because that would bury the main takeaways.

Suggested title:

> Key Findings

Alternative title:

> What H²EPR-Bench Reveals

Recommended title: `Key Findings`, because it is short and familiar.

## Findings Draft

The section should use short finding cards, not long paragraphs. Each card should contain a direct title and one concise explanation.

### Finding 1: Valid Graphs Are Not Enough

> Schema-valid outputs still miss temporal order, process structure, and action-result logic.

Grounding: supported by the valid-output rate and diagnostic subscore pattern.

### Finding 2: Process Is the Bottleneck

> Models often retain facts, but struggle to organize them into coherent staged event processes.

Grounding: supported by process-related diagnostic subscores and manual analysis of direct reconstruction failures. This wording is less likely to overclaim than "evidence is easier than process."

### Finding 3: Failure Modes Are Systematic

> Weak sequencing, missing event-type operations, and shallow action-outcome links recur across model families.

Grounding: supported by the failure-mode heatmap and model cards.

### Finding 4: Beyond Reconstruction

> The same event-process substrate supports continuation prediction, agent evaluation, and simulation studies.

Grounding: this is a forward-looking value claim. It should be presented as enabled future work, not as a completed evaluation in Core-1000.

## Findings Section Layout Draft

Proposed layout:

- A short intro sentence:

> H²EPR-Bench exposes where current systems lose event structure, and turns those errors into reusable diagnostics for reconstruction, prediction, and simulation.

- Four cards in a 2-by-2 responsive grid:
  - Valid Graphs Are Not Enough
  - Process Is the Bottleneck
  - Failure Modes Are Systematic
  - Beyond Reconstruction

## Recommended Immediate Adoption Set

If adopting in the next website pass, use:

1. Replace the hero summary with:

> H²EPR-Bench evaluates whether models and agent systems can understand real-world events: summarizing evidence, reconstructing event processes, predicting plausible continuations, and supporting simulation from fixed evidence contexts.

2. Replace the teaser line with:

> H²EPR-Bench maps real-world events into hierarchical heterogeneous Event-Process Graphs for reconstruction, analysis, prediction, and simulation.

3. Add a `Key Findings` section between `Results & Diagnostics` and `Access`.

4. Use the four finding cards above in a 2-by-2 layout, with low-saturation color variation across cards.

## Self-Review Notes

- Page text has adopted the compact hero summary, the revised teaser line, and the four-card Key Findings section.
- Claims about prediction, simulation, and world models are framed as supported directions or enabled future work unless the line explicitly says benchmark/data resource.
- The draft avoids presenting FinalCascade as Gold.
- The draft keeps the current release centered on Core-1000 and fixed-evidence reconstruction while allowing broader positioning.
