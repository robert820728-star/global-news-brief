# Scheduled Task Lifecycle Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one daily 06:00 ChatGPT Scheduled Task install and run without duplicate creation, occurrence deadlock, self-disable, cross-workflow races, or off-main runtime execution.

**Architecture:** Keep task-control decisions in the installation contract and keep news occurrences unable to mutate task control. Preserve the existing `scheduled_for` ledger field while adding a host-provenance fallback that derives it only for a real Scheduled Task trigger. Serialize every `run-logs` writer on one shared concurrency group and validate requested runtime ancestry before checkout.

**Tech Stack:** Markdown contracts, Python `unittest`, GitHub Actions YAML, bundled Python 3.12, bootstrap capsule tooling.

## Global Constraints

- The formal daily 06:00 task must not be modified by repository runtime occurrences.
- The cancelled ten-minute acceptance automation must not be recreated.
- Every production change starts with a failing test and ends with targeted tests, the full suite, capsule verification, a clean export, and `project-final-state-audit` outcome validation.
- Existing user files and unrelated worktrees remain untouched.
- All agent-facing documents remain English; user-facing acceptance and version records are bilingual Traditional Chinese and English.

---

### Task 1: Duplicate-safe installation state machine

**Files:**
- Modify: `INSTALL.md`
- Modify: `README.md`
- Modify: `mobile-chatgpt-start-prompt.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `tests/test_schedule_prompt_control_plane.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: authoritative Scheduled Task inventory when the host provides it, exact task IDs, and the canonical saved prompt.
- Produces: `ensure_singleton` with legal `present`, `absent`, `multiple_present`, and `unknown` outcomes.

- [ ] **Step 1: Write the failing state-transition tests**

```python
def test_singleton_installer_covers_present_absent_and_unknown_states(self):
    prompt = paste_ready_prompt()
    self.assertIn("本次安裝意圖：ensure_singleton", prompt)
    self.assertIn("authoritative inventory", prompt)
    self.assertIn("multiple_present", prompt)
    self.assertNotIn("本次安裝意圖：create_new", prompt)
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_schedule_prompt_control_plane -v`  
Expected: FAIL because the current starter contains `create_new` and forbids inventory.

- [ ] **Step 3: Implement the minimal contract change**

Replace the default starter and installation lifecycle prose with the four-state `ensure_singleton` transaction. Preserve explicit exact-ID `update_existing`; remove the assertion that anti-duplicate only applies to a second create.

- [ ] **Step 4: Verify GREEN and the complete repository**

Run: `python -m unittest tests.test_schedule_prompt_control_plane -v`  
Expected: PASS.  
Run: `python -m unittest discover -s tests`  
Expected: all tests PASS.

- [ ] **Step 5: Rebuild capsule, run clean-export audit, update the bilingual version record, and commit**

Run the repository capsule builder and verifier, validate a clean tracked export, append the new commit identity and rollback source `03339d41c74d352d705e6a1a11228ba3315b94f9`, then commit with `fix: make schedule install duplicate safe`.

### Task 2: Host-compatible occurrence authority

**Files:**
- Modify: `scheduled-task-prompt-template.md`
- Modify: `INSTALL.md`
- Modify: `README.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-start-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `tests/test_schedule_prompt_control_plane.py`
- Modify: `tests/test_mobile_run_log.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: structured `scheduled_for`, or verified Scheduled Task host provenance with exact task identity and first actual execution timestamp.
- Produces: one normalized `scheduled_for` ledger value; rejects ordinary follow-ups and manually supplied timestamps.

- [ ] **Step 1: Write failing authority-chain tests**

```python
def test_real_host_trigger_can_derive_occurrence_key_without_structured_scheduled_for(self):
    contract = scheduled_contract()
    self.assertIn("HOST_SCHEDULED_TRIGGER_AUTHORITY_FALLBACK", contract)
    self.assertIn("exact task identity", contract)
    self.assertIn("first actual execution timestamp", contract)
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_schedule_prompt_control_plane tests.test_mobile_run_log -v`  
Expected: FAIL because missing `scheduled_for` is currently an unconditional blocker.

- [ ] **Step 3: Implement the minimal authority chain**

Add the fallback contract to every canonical runtime entry. Keep manual chat continuation blocked and keep the existing ledger field/schema stable.

- [ ] **Step 4: Verify GREEN and full regression**

Run the two targeted modules and `python -m unittest discover -s tests`; both must PASS.

- [ ] **Step 5: Rebuild capsule, audit an independent clean export, update version evidence, and commit**

Commit with `fix: accept verified scheduled host occurrence authority` only after fresh evidence passes.

### Task 3: Formal recurring task immutability

**Files:**
- Modify: `scheduled-task-prompt-template.md`
- Modify: `INSTALL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `mobile-chatgpt-daily-prompt.md`
- Modify: `tests/test_schedule_prompt_control_plane.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: runtime failures and run-ledger state.
- Produces: run-ledger/failure receipts only; no task-control operations.

- [ ] **Step 1: Write the failing mutation-prohibition test**

```python
def test_runtime_contract_unconditionally_forbids_formal_task_mutation(self):
    for contract in runtime_contracts():
        self.assertIn("FORMAL_RECURRING_TASK_IMMUTABILITY_GATE", contract)
        self.assertIn("update／pause／disable／delete／reschedule／replace", contract)
```

- [ ] **Step 2: Verify RED**

Run the schedule control-plane test module and observe the missing global invariant.

- [ ] **Step 3: Add one unconditional invariant to each canonical runtime contract**

Permit task-control mutation only in a separate installation or maintenance conversation carrying an exact task ID and direct user authorization.

- [ ] **Step 4: Verify targeted and full suites**

Both commands must exit zero with no failures.

- [ ] **Step 5: Rebuild capsule, clean-export audit, version record, and commit**

Commit with `fix: keep formal news schedule immutable at runtime`.

### Task 4: Shared run-log serialization and main ancestry

**Files:**
- Modify: `.github/workflows/remote-acquisition-bridge.yml`
- Modify: `.github/workflows/mobile-candidate-audit-bridge.yml`
- Modify: `tests/test_remote_acquisition_bridge.py`
- Modify: `tests/test_mobile_candidate_audit_bridge.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: issue number and requested occurrence `main_sha`.
- Produces: one shared `run-logs-issue-<number>` queue and a verified main-ancestor runtime checkout.

- [ ] **Step 1: Write failing workflow tests**

```python
def test_all_run_log_writers_share_one_queued_concurrency_group(self):
    self.assertEqual(remote_group(), candidate_group())
    self.assertEqual(remote_queue(), "max")

def test_pinned_runtime_is_validated_as_main_ancestor_before_checkout(self):
    self.assert_before("Validate occurrence SHA belongs to main history", "Checkout pinned")
```

- [ ] **Step 2: Verify RED**

Run both bridge test modules; expect group and ancestry assertions to fail.

- [ ] **Step 3: Implement shared queue and ancestry guard**

Use the exact group `run-logs-issue-${{ github.event.issue.number }}` with `queue: max`. Fetch `origin/main` and the requested SHA in a temporary Git repository, then run `git merge-base --is-ancestor "$REQUESTED_SHA" refs/remotes/origin/main` before pinned runtime checkout.

- [ ] **Step 4: Verify targeted tests, full suite, and workflow syntax**

Run both bridge modules, the full suite, and parse both YAML files with the repository's workflow contract tests.

- [ ] **Step 5: Rebuild capsule, audit two unchanged-fingerprint clean exports, update version evidence, and commit**

Commit with `fix: serialize run logs and validate runtime ancestry` after both complete audit cycles PASS.

