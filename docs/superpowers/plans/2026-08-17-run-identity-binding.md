# Run Identity Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every scheduled execution a collision-resistant id and fail publication whenever any release-facing artifact belongs to another run.

**Architecture:** A small `run_identity.py` module owns generation, validation, and reader identity formatting. Existing log, manifest, reader, and publisher components consume that shared contract. The publisher stores an immutable run-log snapshot so later stage updates cannot invalidate the release receipt.

**Tech Stack:** Python 3.12 standard library, JSON Schema, unittest, GitHub Actions YAML, Markdown contracts.

## Global Constraints

- Canonical id: `gnb-YYYYMMDDTHHMMSSZ-xxxxxxxx` in UTC with eight lowercase hexadecimal suffix characters.
- The same run id binds the checkpoint, latest candidate-audit run, manifest, reader, release receipt, and ledger snapshot.
- The same 40-character main SHA binds the manifest, reader, and ledger snapshot.
- No new runtime dependency.
- Preserve the existing two-generation compact run ledger.

---

### Task 1: Canonical run identifier

**Files:**
- Create: `scripts/run_identity.py`
- Create: `tests/test_run_identity.py`
- Modify: `.github/workflows/prepare-mobile-run-ledger.yml`
- Modify: `scripts/manage_mobile_run_log.py`
- Modify: `schemas/mobile-run-log.schema.json`
- Test: `tests/test_manage_mobile_run_log.py`

**Interfaces:**
- Produces: `generate_run_id(now=None, suffix=None) -> str`, `is_valid_run_id(value) -> bool`, and CLI command `generate`.
- Consumes: UTC time and `secrets.token_hex(4)`.

- [ ] Write tests that reject legacy ids and prove two ids generated for the same second differ.
- [ ] Run `python -m unittest tests.test_run_identity tests.test_manage_mobile_run_log -v` and confirm failures are caused by the missing contract.
- [ ] Implement the minimal generator and validation integration.
- [ ] Update the watchdog to call the generator.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Manifest and reader identity

**Files:**
- Modify: `schemas/news-event-manifest.schema.json`
- Modify: `scripts/validate_news_brief.py`
- Modify: `tests/test_validate_news_brief.py`
- Modify: `news-brief-template.md`
- Modify: `mobile-chatgpt-daily-prompt.md`

**Interfaces:**
- Consumes: manifest `run.run_id`, `run.main_sha`, and `final_status`.
- Produces: three exact reader identity lines immediately after the date line.

- [ ] Write tests that reject a missing id, invalid SHA, stale reader id, and missing formal-release marker.
- [ ] Run the focused validator tests and confirm the new tests fail for the expected missing behavior.
- [ ] Add schema and validator requirements and update the reader contracts.
- [ ] Re-run the focused tests and confirm they pass.

### Task 3: Canonical publisher cross-artifact gate

**Files:**
- Modify: `scripts/publish_news_brief.py`
- Modify: `tests/test_publish_news_brief.py`
- Modify: `daily-schedule-prompt.md`

**Interfaces:**
- Consumes: required `--run-log` JSON plus checkpoint, manifest, audit, source pool, and brief.
- Produces: immutable `run-log-snapshot.json` and a receipt containing `run_id` and `main_sha`.

- [ ] Write tests that make manifest and run-log identities stale independently and assert publication is blocked.
- [ ] Run the focused publisher tests and confirm failure is due to the absent gate.
- [ ] Implement one identity comparison path and snapshot binding.
- [ ] Re-run focused tests and confirm they pass.

### Task 4: Loop verification and publication

**Files:**
- Modify: `news-brief-settings.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/select-news-events/references/selection-policy.md`
- Test: `tests/test_selection_rules.py`

**Interfaces:**
- Consumes: confirmed disaster or disease deaths, transmission evidence, pathogen risk group, global spread, and world-scale consequence evidence.
- Produces: an A ceiling for death toll alone, evidence-gated A+, and pandemic-only S- or higher.

- [ ] Write contract tests for the 2,500-death A ceiling, nonautomatic Risk Group 4 uplift, and COVID-19 global-lockdown S- reference.
- [ ] Run the focused contract tests and confirm the required language is absent.
- [ ] Add the exact thresholds, upgrade evidence, and counterexample language to all grading contracts.
- [ ] Re-run the focused tests and confirm they pass.

### Task 5: Loop verification and publication

**Files:**
- Modify generated bootstrap capsule files only through `scripts/build_bootstrap_capsule.py`.

**Interfaces:**
- Consumes: all updated source and contract files.
- Produces: passing unit suite, verified capsule, GitHub commit, and email notification.

- [ ] Run all unit tests.
- [ ] Rebuild the bootstrap capsule.
- [ ] Run all unit tests again and verify the capsule.
- [ ] If any check fails, record the first failure, fix only that cause, and restart this verification task.
- [ ] Commit only intended source, tests, docs, workflow, and rebuilt capsule files.
- [ ] Push through the GitHub connector, verify the remote commit and Linux workflow, then send the requested Gmail notification.
