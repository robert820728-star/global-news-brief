# RC.7 Contract Mode Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining rc.6 execution-mode, section, policy-stage, dead-config, and example contradictions with no new architecture.

**Architecture:** Keep one canonical contract and select its executable mechanism from the existing execution mode. Reuse current fields and validators, remove unreachable legacy fallbacks, and express policy requirements by existing stage values.

**Tech Stack:** Markdown contracts, JSON configuration/schema, Python 3, `unittest`, generated bootstrap capsule.

## Global Constraints

- Do not add a schema, validator, receipt, recovery state, fallback source class, compatibility mode, or image-evidence semantic gate.
- Keep `reader_omission_note` unchanged.
- Use `section_scopes` as the only current section authority.
- Preserve Public Value V2 weights and grade bands.
- Roll back from remote `1e6e073778dd5d7aa6d556759c6315ab3f67f352` or local `fa5d1aa34a9cf07fbb3e4cbb864970eda21a5b54`.

---

### Task 1: Lock section and runtime-mode contracts

**Files:**
- Modify: `tests/test_no_obsolete_contracts.py`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `news-brief-settings.md`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `scripts/manage_candidate_audit.py`

**Interfaces:**
- Consumes: current `section_scopes`, `MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT`, and `MOBILE_READER_STRUCTURE_EQUIVALENT`.
- Produces: one current section resolution rule and capability-conditional shared validation prose.

- [ ] **Step 1: Write failing contract tests**

```python
def test_shared_contracts_make_python_capability_conditional(self):
    for text in shared_texts:
        self.assertIn("只有可執行 runtime 時", text)
        self.assertIn("MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT", text)

def test_current_section_contract_has_no_else_glb_fallback(self):
    self.assertNotIn("其餘國家、跨國或全球事件對應世界", settings)
    self.assertNotIn('else "GLB"', validator)
```

- [ ] **Step 2: Run the tests and observe the rc.6 failures**

Run: `python -m unittest tests.test_no_obsolete_contracts tests.test_pipeline_contract -v`

Expected: failures on unconditional Python and non-TWN/non-CHN `GLB` fallback.

- [ ] **Step 3: Apply the minimum contract edits**

Replace the hard-coded mapping with ordered scope matching. Qualify Python commands with runtime availability and point mobile-native to the existing structural equivalent. Remove the validator's final hard-coded fallback; invalid current scopes remain errors from their existing validation.

- [ ] **Step 4: Run the focused tests**

Expected: both modules pass.

### Task 2: Split image evidence by existing execution mode

**Files:**
- Modify: `tests/test_pipeline_contract.py`
- Modify: `tests/test_no_obsolete_contracts.py`
- Modify: `INSTALL.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `docs/mobile-run-ledger.md`
- Modify: `.agents/skills/collect-news-images/SKILL.md`
- Modify: `news-brief-settings.md`

**Interfaces:**
- Consumes: `execution_mode`, `delivery_profile`, `native_media_status`, `capability_limitations`, and `image_evidence_artifact`.
- Produces: truthful runtime and mobile-native evidence routes using the same existing state fields.

- [ ] **Step 1: Write failing mobile profile tests**

```python
def test_mobile_native_image_route_does_not_require_local_materialization(self):
    self.assertIn("MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE", mobile)
    self.assertIn("不得捏造本地", mobile)
    self.assertNotIn("mobile-native actually attempted download, screenshot fallback", ledger)
```

- [ ] **Step 2: Verify the test fails on rc.6**

Run the single test and confirm the missing profile split is the failure.

- [ ] **Step 3: Edit only existing contracts**

Mark local `evidence_path`, materializer, file, screenshot, and pixel checks as runtime-profile requirements. Define mobile-native as source inspection plus native card attempt plus structured host result. State that the blob pointer proves persistence, not semantic validation.

- [ ] **Step 4: Run focused tests**

Expected: pipeline and obsolete-contract tests pass without schema changes.

### Task 3: Relax policy effects only before operational stages

**Files:**
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `scripts/manage_candidate_audit.py`

**Interfaces:**
- Consumes: existing `policy_stage` and `policy_governance_review`.
- Produces: stage-specific non-empty requirements with no schema shape change.

- [ ] **Step 1: Add failing proposal and draft fixtures**

```python
def test_policy_proposal_without_window_effect_does_not_fabricate_one(self):
    review["window_material_effects"] = []
    self.assertEqual([], validate(candidate_with_stage("proposal", review)))
```

Add the same assertion for `draft`, plus a negative `effective` fixture that must still fail when the list is empty.

- [ ] **Step 2: Verify proposal/draft fail and effective already fails**

Run the three tests before implementation.

- [ ] **Step 3: Change the existing required-list selection**

Require legal basis, official action, and affected actors for proposal through signed stages. Append `window_material_effects` only for `effective`, `implemented`, and `measurable_effect`.

- [ ] **Step 4: Run all candidate-audit tests**

Expected: pass with no score, grade, or schema changes.

### Task 4: Remove stale configuration and examples

**Files:**
- Modify: `tests/test_no_obsolete_contracts.py`
- Modify: `news-source-pool.json`
- Modify: `news-brief-examples.md`

**Interfaces:**
- Consumes: current same-source acquisition policy and manifest `images.assets.maxItems = 2`.
- Produces: no duplicate dead boolean and examples consistent with the Reader.

- [ ] **Step 1: Add failing structural tests**

Assert that no `same_source_only` key exists, the positive example has no manual total, and positive image guidance has no `圖三`, `1-5`, or `5 張`.

- [ ] **Step 2: Verify failures on rc.6**

- [ ] **Step 3: Delete the booleans and rewrite examples to at most two images**

- [ ] **Step 4: Run obsolete-contract and JSON tests**

Expected: pass.

### Task 5: Version, package, audit, and publish

**Files:**
- Modify: `VERSION-RECORD.md`
- Regenerate: `bootstrap/capsule-manifest.json`, `bootstrap/capsule-payload.tar.xz`, `bootstrap/capsule.part*.txt`

**Interfaces:**
- Produces: bilingual rc.7 record and a source-bound capsule.

- [ ] **Step 1: Add the bilingual rc.7 version entry**

- [ ] **Step 2: Rebuild and verify the capsule**

Run: `python scripts/build_bootstrap_capsule.py` and `python scripts/verify_bootstrap_capsule.py`.

- [ ] **Step 3: Run the complete repository suite**

Run: `python -m unittest discover -s tests -v`.

- [ ] **Step 4: Run two unchanged-fingerprint final-state cycles**

Each cycle includes residue, reverse-contract, adversarial policy/mobile probes, full suite, capsule verification, INSTALL path, and scope diff.

- [ ] **Step 5: Commit and publish to `main`**

Use ordinary Git HTTPS only if reachable; otherwise use the already proven GitHub Git Data API path. Verify remote `main`, CI success, and any manifest-only workflow commit.
