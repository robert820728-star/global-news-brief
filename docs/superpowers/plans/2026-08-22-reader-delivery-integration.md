# Reader Delivery Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the daily brief on one sectioned reader contract and make maps and image placement fail closed.

**Architecture:** Keep the manifest as the single source of truth. Route both publication and delivery revalidation through one sectioned reader validator, then compare the complete ordered Markdown attachment stream with the manifest. Keep recovery stage-local.

**Tech Stack:** Python 3 standard library, unittest, JSON Schema 2020-12, Markdown text validation.

## Global Constraints

- Do not change discovery, semantic event clustering, six-dimension scoring, or selection thresholds.
- The canonical reader is the existing sectioned layout from `news-brief-template.md`.
- A required map must be ready before canonical release.
- Every visible image must belong to exactly one manifest event and appear in canonical order.
- Mobile-native fallback may emit only a degraded draft when full visual validation is unavailable.

---

### Task 1: Canonical reader regression tests

**Files:**
- Modify: `tests/test_validate_news_brief.py`
- Modify: `tests/test_publish_news_brief.py`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `validate_legacy_sectioned_layout(manifest: dict, text: str) -> list[str]`
- Produces: executable acceptance tests for the canonical reader and publisher routing.

- [ ] **Step 1: Write failing tests**

Add tests asserting that reversed assets, captions not immediately after their
attachment, unmanifested images, out-of-story images, and a required omitted map
are rejected. Add a publisher test whose valid input uses the sectioned layout.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_validate_news_brief tests.test_publish_news_brief tests.test_pipeline_contract -v`

Expected: new tests fail because legacy validation only checks substring
presence and publisher still calls `validate_brief_text`.

### Task 2: Manifest and canonical validator

**Files:**
- Modify: `schemas/news-event-manifest.schema.json`
- Modify: `scripts/validate_news_brief.py`

**Interfaces:**
- Produces: `validate_canonical_reader(data: dict, text: str) -> list[str]`.

- [ ] **Step 1: Add `images.reader_omission_note` to the schema**

Permit a nullable string and keep `additionalProperties: false`.

- [ ] **Step 2: Implement exact attachment stream validation**

For each story, build the expected ordered stream from `map.assets`,
`charts.assets`, and `images.assets`. Parse Markdown image targets, reject
unknown paths, require the expected numbered alt prefix, and require the exact
caption on the next nonblank line.

- [ ] **Step 3: Reject attachments outside stories**

Compare every reader Markdown image target to the concatenated per-story stream.
Reject header, table, between-section, and trailing images.

- [ ] **Step 4: Make required maps fail closed**

When `final_status == "ready"`, require each `map.required == true` result to
have `status == "ready"` and at least one asset.

- [ ] **Step 5: Verify GREEN**

Run the Task 1 test command and require zero failures.

### Task 3: Publisher and contract convergence

**Files:**
- Modify: `scripts/publish_news_brief.py`
- Modify: `scripts/check_unique_delivery_gate.py`
- Modify: `news-brief-settings.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `bootstrap-workspace.md`

**Interfaces:**
- Consumes: `validate_canonical_reader`.
- Produces: one production layout contract and full-runtime-only completion.

- [ ] **Step 1: Route publisher and revalidation**

Replace calls to `validate_brief_text` with `validate_canonical_reader`.

- [ ] **Step 2: Remove the retired structured reader instructions**

Align settings and schedule text with the sectioned template. State that
mobile-native output is draft-only when it cannot perform full attachment
validation.

- [ ] **Step 3: Run targeted tests**

Run: `python -m unittest tests.test_validate_news_brief tests.test_publish_news_brief tests.test_pipeline_contract tests.test_delivery_runtime_revalidation -v`

Expected: all tests pass.

### Task 4: Full verification and repository delivery

**Files:**
- Modify: `bootstrap/capsule-manifest.json` and capsule payload files through the repository's canonical capsule build workflow.

**Interfaces:**
- Produces: a GitHub commit based on the latest `main`.

- [ ] **Step 1: Run full tests**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

- [ ] **Step 2: Build and verify the bootstrap capsule**

Run the repository capsule build and verification commands. Confirm manifest
source SHA, payload hash, and runtime fingerprint.

- [ ] **Step 3: Commit and update GitHub**

Create one commit based on the latest `main`, update `main` by fast-forward,
and verify the remote SHA plus all modified blob SHAs.
