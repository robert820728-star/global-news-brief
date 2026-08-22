# GDELT Archive-Primary Acquisition Implementation Plan

> **For agentic workers:** Execute inline in the current main conversation; no subagent delegation is authorized.

**Goal:** Make official GDELT 15-minute archives primary discovery and remove repeated DOC API waits.

**Architecture:** Reorder the existing fetcher without adding a second acquisition implementation. Preserve the current archive materializer and cache recovery; treat DOC API as one optional degraded path.

**Tech Stack:** Python standard library, JSON route configuration, unittest.

## Global Constraints

- Do not run a live 24-hour download for this code change.
- Do not change candidate scoring or model-card limits.
- Preserve publication continuity when a single route fails.

### Task 1: Archive-first route

**Files:** `scripts/fetch_source_routes.py`, `source-route-config.json`, acquisition prompts/settings/skill, focused tests.

- [x] Add a failing test proving archive success skips DOC API.
- [x] Run it and observe failure because DOC API is still called first.
- [x] Reorder the existing route and mark optional DOC coverage degraded.
- [x] Update executable configuration and runtime contracts.
- [x] Run focused fetcher and contract tests.
