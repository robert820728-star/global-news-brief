# Bootstrap Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight pre-checkpoint diagnostics, bounded retry evidence, adaptive grouped capsule retrieval, and a best-effort external run ledger for mobile ChatGPT scheduled runs.

**Architecture:** A standalone standard-library helper owns one atomic `bootstrap-progress.json` and deterministic `RUN_RECEIPT`. The scheduled contract fetches that helper from the pinned commit, uses grouped 16-line reads with verified 8-line fallback, and mirrors coarse progress to one GitHub Issue comment without making GitHub writes a pipeline dependency.

**Tech Stack:** Python 3 standard library, JSON, unittest, Markdown execution contracts, GitHub REST connector, GitHub Actions Ubuntu CI.

## Global Constraints

- Do not create the news checkpoint before a verified workspace exists.
- The mobile scheduled path must not use PowerShell.
- Successful block fetches persist once per completed chunk; retry and failure events persist immediately.
- Each individual 8-line block receives one initial attempt plus at most three retries with 2, 5, and 10 second backoffs.
- GitHub ledger writes are best-effort and never block canonical news delivery.
- Successful canonical delivery removes local bootstrap progress and retains one compact external receipt.
- Do not modify or stage existing generated map changes or `work/` files.

---

### Task 1: Atomic bootstrap progress helper

**Files:**
- Create: `bootstrap/bootstrap_progress.py`
- Create: `bootstrap/bootstrap-progress.schema.json`
- Create: `tests/test_bootstrap_progress.py`

**Interfaces:**
- Produces: `new_progress(run_id: str, resolved_commit: str, chunks_total: int) -> dict`
- Produces: `record_chunk(progress: dict, chunk_name: str, completed: int, blocks_total: int) -> dict`
- Produces: `record_attempt(progress: dict, *, chunk_name: str, block_index: int, attempt: int, byte_size: int, sha256: str | None, error: str | None) -> dict`
- Produces: `render_receipt(progress: dict) -> str`
- Produces: CLI commands `init`, `chunk`, `attempt`, `stage`, `ledger`, `receipt`, and `finalize`.

- [ ] **Step 1: Write failing persistence and interruption tests**

```python
def test_interruption_after_chunk_40_keeps_valid_running_record(self):
    progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
    for completed in range(1, 41):
        progress = PROGRESS.record_chunk(progress, f"capsule.part{completed:04d}.txt", completed, 4)
    PROGRESS.atomic_write(self.path, progress)
    loaded = PROGRESS.load_progress(self.path)
    self.assertEqual(loaded["chunks_completed"], 40)
    self.assertEqual(loaded["status"], "running")
```

- [ ] **Step 2: Run RED test**

Run: `python -m unittest tests.test_bootstrap_progress -v`
Expected: import or missing-file failure for `bootstrap/bootstrap_progress.py`.

- [ ] **Step 3: Implement the minimal atomic record**

```python
def atomic_write(path: Path, progress: dict) -> None:
    raw = (json.dumps(progress, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
```

- [ ] **Step 4: Add RED tests for four bounded attempts, receipt, and success cleanup**

```python
def test_initial_attempt_plus_three_retries_is_bounded(self):
    progress = PROGRESS.new_progress("run-1", "a" * 40, 44)
    for attempt in range(1, 5):
        progress = PROGRESS.record_attempt(
            progress, chunk_name="capsule.part0041.txt", block_index=3,
            attempt=attempt, byte_size=1024, sha256="b" * 64, error="sha mismatch"
        )
    self.assertEqual(len(progress["current_block_attempts"]), 4)
    self.assertEqual(progress["retry_count"], 3)
```

- [ ] **Step 5: Implement bounded attempts, CLI, schema validation, receipt, and finalize cleanup**

`finalize --canonical-delivery true --clear` must render the receipt before unlinking the progress file. `receipt` never deletes. Attempts outside `1..4`, decreasing chunk counts, invalid SHAs, and unknown statuses fail closed.

- [ ] **Step 6: Run GREEN tests and compile**

Run: `python -m unittest tests.test_bootstrap_progress -v && python -m py_compile bootstrap/bootstrap_progress.py`
Expected: all bootstrap progress tests pass with no warnings.

- [ ] **Step 7: Commit Task 1**

```bash
git add bootstrap/bootstrap_progress.py bootstrap/bootstrap-progress.schema.json tests/test_bootstrap_progress.py
git commit -m "feat: add atomic bootstrap progress receipt"
```

### Task 2: Mobile Stage -1 transport and receipt contract

**Files:**
- Modify: `bootstrap-workspace.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `bootstrap/TRANSPORT_FORMAT.md`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Consumes: `bootstrap/bootstrap_progress.py` CLI from Task 1.
- Produces: exact grouped-fetch, fallback, retry, cleanup, and `RUN_RECEIPT` execution contract.

- [ ] **Step 1: Add failing contract tests**

```python
def test_mobile_bootstrap_has_bounded_diagnostic_transport(self):
    for document in (prompt, bootstrap):
        self.assertIn("bootstrap/bootstrap_progress.py", document)
        self.assertIn("16-line", document)
        self.assertIn("one initial attempt plus at most three retries", document)
        self.assertIn("2, 5, and 10", document)
        self.assertIn("RUN_RECEIPT", document)
        self.assertIn("external_ledger: unavailable", document)
```

- [ ] **Step 2: Run RED contract test**

Run: `python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_mobile_bootstrap_has_bounded_diagnostic_transport -v`
Expected: failure because the new contract text is absent.

- [ ] **Step 3: Add the minimal Stage -1 rules**

Require the helper and schema to be fetched from the pinned SHA and checked against the recursive tree. Initialize progress before manifest/chunk retrieval. A grouped 16-line response is split into the two manifest-declared 8-line blocks and both hashes must pass; otherwise use individual 8-line reads. Persist each completed chunk and every retry/failure. Emit the receipt on every controlled exit.

- [ ] **Step 4: Run GREEN contract and progress tests**

Run: `python -m unittest tests.test_pipeline_contract tests.test_bootstrap_progress -v`
Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add bootstrap-workspace.md daily-schedule-prompt.md bootstrap/TRANSPORT_FORMAT.md tests/test_pipeline_contract.py
git commit -m "feat: make mobile bootstrap diagnosable"
```

### Task 3: Best-effort GitHub run ledger

**Files:**
- Create: `bootstrap/RUN_LEDGER_PROTOCOL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `bootstrap-workspace.md`
- Modify: `INSTALL.md`
- Modify: `tests/test_pipeline_contract.py`

**Interfaces:**
- Produces: one stable ledger Issue URL and one-comment-per-run update protocol.
- Consumes: GitHub connector issue-comment create/update operations; no shell GitHub network.

- [ ] **Step 1: Add failing ledger contract test**

```python
def test_external_ledger_is_debounced_and_never_blocks_news(self):
    self.assertIn("one comment per run", prompt)
    self.assertIn("every 8 completed chunks", prompt)
    self.assertIn("at most once every 3 minutes", prompt)
    self.assertIn("must not block", prompt)
    self.assertIn("compact final receipt", prompt)
```

- [ ] **Step 2: Run RED ledger test**

Run: `python -m unittest tests.test_pipeline_contract.PipelineContractTests.test_external_ledger_is_debounced_and_never_blocks_news -v`
Expected: failure because the ledger protocol is absent.

- [ ] **Step 3: Create and probe the real ledger Issue**

Create `Daily News Run Ledger`, add one permission-probe comment, then update that same comment. Record the Issue URL in `bootstrap/RUN_LEDGER_PROTOCOL.md`. Do not include news content or credentials.

- [ ] **Step 4: Document best-effort behavior and success compaction**

If read, create, or update is unavailable, write `external_ledger: unavailable` locally and continue. On success replace the comment with the compact receipt; on failure retain diagnostic fields. Locate a resumed run comment by the run's marker, for example `<!-- daily-news-run:20260817T060000Z-ab12 -->`.

- [ ] **Step 5: Run GREEN ledger contract**

Run: `python -m unittest tests.test_pipeline_contract -v`
Expected: all pipeline contracts pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add bootstrap/RUN_LEDGER_PROTOCOL.md bootstrap-workspace.md daily-schedule-prompt.md INSTALL.md tests/test_pipeline_contract.py
git commit -m "feat: add best-effort external run ledger"
```

### Task 4: Capsule, version record, cyclic regression, and GitHub publication

**Files:**
- Modify: `scripts/build_bootstrap_capsule.py`
- Modify: `.github/workflows/build-bootstrap-capsule.yml`
- Modify: `tests/test_bootstrap_capsule.py`
- Modify: `README.md`
- Modify: `VERSION-RECORD.md`
- Regenerate: `bootstrap/capsule-manifest.json`
- Regenerate: `bootstrap/capsule.part*.txt`

**Interfaces:**
- Consumes: the Task 1 helper as an explicit runtime file.
- Produces: verified mobile capsule and Ubuntu coverage for the helper tests.

- [ ] **Step 1: Add RED capsule closure assertions**

```python
self.assertIn("bootstrap/bootstrap_progress.py", runtime_paths)
self.assertIn("bootstrap/bootstrap-progress.schema.json", runtime_paths)
```

- [ ] **Step 2: Run RED capsule test**

Run: `python -m unittest tests.test_bootstrap_capsule.BootstrapCapsuleTests.test_runtime_closure_includes_source_route_config -v`
Expected: failure until both files enter `RUNTIME_FILES`.

- [ ] **Step 3: Include and compile the helper in the capsule workflow**

Add both bootstrap files to `RUNTIME_FILES`, compile the helper in Ubuntu, and add `tests/test_bootstrap_progress.py` to focused tests.

- [ ] **Step 4: Run cyclic round A — focused failure simulations**

Run: `python -m unittest tests.test_bootstrap_progress tests.test_pipeline_contract tests.test_bootstrap_capsule -v`
Expected: chunk-41 interruption, four-attempt exhaustion, cleanup, transport contract, and capsule tests all pass. Report any failure cause and the minimal corrective change before rerunning.

- [ ] **Step 5: Rebuild and verify capsule**

Run: `python scripts/build_bootstrap_capsule.py --source-commit 6efc7c6d4d00b19faad0e3241d18a901f81669fd` then `python scripts/verify_bootstrap_capsule.py`. Immediately before execution, replace that recorded starting SHA only if the two nonce-bearing GitHub endpoints both prove that `main` has advanced.
Expected: completed status, no PowerShell, no generated PNG/SVG.

- [ ] **Step 6: Run cyclic round B — full bundled-runtime regression**

Run: `C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v`.
Expected: all tests pass. A system-Python Pillow failure is an environment mismatch and must be rerun only with the already resolved bundled runtime.

- [ ] **Step 7: Update bilingual version record and commit implementation**

Record reason, confirmed cause, approach, changed entry points, configuration, validation, result, and next decision in Traditional Chinese and English.

- [ ] **Step 8: Publish through the GitHub Git Data API**

Resolve `main` through both nonce-bearing endpoints, create blobs/tree/commit against that parent, update `main` fast-forward only, and wait for Ubuntu CI.

- [ ] **Step 9: Run cyclic round C — remote verification**

Require successful Ubuntu CI, matching core remote blob SHAs, manifest source commit equal to the feature commit or its first parent, helper/schema present, and no PowerShell/generated images. Report and repair any failing boundary, then repeat only that boundary and the full remote acceptance.

### Task 5: Acceptance email

**Files:** none.

**Interfaces:**
- Consumes: final GitHub commit, CI URL, ledger Issue URL, test counts, capsule fingerprint, and known mobile-only acceptance limitation.
- Produces: one Gmail message to the connected account owner for final user acceptance.

- [ ] **Step 1: Resolve the connected Gmail account identity**

Use the Gmail connector's account/profile capability. If it cannot identify a recipient address, stop only the email step and request the address; do not alter the verified repository result.

- [ ] **Step 2: Send the bilingual acceptance email**

Subject: `每日新聞手機排程 Stage -1 診斷改善驗收 / Mobile Stage -1 diagnostics acceptance`

The body must include: what changed, every test round's failure/countermeasure/result, final commit and CI links, ledger link, exact `RUN_RECEIPT` fields, and the one remaining user action—rerun the mobile Scheduled Task and reply with its receipt if the host still terminates unexpectedly.

- [ ] **Step 3: Verify send result**

Record the Gmail message/thread identifier and report it in the final delivery summary. Do not send duplicates.
