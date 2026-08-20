# Lossless Article Grouping Pilot Design

## Goal

Measure how much model workload can be reduced before scoring without deleting low-value events, and use model review to detect false merges and missed merges before any rule is promoted to the daily schedule.

## Scope

This is a non-production pilot against the saved 20,450-row source candidate artifact from the 2026-08-20 run. It does not change the daily schedule, the six-dimension rubric, the C publication threshold, or GitHub `main`.

## Non-negotiable invariants

- Article cleanup never assigns importance, grade, or publication status.
- Every input row remains auditable and maps to exactly one provisional group.
- Row conservation uses a pilot-generated ordinal `row_id`; source `candidate_id` values remain evidence and are not assumed unique.
- Duplicate rows are consolidated as evidence; they are not deleted from the audit trail.
- Placeholder or unusable titles route to `needs_title_recovery`; title shape alone never produces `non_news`.
- Keywords, country, region, topic, publisher, and predicted importance cannot merge, exclude, promote, or demote an item.
- Output counts are article and provisional-group counts. They cannot be called semantic events or news counts.

## Pilot grouping rules

1. Canonical URL grouping removes fragments, normalizes scheme and host casing, removes default ports, sorts query parameters, and removes only known tracking parameters such as `utm_*`, `fbclid`, and `gclid`.
2. Exact-title grouping applies Unicode NFKC, case folding, and punctuation/whitespace normalization. It groups only descriptive titles with the same section.
3. Empty titles, domain-only `news report` labels, bare UUIDs, and `article` identifiers are never title-grouped. They remain separate recovery items.
4. No fuzzy or semantic merge is automatic in this pilot. Near-title pairs are generated only as a model-review queue for measuring missed merges.

## Model review

The model reviews three strata:

- every multi-row exact-title group for false merges;
- a deterministic sample of title-recovery rows for real-news recoverability versus true non-news;
- a deterministic sample of high-similarity unmerged pairs for missed merges.

The model records one structured verdict per reviewed item and does not modify the pilot grouping. Any disagreement remains evidence for the next experimental revision.

## Promotion criteria

The rule may be proposed for production only after three independent 24-hour datasets satisfy all of the following:

- conservation is exact: every input row appears once;
- zero confirmed false merges in the full exact-group review;
- zero title-only false deletions, because the pilot has no title-only deletion path;
- model-reviewed recovery and missed-merge rates are reported with their sample sizes;
- the same code and policy hash produce deterministic counts;
- the production design and tests are separately approved.

## Deliverables

- `scripts/pilot_lossless_article_grouping.py`: read-only pilot classifier and report generator.
- `tests/test_pilot_lossless_article_grouping.py`: conservation and grouping contract tests.
- `pilot-output/lossless-grouping-report.json`: full-run counts and review queues, not committed.
- `docs/pilot-results/2026-08-20-lossless-article-grouping.md`: compact bilingual result and promotion verdict.

