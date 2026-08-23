# Pre-Manifest Recovery Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist byte-verifiable same-run recovery inputs before the first content-hydration batch.

**Architecture:** Extend the existing connector-safe canonical bundle utility with a pre-manifest recovery profile. It deterministically materializes admitted rows into batches of at most 20, then packs the checkpoint and all pre-selection inputs with the existing lossless base64/chunk transport. Workflow contracts require persistence and restore verification before `select-news-events` starts.

**Tech Stack:** Python 3 standard library, `unittest`, JSON, SHA-256/Git blob integrity, Markdown workflow contracts.

## Global Constraints

- Do not modify prior run artifacts or `logs/current.json`.
- Do not change admission, event identity, scoring, or publisher standards.
- Preserve `canonical-run-bundle-v1` compatibility.
- Use TDD: every production behavior must first fail in a focused test.
- Hydration/review batches contain at most 20 admitted article rows and conserve every admitted candidate exactly once.

---

### Task 1: Deterministic recovery bundle

**Files:**
- Modify: `tests/test_manage_canonical_run_bundle.py`
- Modify: `scripts/manage_canonical_run_bundle.py`

**Interfaces:**
- Consumes: `run_id: str`, checkpoint/source/gate/admitted/preprocessed JSON paths, `batch_index_path`, transport directory, manifest path, and optional `max_batch_rows`/`max_blob_bytes`.
- Produces: `build_hydration_batch_index(run_id: str, admitted: dict, max_batch_rows: int = 20) -> dict` and `pack_pre_manifest_recovery_bundle(...) -> dict`.

- [ ] **Step 1: Write the failing conservation and round-trip tests**

Add a fixture containing 43 admitted candidates and a checkpoint with the same run/window. Assert:

```python
manifest = module.pack_pre_manifest_recovery_bundle(
    run_id=run_id,
    checkpoint_path=checkpoint,
    source_candidates_path=source,
    relevance_gate_path=gate,
    admitted_candidates_path=admitted,
    preprocessed_candidates_path=preprocessed,
    batch_index_path=batch_index,
    transport_dir=transport,
    manifest_path=manifest_path,
    max_batch_rows=20,
    max_blob_bytes=256,
)
self.assertEqual("pre-manifest-recovery", manifest["profile"])
self.assertEqual([20, 20, 3], [item["article_row_count"] for item in batch_data["batches"]])
self.assertEqual(43, batch_data["candidate_count"])
```

Delete the original files, restore the bundle, and assert byte equality for all six logical artifacts. Add rejection tests for duplicate candidate ids and checkpoint/admitted run or window mismatches.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_manage_canonical_run_bundle -v
```

Expected: FAIL because `pack_pre_manifest_recovery_bundle` does not exist.

- [ ] **Step 3: Implement deterministic batching**

Add:

```python
def build_hydration_batch_index(*, run_id: str, admitted: dict, max_batch_rows: int = 20) -> dict:
    if not 1 <= max_batch_rows <= 20:
        raise ValueError("max_batch_rows must be between 1 and 20")
    items = admitted.get("items")
    if not isinstance(items, list):
        raise ValueError("admitted candidate items must be an array")
    seen = set()
    rows = []
    for item in items:
        candidate_id = str(item.get("candidate_id", ""))
        if not candidate_id or candidate_id in seen:
            raise ValueError("admitted candidate ids must be non-empty and unique")
        seen.add(candidate_id)
        rows.append({
            "candidate_id": candidate_id,
            "source_id": str(item.get("source_id", "")),
            "canonical_url": str(item.get("canonical_url") or item.get("url") or ""),
            "summary_quality": str(item.get("summary_quality", "")),
        })
    batches = []
    for offset in range(0, len(rows), max_batch_rows):
        batch_rows = rows[offset:offset + max_batch_rows]
        batches.append({
            "batch_id": f"batch-{len(batches) + 1:03d}",
            "article_row_count": len(batch_rows),
            "items": batch_rows,
        })
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "candidate_count": len(rows),
        "max_batch_rows": max_batch_rows,
        "batches": batches,
    }
```

- [ ] **Step 4: Implement the recovery profile and CLI**

Add `pack_pre_manifest_recovery_bundle()` to validate run/window consistency, write the batch index atomically, call `pack_bundle()` with these logical paths, and add `profile="pre-manifest-recovery"`:

```text
recovery/checkpoint.json
recovery/source-candidates.json
recovery/news-relevance-gate.json
recovery/model-source-candidates.json
recovery/preprocessed-candidates.json
recovery/content-hydration-batches.json
```

Add a `pack-recovery` CLI with explicit path arguments and `--max-batch-rows` defaulting to 20.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_manage_canonical_run_bundle -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add scripts/manage_canonical_run_bundle.py tests/test_manage_canonical_run_bundle.py
git commit -m "fix: persist pre-manifest recovery inputs"
```

### Task 2: Enforce the recovery boundary in workflow contracts

**Files:**
- Modify: `tests/test_pipeline_contract.py`
- Modify: `.agents/skills/daily-news-brief/SKILL.md`
- Modify: `.agents/skills/recover-news-run/SKILL.md`
- Modify: `daily-schedule-prompt.md`
- Modify: `scripts/news_run_checkpoint.py`
- Modify: `VERSION-RECORD.md`

**Interfaces:**
- Consumes: the `pack-recovery`, `verify`, and `restore` CLI commands from Task 1.
- Produces: a mandatory `PRE_MANIFEST_RECOVERY_BUNDLE_GATE` between completed preprocessing and running selection.

- [ ] **Step 1: Write the failing contract test**

Add a test that asserts all workflow documents contain `PRE_MANIFEST_RECOVERY_BUNDLE_GATE`, `pack-recovery`, the six required logical artifact names, `atomic tree/commit`, and `restore`. Assert the gate text appears before the first `select-news-events` execution instruction. Assert `scripts/manage_canonical_run_bundle.py` is in `BOOTSTRAP_REQUIRED_PATHS`.

- [ ] **Step 2: Run contract tests and verify RED**

Run:

```powershell
python -m unittest tests.test_pipeline_contract tests.test_news_run_checkpoint -v
```

Expected: FAIL because the pre-manifest recovery gate is absent.

- [ ] **Step 3: Add the minimal workflow contract**

Document the exact command sequence after preprocessing:

```powershell
python scripts/manage_canonical_run_bundle.py pack-recovery --run-id <run-id> --checkpoint <checkpoint> --source-candidates <source-candidates> --relevance-gate <relevance-gate> --admitted-candidates <model-source-candidates> --preprocessed-candidates <preprocessed-candidates> --batch-index <content-hydration-batches> --transport-dir <transport-dir> --manifest <recovery-bundle-manifest>
python scripts/manage_canonical_run_bundle.py verify --manifest <recovery-bundle-manifest> --transport-dir <transport-dir>
python scripts/manage_canonical_run_bundle.py restore --manifest <recovery-bundle-manifest> --transport-dir <transport-dir> --output-dir <restore-proof-dir>
```

Require one atomic `run-logs` tree/commit and byte-identity readback before selection starts. Add the bundle script to `BOOTSTRAP_REQUIRED_PATHS`. Record the attempted version and validation result in `VERSION-RECORD.md`.

- [ ] **Step 4: Run contract and focused suite**

Run:

```powershell
python -m unittest tests.test_manage_canonical_run_bundle tests.test_pipeline_contract tests.test_news_run_checkpoint tests.test_pre_manifest_recovery -v
```

Expected: all tests pass.

- [ ] **Step 5: Run regression suite and inspect diff**

Run:

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
git diff --check
git status --short
```

Expected: no new failures beyond the documented baseline capsule/Pillow/resolver failures; no whitespace errors; only planned files changed.

- [ ] **Step 6: Commit and push**

```powershell
git add .agents/skills/daily-news-brief/SKILL.md .agents/skills/recover-news-run/SKILL.md daily-schedule-prompt.md scripts/news_run_checkpoint.py tests/test_pipeline_contract.py VERSION-RECORD.md
git commit -m "fix: require durable pre-manifest recovery bundle"
git push origin HEAD:main
```

### Task 3: Capsule verification and retest scheduling

**Files:**
- No source edits unless GitHub Actions reports a build defect directly caused by Tasks 1-2.

**Interfaces:**
- Consumes: pushed source commit and GitHub Actions capsule output.
- Produces: verified capsule manifest with source commit/hash closure and one future fresh final-acceptance task.

- [ ] **Step 1: Poll main until a new capsule commit appears**

Confirm `bootstrap/capsule-manifest.json.source_commit` equals the pushed source commit and verify runtime inventory includes the changed script and skills.

- [ ] **Step 2: Verify capsule from a clean checkout**

Run the repository capsule verifier and require exit code 0.

- [ ] **Step 3: Create exactly one fresh retest**

In target thread `6a8640a3-f48c-83ee-b968-28be68992410`, create/update one `新聞管線最終驗收重測` at least five minutes in the future. Require fresh main/run/diag/window and complete S4+S5.
