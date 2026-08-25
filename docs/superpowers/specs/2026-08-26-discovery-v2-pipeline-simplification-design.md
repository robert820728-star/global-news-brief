# Discovery Completeness and Public Value V2 Cleanup Design

## Status

Approved by the user on 2026-08-26 through the instruction to implement the previously reviewed findings and then run the long-horizon project acceptance Skill.

## Objective

Repair deterministic discovery coverage gaps, remove executable pre-V2 grade rules, separate discovery ordering from semantic-event importance, and make non-evidentiary visual and recovery artifacts degradable instead of publication-blocking.

## Design

### Discovery completeness

- ChinaNews fetches date offsets `0` and `-1`. A single successful date remains usable but is explicitly partial; both dates are required for a complete route.
- GDELT archive completeness is authoritative. A partial archive may contribute candidates but reports `degraded_partial`, never live/full coverage.
- CNA pagination reuses the configured POST request, replaces `pageidx` for each request, follows `NextPageIdx`, and stops only after source exhaustion or crossing `window_start`.
- Route evidence separates `route_ready` (usable data) from `coverage_complete` (the requested window was completely traversed).

### Lossless semantic admission

- The relevance gate remains a routing ledger, not an exclusion gate.
- Strong-signal rows use `content_hydration`; weak-signal rows use `lightweight_semantic_review`.
- Both routes remain in `model-source-candidates.json`. Fixed keywords may prioritize hydration but cannot decide whether a global event reaches semantic review.

### Public Value V2 authority

- Event class never assigns a minimum, default, forced, or ceiling grade.
- Cultural, border-conflict, ongoing-conflict, and passive-event rules provide evidence and continuity context only; the configured weighted dimensions produce the grade.
- The five-day grade ceiling and `default_d_applied` contract are removed from configuration, schemas, validators, documentation, preferences, and tests.
- Grade bands, casualty floors, urgency anchors, and confidence bands are read from `news-source-pool.json`; Python contains no second numeric authority.
- A dimension scored zero may use an empty evidence list. Positive dimensions still require eligible fact IDs.
- Verbose grade explanations are conditional: core fact/evidence links remain mandatory, while boundary explanations are required only when a score/grade gate needs them.

### Discovery priority terminology

- Source-scan ordering uses `discovery_priority_v1`, `discovery_priority_score`, `discovery_signals`, and `discovery_priority_reason`.
- `public_value_v2`, `importance_score`, and `importance_breakdown` are created only for hydrated semantic events.

### Publication and recovery

- Textual Reader output is the primary artifact.
- Missing illustrative images, professional visuals, or locator maps produce explicit visual degradation and omission reasons without blocking an otherwise validated Reader.
- A visual remains blocking only when the visual itself is declared claim-critical evidence.
- The pre-manifest remote recovery bundle is conditional on cross-host handoff, ephemeral-workspace risk, or an approaching execution limit. A local hashed checkpoint is the default selection boundary.
- Bootstrap integrity remains unchanged.

## Acceptance

- New regression tests fail on the old behavior before implementation and pass afterward.
- Structural tests reject grade floors/defaults/ceilings and source-scan V2 terminology.
- The full repository test suite passes with the bundled Python runtime.
- `INSTALL.md` and every active execution surface describe the same flow.
- The long-horizon final-state acceptance Skill runs against the final commit; any finding that causes a repository edit resets its consecutive-pass count.

## Operational boundary

This change does not redesign bootstrap integrity, alter the six dimension weights, change grade bands, merge the mobile and full-runtime stage machines, or require every possible external discovery source to be available.
