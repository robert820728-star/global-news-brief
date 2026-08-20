# Semantic Event Ledger Design

## Goal

Count, grade, and publish news as semantic events rather than article URLs or title groups, while retaining every source row as auditable evidence so no input can disappear silently.

## Chosen approach

Use a row-disposition ledger plus explicit semantic-event identities. Each in-window source row receives exactly one disposition: `event_evidence`, `non_news`, or `unresolved`. Event evidence must point to one candidate `semantic_event_id`; many rows may point to the same event. Non-news rows require a concrete reason. An unresolved row prevents the audit from claiming completion.

Alternatives rejected:

- Treating title-similarity clusters as events is cheap but cannot establish that two differently worded reports describe the same event or that similar headlines describe different events.
- Scoring every article row directly preserves recall but multiplies syndicated reports, wastes model budget, and still does not produce event-level news.

## Data contract

The latest audit run contains `article_dispositions`. Each item has `source_id`, `url`, `disposition`, `semantic_event_id`, and `reason`. The `(source_id, url)` pairs must exactly match the successful source-pool rows, including repeated URLs from different discovery routes.

Each latest-run candidate contains a unique `semantic_event_id` and `event_identity` with a non-empty `who_or_what`, `what_happened`, `where`, `when`, and `semantic_merge_basis`. Candidate URLs remain evidence links, not event counts.

`processing_counts` adds `event_evidence_article_row_count`, `non_news_article_row_count`, and `unresolved_article_row_count`. These three fields must sum to `in_window_article_row_count`. `semantic_event_count`, `scored_event_count`, and `deduplicated_candidate_count` must all equal the number of candidate event objects. Only this number may be described as news candidates or scored news.

## Pipeline behavior

`preprocess-news-candidates` performs deterministic time-window filtering, URL normalization, exact duplication, and provisional title grouping. Its output is explicitly article-level and never claims semantic events.

`select-news-events` reviews article content or source-backed summaries, creates semantic events, and writes the disposition ledger. Ambiguous material defaults to an event candidate rather than `non_news`. Title similarity alone cannot justify semantic merging or non-news classification.

`audit-news-candidates` validates complete row disposition, unique event identities, event mappings, count conservation, and six-dimension scoring for every semantic event. Publication remains free of arbitrary article or event quotas.

## Error handling

- Missing or duplicate row dispositions fail the candidate audit.
- `event_evidence` without a valid `semantic_event_id` fails.
- `non_news` without a concrete reason fails.
- Any `unresolved` row fails completion and must be reprocessed; it cannot be hidden by a count adjustment.
- Article counts remain internal coverage diagnostics and must never be presented as news counts.

## Verification

Tests cover row partition conservation, multiple reports mapping to one event, rejection of unresolved rows, rejection of article-level candidates without event identity, prompt terminology, publisher compatibility, and the complete regression suite.
