# Local Semantic Event Clustering Pilot Design

## Goal

Measure how much a local multilingual embedding stage can reduce the 19,699 provisional evidence groups before GPT triage without deleting any article or making any importance decision.

## Scope

This is an experimental-branch pilot over the saved 20,450-row 2026-08-20 artifact. It does not change GitHub `main`, the production schedule, the six-dimension rubric, or the publication threshold. The pilot may consolidate only evidence judged to describe the same event.

## Architecture

1. Consume the URL-recovery report and build one semantic text per provisional group from its effective title and usable summary evidence.
2. Leave unresolved placeholder groups as singletons. They require metadata or body recovery and are never discarded.
3. Generate normalized multilingual embeddings locally with FastEmbed and a fixed multilingual model. No GPT or embedding API is used.
4. Use a local nearest-neighbor index to produce bounded candidate neighbors instead of an all-pairs comparison.
5. Extract deterministic anchors from text: typed numeric facts, dates, named capitalized or CJK spans, and explicit place terms available in the text.
6. Auto-merge only high-similarity pairs that pass time and identity-anchor gates. Changing casualty counts such as 21 then 23 do not identify different events; the cluster preserves both values as a versioned fact conflict. Different metric types, incompatible event dates, explicit countries, or incompatible identity anchors raise review risk instead of silently discarding evidence.
7. Keep medium-similarity pairs in an ambiguity review queue. Similarity or keywords never score importance and never delete a group.
8. Produce a conservation ledger from every input `row_id` to exactly one semantic cluster and package one compact event card per cluster.

## Error Measurement

The pilot reports two audit estimates rather than claiming unknowable global truth:

- false-merge estimate: model review of every auto-merged cluster when the count is bounded, otherwise a deterministic sample of at least 200 clusters;
- missed-merge estimate: model review of at least 200 highest-similarity pairs left separate, excluding pairs blocked by explicit factual contradictions.

Known deterministic duplicate groups serve as positive controls. Explicitly unrelated synthetic fixtures serve as negative controls. Audit denominators and uncertain cases remain visible.

## Acceptance

- zero GPT/API tokens for embedding and nearest-neighbor generation;
- exact row conservation with zero automatic deletions and zero importance decisions;
- deterministic clustering for fixed vectors and configuration;
- unresolved-title rows remain present as singletons;
- changing casualty totals remain mergeable when event identity anchors agree, while all conflicting values remain preserved;
- full-run counts, elapsed time, local resource usage, and audited false-merge/missed-merge estimates are recorded;
- no production promotion based on this single artifact.

