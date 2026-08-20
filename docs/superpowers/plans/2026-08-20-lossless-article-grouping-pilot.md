# Lossless Article Grouping Pilot — Implementation Plan

> Experimental branch only. Do not wire this pilot into the production schedule without a separate promotion decision.

**Goal:** Run a lossless first-stage grouping pilot on the saved 20,450-row source list, measure the reduction in downstream model units, and use model review to find false merges and missed merges.

**Architecture:** A standalone standard-library Python CLI reads `source-candidates.json`, assigns a unique ordinal `row_id` to every source row, consolidates only canonical-URL or normalized exact-title evidence, and routes structurally unusable titles to recovery. It performs no importance scoring, non-news classification, deletion, or publication decision.

## Task 1: Freeze executable invariants with TDD

**Files:**
- Create: `tests/test_pilot_lossless_article_grouping.py`
- Create: `scripts/pilot_lossless_article_grouping.py`

1. Write tests for URL canonicalization, exact descriptive-title grouping, separate recovery rows for placeholders, row conservation, duplicate source candidate IDs, deterministic output, forbidden decision fields, and tamper detection.
2. Run `python -m unittest tests.test_pilot_lossless_article_grouping -v` and observe RED before implementation.
3. Implement only the behavior required by the tests.
4. Run the same test command and `python -m py_compile scripts/pilot_lossless_article_grouping.py` until GREEN.

Completion condition: all ten frozen tests pass and every new public function is exercised.

## Task 2: Execute the saved 20,450-row dataset

1. Run `python scripts/pilot_lossless_article_grouping.py --input pilot-input/source-candidates.json --output pilot-output/lossless-grouping-report.json --sample-size 200 --seed 20260820`.
2. Independently run `python scripts/pilot_lossless_article_grouping.py --verify pilot-output/lossless-grouping-report.json`.
3. Record input rows, provisional groups, consolidated evidence rows, recovery rows, and zero-deletion counters.

Completion condition: `CONSERVATION_OK` and matching independent counts.

## Task 3: Model audit and corrective loop

Review every canonical-URL multi-row group, every exact-title multi-row group, 200 deterministic title-recovery rows, and 200 deterministic suspected near-pair candidates.

If the model finds a structural false merge, add the observed format to the existing recovery test, confirm RED, implement the minimal format rule, and rerun the full dataset. Never convert the observation into an importance keyword or deletion rule.

Completion condition: corrected full run passes conservation; all confirmed structural false merges are removed; limitations and uncertain near pairs are recorded.

## Task 4: Evidence and publication

1. Write a bilingual result at `docs/pilot-results/2026-08-20-lossless-article-grouping-pilot-result.md`.
2. Rerun focused tests, compile check, full deterministic run, and independent verification.
3. Commit only pilot source, tests, design, plan, and compact result documentation to an experimental GitHub branch based on verified current `main`.
4. Do not commit the 23 MB source dataset or generated full report.

Completion condition: the uploaded commit is traceable, production `main` and the scheduled task remain unchanged, and the report states that three independent 24-hour datasets are required before promotion can be considered.

