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
