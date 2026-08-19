# Native Image Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert selected-news source images into validated deterministic local assets and a manifest suitable for native ChatGPT attachment delivery.

**Architecture:** A focused Python CLI owns download, decode, resize, encode, hashing, and manifest output. The existing prompt invokes it after selection and before native media delivery; image failure remains event-local.

**Tech Stack:** Python 3, Pillow, urllib.request, unittest

## Global Constraints

- Do not add a service, pipeline stage, schema version, renderer, or workflow.
- Keep reader, audit, grading, and verification checkpoints unchanged.
- Longest output edge is exactly 640 pixels when resizing is required.
- Accept only HTTP(S) sources and emit JPEG or WebP files.
- Freeze exactly three materializer behavior tests plus the existing pipeline-contract tests.

---

### Task 1: Deterministic image materializer

**Files:**
- Create: `scripts/materialize_news_images.py`
- Create: `tests/test_materialize_news_images.py`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`

**Interfaces:**
- Consumes: JSON array entries with `event_id`, `source_url`, optional `alt`, optional `credit`.
- Produces: `materialize(inputs: list[dict], output_dir: Path) -> list[dict]` and a JSON manifest with per-entry status, local path, MIME, dimensions, SHA-256, alt, and credit.

- [ ] **Step 1: Write the failing tests**

Create three tests that call `materialize_image_bytes`: a valid JPEG writes a decodable asset and successful record; corrupt bytes return a failed record and no file; a 1280x800 input becomes 640x400.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.test_materialize_news_images -v`

Expected: FAIL because `scripts.materialize_news_images` does not exist.

- [ ] **Step 3: Implement the minimal CLI**

Implement URL validation, bounded download, Pillow decode and EXIF transpose, RGB conversion, longest-edge scaling, deterministic JPEG/WebP encoding, SHA-256, atomic asset writes, and atomic manifest write. A failed input appends a bounded error record and continues.

- [ ] **Step 4: Wire the existing prompts**

Require the full-runtime image stage to call `scripts/materialize_news_images.py --input <json> --output-dir <dir> --manifest <json>` and pass only successful local assets to native delivery. Preserve `NATIVE_MEDIA_UNAVAILABLE` and stage-local recovery behavior.

- [ ] **Step 5: Run frozen verification**

Run: `python -m unittest tests.test_materialize_news_images tests.test_pipeline_contract -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit and publish atomically**

Commit the script, tests, prompts, spec, and plan together; publish to `main`, then require the existing bootstrap capsule workflow to pass before the next single ChatGPT validation run.
