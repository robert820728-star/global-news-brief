# Regional Supplement Model Admission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce complete model admission for every in-window CNA and China News provisional group without using media heat as an importance gate.

**Architecture:** A standalone validator derives the required groups from preprocessing evidence and discovery-source roles, then compares them with the model selection artifact. Contract documents invoke the validator before semantic merging and six-dimension scoring.

**Tech Stack:** Python 3 standard library, `unittest`, JSON pipeline artifacts, Markdown runtime contracts.

## Global Constraints

- Heat and keyword signals may prioritize or add recall, but may never exclude a regional-supplement group.
- The validator does not assign importance or grades.
- Existing reader, image, map, temporal, region, and scoring rules remain unchanged.
- Existing untracked run artifacts are out of scope.

---

### Task 1: Regional admission validator

**Files:**
- Create: `scripts/validate_local_source_admission.py`
- Create: `tests/test_validate_local_source_admission.py`

**Interfaces:**
- Consumes: preprocessing JSON, selection JSON, source-pool JSON.
- Produces: `validate_local_source_admission(preprocessed, selection, source_pool) -> tuple[list[str], dict[str, int]]` and a fail-closed CLI.

- [ ] Write tests proving omitted regional groups and rows fail while complete coverage passes.
- [ ] Run `python -m unittest tests.test_validate_local_source_admission -v` and observe failure because the validator is absent.
- [ ] Implement the minimum validator.
- [ ] Re-run the target test and require zero failures.

### Task 2: Runtime contract wiring

**Files:**
- Modify: `news-source-pool.json`
- Modify: `news-brief-settings.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/select-news-events/SKILL.md`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE` and the validator CLI.
- Produces: a mandatory pre-scoring gate in every runtime profile.

- [ ] Write a contract test requiring the policy marker and validator command.
- [ ] Run the focused contract test and observe the missing-contract failure.
- [ ] Add the minimal policy and runtime instructions.
- [ ] Run both focused test modules and require zero failures.

### Task 3: Verification and delivery

**Files:**
- Modify generated bootstrap capsule files using the repository build command.

**Interfaces:**
- Consumes: repository test suite and capsule builder.
- Produces: a verified commit on GitHub `main`.

- [ ] Run the complete repository test suite.
- [ ] Rebuild and verify the bootstrap capsule using the repository workflow commands.
- [ ] Review `git diff --check` and the scoped diff.
- [ ] Commit, push `HEAD:main`, and verify the remote SHA.

