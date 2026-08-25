# Discovery and Public Value V2 Pipeline Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make discovery coverage truthful and complete, remove executable V1 grade rules, separate discovery ordering from semantic-event importance, and prevent non-evidentiary visuals or routine recovery transport from blocking the Reader.

**Architecture:** Source fetchers expose usability separately from completeness; semantic admission is lossless; `news-source-pool.json` is the sole numeric scoring authority. Text publication is primary, while visual and remote-recovery artifacts become conditional enhancements with explicit degraded states.

**Tech Stack:** Python 3 standard library, JSON Schema, Markdown contracts, `unittest`, Git.

## Global Constraints

- Preserve the six Public Value V2 weights and current grade bands.
- Preserve bootstrap integrity and the 14-day durable audit.
- Do not use event categories, elapsed days, source count, geography, or one dimension as a final-grade floor, default, cap, or override.
- All active instructions and `INSTALL.md` must match executable behavior.
- Use the bundled Python at `C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
- Do not use subagents; the user authorized direct execution in the current task.

---

### Task 1: Truthful and complete discovery routes

**Files:**
- Modify: `source-route-config.json`
- Modify: `scripts/fetch_source_routes.py`
- Test: `tests/test_fetch_source_routes.py`

**Interfaces:**
- Consumes: configured GET/POST routes, `window_start`, `window_end`, and GDELT archive parts.
- Produces: per-route `route_ready`, `coverage_complete`, `coverage_status`, page snapshots, and aggregate truthful status.

- [ ] **Step 1: Write failing tests**

```python
def test_config_requires_two_chinanews_dates_and_cna_post_pagination(self):
    config = json.loads((ROOT / "source-route-config.json").read_text(encoding="utf-8"))
    routes = {item["source_id"]: item for item in config["routes"]}
    self.assertEqual([0, -1], routes["chinanews"]["date_offsets_days"])
    self.assertEqual(2, routes["chinanews"]["minimum_ready_variants"])
    self.assertEqual("POST", routes["cna"]["pagination"]["request_method"])

def test_partial_gdelt_archive_is_degraded_not_live_complete(self):
    # Mock an archive result with route_ready=True and archive_complete=False.
    self.assertEqual("degraded", coverage["status"])
    self.assertFalse(coverage["gdelt_live_ready"])
    self.assertEqual("degraded_partial", coverage["results"][0]["coverage_status"])

def test_post_pagination_updates_pageidx_until_next_page_is_empty(self):
    # Local HTTP handler records JSON POST bodies and returns NextPageIdx.
    self.assertEqual([1, 2, 3], requested_page_indexes)
    self.assertTrue(result["pagination_exhausted"])
    self.assertTrue(result["coverage_complete"])
```

- [ ] **Step 2: Run RED tests**

Run: `python -m unittest tests.test_fetch_source_routes -v`
Expected: FAIL because ChinaNews is single-day, GDELT partial is live-ready, and pagination is GET-only.

- [ ] **Step 3: Implement minimal route changes**

```python
def request_payload(route, page_index=None):
    payload = dict(route.get("request_json") or {})
    page_field = (route.get("pagination") or {}).get("page_field")
    if page_field and page_index is not None:
        payload[page_field] = page_index
    return payload or None

# route_ready means usable rows; coverage_complete means the requested traversal completed.
result["coverage_complete"] = bool(result.get("archive_complete", True))
result["coverage_status"] = "complete" if result["coverage_complete"] else "degraded_partial"
```

- [ ] **Step 4: Run GREEN tests and full fetcher tests**

Run: `python -m unittest tests.test_fetch_source_routes tests.test_source_route_fetcher -v`
Expected: PASS.

### Task 2: Lossless semantic admission

**Files:**
- Modify: `scripts/build_news_relevance_gate.py`
- Modify: `schemas/news-relevance-gate.schema.json`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `INSTALL.md`
- Test: `tests/test_build_news_relevance_gate.py`

**Interfaces:**
- Consumes: every verified in-window discovery row.
- Produces: routing decisions for `content_hydration` or `lightweight_semantic_review`; both routes remain in model input.

- [ ] **Step 1: Write failing losslessness test**

```python
def test_weak_gdelt_science_row_reaches_lightweight_semantic_review(self):
    gate = MODULE.build_gate(source_candidates)
    admitted = MODULE.build_admitted_candidates(source_candidates, gate)
    self.assertEqual("lightweight_semantic_review", gate["decisions"][0]["route"])
    self.assertEqual(source_candidates["items"], admitted["items"])
```

- [ ] **Step 2: Run RED, implement, and run GREEN**

Run: `python -m unittest tests.test_build_news_relevance_gate -v`
Expected RED: weak GDELT row uses `structured_review` and is absent.

Implementation: rename the weak route, preserve all candidate IDs in output, and assert exact row conservation.

Expected GREEN: every input row is present exactly once.

### Task 3: Remove V1 grade logic and centralize scoring authority

**Files:**
- Modify: `news-source-pool.json`
- Modify: `user-preferences.example.yaml`
- Modify: `schemas/news-candidate-audit.schema.json`
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `news-brief-settings.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/audit-news-candidates/SKILL.md`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `tests/test_no_obsolete_contracts.py`

**Interfaces:**
- Consumes: `news-source-pool.json.ranking` as the only scoring authority.
- Produces: weighted scores and grades without category defaults or elapsed-day ceilings.

- [ ] **Step 1: Write failing structural and behavior tests**

```python
def test_active_contract_has_no_grade_floor_default_or_ceiling_keys(self):
    forbidden = re.compile(r"(?:min|minimum|default|forced|maximum|ceiling)_grade|default_d_applied")
    self.assertEqual([], structural_key_hits(ROOT, forbidden))

def test_zero_score_dimension_may_have_no_fact_ids(self):
    item = candidate()
    item["importance_breakdown"]["urgency_and_safety"] = 0
    item["dimension_evidence"]["urgency_and_safety"] = []
    recalculate(item)
    self.assertEqual([], MODULE.validate_v2_candidate(item, source_pool()["ranking"], "candidate"))

def test_runtime_grade_bands_and_confidence_bands_come_from_config(self):
    ranking = source_pool()["ranking"]
    self.assertEqual("B", MODULE.grade_from_importance_score(60, ranking))
    self.assertEqual("medium", MODULE.confidence_band(60, ranking))
```

- [ ] **Step 2: Run RED tests**

Run: `python -m unittest tests.test_manage_candidate_audit tests.test_no_obsolete_contracts -v`
Expected: FAIL on existing config/schema/validator keys and zero-score evidence.

- [ ] **Step 3: Implement config-driven scoring and remove hard rules**

```python
def grade_from_importance_score(score, ranking=None):
    bands = (ranking or repository_ranking())["grade_minimum_scores"]
    return max(bands, key=lambda grade: bands[grade] if score >= bands[grade] else -1)

def confidence_band(score, ranking=None):
    bands = (ranking or repository_ranking())["confidence_bands"]
    return next(item["band"] for item in bands if score >= item["minimum"])

if score_value > 0 and not fact_ids:
    errors.append(label + f".dimension_evidence.{dimension} positive score requires fact_id evidence")
```

Remove the five-day ceiling and all cultural/conflict grade defaults. Retain only fact collection, continuity, and no-grade-inheritance constraints.

- [ ] **Step 4: Run GREEN tests**

Run: `python -m unittest tests.test_manage_candidate_audit tests.test_no_obsolete_contracts tests.test_severity_contract -v`
Expected: PASS.

### Task 4: Rename source-scan heuristics to discovery priority

**Files:**
- Modify: `scripts/materialize_source_scans.py`
- Modify: `schemas/news-candidate-audit.schema.json`
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `tests/test_materialize_source_scans.py`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `tests/test_no_obsolete_contracts.py`
- Modify: active documentation and Skills that describe source ranking.

**Interfaces:**
- Consumes: title, summary, section, and raw discovery signals.
- Produces: discovery-priority fields only; no semantic-event importance fields.

- [ ] **Step 1: Write RED schema/output tests**

```python
self.assertEqual("discovery_priority_v1", coverage["discovery_ranking_method"])
self.assertIn("discovery_priority_score", coverage["ranked_items"][0])
self.assertNotIn("importance_score", coverage["ranked_items"][0])
self.assertNotIn("importance_breakdown", coverage["ranked_items"][0])
```

- [ ] **Step 2: Run RED, rename implementation/schema fields, then run GREEN**

Run: `python -m unittest tests.test_materialize_source_scans tests.test_pipeline_contract tests.test_no_obsolete_contracts -v`

Implementation uses bounded discovery signals and never labels them `public_value_v2`.

### Task 5: Make non-evidentiary media and remote recovery conditional

**Files:**
- Modify: `schemas/news-event-manifest.schema.json`
- Modify: `scripts/validate_news_brief.py`
- Modify: `scripts/validate_map_decisions.py`
- Modify: `.agents/skills/collect-news-images/SKILL.md`
- Modify: `.agents/skills/build-news-maps/SKILL.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `.agents/skills/recover-news-run/SKILL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `INSTALL.md`
- Test: `tests/test_validate_news_brief.py`
- Test: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: per-asset `claim_critical` and per-run recovery risk indicators.
- Produces: `ready`, `omitted`, or `degraded` enhancements; only claim-critical evidence blocks.

- [ ] **Step 1: Write failing degradation tests**

```python
def test_ready_text_reader_allows_noncritical_visual_degradation(self):
    manifest = valid_manifest()
    event = manifest["events"][0]
    event["images"].update({"status": "omitted", "claim_critical": False, "omission_reason": "source image unavailable"})
    event["map"].update({"required": True, "status": "omitted", "claim_critical": False, "omission_reason": "renderer unavailable"})
    self.assertEqual([], VALIDATOR.validate_manifest_data(manifest))

def test_claim_critical_visual_still_blocks(self):
    manifest = valid_manifest()
    event = manifest["events"][0]
    event["images"]["status"] = "omitted"
    event["images"]["claim_critical"] = True
    self.assertTrue(VALIDATOR.validate_manifest_data(manifest))
```

- [ ] **Step 2: Run RED, implement conditional gates, and run GREEN**

Run: `python -m unittest tests.test_validate_news_brief tests.test_validate_map_decisions tests.test_pipeline_contract -v`

Documentation changes make local checkpoint/hash the default and remote bundle conditional on explicit risk.

### Task 6: Documentation closure, generated artifacts, final verification, and publication

**Files:**
- Modify: `INSTALL.md` and every active instruction named by structural tests.
- Regenerate: bootstrap capsule artifacts using the repository builder.
- Run: the installed long-horizon final-state acceptance Skill.

**Interfaces:**
- Consumes: the final working tree only.
- Produces: consistent contracts, regenerated closure artifacts, acceptance ledger, and a pushed main commit.

- [ ] **Step 1: Run targeted and full repository tests**

Run: `python -m unittest discover -s tests -q`
Expected: all tests pass.

- [ ] **Step 2: Rebuild generated closure and rerun full tests**

Run in PowerShell:

```powershell
$capsuleSourceCommit = git rev-parse HEAD
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/build_bootstrap_capsule.py --root . --source-commit $capsuleSourceCommit
```

Then rerun the full suite.

- [ ] **Step 3: Run structural searches and `git diff --check`**

Reject active `*_min_grade`, `*_default_grade`, `default_d_applied`, passive five-day ceilings, source-scan `public_value_v2`, unconditional media blocking, and mandatory pre-selection remote bundles.

- [ ] **Step 4: Run the long-horizon acceptance Skill**

Apply its independent-method ledger and reset rule against one final commit fingerprint. If it modifies repository files, restart its final-state pass count.

- [ ] **Step 5: Commit and push**

Commit the verified implementation, fetch `origin/main`, confirm fast-forward safety, and push `HEAD:main`.
