# Scheduled Occurrence Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject ordinary chat continuations before they can enter the Scheduled Task daily-news pipeline.

**Architecture:** Add one cross-layer contract marker, `CHAT_CONTINUATION_IS_NOT_SCHEDULED_OCCURRENCE_GATE`, to every runtime authority document. The gate requires a real control-plane `scheduled_for` value before run creation/resume or news work, and permits only a concise lifecycle blocker receipt when the value is absent.

**Tech Stack:** Markdown runtime contracts and Python `unittest` contract tests.

## Global Constraints

- Do not change the formal daily 06:00 schedule.
- Do not recreate the cancelled ten-minute validation automation.
- Do not permit degraded, diagnostic, preview, or text-only Reader output on lifecycle failure.
- Preserve valid manual task triggers that carry control-plane occurrence authority.

---

### Task 1: Add the lifecycle regression

**Files:**
- Modify: `tests/test_schedule_prompt_control_plane.py`
- Modify: `INSTALL.md`
- Modify: `scheduled-task-prompt-template.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`

**Interfaces:**
- Consumes: control-plane `scheduled_for` evidence.
- Produces: fail-closed lifecycle behavior before fresh-main resolution, run creation/resume, discovery, or Reader rendering.

- [ ] **Step 1: Write the failing test**

```python
def test_chat_continuation_is_not_a_scheduled_occurrence(self):
    documents = {name: (ROOT / name).read_text(encoding="utf-8") for name in (...) }
    for document in documents.values():
        self.assertIn("CHAT_CONTINUATION_IS_NOT_SCHEDULED_OCCURRENCE_GATE", document)
        self.assertIn("scheduled_for", document)
        self.assertIn("重新執行", document)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_schedule_prompt_control_plane.SchedulePromptControlPlaneTests.test_chat_continuation_is_not_a_scheduled_occurrence -v`

Expected: `FAIL` because the gate marker is absent.

- [ ] **Step 3: Add the minimal contract**

Add the same gate semantics to all four authority documents: a normal message such as `重新執行` is not an occurrence; only a real trigger with `scheduled_for` may proceed; absent authority returns only a blocker receipt.

- [ ] **Step 4: Run targeted and full verification**

Run the targeted unittest, full unittest discovery, capsule build/verify, and source-binding checks. Expected: all commands exit zero.

- [ ] **Step 5: Commit and publish**

Commit the source change, rebuild the capsule against the exact source commit, push to `main`, verify remote CI, then run two tracked-only clean export cycles against the unchanged final remote fingerprint.
