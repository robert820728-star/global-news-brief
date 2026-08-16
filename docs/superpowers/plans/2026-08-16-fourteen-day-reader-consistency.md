# Fourteen-Day Audit and Reader Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce complete six-dimension shortlist scoring, current-run C-or-above reader coverage, and reader explanations for omitted images.

**Architecture:** Keep `state/candidate-audit.json` as the sole shortlist and grade source. The manifest remains the event exchange layer, while the canonical publisher compares the latest audit run to the manifest. Image backend evidence and reader wording use separate fields.

**Tech Stack:** Python 3, `unittest`, JSON Schema, Markdown contracts.

## Global Constraints

- Reader time window remains the exact previous 24 hours.
- Audit retention remains 14 days.
- C or above means `SS` through `C`; `C-` remains conditional.
- No-image notes must be Traditional Chinese and must not expose retry or download internals.

---

### Task 1: Shortlist score contract

**Files:** `tests/test_manage_candidate_audit.py`, `scripts/manage_candidate_audit.py`, `schemas/news-candidate-audit.schema.json`.

**Interfaces:** Consumes `news-source-pool.json:ranking.dimensions`; produces `ranked_items[].importance_breakdown: dict[str, number]`.

- [x] Add a failing test that removes `importance_breakdown` and expects an error.
- [x] Add a failing test that sets `public_impact=31` and expects a weight and total error.
- [x] Validate exact keys, numeric ranges, configured maxima, and a sum equal to `importance_score` within `0.01`.
- [x] Run the two tests and confirm PASS.

### Task 2: C-or-above reader mapping

**Files:** `tests/test_manage_candidate_audit.py`, `tests/test_publish_news_brief.py`, `scripts/manage_candidate_audit.py`, `scripts/publish_news_brief.py`.

**Interfaces:** Produces `selected_event_id: str` for every C-or-above selected or merged candidate; consumes manifest `events[].event_id`.

- [x] Add a failing test for a C-grade merged candidate with no event mapping.
- [x] Add a failing publisher test for a mapped merged event absent from the manifest.
- [x] Require the mapping and compare the complete mapped set with manifest IDs.
- [x] Run both tests and confirm PASS.

### Task 3: Reader explanation for omitted images

**Files:** `tests/test_validate_news_brief.py`, `scripts/validate_news_brief.py`, `schemas/news-event-manifest.schema.json`, `news-brief-template.md`.

**Interfaces:** Produces `images.reader_omission_note: string | null`; renders `**圖片說明：**<note>`.

- [x] Add a failing brief test for an omitted-image event whose note is absent from Markdown.
- [x] Require the field when final image status is `omitted`.
- [x] Require exact note rendering before event details.
- [x] Run the test and confirm PASS.

### Task 4: Runtime and scheduled acceptance

**Files:** runtime capsule, candidate audit, manifest, reader brief, release receipt.

- [ ] Rebuild the candidate runtime capsule and verify its file fingerprint.
- [ ] Run the complete unit suite and distinguish pre-existing Windows-only failures from regressions.
- [ ] Wait five minutes after the final settings change.
- [ ] Start one local candidate schedule run.
- [ ] Validate the audit, manifest, brief, attachments, and canonical publisher output.
- [ ] If any acceptance condition fails, record the first failing checkpoint and begin the next bounded iteration.

