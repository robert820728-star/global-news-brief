# Canonical Scheduled Task Instruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the launcher-only Scheduled Task prompt with one complete canonical instruction template.

**Architecture:** Keep repository documents authoritative while copying a stable minimum execution envelope into the Scheduled Task instruction. `INSTALL.md` owns creation rules and points to exactly one template file.

**Tech Stack:** Markdown contracts and Python `unittest` contract tests.

## Global Constraints

- Do not add schemas, validators, receipts, recovery states, source classes, or compatibility modes.
- Only regions and monitoring types are substitutable in the canonical prompt.
- Preserve fresh-main resolution and current-conversation delivery.

---

### Task 1: Contract regression

**Files:**
- Modify: `tests/test_pipeline_contract.py`

- [ ] Add a test requiring the canonical template, all execution families, all image fallback tiers, and removal of the launcher-only prohibition.
- [ ] Run the test and confirm it fails because the template is absent and the old prohibition remains.

### Task 2: Canonical template and authority wiring

**Files:**
- Create: `scheduled-task-prompt-template.md`
- Modify: `INSTALL.md`
- Modify: `README.md`

- [ ] Write the complete task instruction.
- [ ] Replace the short embedded prompt with a verbatim-template requirement.
- [ ] Link the template from onboarding documentation.
- [ ] Run the focused contract test and confirm it passes.

### Task 3: Verification and release

**Files:**
- Modify: `VERSION-RECORD.md`
- Regenerate: `bootstrap/*`

- [ ] Run focused negative/positive schedule checks.
- [ ] Run the complete repository suite.
- [ ] Run final-state residue and cross-layer checks.
- [ ] Generate and verify the capsule, publish source, and confirm remote CI/capsule binding.

