# Visible Source Image Delivery Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep verified-but-undelivered source images recoverable instead of publishing a zero-image canonical run.

**Architecture:** Reuse the existing mobile ledger limitation and stage machine. Block `NATIVE_MEDIA_UNAVAILABLE` at `visuals-completed`, retain source-exhausted omission, and align the active operator contracts.

**Tech Stack:** Python 3.12+, `unittest`, Markdown contracts, existing mobile ledger schema 1.5.0.

## Global Constraints

- Add no schema field, validator, receipt, manifest, recovery state, or compatibility mode.
- Mobile-native must not claim local download or materialization.
- Preserve the same run and all completed news stages.

---

### Task 1: Lock the ledger behavior

**Files:**
- Modify: `tests/test_manage_mobile_run_log.py`
- Modify: `scripts/manage_mobile_run_log.py`

**Interfaces:**
- Consumes: existing `delivery_profile`, `native_media_status`, and `capability_limitations`.
- Produces: validation that refuses progress past `visuals-completed` while `NATIVE_MEDIA_UNAVAILABLE` is present.

- [ ] Add tests for the blocked forward transition, blocked completion, and allowed source-exhausted completion.
- [ ] Run the focused tests and confirm the new cases fail for the current permissive behavior.
- [ ] Add the smallest validation condition to the existing manager.
- [ ] Re-run focused tests and confirm they pass.

### Task 2: Align active contracts

**Files:**
- Modify: `INSTALL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/collect-news-images/SKILL.md`
- Modify: `.agents/skills/recover-news-run/SKILL.md`
- Modify: `docs/mobile-run-ledger.md`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: the Task 1 stage boundary.
- Produces: one consistent operator rule distinguishing delivery failure from source exhaustion.

- [ ] Add a structural regression that rejects the retired nonblocking-delivery wording.
- [ ] Confirm it fails against the current documents.
- [ ] Replace only the conflicting active statements with the recovery rule.
- [ ] Confirm focused tests pass.

### Task 3: Release and operational cutover

**Files:**
- Modify: `VERSION-RECORD.md`
- Regenerate: `bootstrap/*`
- Operational update: `run-logs/logs/current.json`

**Interfaces:**
- Consumes: verified source commit and the existing run-log record.
- Produces: installable capsule plus a truthful recoverable current run.

- [ ] Run the complete bundled-Python suite.
- [ ] Regenerate and verify the capsule with the exact source commit.
- [ ] Complete two unchanged-fingerprint final-state audit cycles.
- [ ] Push source and capsule, then correct the current run without creating a replacement run.
