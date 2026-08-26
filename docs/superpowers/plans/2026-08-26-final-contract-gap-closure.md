# Final Contract Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the verified residual mobile, fallback, custom-map, local-map, grade, and seed contradictions without adding parallel validation infrastructure.

**Architecture:** Reuse the existing mobile prompt, map renderer, manifest validator, candidate-audit validator, and obsolete-contract test suite. Dynamic custom maps resolve through the existing initialized section metadata. All other changes delete contradictory prose or stale schema values.

**Tech Stack:** Python 3.12, JSON Schema, Markdown contracts, `unittest`.

## Global Constraints

- Do not add a validator, recovery state, receipt layer, workflow, source class, scoring rule, or map mode.
- Preserve Public Value V2, the three-part reader, run ownership, verification rewind, and visual degradation behavior.
- Use test-first red/green cycles for behavior changes.

---

### Task 1: Freeze contract regressions

**Files:**
- Modify: `tests/test_pipeline_contract.py`
- Modify: `tests/test_no_obsolete_contracts.py`
- Modify: `tests/test_render_base_maps.py`
- Modify: `tests/test_validate_news_brief.py`
- Modify: `tests/test_manage_candidate_audit.py`

- [ ] Add assertions for conditional mobile commands, same-source-only web fallback, no active local-detail mode, no selected `C-` prose, and a valid shipped seed.
- [ ] Add a custom-section event overlay test and a wrong-custom-basemap negative test.
- [ ] Run the focused tests and confirm failures identify the current defects.

### Task 2: Apply the minimum production and contract repair

**Files:**
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/acquire-news-candidates/SKILL.md`
- Modify: `.agents/skills/verify-news-events/SKILL.md`
- Modify: `.agents/skills/build-news-maps/SKILL.md`
- Modify: `INSTALL.md`
- Modify: `maps/README.md`
- Modify: `news-brief-examples.md`
- Modify: `schemas/news-event-manifest.schema.json`
- Modify: `scripts/render_base_maps.py`
- Modify: `scripts/validate_news_brief.py`
- Modify: `scripts/validate_map_decisions.py`
- Modify: `state/candidate-audit.json`

- [ ] Make mobile Python invocations conditional and state the equivalent structural invariants directly.
- [ ] Remove candidate-producing web fallback prose.
- [ ] Resolve custom event maps through initialized section metadata and validate the custom base path.
- [ ] Remove `regional_detail` and all active cropped/local-detail guidance.
- [ ] Remove the selected `C-` statement and update the audit seed.
- [ ] Change map omission wording to internal metadata only.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Synchronize operator records and generated artifacts

**Files:**
- Modify: `README.md`
- Modify: `VERSION-RECORD.md`
- Modify: `docs/news-rule-matrix.json`
- Rebuild: `bootstrap/**`

- [ ] Record the bounded repair and rollback source `f44207d9` bilingually.
- [ ] Update the rule matrix without adding a new authority layer.
- [ ] Rebuild and verify the bootstrap capsule.

### Task 4: Verify and publish

- [ ] Run focused tests and the complete repository suite.
- [ ] Run exact-residue, reverse-contract, schema/config/docs, execution-path, and commit-scope checks.
- [ ] Complete two consecutive final-state cycles on one unchanged fingerprint.
- [ ] Commit, push to GitHub `main`, and confirm the remote workflow result.
