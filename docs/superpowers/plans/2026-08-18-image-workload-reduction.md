# Image Workload Reduction Implementation Plan

> **For Codex:** Execute directly under the user's standing authorization. Keep the change minimal and test-driven.

**Goal:** Reduce daily image workload while preserving complete C-or-above news coverage and reliable mobile rendering.

**Architecture:** Tighten the existing manifest and image-collection contract instead of adding infrastructure. SHA-256 is stored per image asset so duplicate bytes can reuse acquisition, resizing, and visual acceptance within one run.

**Tech Stack:** Markdown contracts, JSON Schema, Python validator, unittest.

---

### Task 1: Add failing contract and validator tests

**Files:** `tests/test_pipeline_contract.py`, `tests/test_validate_news_brief.py`

Add tests for a two-image maximum, duplicate content hashes, one-image default, justified second image, SHA reuse, one-time visual acceptance, and existing 640 px/browser-last rules. Run only these tests and confirm failures are caused by the missing behavior.

### Task 2: Implement the minimum contract

**Files:** `.agents/skills/collect-news-images/SKILL.md`, `schemas/news-event-manifest.schema.json`, `scripts/validate_news_brief.py`, `mobile-chatgpt-daily-prompt.md`, `news-brief-settings.md`, `news-brief-template.md`, `VERSION-RECORD.md`

Set the source-image maximum to two, require `content_sha256`, reject duplicate hashes, permit one qualifying asset to satisfy both source and professional checks, and document the low-pressure processing order. Do not add external caching or services.

### Task 3: Verify and publish

Run focused tests, the non-capsule suite, and capsule validation. Commit directly to `main`, push once, wait for Linux capsule rebuild, then verify the rebuilt remote commit from a clean clone.
