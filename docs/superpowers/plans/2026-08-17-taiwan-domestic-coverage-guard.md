# Taiwan Domestic Coverage Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover important Taiwan domestic economy, consumer-safety, and central-institution stories without increasing the fifteen-source primary scan or flooding the reader edition.

**Architecture:** Repair generic HTML materialization so descriptive anchor metadata wins over numeric URL slugs. Add three bounded, same-source Taiwan coverage sweeps to the orchestration contract, then calibrate grades around verified national consequences rather than topics or political rhetoric.

**Tech Stack:** Python 3.12 standard library, JSON configuration, Markdown prompt/skill contracts, `unittest`.

## Global Constraints

- Keep exactly five primary sources per section and fifteen primary sources total.
- Run three Taiwan-only coverage sweeps with at most five results per beat.
- Sweep results must resolve to an existing configured Taiwan source and re-enter its canonical scan before selection.
- Do not auto-promote rumors, unchanged partisan rhetoric, or a topic without a current-window consequence.
- Keep all user-facing policy and version entries bilingual where applicable.

---

### Task 1: Repair descriptive HTML titles

**Files:**
- Modify: `scripts/materialize_source_scans.py`
- Test: `tests/test_materialize_source_scans.py`

**Interfaces:**
- Consumes: HTML anchors already processed by `parse_html(...)`.
- Produces: candidate dictionaries whose `title` prefers anchor `title`, then `aria-label`, then visible text; `add_item(...)` replaces an equal-time numeric title with a descriptive title for the same canonical URL.

- [ ] **Step 1: Write the failing tests**

```python
def test_anchor_title_attribute_beats_numeric_slug():
    html = '<time>2026-08-17 06:11</time><a href="/news/story/1/9695476" title="全國食安回收擴大"><img></a>'
    items = MODULE.parse_html(html, "https://udn.com/news/breaknews/1", "https://udn.com/news/index", "html_direct", 2026)
    self.assertEqual("全國食安回收擴大", next(iter(items.values()))["title"])
```

- [ ] **Step 2: Run the test and confirm the current numeric-title failure**

Run: `python -m unittest tests.test_materialize_source_scans -v`
Expected: FAIL because the current anchor parser ignores `title` and `aria-label`.

- [ ] **Step 3: Implement the minimal parser repair**

Capture the complete anchor attributes, extract `title` or `aria-label`, and pass the first nonempty descriptive value to `add_item`. Add a small title-quality comparison that treats all-digit and generic fallback titles as lower quality when timestamps are equal.

- [ ] **Step 4: Run the target tests**

Run: `python -m unittest tests.test_materialize_source_scans -v`
Expected: PASS.

### Task 2: Add bounded Taiwan coverage and grading contracts

**Files:**
- Modify: `news-source-pool.json`
- Modify: `news-brief-settings.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/acquire-news-candidates/SKILL.md`
- Modify: `.agents/skills/select-news-events/references/severity-rubric.md`
- Modify: `news-brief-examples.md`
- Modify: `VERSION-RECORD.md`
- Test: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `taiwan_coverage_sweeps` configuration with `sweep_id`, `topics`, `result_limit`, and `same_source_only`.
- Produces: a prompt-level recovery contract that adds discovered URLs to the owning primary source scan before canonical candidate construction.

- [ ] **Step 1: Write failing contract tests**

Assert exactly three configured Taiwan sweeps, each capped at five, and assert that all daily/mobile/acquisition instructions require same-source rematerialization and normal audit. Assert grading text covers measured broad business impact, nationwide consumer recall, and central-budget constitutional consequences while rejecting rhetoric-only promotion.

- [ ] **Step 2: Run the contract tests and confirm missing configuration**

Run: `python -m unittest tests.test_pipeline_contract -v`
Expected: FAIL because `taiwan_coverage_sweeps` and domestic calibration are absent.

- [ ] **Step 3: Add the minimal configuration and prose contracts**

Add three sweeps (`economy_trade_industry`, `health_food_consumer`, `central_policy_institutions`) with `result_limit: 5`, `same_source_only: true`, and `window_hours: 24`. Specify that a lead must be materialized into the owning configured source scan and cannot bypass candidate audit.

- [ ] **Step 4: Run target tests**

Run: `python -m unittest tests.test_pipeline_contract tests.test_materialize_source_scans -v`
Expected: PASS.

### Task 3: Release verification and one-month acceptance search

**Files:**
- Modify generated: `bootstrap/capsule-manifest.json`, `bootstrap/capsule.part*.txt`
- Create outside release source: one-month acceptance list in the task response and Gmail receipt.

**Interfaces:**
- Consumes: verified repository rules and web results from the last month.
- Produces: a deduplicated, sectioned list with grade and approximately 50 Traditional-Chinese characters per item, plus counts by grade and a reasonableness verdict.

- [ ] **Step 1: Run the full local suite**

Run: `python -m unittest discover -s tests -v`
Expected: all tests pass.

- [ ] **Step 2: Rebuild and verify the bootstrap capsule**

Run: `python scripts/build_bootstrap_capsule.py --source-commit <feature-sha>` and `python scripts/verify_bootstrap_capsule.py`
Expected: completed status and verified chunks.

- [ ] **Step 3: Publish only scoped files to GitHub main and confirm Actions**

Do not stage existing generated map changes or `work/`. Confirm the final remote `main` commit and successful capsule workflow.

- [ ] **Step 4: Search the previous month and audit volume**

Search Taiwan, China, and global sections; merge identical underlying events; grade using the repository rubric; list C and above plus representative C-/D exclusions. Report unique-event counts and whether C-and-above volume is excessive.

- [ ] **Step 5: Send Gmail acceptance notice**

Send to `me` with the final commit, test result, Actions result, event counts, and a link to this task's GitHub repository.
