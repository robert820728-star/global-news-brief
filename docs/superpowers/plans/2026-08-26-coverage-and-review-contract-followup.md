# Coverage and Review Contract Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve truthful discovery coverage through publication and remove remaining forced-evidence and stale-routing contracts.

**Architecture:** Route fetch results remain authoritative for coverage completeness. Materialization records scan execution separately, audit validation retains every configured route, and the release receipt exposes the compact result. Policy and conflict evidence use conditional structures so absence of realized effects does not require invented facts.

**Tech Stack:** Python 3.12+, JSON Schema 2020-12, unittest, GitHub Actions YAML.

## Global Constraints

- Remove the overloaded source-coverage `status` field rather than retaining a compatibility alias.
- Partial and unavailable sources never block publication when verified candidates remain, but they may never be labeled complete.
- Use `news-source-pool.json` as policy authority and preserve all discovery rows for semantic review.
- Do not modify image-search or map-layout policy in this change.
- Write failing behavior tests before production changes and rebuild the checked-in capsule only after source tests pass.

---

### Task 1: Truthful coverage propagation

**Files:**
- Modify: `scripts/fetch_source_routes.py`
- Modify: `scripts/materialize_source_scans.py`
- Modify: `scripts/validate_source_scan_evidence.py`
- Modify: `schemas/news-candidate-audit.schema.json`
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `scripts/publish_news_brief.py`
- Test: `tests/test_fetch_source_routes.py`
- Test: `tests/test_materialize_source_scans.py`
- Test: `tests/test_validate_source_scan_evidence.py`
- Test: `tests/test_manage_candidate_audit.py`
- Test: `tests/test_publish_news_brief.py`

**Interfaces:**
- Consumes: route results with `route_ready`, `coverage_complete`, `coverage_status`, route warning/error, and missing segment/variant evidence.
- Produces: audit schema `1.2.0` source rows with `scan_status`, `coverage_complete`, `coverage_status`, `coverage_reason`, `missing_segments`, and `missing_date_variants`; release receipt `discovery_coverage` summary.

- [ ] Add failing tests proving a partial route remains degraded after materialization, an unavailable configured route remains visible, scan evidence and audit metadata must match, and the receipt preserves degradation.
- [ ] Run the five targeted modules and confirm failures arise from the missing fields/old laundering behavior.
- [ ] Implement the minimum route metadata, materialization, schema, validator, and receipt changes.
- [ ] Run the five targeted modules and confirm they pass.
- [ ] Commit the coverage slice.

### Task 2: Evidence-safe policy and conditional conflict reviews

**Files:**
- Modify: `schemas/news-candidate-audit.schema.json`
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `tests/test_publish_news_brief.py`

**Interfaces:**
- Consumes: existing `policy_stage`, `consequence_evidence`, and grading review objects.
- Produces: empty-but-valid `direct_operational_effects` and minimal nonapplicable conflict objects.

- [ ] Add a full candidate regression where a proposal has `direct_operational_effects=[]` and potential consequences remain separate.
- [ ] Add regressions where unrelated events use `border_conflict_review={"applies": false}` and `ongoing_conflict_review={"applies": false}` while applicable reviews still require all detail fields.
- [ ] Run the candidate-audit tests and confirm the intended failures.
- [ ] Implement conditional schema and Python validation.
- [ ] Run candidate-audit and publisher tests and confirm they pass.
- [ ] Commit the review-data slice.

### Task 3: Relevance authority, CI, and active prose cleanup

**Files:**
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `news-source-pool.json`
- Modify: `.github/workflows/build-bootstrap-capsule.yml`
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `tests/test_no_obsolete_contracts.py`

**Interfaces:**
- Consumes: `content_hydration` and `lightweight_semantic_review` relevance routes.
- Produces: explicit all-row model admission and a hosted full-suite gate.

- [ ] Add failing structural tests forbidding `structured_review`, requiring all-row admission configuration, requiring the workflow full unittest command, and forbidding the two stale phrases.
- [ ] Run those structural tests and confirm expected failures.
- [ ] Apply the smallest config, skill, workflow, and message changes.
- [ ] Rerun structural and relevance tests and confirm they pass.
- [ ] Commit the contract-cleanup slice.

### Task 4: Documentation, generated closure, and final audit

**Files:**
- Modify: `INSTALL.md`
- Modify: `VERSION-RECORD.md`
- Regenerate: `bootstrap/capsule-manifest.json`
- Regenerate: `bootstrap/capsule-payload.tar.xz`
- Regenerate: `bootstrap/capsule.part*.txt`

**Interfaces:**
- Consumes: final source commit and current capsule builder.
- Produces: operator documentation, bilingual version record, verified capsule, and final-state audit evidence.

- [ ] Update INSTALL and version records with scan-vs-coverage semantics, audit schema `1.2.0`, conditional reviews, and hosted full-suite validation.
- [ ] Run targeted tests and the full bundled-Python suite.
- [ ] Commit source/document changes, rebuild the capsule from that exact source commit, and verify it.
- [ ] Run `project-final-state-audit` methods, repair any finding, reset on change, and obtain two consecutive complete cycles on one unchanged final fingerprint.
- [ ] Push to GitHub `main`, validate the hosted workflow and clean remote archive, and record the final SHA.

