# Source Row Admission Ledger Design

## Problem

The discovery pipeline can complete `source-scan` after persisting the full source candidate list and relevance routing decisions, but before it persists an immutable, row-addressable admission universe. The model input then contains only `content_hydration` rows. If selection or candidate audit fails later, the run cannot prove where every discovery row went, and same-run recovery cannot legally rescan completed discovery.

## Scope

This change adds one durable boundary artifact and validates its downstream conservation. It does not change event scoring, selection thresholds, Reader rendering, image delivery, or Scheduled Task control.

## Data contract

Every source candidate receives a deterministic `row_id`, distinct from `candidate_id`, so repeated rows remain independently addressable. The candidate also persists listing timestamp evidence, source/section identity, canonical URL, and a deterministic provisional group seed.

`source-row-admissions.json` is produced before `source-scan` can complete. It contains every source row exactly once and preserves:

- `row_id`, `candidate_id`, `provisional_group_id`;
- source, section, original URL, and canonical URL;
- listing timestamp and listing evidence;
- article-body timestamp, quoted timestamp evidence, evidence URL/path, and content SHA-256;
- relevance route and reasons;
- the current semantic disposition state and model evidence.

At the source-scan boundary, rows may remain `unresolved`, but they must already contain sufficient article evidence for same-run semantic review without rediscovery. Later candidate audit dispositions must reference the same row identity and carry terminal model evidence. `unresolved` remains fail-closed; `unresolved_exhausted` remains an explicit degraded terminal state.

## Pipeline behavior

1. Source candidate materialization assigns stable row identities without collapsing duplicate rows.
2. Relevance routing preserves and emits those row identities.
3. The row-ledger materializer joins source candidates, gate decisions, and per-row article evidence one-to-one. Missing, duplicate, or foreign rows fail the build.
4. The checkpoint refuses `source-scan=completed` unless `source_row_admissions` is bound alongside the existing three artifacts.
5. Candidate audit validates exact row-id conservation between the embedded admissions and final `article_dispositions`; it does not reconstruct missing rows from selected events or rerun discovery.
6. Recovery bundles include the row-ledger artifact so selection and audit can resume from persisted evidence.

## Compatibility and failure policy

Historical compact runs remain readable. The newest run must carry the new admission universe. A run created under the new checkpoint schema cannot complete source-scan with a legacy three-artifact set. Any count mismatch, evidence gap, duplicate row identity, or nonterminal `unresolved` disposition blocks completion.

## Acceptance

- A 132-row input produces exactly 132 uniquely identified admission rows.
- Duplicate source/candidate URLs remain distinct rows.
- Missing article-body timestamp evidence fails before source-scan completion.
- The source-scan checkpoint requires and binds the row ledger.
- Candidate audit rejects missing, duplicate, foreign, or identity-mismatched dispositions and accepts a complete 132-to-132 mapping.
- Pre-manifest recovery contains the row ledger and never needs discovery replay.

