# rc.46 Known-Gap Executable Adapters Implementation Plan

> **Execution:** Use `superpowers:executing-plans` in the current main conversation. Required implementation skills: `superpowers:test-driven-development`, `superpowers:systematic-debugging`, and `superpowers:verification-before-completion`.

**Goal:** Make canonical prompt installation, discovery boundary proof, and raw source-media integrity executable and fail-closed.

**Architecture:** Three small adapters own one boundary each. The prompt builder produces immutable saved-prompt bytes plus a separate extension sidecar. The route fetcher validates configured exhaustion evidence before admission. The image materializer proves original input bytes before normalizing an attachment asset.

**Tech Stack:** Python 3 standard library, Pillow, `unittest`, existing repository capsule and audit scripts.

---

### Task 1: Canonical Scheduled Task install payload

**Files:**
- Create: `scripts/build_scheduled_task_install_payload.py`
- Create: `tests/test_build_scheduled_task_install_payload.py`
- Modify: `INSTALL.md`, `README.md`, `mobile-chatgpt-start-prompt.md`

1. Add failing tests for exact two-line substitution, separate extension sidecar, receipt hashes/counts, and invalid placeholder/extension rejection.
2. Run the focused test and confirm it fails because the builder does not exist.
3. Implement the minimal builder and atomic outputs.
4. Run the focused test to green.
5. Update the three installation documents and add contract assertions for the executable builder and non-mutating extension.

### Task 2: Discovery exhaustion proof

**Files:**
- Modify: `scripts/fetch_source_routes.py`
- Modify: `tests/test_source_route_fetcher.py`

1. Add failing server-backed tests showing 2xx HTML without its marker and JSON without the configured path are rejected without an admitted snapshot.
2. Run the focused tests and confirm the false-positive behavior.
3. Implement key-existence-aware JSON path proof and text marker proof in the initial fetch boundary.
4. Run route-fetcher and materialized-scan tests to green.

### Task 3: Raw source-media integrity receipt

**Files:**
- Modify: `scripts/materialize_news_images.py`
- Modify: `tests/test_materialize_news_images.py`

1. Add failing tests for raw byte/hash/dimension/format receipt, expected-value mismatch rejection, and distinct `source_bytes_path`/screenshot acquisition methods.
2. Run the focused tests and confirm missing receipt behavior.
3. Implement raw metadata, expected assertion checks, and safe local source-byte acquisition.
4. Run materializer and publisher-focused tests to green.
5. Run the real CNA fixture probe when network transport is available and compare exact expected values.

### Task 4: Verification and integration

**Files:**
- Modify as required by contract failures only.

1. Run all focused tests frozen above.
2. Run the complete 484+ test suite with bundled Python.
3. Build and verify the bootstrap capsule and source binding.
4. Run `project-final-state-audit`, inspect the diff, and verify the worktree is clean except intentional changes.
5. Commit the verified rc.46 changes. Do not merge, publish, restore automation, or alter the formal 06:00 task without a separate user instruction.

