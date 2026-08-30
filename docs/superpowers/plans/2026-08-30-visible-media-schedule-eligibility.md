# Visible-Media Schedule Eligibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent installation of a recurring canonical daily-news task on an execution surface that cannot deliver mandatory images as visible local attachments.

**Architecture:** Keep the existing full-runtime and mobile-native implementations, but move production eligibility to installation. A desktop/local-project full-runtime task must pass one existing-asset visible-attachment smoke test before recurrence activation; mobile-native remains non-production diagnostic capability.

**Tech Stack:** Markdown contracts, Python `unittest` contract tests, existing capsule builder and verifier.

## Global Constraints

- Preserve `NO_EXTERNAL_IMAGE_URL_DELIVERY_GATE` and `IMAGE_FALLBACK_EXHAUSTION_GATE`.
- Do not add a schema, receipt, recovery state, validator, execution mode, or compatibility path.
- Use the existing checked-in `maps/generated/taiwan-counties-yellow-v2.png` for the installation smoke test.
- Return scheduled results to the current conversation.

---

### Task 1: Lock production schedule eligibility

**Files:**
- Modify: `tests/test_pipeline_contract.py`
- Modify: `INSTALL.md`
- Modify: `scheduled-task-prompt-template.md`
- Modify: `mobile-chatgpt-start-prompt.md`
- Modify: `README.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: existing full-runtime project execution and visible local attachment behavior.
- Produces: `VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE` and `VISIBLE_LOCAL_ATTACHMENT_INSTALL_SMOKE_GATE` contract markers.

- [ ] **Step 1: Write the failing contract regression**

Add a test that requires both markers, desktop/local-project full-runtime eligibility, the exact checked-in smoke image, refusal to activate on failure, and explicit non-production mobile-native wording across the high-authority installation surfaces.

- [ ] **Step 2: Run the targeted test to verify RED**

Run: `python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_visible_media_schedule_requires_proven_full_runtime_attachment -v`

Expected: FAIL because the new markers are absent.

- [ ] **Step 3: Implement the minimal contract change**

Add the bounded eligibility and smoke-test language to the named files without changing runtime schemas or state machines. Clarify that an accidentally invoked mobile-native production task stops before news discovery rather than creating a doomed occurrence.

- [ ] **Step 4: Run targeted and full tests**

Run the targeted test, `python -m unittest tests.test_pipeline_contract -v`, then `python -m unittest discover -s tests -v`.

Expected: all PASS.

- [ ] **Step 5: Audit, version, and publish**

Run exact-residue, reverse-contract, execution-path, generated-capsule, full-suite, and scoped-diff checks twice on one unchanged source fingerprint. Commit and push the source, wait for the capsule commit and CI, then confirm `capsule-manifest.json.source_commit` equals the source commit.
