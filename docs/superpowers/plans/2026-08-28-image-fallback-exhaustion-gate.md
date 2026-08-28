# Image Fallback Exhaustion Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent premature image blockers by requiring four-tier fallback exhaustion in the existing mobile image-evidence artifact and ledger transition gate.

**Architecture:** Extend the existing `manage_mobile_run_log.py` transition validation to read the already-bound run-scoped image evidence. Align the existing image skill, operator contracts, and outer scheduled prompt without adding a schema, receipt, recovery state, or compatibility layer.

**Tech Stack:** Python 3, JSON artifacts, Markdown operational contracts, `unittest`.

## Global Constraints

- Preserve the existing `NATIVE_MEDIA_UNAVAILABLE` visual-recovery state.
- Preserve qualified-image delivery independent of `claim_critical`.
- Add no new validator file, schema file, receipt, recovery state, compatibility mode, or source class.
- Keep changes limited to image fallback exhaustion and directly conflicting active prose.

---

### Task 1: Reproduce premature blocker acceptance

**Files:**
- Modify: `tests/test_manage_mobile_run_log.py`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: existing `advance_run()` mobile stage transitions and run-scoped image artifact reference.
- Produces: negative tests for incomplete fallback and positive tests for complete exhaustion/success.

- [ ] Add a real run-scoped image-evidence fixture writer to the existing test class.
- [ ] Add a test where one fallback tier is false and `delivery_result=delivery_unavailable`; expect transition rejection.
- [ ] Add a test where one fallback tier is false and `delivery_result=source_exhausted`; expect Reader transition rejection.
- [ ] Add positive complete-exhaustion and delivered-image cases.
- [ ] Run only these tests and confirm the new negative tests fail because the current manager accepts incomplete evidence.

### Task 2: Implement the existing-manager gate

**Files:**
- Modify: `scripts/manage_mobile_run_log.py`

**Interfaces:**
- Consumes: the existing bound `image_evidence_artifact.path` and its event checklist.
- Produces: `_validate_bound_image_evidence(ledger_dir, record)` invoked at relevant mobile transitions.

- [ ] Resolve the deterministic run-scoped evidence path inside the existing run-logs checkout.
- [ ] Validate checklist fields and delivery-result truth table.
- [ ] Require full fallback exhaustion for `delivery_unavailable` and `source_exhausted`.
- [ ] Allow successful delivery without unnecessary later fallback attempts.
- [ ] Run the focused tests and confirm green.

### Task 3: Align active contracts and outer prompt

**Files:**
- Modify: `INSTALL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `news-brief-settings.md`
- Modify: `.agents/skills/collect-news-images/SKILL.md`
- Modify: `.agents/skills/collect-news-images/references/image-policy.md`
- Modify: `docs/mobile-run-ledger.md`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: the seven-field checklist and current visual recovery contract.
- Produces: one consistent operator rule and no non-critical omission escape.

- [ ] State the four-tier order and exact checklist fields on each active surface.
- [ ] State that text and image evidence may use different reliable same-event sources.
- [ ] Put the no-early-exit rule before the generic blocker rule in the outer schedule prompt.
- [ ] Remove the stale non-critical acquisition-failure omission sentence.
- [ ] Record the bilingual version change.

### Task 4: Verify and publish

**Files:**
- Modify: generated `bootstrap/*` only through the canonical builder.

**Interfaces:**
- Consumes: final source fingerprint.
- Produces: targeted tests, full suite, generated capsule, commit, remote CI evidence.

- [ ] Run focused image/ledger/pipeline tests.
- [ ] Run the full repository suite.
- [ ] Perform residue, reverse-contract, execution-path, cross-layer, adversarial, generated-artifact, and diff checks twice on one unchanged fingerprint.
- [ ] Build and verify the capsule with the final source commit.
- [ ] Push the source, verify remote CI, and verify capsule `source_commit` binding.
