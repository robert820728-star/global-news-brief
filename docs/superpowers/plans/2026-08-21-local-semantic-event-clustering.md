# Local Semantic Event Clustering Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and measure a conservative local multilingual semantic clustering stage over the saved 20,450-row artifact.

**Architecture:** A focused Python module consumes the existing URL-recovery report, obtains local embeddings through an injected provider, finds bounded nearest neighbors, applies deterministic time and factual-anchor gates, and emits conserved semantic clusters plus audit queues. Runtime model files and full reports remain uncommitted.

**Tech Stack:** Python 3, FastEmbed/ONNX Runtime, NumPy, local nearest-neighbor index, `unittest`, JSON.

## Global Constraints

- Preserve every source row exactly once.
- Never delete, grade, promote, demote, or make a publication decision.
- Unresolved titles stay separate until metadata or body recovery.
- Similarity alone cannot override incompatible event-identity anchors; changing casualty totals are preserved as versioned facts rather than treated as different events.
- Use no GPT or remote embedding API for bulk clustering.
- Do not modify production schedule files or GitHub `main`.

---

### Task 1: Deterministic clustering core

**Files:**
- Create: `scripts/pilot_local_semantic_event_clustering.py`
- Create: `tests/test_pilot_local_semantic_event_clustering.py`

**Interfaces:**
- Produces `extract_fact_anchors(text: str) -> dict`.
- Produces `pair_decision(left: dict, right: dict, similarity: float, config: dict) -> str`.
- Produces `cluster_from_neighbor_pairs(report: dict, pairs: list, config: dict) -> dict`.

- [ ] Write six frozen tests covering positive merging, evolving casualty facts, time gating, unresolved preservation, row conservation, and deterministic output.
- [ ] Run the focused suite and observe RED because the module does not exist.
- [ ] Implement the minimal pure clustering core and rerun until GREEN.

### Task 2: Local embedding and neighbor generation

**Files:**
- Modify: `scripts/pilot_local_semantic_event_clustering.py`

**Interfaces:**
- Produces `embed_groups(groups, model_name, cache_dir) -> vectors`.
- Produces `nearest_neighbor_pairs(vectors, top_k, minimum_similarity) -> list`.

- [ ] Install runtime-only dependencies in an isolated pilot directory and record their versions.
- [ ] Load the fixed multilingual model locally and run a bilingual smoke comparison.
- [ ] Generate bounded nearest neighbors without constructing a full all-pairs matrix.

### Task 3: Full artifact and audit

**Files:**
- Create at runtime only: `pilot-output/local-semantic-event-clustering.json`
- Create: `docs/pilot-results/2026-08-21-local-semantic-event-clustering-result.md`

- [ ] Run all eligible 2026-08-20 groups and independently verify the output.
- [ ] Review auto-merged clusters and highest-similarity non-merged pairs for false merges and missed merges.
- [ ] Record exact counts, audit denominators, error estimates, elapsed time, and unresolved-title treatment bilingually.

### Task 4: Verification and experimental publication

**Files:**
- Publish only source, tests, specification, plan, and compact result documentation.

- [ ] Run the complete pilot test suite, compile checks, conservation verifier, and deterministic repeat check.
- [ ] Commit and push to `codex/lossless-article-grouping-pilot` without force.
- [ ] Verify the branch remains ahead of and not behind `main`, with no production schedule change.

