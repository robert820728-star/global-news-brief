# Semantic Event Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make semantic events the only countable and gradable news unit while preserving every article row in a disposition ledger.

**Architecture:** Keep deterministic preprocessing article-level. Add an audit-level row disposition ledger that maps every successful source row either to a semantic event or to an explicit non-news/unresolved outcome. Validate conservation and require event identity before scoring or publication.

**Tech Stack:** Python 3 standard library, JSON Schema draft 2020-12, unittest, Markdown execution contracts.

## Global Constraints

- No fixed article or event count limit.
- Article URLs and provisional title groups are evidence diagnostics, never news counts.
- Only semantic event objects receive the six-dimension score.
- Existing reader layout remains unchanged.
- Existing fourteen-day historical runs remain readable; strict new fields apply to the latest run.

---

### Task 1: Event and disposition schema

**Files:**
- Modify: `schemas/news-candidate-audit.schema.json`
- Test: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: latest audit run and candidate objects.
- Produces: `article_dispositions`, `semantic_event_id`, `event_identity`, and three row-disposition count fields.

- [ ] **Step 1: Write the failing schema contract test** asserting the new fields, enums, and event-identity keys.
- [ ] **Step 2: Run** `python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_semantic_event_ledger_schema_contract` and expect missing-field failures.
- [ ] **Step 3: Add the minimal JSON Schema definitions** for dispositions and event identity while leaving them optional for historical runs.
- [ ] **Step 4: Rerun the test** and expect `OK`.
- [ ] **Step 5: Commit** the schema and test.

### Task 2: Audit conservation and semantic-event enforcement

**Files:**
- Modify: `scripts/manage_candidate_audit.py`
- Modify: `tests/test_manage_candidate_audit.py`
- Modify: `tests/test_publish_news_brief.py`

**Interfaces:**
- Consumes: source coverage, dispositions, semantic event candidates, and `processing_counts`.
- Produces: validation errors for missing rows, unresolved rows, invalid mappings, duplicate event IDs, and non-conserved counts.

- [ ] **Step 1: Write failing tests** for two source reports mapped to one semantic event, an unresolved row, and a candidate missing event identity.
- [ ] **Step 2: Run** the three named candidate-audit tests and confirm failures are caused by absent enforcement.
- [ ] **Step 3: Implement latest-run validation** that matches `(source_id, url)` rows exactly, validates disposition semantics, validates event identities, and recomputes all counts.
- [ ] **Step 4: Update shared valid fixtures** to express one semantic event backed by all fixture source rows.
- [ ] **Step 5: Run** `python -m unittest tests.test_manage_candidate_audit tests.test_publish_news_brief` and expect `OK`.
- [ ] **Step 6: Commit** validator and fixture changes.

### Task 3: Article-level terminology and execution gates

**Files:**
- Modify: `scripts/preprocess_news_candidates.py`
- Modify: `tests/test_preprocess_news_candidates.py`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `.agents/skills/audit-news-candidates/SKILL.md`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: raw article rows and provisional groups.
- Produces: explicitly article-level output and instructions that create events only after semantic review.

- [ ] **Step 1: Write failing terminology tests** that forbid preprocessor output from describing rows or title groups as events/news and require the semantic-event gate in all execution surfaces.
- [ ] **Step 2: Run** the focused preprocessing and contract tests and confirm expected failures.
- [ ] **Step 3: Rename output aliases and documentation** to article-level terms, retain compatibility fields only with an explicit deprecated article-count label, and add the semantic-event ledger gate.
- [ ] **Step 4: Run** the focused tests and expect `OK`.
- [ ] **Step 5: Commit** runtime and contract changes.

### Task 4: Capsule and complete verification

**Files:**
- Regenerate: `bootstrap/capsule-manifest.json`
- Regenerate: `bootstrap/capsule-payload.tar.xz`
- Regenerate: `bootstrap/capsule.part*.txt`

**Interfaces:**
- Consumes: final runtime source commit.
- Produces: verified runtime capsule and complete passing test evidence.

- [ ] **Step 1: Rebuild** with `python scripts/build_bootstrap_capsule.py --source-commit <source-sha>`.
- [ ] **Step 2: Verify** with `python scripts/verify_bootstrap_capsule.py` and expect `status=completed`.
- [ ] **Step 3: Run** `python -m unittest discover -s tests -p "test_*.py"` and expect zero failures.
- [ ] **Step 4: Commit** generated capsule files.
- [ ] **Step 5: Push** the source commit and verify the GitHub Actions capsule commit on `main`.
