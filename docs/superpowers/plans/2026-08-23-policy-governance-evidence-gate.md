# Policy Governance Evidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require evidence-backed policy/governance event identity and reject unresolved contradictions between institutional evidence and six-dimension scoring.

**Architecture:** Extend the existing `grading_evidence` object with a latest-run `policy_governance_review`. Keep score calculation unchanged; add structural and cross-field validation that sends contradictions back for model review rather than assigning an automatic grade.

**Tech Stack:** Python 3 standard library, JSON Schema, unittest, Markdown runtime prompts, deterministic bootstrap capsule builder.

## Global Constraints

- Do not create a named-event exception or automatic B-grade floor.
- Prove event identity before scoring.
- Any unresolved evidence/score contradiction blocks audit completion.
- Unverified allegations remain separate and cannot increase scores.
- Preserve all unrelated worktree changes and historical-run compatibility.

---

### Task 1: Policy Governance Review Contract

**Files:**
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `schemas/news-candidate-audit.schema.json`

**Interfaces:**
- Consumes: latest-run candidate `grading_evidence` and `importance_breakdown`.
- Produces: `grading_evidence.policy_governance_review` validation errors or a consistent candidate.

- [ ] **Step 1: Write failing validator tests**

Add a helper that returns a complete review and tests that remove `why_not_b`, set `unverified_allegations_separated=false`, or set an alignment field to `contradiction`.

```python
def policy_governance_review(applies=False):
    return {"applies": applies}

def test_strong_policy_governance_below_b_requires_why_not_b(self):
    audit = valid_audit()
    item = audit["runs"][0]["candidates"][0]
    item["grading_evidence"]["policy_governance_review"] = strong_policy_review()
    item["provisional_grade"] = "C+"
    item["importance_score"] = 54
    item["importance_breakdown"] = breakdown_for_54()
    assert any("why_not_b" in error for error in MODULE.validate(audit, source_pool()))
```

- [ ] **Step 2: Run red tests**

Run: `python -m unittest tests.test_manage_candidate_audit -v`

Expected: FAIL because the validator does not require or interpret `policy_governance_review`.

- [ ] **Step 3: Add schema and minimal validation**

Add schema definitions for trigger enums, evidence arrays, claim separation, alignment statuses, `why_not_b`, and review outcome. In `validate`, require the review for latest-run candidates, validate applicable evidence, detect strong-governance below-B challenge requirements, and reject non-consistent alignment/outcomes.

```python
strong_profile = (
    bool(triggered_by & OFFICIAL_POLICY_TRIGGERS)
    and "platform_or_operator_action" in triggered_by
    and bool(triggered_by & SYSTEM_SCOPE_TRIGGERS)
)
if strong_profile and importance_score < 60 and not why_not_b.strip():
    errors.append(label + " policy_governance_review strong profile below B requires why_not_b")
```

- [ ] **Step 4: Run green tests**

Run: `python -m unittest tests.test_manage_candidate_audit -v`

Expected: all tests pass.

### Task 2: Runtime Rule Integration

**Files:**
- Modify: `news-brief-settings.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: `POLICY_GOVERNANCE_EVIDENCE_GATE` contract from Task 1.
- Produces: identical full-runtime and mobile instructions plus bilingual version traceability.

- [ ] **Step 1: Write failing contract test**

```python
def test_policy_governance_gate_is_locked_across_runtime_documents(self):
    for path in REQUIRED_RUNTIME_DOCUMENTS:
        self.assertIn("POLICY_GOVERNANCE_EVIDENCE_GATE", path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run red contract test**

Run: `python -m unittest tests.test_pipeline_contract -v`

Expected: FAIL because the gate is absent.

- [ ] **Step 3: Add the approved rule to runtime documents**

Document the mandatory pre-score event-identity review, claim separation, strong-profile below-B challenge, and contradiction-to-review behavior. Add a bilingual version record describing reason, approach, validation, result, and next decision.

- [ ] **Step 4: Run focused green tests**

Run: `python -m unittest tests.test_manage_candidate_audit tests.test_pipeline_contract -v`

Expected: all tests pass.

### Task 3: Capsule and Release Verification

**Files:**
- Modify: `bootstrap/capsule-manifest.json`
- Modify: `bootstrap/capsule-payload.tar.xz`
- Modify: `bootstrap/capsule.part*.txt`

**Interfaces:**
- Consumes: modified runtime closure.
- Produces: verified deterministic runtime capsule pinned to the implementation commit parent.

- [ ] **Step 1: Build the capsule**

Run: `python scripts/build_bootstrap_capsule.py`

Expected: manifest, payload, and transport chunks are regenerated.

- [ ] **Step 2: Run full verification**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

Run: `python scripts/verify_bootstrap_capsule.py`

Expected: capsule verification succeeds.

- [ ] **Step 3: Inspect diff and commit**

Run: `git diff --check`

Expected: no whitespace errors.

Commit only the planned files with `feat: require policy governance evidence review`.

- [ ] **Step 4: Push latest main**

Run: `git fetch origin main && git rebase origin/main && git push origin HEAD:main`

Expected: remote `main` advances to the new commit and contains the gate, tests, documentation, and verified capsule.
