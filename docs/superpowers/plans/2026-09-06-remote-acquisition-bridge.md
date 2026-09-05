# Remote Acquisition Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed remote acquisition bridge and executable prompt/readback verification for constrained Scheduled Task hosts.

**Architecture:** A validated issue-comment request invokes a default-branch Actions workflow. Existing canonical CNA/China News and media scripts produce run-scoped artifacts on `run-logs`; the Scheduled Task retrieves normalized image bytes as base64, revalidates them locally, and performs its already-proven attachment handoff. GDELT retains the bounded degraded fallback because its 24-hour archive is not connector-safe.

**Tech Stack:** Python 3.12 standard library, Pillow, GitHub Actions YAML, unittest.

## Global Constraints

- Never modify the formal daily 06:00 task or recreate the deleted ten-minute automation.
- Never count URLs, Markdown, tool previews, or serialized refs as visible media.
- Bind every bridge request and result to one run, main SHA, and exact window.
- Preserve existing discovery, scoring, and Reader contracts.

---

### Task 1: Canonical prompt verification

**Files:**
- Create: `scripts/verify_scheduled_task_install.py`
- Create: `tests/test_verify_scheduled_task_install.py`

**Interfaces:**
- Consumes: template, builder receipt, outbound saved prompt, optional readback text.
- Produces: JSON verification result and nonzero exit on mismatch.

- [ ] Write tests rejecting launcher/truncation/extension contamination and accepting exact normalized readback.
- [ ] Run tests and confirm RED because the verifier does not exist.
- [ ] Implement the minimal verifier.
- [ ] Run focused tests and confirm PASS.

### Task 2: Remote bridge request and media byte handoff

**Files:**
- Create: `scripts/remote_acquisition_bridge.py`
- Modify: `scripts/materialize_news_images.py`
- Create: `tests/test_remote_acquisition_bridge.py`
- Modify: `tests/test_materialize_news_images.py`

**Interfaces:**
- Consumes: a versioned request bound to run/main/window and a media input list.
- Produces: validated operation arguments, normalized media artifacts, and receipts.

- [ ] Write tests for envelope validation and base64 source bytes.
- [ ] Run tests and confirm RED for the missing bridge/base64 route.
- [ ] Implement request validation, media execution, and base64 decoding with size limits.
- [ ] Run focused tests and confirm PASS.

### Task 3: Actions transport and operator contract

**Files:**
- Create: `.github/workflows/remote-acquisition-bridge.yml`
- Modify: `INSTALL.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `scheduled-task-prompt-template.md`
- Modify: `VERSION-RECORD.md`
- Modify: `tests/test_fault_penetration_contract.py`

**Interfaces:**
- Consumes: an authorized issue #3 bridge request.
- Produces: run-scoped `run-logs` artifacts without writing generated output to `main`.

- [ ] Add contract tests for authorization, stale-main rejection, source/media resume boundaries, and visible-delivery non-bypass.
- [ ] Run tests and confirm RED.
- [ ] Implement the workflow and concise operator instructions.
- [ ] Run focused and complete suites, build/verify the capsule, and record exact results.
