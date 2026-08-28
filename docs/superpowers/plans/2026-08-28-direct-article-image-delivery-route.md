# Direct Article Image Delivery Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require the direct article-media URL path before image unavailability or source exhaustion, while allowing successful direct delivery to skip unnecessary later fallbacks.

**Architecture:** Extend the existing event checklist in `image-evidence.json` with one boolean and enforce it inside the existing mobile run manager. Align the existing high-authority image contracts and regression checks; introduce no new runtime component.

**Tech Stack:** Python 3 standard library, `unittest`, Markdown contracts, Git.

## Global Constraints

- Preserve `NATIVE_MEDIA_UNAVAILABLE` and `visuals-completed` recovery semantics.
- A bare URL or Markdown image string is not visible delivery.
- Do not add a schema file, validator, receipt, recovery state, compatibility mode, or source class.
- Use test-first red-green implementation.

---

### Task 1: Reproduce direct-media-path omission

**Files:**
- Modify: `tests/test_manage_mobile_run_log.py`

**Interfaces:**
- Consumes: existing `unavailable_image_event()` and mobile ledger transition helpers.
- Produces: `test_qualified_direct_media_url_requires_actual_attempt_before_unavailable`.

- [ ] **Step 1: Write the failing test**

Create an unavailable event with `qualified_image_found=True`, all existing source-tier flags true, `delivery_attempted=True`, but `direct_media_url_attempted=False`. Advance the run to `visuals-completed` and assert rejection mentioning the direct media URL path.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_manage_mobile_run_log.MobileRunLogTests.test_qualified_direct_media_url_requires_actual_attempt_before_unavailable -v`

Expected: FAIL because the current manager accepts the evidence.

### Task 2: Enforce direct article-media delivery route

**Files:**
- Modify: `scripts/manage_mobile_run_log.py`
- Modify: `tests/test_manage_mobile_run_log.py`
- Modify: `tests/fixtures/mobile-reader-missing-verified-image-evidence.json`

**Interfaces:**
- Consumes: event-level `direct_media_url_attempted: bool`.
- Produces: existing `_validate_bound_image_evidence()` rejects exhausted/unavailable results when the direct media path was not attempted.

- [ ] **Step 1: Add the minimal implementation**

Require `direct_media_url_attempted` as a boolean in every event checklist and include it in the attempt set required by `delivery_unavailable` and `source_exhausted`.

- [ ] **Step 2: Add the positive direct-delivery regression**

Create a delivered event with `direct_media_url_attempted=True`, `qualified_image_found=True`, `delivery_attempted=True`, and later fallback flags false. Assert it passes.

- [ ] **Step 3: Run focused tests**

Run: `python -m unittest tests.test_manage_mobile_run_log -v`

Expected: all mobile run-log tests PASS.

### Task 3: Align active contracts and prevent prose regression

**Files:**
- Modify: `INSTALL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `news-brief-settings.md`
- Modify: `.agents/skills/collect-news-images/SKILL.md`
- Modify: `.agents/skills/collect-news-images/references/image-policy.md`
- Modify: `docs/mobile-run-ledger.md`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: `DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE` and `direct_media_url_attempted`.
- Produces: one consistent outer-task, install, skill, settings, reference, ledger, and regression contract.

- [ ] **Step 1: Update active contracts**

State that native image search/card is not the sole legal acquisition path. Require article `img`/`srcset`/`og:image` extraction, direct JPEG/WebP media opening, and visible delivery before fallback exhaustion.

- [ ] **Step 2: Update contract regression**

Require every active contract surface to contain `DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE` and `direct_media_url_attempted`.

- [ ] **Step 3: Run contract and full tests**

Run: `python -m unittest tests.test_pipeline_contract -v`

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 4: Commit and publish**

Commit the source, update GitHub main, wait for capsule generation, and confirm remote CI plus capsule `source_commit` binding.
