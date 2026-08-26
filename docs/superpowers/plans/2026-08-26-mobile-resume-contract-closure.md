# Mobile Resume Contract Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make execution-mode instructions consistent and make completed mobile verification/map work durably resumable.

**Architecture:** Keep the existing two execution modes and mobile ledger. Add only two nullable artifact references to the current ledger, enforce them at the existing stage boundaries, and synchronize the authoritative prose and release order.

**Tech Stack:** Markdown contracts, JSON Schema 2020-12, Python standard library `unittest`, GitHub Actions.

## Global Constraints

- Do not add a new schema file, validator, receipt, recovery state, manifest, compatibility layer, or fallback source class.
- Preserve full-runtime manifest validation and mobile-native audit authority.
- Preserve active-stage semantics and same-occurrence resume.
- Use TDD and rebuild the checked-in capsule only after the final source/version state is fixed.

---

### Task 1: Mode-aware active contracts

**Files:**
- Modify: `news-brief-settings.md`
- Modify: `INSTALL.md`
- Test: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: existing `full-runtime`, `mobile-native`, `MOBILE_READER_STRUCTURE_EQUIVALENT` contracts.
- Produces: one mode-aware description of stages 7–11 and event authority.

- [ ] Add assertions that reject unconditional mobile manifest/local-asset wording and require both mode paths.
- [ ] Run the focused contract test and confirm the new assertions fail.
- [ ] Make the minimum prose edits to settings and INSTALL.
- [ ] Run the focused contract test and confirm it passes.

### Task 2: Durable mobile resume bindings

**Files:**
- Modify: `schemas/mobile-run-log.schema.json`
- Modify: `scripts/manage_mobile_run_log.py`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `docs/mobile-run-ledger.md`
- Test: `tests/test_manage_mobile_run_log.py`

**Interfaces:**
- Consumes: `advance_run(...)`, stage order, existing artifact-reference shape.
- Produces: nullable `verification_artifact` and `map_decisions_artifact` ledger fields and CLI inputs.

- [ ] Add negative tests for crossing into `visuals-completed` without verification binding and `reader-rendered` without map binding.
- [ ] Add a positive same-occurrence resume test preserving both references.
- [ ] Run the focused tests and confirm they fail for the missing fields/enforcement.
- [ ] Bump the current-only ledger schema version and extend the existing manager/schema/CLI without compatibility migration.
- [ ] Document the deterministic paths and identity-only meaning in the existing mobile contracts.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Release-order closure and verification

**Files:**
- Modify: `INSTALL.md`
- Modify: `VERSION-RECORD.md`
- Test: `tests/test_pipeline_contract.py`
- Generate: `bootstrap/capsule-manifest.json`
- Generate: `bootstrap/capsule-part-*.txt`

**Interfaces:**
- Consumes: final source tree and existing capsule workflow.
- Produces: one final source candidate followed by one generated capsule.

- [ ] Add a regression assertion for source/version-before-capsule ordering.
- [ ] Record the bilingual version entry before capsule generation.
- [ ] Run focused tests, the full repository suite, and generated-artifact verification.
- [ ] Run the final-state audit gate twice on one unchanged fingerprint.
- [ ] Publish the final source state once, wait for remote CI/capsule, and do not create a post-capsule active-source commit.

## Self-Review

- Spec coverage: all three accepted changes map to one task; prohibited architecture is explicitly excluded.
- Placeholder scan: no deferred implementation placeholder is present.
- Type consistency: both artifact names and deterministic paths are identical across schema, manager, prompt, docs, and tests.

