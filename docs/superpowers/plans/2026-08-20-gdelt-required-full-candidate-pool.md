# GDELT-Resilient Full Candidate Pool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep publication running through GDELT DOC API failures and send every verified in-window discovery item into deduplication without a fixed per-source cutoff.

**Architecture:** Add Retry-After-aware retries, an official GDELT export-archive fallback, explicit degraded coverage, and replace the materializer's top-30 selection with complete ranked URL transfer. Lock the same contract in runtime validation and execution guidance.

**Tech Stack:** Python 3 standard library, JSON, Markdown, `unittest`

## Global Constraints

- GDELT is primary; CNA and China News Service are optional supplements.
- A DOC API failure must not stop publication.
- Live fallback uses GDELT official export archives; cache is last resort and must be labeled.
- All verified in-window discovery candidates enter the pool.
- No fixed discovery count limit may replace complete transfer.
- Do not change grading, images, delivery, or scheduling.
- Do not commit or push without separate authorization.

---

### Task 1: Lock resilient GDELT behavior

**Files:**
- Modify: `source-route-config.json`
- Modify: `scripts/fetch_source_routes.py`
- Test: `tests/test_fetch_source_routes.py`

- [ ] Add a failing test proving that `Retry-After` is honored.
- [ ] Add a failing test proving that continued DOC API failure invokes the official export fallback.
- [ ] Add a failing test proving that total GDELT unavailability is explicit but does not stop publication when supplements have candidates.
- [ ] Implement GDELT acquisition-mode and live-readiness coverage fields.
- [ ] Run the focused route tests and confirm GREEN.

### Task 2: Remove fixed candidate truncation

**Files:**
- Modify: `scripts/materialize_source_scans.py`
- Modify: `scripts/recover_same_source_leads.py`
- Modify: `scripts/manage_candidate_audit.py`
- Test: `tests/test_materialize_source_scans.py`
- Test: `tests/test_manage_candidate_audit.py`

- [ ] Add a failing test with more than 30 in-window articles and require every URL in `selected_item_urls`.
- [ ] Add a failing audit test rejecting successful coverage that selects fewer URLs than `ranked_count`.
- [ ] Replace top-30 slices with complete ranked URL transfer.
- [ ] Update validation to require `selected_for_pool_count == ranked_count` and no non-empty overflow list.
- [ ] Run the focused materializer and audit tests and confirm GREEN.

### Task 3: Align execution contracts

**Files:**
- Modify: `news-source-pool.json`
- Modify: `news-brief-settings.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/acquire-news-candidates/SKILL.md`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `.agents/skills/audit-news-candidates/SKILL.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `tests/test_pipeline_contract.py`

- [ ] Add failing contract assertions for resilient GDELT, complete candidate transfer, and removal of the stale fixed-site rule.
- [ ] Update configuration and all execution surfaces to the same contract.
- [ ] Run contract tests and confirm GREEN.

### Task 4: Verify and record

**Files:**
- Modify: `VERSION-RECORD.md`

- [ ] Run focused tests for route fetching, materialization, audit, and pipeline contracts.
- [ ] Run the full test suite and report every failure without hiding pre-existing capsule overlap.
- [ ] Validate changed JSON files and run `git diff --check`.
- [ ] Add a bilingual version record with RED/GREEN evidence and known limitations.
