# 48-Hour Re-entry and Per-Story Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a per-story visible-image decision and replace immediate unchanged-event suppression with a 48-hour cooldown followed by fresh impact scoring.

**Architecture:** This is a contract-only change. Add two regression tests to the existing pipeline contract suite, then minimally align `news-brief-settings.md` and `mobile-chatgpt-daily-prompt.md`; all existing schemas, stages, services, and publishers remain unchanged.

**Tech Stack:** Markdown contracts, Python `unittest`, Git.

## Global Constraints

- Do not add a schema, service, image proxy, stage, classifier, renderer, checkpoint, or publishing path.
- A 48-hour cooldown must not block a verified C-or-higher material escalation.
- Passing 48 hours triggers current-impact rescoring; it does not force republication.
- Image attempts and omission decisions are per story; one visible image cannot satisfy another story.

---

### Task 1: Freeze the two contract failures

**Files:**
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: repository Markdown files read through `ROOT / <filename>`.
- Produces: two contract tests that fail until the required policy tokens and wording exist.

- [ ] **Step 1: Add the failing 48-hour re-entry test**

```python
def test_mobile_reentry_uses_48_hour_cooldown_and_current_impact(self):
    daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
    settings = (ROOT / "news-brief-settings.md").read_text(encoding="utf-8")
    for document in (daily, settings):
        for requirement in (
            "MATERIAL_UPDATE_48_HOUR_REENTRY_GATE",
            "48 小時內",
            "滿 48 小時",
            "不得自動重刊",
            "獨立達到 C 級",
        ):
            self.assertIn(requirement, document)
    self.assertIn("實質惡化", daily)
```

- [ ] **Step 2: Add the failing per-story image test**

```python
def test_mobile_images_are_gated_per_story(self):
    daily = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
    settings = (ROOT / "news-brief-settings.md").read_text(encoding="utf-8")
    for document in (daily, settings):
        for requirement in (
            "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
            "每一則",
            "不得替其他新聞通過",
            "逐則",
        ):
            self.assertIn(requirement, document)
    self.assertIn("og:image", daily)
    self.assertIn("srcset", daily)
```

- [ ] **Step 3: Verify RED**

Run:

```powershell
python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_mobile_reentry_uses_48_hour_cooldown_and_current_impact tests.test_pipeline_contract.PipelineContractTests.test_mobile_images_are_gated_per_story
```

Expected: two assertion failures because the new gate names and per-story/48-hour wording are absent.

### Task 2: Implement the minimal contract changes

**Files:**
- Modify: `news-brief-settings.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Test: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: the existing `MATERIAL_UPDATE_REENTRY_GATE`, `IMPACT_DELTA_CONTINUITY_SCORING`, `IMAGE_DEFAULT_ONE_ASSET`, and mobile image-delivery rules.
- Produces: `MATERIAL_UPDATE_48_HOUR_REENTRY_GATE` and `MOBILE_PER_STORY_VISIBLE_IMAGE_GATE` contract text without changing the artifact schema.

- [ ] **Step 1: Replace the immediate re-entry wording in both contracts**

Required semantics:

```text
Within 48 hours of the last reader publication, republish only a newly verified C-or-higher material impact. Material escalation can republish immediately. At or after 48 hours, rescore current impact and republish only if it still reaches C or higher; elapsed time alone never republishes an event.
```

- [ ] **Step 2: Replace the document-level image minimum with a per-story gate**

Required semantics:

```text
Every selected story performs its own source-image search. A qualifying image must be visible in the conversation. One story's image cannot satisfy another. A per-story omission is allowed only after the cited-source and one already-cited same-event fallback checks find no qualifying public image or embedding is unsuitable, and the reader states the story-specific non-technical reason.
```

- [ ] **Step 3: Verify GREEN for the two tests**

Run the same two-test command from Task 1.

Expected: `Ran 2 tests ... OK`.

- [ ] **Step 4: Run the frozen related regression set**

Run:

```powershell
python -m unittest tests.test_pipeline_contract
```

Expected: all pipeline contract tests pass with no failures or errors.

- [ ] **Step 5: Review and commit**

Run:

```powershell
git diff --check
git diff -- tests/test_pipeline_contract.py news-brief-settings.md mobile-chatgpt-daily-prompt.md
git add tests/test_pipeline_contract.py news-brief-settings.md mobile-chatgpt-daily-prompt.md
git commit -m "Require per-story images and 48-hour re-entry scoring"
```

Expected: only the declared tests and two Markdown contracts are included in the implementation commit.
