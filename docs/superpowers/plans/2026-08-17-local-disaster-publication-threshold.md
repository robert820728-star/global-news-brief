# Local Disaster Publication Threshold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce a 50-death C-grade floor for ordinary local disasters while preserving verified scope and conflict exceptions.

**Architecture:** Add one compact review object to the candidate audit and validate it only for the newest retained run. Keep military/conflict decisions in their existing reviews, and align the prose rules, mobile prompt, examples, and capsule with the executable validator.

**Tech Stack:** Python 3, unittest, JSON Schema, Markdown contracts, deterministic bootstrap capsule.

## Global Constraints

- Under 50 confirmed deaths is below C for an ordinary local disaster with no special significance.
- 50–99 confirmed deaths is C when no special significance exists.
- 100–249 confirmed deaths is B; 250 or more is A-.
- Any upward or downward adjustment requires a concrete reason; upward adjustment also requires a verified special-significance trigger.
- Verified special significance may override the casualty floor, including extreme abnormal missing/serious-injury/evacuation counts, major public-system disruption, rapid growth, multinational impact, rare mechanisms, regulatory/systemic risk, monitored-region conflict escalation, or another event-specific verified trigger.
- Existing military and ongoing-conflict rules remain authoritative.
- Do not stage unrelated generated maps or `work/` files.

---

### Task 1: Executable audit gate

**Files:** `tests/test_manage_candidate_audit.py`, `scripts/manage_candidate_audit.py`, `schemas/news-candidate-audit.schema.json`.

**Interfaces:** Consumes `grading_evidence`; produces `local_disaster_review` validation errors and a schema property.

- [ ] Add the fixed acceptance set: 49 deaths, 50 deaths, 50–99 overgrading, 100-death B, 250-death A-, reasoned upward adjustment, reasoned downward adjustment, extreme-scope exception, monitored-region conflict risk, and conflict/local-disaster overlap.
- [ ] Run `python -m unittest tests.test_manage_candidate_audit -v` and confirm failures are caused by the missing gate.
- [ ] Implement the minimal validator and schema contract.
- [ ] Rerun the target test module and confirm it passes.

### Task 2: Rule and mobile alignment

**Files:** `tests/test_pipeline_contract.py`, `news-brief-settings.md`, `news-brief-examples.md`, `.agents/skills/select-news-events/SKILL.md`, `.agents/skills/select-news-events/references/severity-rubric.md`, `.agents/skills/audit-news-candidates/SKILL.md`, `daily-schedule-prompt.md`, `mobile-chatgpt-daily-prompt.md`.

**Interfaces:** Produces one precedence order and the exact 50-death/mobile contract consumed by scheduled runs.

- [ ] Add failing text-contract tests for the 50-death gate, special-significance exception, and military-rule precedence.
- [ ] Run the contract tests and confirm the required language is absent.
- [ ] Align all rule surfaces and remove the contradictory 100-death A- example.
- [ ] Rerun the contract tests and the audit tests.

### Task 3: Runtime delivery and publication

**Files:** `VERSION-RECORD.md`, `bootstrap/capsule-manifest.json`, `bootstrap/capsule.part*.txt`.

**Interfaces:** Produces a verified capsule and a GitHub `main` commit readable by mobile ChatGPT.

- [ ] Record the bilingual version entry.
- [ ] Run `python scripts/build_bootstrap_capsule.py` and `python scripts/verify_bootstrap_capsule.py`.
- [ ] Run the full unittest suite.
- [ ] Stage only declared files, commit, and push the current commit to `origin/main`.
