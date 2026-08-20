# URL Recovery and Batched Model Triage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover descriptive titles from content URLs and package all lossless evidence groups into deterministic batches of at most 100 model units.

**Architecture:** A new standard-library pilot imports the first lossless grouping module, adds conservative URL-slug recovery, reuses exact grouping, and creates a separately verifiable batch manifest. Fuzzy similarity remains review-only and the code makes no news-value decision.

**Tech Stack:** Python 3 standard library, `unittest`, JSON CLI artifacts.

## Global Constraints

- Preserve every input row exactly once through a generated `row_id`.
- Never assign importance, grade, publication status, or `non_news` in this stage.
- Never automatically merge fuzzy titles.
- Never allow a model batch to exceed 100 groups.
- Do not modify the production schedule or GitHub `main`.

---

### Task 1: Conservative URL title recovery

**Files:**
- Create: `scripts/pilot_url_recovery_batched_triage.py`
- Create: `tests/test_pilot_url_recovery_batched_triage.py`

**Interfaces:**
- Produces `recover_title_from_url(url: str) -> str | None`.
- Produces `build_recovered_report(payload: dict, batch_size: int, sample_size: int, seed: int) -> dict`.

- [ ] Write tests proving descriptive slugs recover, numeric and opaque paths do not recover, original usable titles win, recovered exact titles group only within the same section, and all rows remain conserved.
- [ ] Run `python -m unittest tests.test_pilot_url_recovery_batched_triage -v` and confirm RED because the module does not exist.
- [ ] Implement percent-decoding, file-extension removal, path-segment selection, structural rejection, effective-title provenance, and exact regrouping.
- [ ] Run the focused tests and `python -m py_compile scripts/pilot_url_recovery_batched_triage.py` until GREEN.

### Task 2: Deterministic model batch manifest

**Files:**
- Modify: `scripts/pilot_url_recovery_batched_triage.py`
- Modify: `tests/test_pilot_url_recovery_batched_triage.py`

**Interfaces:**
- Produces `build_model_batches(groups: list[dict], batch_size: int) -> list[dict]`.
- Produces `verify_recovered_report(report: dict) -> dict[str, int]`.

- [ ] Extend the existing tests to prove every group occurs in exactly one batch, no batch exceeds the configured size, order and hashes are deterministic, and tampering fails validation.
- [ ] Run the focused test and confirm the new assertions fail.
- [ ] Implement stable sorting, compact model items, per-batch SHA-256, and independent verification.
- [ ] Run the focused tests until GREEN without increasing the frozen test count.

### Task 3: Full execution and model audit

**Files:**
- Create at runtime only: `pilot-output/url-recovery-batched-triage.json`
- Create: `docs/pilot-results/2026-08-20-url-recovery-batched-triage-result.md`

- [ ] Run the full 20,450-row artifact with `--batch-size 100 --sample-size 200 --seed 20260820`.
- [ ] Independently verify the report and repeat the run to compare SHA-256 hashes.
- [ ] Model-review every multi-row group newly created by recovered titles, 200 unresolved rows, and 200 fuzzy review pairs.
- [ ] Run compatibility checks on distinct older saved artifacts, but label them non-comparable because their acquisition logic predates the current GDELT archive design.
- [ ] Record bilingual counts, model findings, limitations, and the next promotion decision.

### Task 4: Publish experimental evidence

**Files:**
- Publish only the two pilot scripts, two test modules, specs, plans, and compact result documents.

- [ ] Run fresh focused tests, compile checks, full report verification, and file-scope inspection.
- [ ] Commit and push to `codex/lossless-article-grouping-pilot` based on its current head.
- [ ] Verify the remote branch is ahead of `main` and that no production schedule file changed.

