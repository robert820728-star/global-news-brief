# Integrated Six-Dimension Grading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive final SS-E candidate grades from the combined evidenced six-dimension total without geographic hard caps or exception patches.

**Architecture:** Preserve the existing six weights, add one deterministic score-to-grade mapping, and require candidate-level score plus evidence. Geographic reach remains a 20-point component, while importance/severity is expressed through the 30-point public-impact component and can combine with the other four dimensions.

**Tech Stack:** Python 3 standard library, JSON, JSON Schema, `unittest`

## Global Constraints

- Weights remain 30, 20, 15, 15, 10, and 10.
- No single dimension sets a hard final-grade ceiling or requires an exception flag.
- Score bands are SS 97, S+ 94, S 90, S- 85, A+ 80, A 75, A- 70, B+ 65, B 60, B- 55, C+ 50, C 45, C- 40, D 20, and E 0.
- Each final candidate must store all six scores and all six evidence statements.
- Do not change discovery, GDELT fallback, fourteen-day merging, images, or delivery.
- Do not commit or push without separate authorization.

---

### Task 1: Replace the rejected hard-cap design

- [x] Remove `ordinary_scope_ceiling`, scope override triggers, and hard-cap tests.
- [x] Add four RED cases for Chongqing mayor D, Taiwan three-county C, four-country B, and severe single-area events rising through their total score.
- [x] Implement `grade_from_importance_score` and `grade_from_importance_breakdown`.
- [x] Run the four cases and verify `Ran 4 tests ... OK`.

### Task 2: Enforce final score evidence

- [x] Require latest-run candidate `importance_score`, six-key `importance_breakdown`, and six-key `dimension_evidence`.
- [x] Reject a `provisional_grade` that differs from the score band.
- [x] Add schema properties while retaining old fourteen-day runs through latest-run validator enforcement.
- [x] Lock grade bands and the no-hard-cap principles in `news-source-pool.json`.

### Task 3: Update guidance and verify

- [x] Update `news-brief-settings.md` and the selection severity reference with the integrated model, casualty floors, urgency anchors, score anchors, and calibration cases.
- [x] Run focused grading, severity, pipeline, and publisher tests (80/80 passed).
- [x] Run `python -m unittest discover -s tests -p "test_*.py"` (225/226 passed; isolated pre-existing capsule overlap failure).
- [x] Add a bilingual version record with RED/GREEN evidence and the next discovery-diagnostic phase.
