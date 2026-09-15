# Usable-First Scheduled Task Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make canonical singleton installation complete on an acknowledged create/update without allowing optional readback or media smoke to disable a usable task.

**Architecture:** Keep the existing singleton state machine, but separate the product mutation from post-install diagnostics. Treat a known exact-ID update as idempotent desired-state convergence and keep runtime publication gates inside occurrences.

**Tech Stack:** Markdown contracts, Python `unittest`, deterministic bootstrap capsule tooling, GitHub Actions.

## Global Constraints

- Do not mutate the live daily 06:00 ChatGPT task.
- Preserve complete canonical saved-prompt generation and the two authorized substitutions.
- Preserve duplicate prevention: never create after an unknown outcome or when multiple matches exist.
- Every formal-file modification resets final-state audit credit.

---

### Task 1: Encode usable-first installation behavior

**Files:**
- Modify: `tests/test_schedule_prompt_control_plane.py`
- Modify: `INSTALL.md`
- Modify: `README.md`
- Modify: `mobile-chatgpt-start-prompt.md`
- Modify: `daily-schedule-prompt.md`

**Interfaces:**
- Consumes: existing `ensure_singleton` entry states and canonical install payload.
- Produces: `USABLE_FIRST_SCHEDULE_INSTALL_GATE` and `POST_INSTALL_DIAGNOSTICS_GATE` contract text.

- [ ] **Step 1: Write failing tests** asserting acknowledged create/update remains enabled when optional readback or smoke is unavailable, known exact-ID recovery permits idempotent update, diagnostic failure forbids schedule mutation, and the paste-ready starter contains no internal state-machine implementation.
- [ ] **Step 2: Run** `python -m unittest tests.test_schedule_prompt_control_plane` and confirm failures name the old blocking semantics.
- [ ] **Step 3: Make the minimum contract edits** across the four authoritative/user-facing documents; remove only obsolete blocking statements.
- [ ] **Step 4: Rerun** `python -m unittest tests.test_schedule_prompt_control_plane` and require zero failures.
- [ ] **Step 5: Commit** the behavioral repair and tests.

### Task 2: Close generated and repository evidence

**Files:**
- Create: `docs/version-records/rc55-usable-first-schedule-install.md`
- Regenerate: `bootstrap/capsule-manifest.json`
- Regenerate: `bootstrap/capsule.part*.txt`
- Create outside source acceptance: `evidence/rc55-final-state-audit.md`
- Create outside source acceptance: `evidence/rc55-outcome-receipt.json`

**Interfaces:**
- Consumes: the final Task 1 contract state.
- Produces: published source/capsule identity and evidence-bounded verdict.

- [ ] **Step 1: Add the bilingual version record** with root cause, changed entry points, rollback source, validation method, and result.
- [ ] **Step 2: Run focused schedule, pipeline, and fault-penetration tests**, then the complete test suite.
- [ ] **Step 3: Rebuild and verify the deterministic capsule**, commit it, and confirm a clean tree.
- [ ] **Step 4: Push the branch to `main` and require remote CI success**, then fast-forward to the Actions-generated capsule commit.
- [ ] **Step 5: Run two final-state cycles** on the unchanged final fingerprint, including tracked-only clean export.
- [ ] **Step 6: Materialize and validate the outcome receipt** with `scripts/validate_outcome_alignment.py`, then write the bilingual audit report.
