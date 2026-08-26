# Three-Part Reader Restoration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `今日總覽／逐條詳報／後續觀察` and the user-approved field-based event report as the only production reader layout without reverting current pipeline improvements.

**Architecture:** Reuse the already present field-based validator as the semantic base, update its header to the current reader-only header, and route publisher/CLI validation exclusively through it. Delete the simplified layout validator and synchronize all active contracts so no parallel reader semantics remain.

**Tech Stack:** Python 3 standard library, JSON/Markdown contracts, `unittest`, Git-tracked bootstrap capsule.

## Global Constraints

- Keep current discovery, scoring, coverage, verification, media, recovery, and run lifecycle behavior unchanged.
- No reader-visible run ID, commit SHA, release marker, internal omission note, or repair log.
- No compatibility mode for the simplified reader layout.
- Use TDD and observe the canonical-path regression fail before production edits.

---

### Task 1: Lock the canonical validator behavior

**Files:**
- Modify: `tests/test_validate_news_brief.py`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `valid_manifest()` and `valid_brief()` test fixtures.
- Produces: executable expectations for `validate_canonical_reader(data, text)`.

- [ ] **Step 1: Write the failing canonical-path tests**

```python
def test_canonical_reader_accepts_three_part_field_layout(self):
    self.assertEqual([], VALIDATOR.validate_canonical_reader(valid_manifest(), valid_brief()))

def test_canonical_reader_rejects_simplified_section_story_layout(self):
    errors = VALIDATOR.validate_canonical_reader(valid_manifest(), simplified_brief())
    self.assertTrue(any("逐條詳報" in error for error in errors), errors)
```

- [ ] **Step 2: Run the focused tests and observe the first test fail because the production path still calls the simplified validator**

Run: `python -m unittest tests.test_validate_news_brief -v`

Expected: the restored-layout canonical test fails for the old simplified-layout gate.

- [ ] **Step 3: Add structural contract assertions**

Assert that the active template and prompts require the three headings and ordered field labels, and no longer require `canonical-sectioned` or forbid field-based detail.

### Task 2: Promote the restored validator and remove the retired path

**Files:**
- Modify: `scripts/validate_news_brief.py`
- Modify: `scripts/publish_news_brief.py` only if its canonical call needs renaming
- Modify: `scripts/check_unique_delivery_gate.py` only if its canonical call needs renaming

**Interfaces:**
- Consumes: manifest `sections`, `events`, `detail`, verification, and visual asset fields.
- Produces: `validate_canonical_reader(data: dict, text: str) -> list[str]` as the only publication oracle.

- [ ] **Step 1: Update the field validator header**

Require `# 每日新聞讀者版`, a manifest-derived statistical-period line, and the exact six-dimension rubric. Continue rejecting backend identity and repair text.

- [ ] **Step 2: Route the canonical entry point to the restored validator**

```python
def validate_canonical_reader(data: dict[str, Any], text: str) -> list[str]:
    return validate_three_part_reader(data, text)
```

- [ ] **Step 3: Remove the simplified layout implementation and `--reader-layout canonical-sectioned` choice**

The `brief` command accepts only `--manifest` and `--input`; publisher and unique-delivery gate continue calling `validate_canonical_reader`.

- [ ] **Step 4: Run focused validator and publisher tests**

Run: `python -m unittest tests.test_validate_news_brief tests.test_publish_news_brief tests.test_unique_delivery_gate -v`

Expected: all selected tests pass.

### Task 3: Synchronize all active reader contracts

**Files:**
- Modify: `news-brief-template.md`
- Modify: `news-brief-settings.md`
- Modify: `INSTALL.md`
- Modify: `README.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `.agents/skills/daily-news-brief/SKILL.md` and relevant references if they define layout
- Modify: `docs/news-rule-matrix.json`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: the canonical validator contract from Task 2.
- Produces: one active operator and model instruction set for the restored layout.

- [ ] **Step 1: Replace the template with the restored three-part skeleton**

Preserve the current statistical window, scoring rubric, claim-critical media behavior, and no-placeholder rule.

- [ ] **Step 2: Replace active simplified-layout prose**

Use one gate name, `CANONICAL_THREE_PART_READER_LAYOUT_GATE`, and remove active statements that field-based detail is retired or forbidden.

- [ ] **Step 3: Update the bilingual version record**

Record the mistaken 2026-08-20 retirement, the selective presentation restoration, rollback sources `134e8d4a` and `42a87ba0`, validation, and next decision.

- [ ] **Step 4: Run focused contract tests**

Run: `python -m unittest tests.test_pipeline_contract tests.test_no_obsolete_contracts -v`

Expected: all selected tests pass and obsolete simplified-layout assertions are absent.

### Task 4: Rebuild and final-state audit

**Files:**
- Regenerate: bootstrap capsule artifacts using the repository generator
- Modify: audit/version evidence only as required by repository convention

**Interfaces:**
- Consumes: the complete modified repository.
- Produces: a fixed fingerprint with two complete audit cycles.

- [ ] **Step 1: Run exact and semantic residue checks**

Search active source, config, docs, skills, workflows, and tests for simplified-layout identifiers, prohibitions, and equivalent prose.

- [ ] **Step 2: Run negative and adversarial reader probes**

Verify that the simplified reader, missing fields, false image descriptions, and separator/follow-up drift fail.

- [ ] **Step 3: Rebuild and verify the bootstrap capsule**

Run the repository-standard capsule generator and verifier, then confirm no generated diff remains after the intended update.

- [ ] **Step 4: Run the complete repository suite twice on one unchanged fingerprint**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures in both final-state cycles.

- [ ] **Step 5: Commit and attempt the authorized GitHub update**

Commit only the intended reader-contract restoration. Push to `main` and verify remote CI when the network is available; otherwise report the exact external blocker without claiming remote completion.

