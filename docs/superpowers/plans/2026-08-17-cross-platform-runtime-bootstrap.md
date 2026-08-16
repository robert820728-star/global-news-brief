# Cross-Platform Runtime Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the verified news runtime and source-route acquisition work on Windows, Linux, and macOS.

**Architecture:** Use standard-library Python as the only scheduled path on every host. Keep existing PowerShell files only as repository history, exclude them from active tests and the runtime capsule, enforce the existing JSON contracts in Python, and transport every required executable through the verified capsule.

**Tech Stack:** Python 3 standard library, `unittest`, GitHub Actions, deterministic tar.xz capsule.

## Global Constraints

- Prefer a host-provided bundled-runtime path.
- Require a real Pillow import before returning a Python executable.
- Do not use PATH Python as the news pipeline runtime merely because it launched the resolver.
- Do not require `powershell.exe` in the scheduled path.
- Rebuild and verify the capsule after runtime files change.

---

### Task 1: Cross-platform bundled Python resolver

**Files:**
- Create: `scripts/resolve_bundled_python.py`
- Modify: `tests/test_workspace_python_resolver.py`

**Interfaces:**
- Consumes: `--preferred-python`, `CODEX_BUNDLED_PYTHON`, runtime-root environment variables, platform cache defaults.
- Produces: `{"status":"ready","python":"<absolute>","pillow":"<version>"}`.

- [ ] Add tests that create a fake executable probe, verify explicit-path precedence, and reject a candidate whose probe fails.
- [ ] Run `python -m unittest tests.test_workspace_python_resolver -v`; expect failure because the `.py` resolver does not exist.
- [ ] Implement candidate discovery and subprocess Pillow probing using only the Python standard library.
- [ ] Run the focused resolver tests; expect all pass.

### Task 2: Cross-platform source route fetcher

**Files:**
- Create: `scripts/fetch_source_routes.py`
- Modify: `tests/test_source_route_fetcher.py`

**Interfaces:**
- Consumes: `--route-config`, `--output-dir`, `--timeout-seconds`.
- Produces: exact snapshot files and `source-route-coverage.json` schema `1.0.0`.

- [ ] Extend the local HTTP fixture test to invoke the Python fetcher and verify exact bytes and SHA-256.
- [ ] Run `python -m unittest tests.test_source_route_fetcher -v`; expect failure because the Python fetcher does not exist.
- [ ] Implement template expansion, redirecting HTTP GET, gzip/deflate decoding, snapshots, coverage JSON, and incomplete-coverage exit 1.
- [ ] Run the focused route tests; expect the Python contract to pass without PowerShell.

### Task 3: Python scheduled path and capsule closure

**Files:**
- Modify: `daily-schedule-prompt.md`
- Modify: `bootstrap-workspace.md`
- Modify: `tests/test_pipeline_contract.py`
- Modify: `tests/test_bootstrap_capsule.py`
- Modify: `VERSION-RECORD.md`
- Rebuild: `bootstrap/capsule-manifest.json`, `bootstrap/capsule.part*.txt`

**Interfaces:**
- Consumes: optional host dependency-locator Python path.
- Produces: verified Python executable and a PowerShell-free route-fetch command.

- [ ] Add contract assertions for the Python resolver/fetcher commands, absence of `powershell.exe`, and capsule membership.
- [ ] Run focused tests; expect failure before prompt and capsule changes.
- [ ] Update platform dispatch, version record, and capsule membership expectations.
- [ ] Build with `python scripts/build_bootstrap_capsule.py --source-commit <HEAD>` and verify with `python scripts/verify_bootstrap_capsule.py`.

### Task 4: Ubuntu CI and release verification

**Files:**
- Modify: `.github/workflows/build-bootstrap-capsule.yml`

**Interfaces:**
- Consumes: an Ubuntu GitHub Actions runner with Python and Pillow installed.
- Produces: compile, resolver, route-fetcher, capsule, and checkpoint test evidence.

- [ ] Add Python compile targets and focused cross-platform tests to the Ubuntu workflow.
- [ ] Run the complete local unittest suite and `git diff --check`.
- [ ] Commit only scoped source, test, workflow, documentation, and rebuilt capsule files.
- [ ] Publish to GitHub `main` without force and verify remote blobs against the local commit.
