# Event Region and Time Identity Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject source-derived region assignments and old-event republication before semantic-event scoring.

**Architecture:** Extend semantic event identity with structured geography and material-update time. Enforce the mapping and exact-window rules in the existing candidate-audit validator, then bind the same contract into the orchestration prompts and selection skill.

**Tech Stack:** Python 3, JSON Schema, unittest, Markdown skills.

## Global Constraints

- Latest GitHub `main` is the only source baseline.
- Source discovery buckets are not event geography.
- Old summaries without an independently verified material update are non-news.
- The gate is fail closed before all six-dimension scoring.

---

### Task 1: Executable identity contract

**Files:**
- Modify: `schemas/news-candidate-audit.schema.json`
- Modify: `scripts/manage_candidate_audit.py`
- Test: `tests/test_manage_candidate_audit.py`

**Interfaces:**
- Consumes: latest run window and semantic-event candidates.
- Produces: validation errors for region/time conflicts; no errors for valid new or continuing events.

- [ ] Add RED tests for CHN/TWN/GLB mapping, source independence, out-of-window updates, and retrospective old events.
- [ ] Run `python -m unittest tests.test_manage_candidate_audit` and confirm the new tests fail.
- [ ] Add the structured identity schema and minimal validator rules.
- [ ] Re-run the target test and confirm it passes.

### Task 2: Orchestration and skill contract

**Files:**
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `.agents/skills/audit-news-candidates/SKILL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `news-brief-settings.md`
- Test: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `EVENT_REGION_AND_TIME_IDENTITY_GATE`.
- Produces: consistent selection, audit, and scheduling instructions.

- [ ] Add a RED contract test requiring the gate and all structured fields.
- [ ] Run `python -m unittest tests.test_pipeline_contract` and confirm failure.
- [ ] Add the gate to every required runtime document and explain source/region and publication/update separation.
- [ ] Re-run the contract test and confirm it passes.

### Task 3: Verify and publish

**Files:**
- Modify: `bootstrap-capsule/*` using the repository builder only.

**Interfaces:**
- Consumes: passing source tree.
- Produces: GitHub source commit plus verified bootstrap capsule commit.

- [ ] Run the complete unittest suite and skill validator.
- [ ] Build and verify the bootstrap capsule bound to the source commit.
- [ ] Commit the verified source and capsule to a feature branch, then fast-forward `main`.
- [ ] Read back GitHub `main` and verify the committed blobs and capsule.
