# H2EPR-Bench Website Contribution and Findings Draft

Date: 2026-06-28

Status: partially adopted. The hero overview image, hero summary, teaser contribution line, and `Key Findings` section have been adopted into `index.html`. This document remains the rationale and wording record for later review.

## Current Status Summary

The website layout issues have been resolved for the current pass. The current stable page has:

- A project-site identity aligned with `AgenticFinLab/H2EPR-Bench`.
- A polished hero with primary links, release-scale facts, and a new overview image.
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

> The release connects real-world evidence, structured event-process data, gated Gold references, diagnostic LLM baselines, and public exploration assets into one benchmark for event analysis, prediction, and simulation.

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

Recommended replacement:

> The release connects real-world evidence, structured event-process data, gated Gold references, diagnostic LLM baselines, and public exploration assets into one benchmark for event analysis, prediction, and simulation.

More assertive candidate:

> H²EPR-Bench turns real-world event understanding into a measurable benchmark, pairing fixed evidence with structured process data, gated Gold references, diagnostic scoring, and public exploration assets.

More application-facing candidate:

> Built from real-world events, H²EPR-Bench provides the data foundation for evaluating event reconstruction, stress-testing predictive reasoning, and building event-driven simulation workflows.

Preferred adoption note:

The first recommended replacement is the most balanced for the website. It names the concrete assets and avoids making the opening sound like only a graph-method page.

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

> Many systems produce schema-valid outputs, but validity does not imply successful event-process reconstruction. The main gap lies in recovering temporal order, process structure, and action-result logic.

Grounding: supported by the valid-output rate and diagnostic subscore pattern.

### Finding 2: Evidence Is Easier Than Process

> Models tend to preserve evidence-bearing content more reliably than they organize that content into coherent event processes. This makes H²EPR-Bench useful for separating source grounding from process understanding.

Grounding: supported by evidence subscore being higher than temporal/mechanistic subscores. Wording should remain careful because this claim can sound too broad if detached from the direct-reconstruction setting.

### Finding 3: Failure Modes Are Systematic

> The same bottlenecks recur across model families: weak temporal sequencing, missing event-type operations, and shallow links between actions and outcomes. These errors are diagnostic signals, not isolated formatting failures.

Grounding: supported by the failure-mode heatmap and model cards.

### Finding 4: Event Understanding Needs Structured Targets

> Summaries and timelines are useful but insufficient for measuring how models understand evolving events. H²EPR-Bench makes stages, actors, relations, evidence, and process logic explicit enough to score and inspect.

Grounding: connects Background & Motivation to the benchmark task.

### Finding 5: A Substrate for Prediction and Simulation

> Structured event-process data enables more than reconstruction: future experiments can mask later stages, ask agents to continue partially observed events, compare predicted trajectories with Gold references, and link multiple events into larger market or social-process simulations.

Grounding: this is a forward-looking value claim. It should be presented as enabled future work, not as a completed evaluation in Core-1000.

## Findings Section Layout Draft

Proposed layout:

- A short intro sentence:

> H²EPR-Bench is designed to reveal where event understanding breaks, and to provide reusable structure for the next generation of event prediction and simulation tasks.

- Five cards in a responsive grid:
  - Valid Graphs Are Not Enough
  - Evidence Is Easier Than Process
  - Failure Modes Are Systematic
  - Event Understanding Needs Structured Targets
  - A Substrate for Prediction and Simulation

- Optional small callout under the cards:

> The current release focuses on fixed-evidence event-process reconstruction. Prediction, simulation, and linked world-model studies are natural extensions built on the same structured event substrate.

## Recommended Immediate Adoption Set

If adopting in the next website pass, use:

1. Replace the hero summary with:

> H²EPR-Bench evaluates whether models and agent systems can understand real-world events: summarizing evidence, reconstructing event processes, predicting plausible continuations, and supporting simulation from fixed evidence contexts.

2. Replace the teaser line with:

> The release connects real-world evidence, structured event-process data, gated Gold references, diagnostic LLM baselines, and public exploration assets into one benchmark for event analysis, prediction, and simulation.

3. Add a `Key Findings` section between `Results & Diagnostics` and `Access`.

4. Use the five finding cards above, with a visual style closer to result takeaways than to a dense paper paragraph.

## Self-Review Notes

- No page text has been adopted yet, except for the hero overview image.
- Claims about prediction, simulation, and world models are framed as supported directions or enabled future work unless the line explicitly says benchmark/data resource.
- The draft avoids presenting FinalCascade as Gold.
- The draft keeps the current release centered on Core-1000 and fixed-evidence reconstruction while allowing broader positioning.
