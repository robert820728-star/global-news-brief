# Mobile ChatGPT Basic News Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a low-cost mobile ChatGPT Scheduled Task entry point without weakening the existing Codex workflow.

**Architecture:** Two Markdown files separate one-time mobile setup from the recurring daily instructions. A static Python contract test prevents Codex-only dependencies or loss of the minimum news acceptance rules.

**Tech Stack:** Markdown, Python `unittest`, GitHub Git Data API.

## Global Constraints

- Use ChatGPT Instant; do not use Thinking or Pro.
- Preserve the fourteen-day candidate list, six scores, all C-or-higher reader items, and no-image explanations.
- Do not require Codex, shell, local files, maps, charts, or canonical publisher execution.
- Commit directly to GitHub `main`.
- Keep the selected image unchanged in content; use its publisher-provided small variant or resize that exact image to a 640 px longest-edge ceiling and 200 KB target.
- Always provide alternative text; if downsizing is unavailable, allow the same stable original before falling back to an image explanation. Never display an image URL or source-page link as an image substitute.

---

### Task 1: Mobile Scheduled Task profile

**Files:**
- Create: `mobile-chatgpt-start-prompt.md`
- Create: `mobile-chatgpt-daily-prompt.md`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `README.md`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: public repository URL, monitored regions, optional weighted topics.
- Produces: a ChatGPT Scheduled Task at 06:00 Asia/Taipei and its reader-facing daily result.

- [ ] **Step 1: Add the failing contract test**

```python
def test_mobile_chatgpt_profile_is_low_cost_and_preserves_minimum_contract(self):
    start = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
    daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
    self.assertIn("Instant", start)
    self.assertIn("C 級以上", daily)
```

- [ ] **Step 2: Run the test and confirm it fails because the files do not exist**

Run: `python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_mobile_chatgpt_profile_is_low_cost_and_preserves_minimum_contract -v`

Expected: `ERROR` with `FileNotFoundError` for `mobile-chatgpt-start-prompt.md`.

- [ ] **Step 3: Add the two prompts and documentation links**

The setup prompt selects Instant, supplies the repository URL and preferences, creates the 06:00 task, and runs once. The daily prompt searches the last 24 hours and maintains the minimum acceptance contract without Codex-only tooling.

- [ ] **Step 4: Run the focused and full contract tests**

Run: `python -m unittest tests.test_pipeline_contract -v`

Expected: all tests pass.

- [ ] **Step 5: Commit directly to GitHub main**

Create one remote commit on the current `main` tree and fast-forward `refs/heads/main` without force.

### Task 2: Stable mobile image delivery

**Files:**
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `mobile-chatgpt-start-prompt.md`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `README.md`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: image metadata and public URLs found during the scheduled web search.
- Produces: zero or one inline image of the same selected visual, or a plain-language image explanation without an image URL substitute.

- [ ] **Step 1: Add the failing image-delivery contract test**

```python
def test_mobile_image_delivery_uses_small_stable_thumbnail_with_fallback(self):
    daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
    for requirement in ("最多一張", "同一張圖", "640px", "200KB", "替代文字"):
        self.assertIn(requirement, daily)
    self.assertNotIn("**圖片來源頁：**", daily)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_mobile_image_delivery_uses_small_stable_thumbnail_with_fallback -v`

Expected: `FAIL` because `最多一張` is absent from the current mobile prompt.

- [ ] **Step 3: Add the minimal three-level image policy**

Require the exact selected image's publisher-provided lower-resolution variant, or resize that same image when conversion is truly available; never swap in a different image to satisfy the size limit. If neither is available, allow the same stable public original image. Only then fall back to `圖片說明`, never a visible image URL or source-page link. Reject authentication-gated, hotlink-protected, signed, expiring, `data:`, and `blob:` image URLs.

- [ ] **Step 4: Run focused and full contract tests**

Run: `python -m unittest tests.test_pipeline_contract -v`

Expected: all four tests pass.

- [ ] **Step 5: Commit and publish**

Commit only the mobile prompt, contract, README, version record, design, and plan files. Fast-forward GitHub `main` without force and verify each changed remote blob matches the local commit.
