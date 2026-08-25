# Public Value V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents for this repository task.

**Goal:** Replace the active `public_value_v1` scoring contract with evidence-bound `public_value_v2.0` while preserving current weights and grade bands.

**Architecture:** Keep `news-source-pool.json` as scoring configuration authority. Add small pure scoring and evidence-validation helpers to `manage_candidate_audit.py`, extend candidate and manifest schemas, and make publisher equality checks reject provisional grades. Calibrated JSON fixtures drive both positive ranges and known inflation rejections.

**Tech Stack:** Python 3 standard library, JSON Schema Draft 2020-12, unittest, Markdown contracts, existing bootstrap capsule tooling.

## Global Constraints

- Six dimensions use normalized 0–100 values in increments of 5.
- Active weights remain 30/20/15/15/10/10.
- Grade minimums remain E 0, D 20, C- 40, C 45, C+ 50, B- 55, B 60, B+ 65, A- 70, A 75, A+ 80, S- 85, S 90, S+ 94, SS 97.
- V2.1 shadow comparison and 30/20/15/15/15/5 weighting are out of scope.
- Importance and evidence confidence remain independent.
- Reader and manifest accept only `grade_status=validated`.
- Tests must be written and observed failing before production changes.

---

### Task 1: Freeze V2 configuration and schema contract with RED tests

**Files:**
- Modify: `tests/test_pipeline_contract.py`
- Modify: `tests/test_manage_candidate_audit.py`
- Test: `tests/test_pipeline_contract.py`
- Test: `tests/test_manage_candidate_audit.py`

**Interfaces:**
- Consumes: approved V2 design and existing `source_pool()` / `audit_doc()` fixtures.
- Produces: failing expectations for `public_value_v2`, normalized dimensions, new candidate fields, and manifest fields.

- [ ] **Step 1: Add failing configuration and schema tests**

```python
def test_public_value_v2_uses_normalized_weighted_dimensions(self):
    pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
    ranking = pool["ranking"]
    self.assertEqual("public_value_v2", ranking["method"])
    self.assertEqual(5, ranking["allowed_score_step"])
    self.assertEqual(100, sum(item["weight_percent"] for item in ranking["dimensions"].values()))
    self.assertTrue(all(item["maximum"] == 100 for item in ranking["dimensions"].values()))

def test_candidate_schema_requires_v2_evidence_and_grade_status(self):
    candidate = schema["$defs"]["candidate"]
    self.assertTrue({
        "scoring_method", "weighted_score", "consequence_evidence", "evidence_facts",
        "policy_stage", "delta_facts", "high_score_challenges",
        "evidence_confidence", "confidence_band", "grade_status",
    }.issubset(candidate["required"]))
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `python -m unittest tests.test_pipeline_contract tests.test_manage_candidate_audit -v`

Expected: failures naming absent `public_value_v2`, `allowed_score_step`, and required schema fields.

- [ ] **Step 3: Commit only after later GREEN**

No production changes or commit occur in this task before Task 2 and Task 3 make these tests pass.

### Task 2: Add V2 configuration and JSON schema fields

**Files:**
- Modify: `news-source-pool.json`
- Modify: `schemas/news-candidate-audit.schema.json`
- Modify: `schemas/news-event-manifest.schema.json`
- Modify: `scripts/materialize_source_scans.py`
- Modify: `scripts/recover_same_source_leads.py`
- Modify: `tests/test_materialize_source_scans.py`
- Modify: `tests/test_recover_same_source_leads.py`

**Interfaces:**
- Consumes: Task 1 expectations.
- Produces: `ranking.dimensions[name] = {minimum, maximum, weight_percent}`, V2 candidate evidence records, and validated manifest score fields.

- [ ] **Step 1: Replace ranking configuration**

```json
"ranking": {
  "method": "public_value_v2",
  "score_range": [0, 100],
  "allowed_score_step": 5,
  "high_score_threshold": 70,
  "material_delta_threshold": 70,
  "cross_dimension_reuse_threshold": 3,
  "dimensions": {
    "public_impact": {"minimum": 0, "maximum": 100, "weight_percent": 30},
    "geographic_or_population_scope": {"minimum": 0, "maximum": 100, "weight_percent": 20},
    "urgency_and_safety": {"minimum": 0, "maximum": 100, "weight_percent": 15},
    "structural_or_policy_significance": {"minimum": 0, "maximum": 100, "weight_percent": 15},
    "material_new_development": {"minimum": 0, "maximum": 100, "weight_percent": 10},
    "core_section_relevance": {"minimum": 0, "maximum": 100, "weight_percent": 10}
  }
}
```

Add the approved anchors, casualty floors `30/45/60/75/90/100`, and confidence bands.

- [ ] **Step 2: Extend candidate schema**

Define reusable `$defs` for `evidenceFact`, `consequenceEvidence`, `deltaFact`, `highScoreChallenge`, `crossDimensionRationale`, and normalized `importanceBreakdown`. Make `dimension_evidence` arrays of fact IDs and require all V2 fields on candidates.

- [ ] **Step 3: Extend manifest schema**

Require each formal event to contain:

```json
{
  "scoring_method": "public_value_v2",
  "validated_importance_score": 68.5,
  "validated_grade": "B+",
  "grade_status": "validated",
  "evidence_confidence": 82,
  "confidence_band": "high"
}
```

- [ ] **Step 4: Migrate discovery ranking output to normalized weighted V2**

Pass the source-pool ranking contract into source materialization and same-source recovery. Preserve the existing heuristic ordering by converting each old contribution to its nearest 5-point normalized score, then compute `importance_score` with the configured weights. Emit `ranking_method=public_value_v2`.

- [ ] **Step 5: Parse all changed JSON and run discovery materialization tests**

Run: `python -m json.tool news-source-pool.json` and both schema files.

Run: `python -m unittest tests.test_materialize_source_scans tests.test_recover_same_source_leads -v`

Expected: exit 0 for all three JSON documents and all discovery ranking tests pass.

### Task 3: Implement weighted scoring and evidence gates with TDD

**Files:**
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `scripts/manage_candidate_audit.py`

**Interfaces:**
- Consumes: V2 ranking configuration and schema-shaped candidate dictionaries.
- Produces:
  - `ranking_contract(source_pool) -> dict`
  - `weighted_score(breakdown, ranking) -> float`
  - `validate_v2_candidate(candidate, ranking, label) -> list[str]`
  - `confidence_band(score) -> str`

- [ ] **Step 1: Add failing score-math tests**

```python
def test_v2_weighted_score_uses_configured_weights(self):
    scores = {
        "public_impact": 30, "geographic_or_population_scope": 30,
        "urgency_and_safety": 20, "structural_or_policy_significance": 80,
        "material_new_development": 60, "core_section_relevance": 50,
    }
    self.assertEqual(41.0, MODULE.weighted_score(scores, source_pool()["ranking"]))

def test_v2_scores_must_use_five_point_steps(self):
    candidate = valid_v2_candidate()
    candidate["importance_breakdown"]["public_impact"] = 73
    self.assertTrue(any("5" in error for error in MODULE.validate(audit_doc(candidate), source_pool())))
```

- [ ] **Step 2: Run and confirm RED**

Expected: missing `weighted_score` and V1 validation behavior.

- [ ] **Step 3: Implement configuration-driven score math**

Read dimension names, maxima, and weights from the supplied ranking. Reject missing dimensions, booleans, out-of-range values, non-5 increments, weight totals other than 100, and mismatch among weighted score, importance score, and grade.

- [ ] **Step 4: Add failing realized/potential tests**

```python
def test_potential_fact_cannot_support_actual_impact_scope_or_urgency(self):
    candidate = valid_v2_candidate()
    candidate["dimension_evidence"]["public_impact"] = ["F_POTENTIAL"]
    errors = MODULE.validate(audit_doc(candidate), source_pool())
    self.assertTrue(any("potential" in error and "public_impact" in error for error in errors))

def test_speculative_fact_cannot_support_any_dimension(self):
    candidate = valid_v2_candidate()
    candidate["dimension_evidence"]["structural_or_policy_significance"] = ["F_SPEC"]
    errors = MODULE.validate(audit_doc(candidate), source_pool())
    self.assertTrue(any("speculative" in error for error in errors))
```

- [ ] **Step 5: Implement fact and consequence validation**

Create a unique fact index, validate consequence group membership, reject unknown IDs, and enforce dimension eligibility.

- [ ] **Step 6: Add and satisfy delta, reuse, challenge, policy, confidence, and grade-status tests**

Tests must separately demonstrate:

- material update 70 without `delta_facts` fails;
- one fact reused by three dimensions without rationale fails;
- dimension 70 without a sustained challenge fails;
- total 70 without an overall challenge fails;
- proposal with high realized impact passes only when eligible realized facts exist;
- confidence band mismatch fails without changing importance;
- provisional selected candidate fails and validated candidate passes.

- [ ] **Step 7: Run the full candidate-audit suite**

Run: `python -m unittest tests.test_manage_candidate_audit -v`

Expected: all candidate-audit tests pass.

### Task 4: Bind validated V2 grades into manifest and publisher

**Files:**
- Modify: `tests/test_publish_news_brief.py`
- Modify: `scripts/publish_news_brief.py`
- Modify: `tests/test_validate_news_brief.py`
- Modify: `scripts/validate_news_brief.py`

**Interfaces:**
- Consumes: latest run candidates with V2 validated score fields.
- Produces: exact manifest/audit equality and reader rejection for non-validated events.

- [ ] **Step 1: Add failing publisher tests**

```python
def test_publish_rejects_provisional_candidate_in_manifest(self):
    audit = valid_audit()
    audit["runs"][-1]["candidates"][0]["grade_status"] = "provisional"
    errors = MODULE.validate_candidate_mapping(audit, manifest())
    self.assertTrue(any("validated" in error for error in errors))

def test_publish_rejects_manifest_score_different_from_audit(self):
    event = manifest()["events"][0]
    event["validated_importance_score"] += 5
    self.assertTrue(MODULE.validate_candidate_mapping(valid_audit(), manifest()))
```

- [ ] **Step 2: Run and confirm RED**

Expected: missing V2 equality enforcement.

- [ ] **Step 3: Implement publisher and reader gates**

For each selected/merged C-or-higher candidate, require `grade_status=validated` and exact equality of scoring method, weighted score, grade, confidence, and confidence band with the mapped manifest event. Reader validation rejects manifest events whose status is not validated.

- [ ] **Step 4: Run publisher and reader suites**

Run: `python -m unittest tests.test_publish_news_brief tests.test_validate_news_brief -v`

Expected: all tests pass.

### Task 5: Add calibrated regression fixtures and active-surface documentation

**Files:**
- Create: `tests/fixtures/grading-cases.json`
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `news-brief-settings.md`
- Modify: `.agents/skills/audit-news-candidates/SKILL.md`
- Modify: `.agents/skills/select-news-events/references/severity-rubric.md`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `INSTALL.md`
- Modify: `README.md`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: V2 configuration and validator behavior.
- Produces: six calibrated cases and one consistent active scoring contract.

- [ ] **Step 1: Create fixture cases**

Each case stores ID, summary, normalized breakdown, expected score range, expected grade range, policy stage, consequence classes, and expected validation result. Include the six approved cases.

- [ ] **Step 2: Add failing fixture calibration test, then make fixture values pass through real score math**

```python
def test_grading_regression_cases_stay_in_calibrated_ranges(self):
    for case in load_cases():
        score = MODULE.weighted_score(case["importance_breakdown"], source_pool()["ranking"])
        self.assertGreaterEqual(score, case["expected_score_range"][0], case["case_id"])
        self.assertLessEqual(score, case["expected_score_range"][1], case["case_id"])
        self.assertIn(MODULE.grade_from_importance_score(score), case["expected_grades"])
```

- [ ] **Step 3: Rewrite active scoring documentation**

Document normalized scoring, evidence-before-score, actual versus potential, policy stage without hard caps, fact reuse rationale, high-score challenge, confidence separation, validated-only reader behavior, and the unchanged bands. Remove active `public_value_v1` wording.

- [ ] **Step 4: Add bilingual version record**

Record reason, approach, changed entry points, parameters, validation method, result, and next V2.1 shadow decision in Traditional Chinese and English.

- [ ] **Step 5: Run contract tests**

Run: `python -m unittest tests.test_pipeline_contract tests.test_severity_contract -v`

Expected: all active-surface tests pass and no active V1 residue remains.

### Task 6: Full verification, capsule rebuild, and GitHub publication

**Files:**
- Modify generated: `bootstrap/capsule-manifest.json`, `bootstrap/capsule-payload.tar.xz`, `bootstrap/capsule.part*.txt`

**Interfaces:**
- Consumes: complete V2 source tree.
- Produces: verified runtime capsule and published main commit.

- [ ] **Step 1: Parse all repository JSON and scan active V1 residue**

Run JSON parsing over all tracked `.json` files. Search active configuration, schemas, scripts, prompts, settings, skills, INSTALL, and README for `public_value_v1`; historical version/spec/plan records are allowed.

- [ ] **Step 2: Run the complete bundled-Python regression**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

- [ ] **Step 3: Commit source changes and rebuild capsule against that source commit**

Run `scripts/build_bootstrap_capsule.py --root . --source-commit <source-commit>` and verify capsule identity.

- [ ] **Step 4: Run the complete regression again**

Expected: zero failures, capsule checkout verification included.

- [ ] **Step 5: Commit generated capsule and publish source snapshot to GitHub main**

Publish through the connected GitHub Git Data API, allow the repository workflow to rebuild the remote capsule, and wait for the workflow conclusion.

- [ ] **Step 6: Verify remote main**

Fetch main ref, manifest, configuration, schemas, and prompts. Confirm the manifest source commit equals the published source commit, method is `public_value_v2`, schema fields are present, no active V1 wording remains, and Actions concluded `success`.
