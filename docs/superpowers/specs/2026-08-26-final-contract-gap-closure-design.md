# Final Contract Gap Closure Design

## Goal

Close the verified residual contract gaps on `f44207d9` without adding a new validator, recovery state, receipt layer, source class, map mode, or scoring rule.

## Scope

1. Make Python commands conditional in the mobile-native prompt while preserving the same conservation and reader-layout invariants as structured checks.
2. Remove prose that allows cross-source web search to create canonical discovery candidates.
3. Extend the existing event-map renderer to load initialized custom-section metadata and make the existing manifest validator require the matching custom basemap.
4. Remove all active local-detail map support because the current map policy requires a complete section canvas.
5. Remove the stale statement that selected events include `C-`.
6. Update the checked-in candidate-audit seed to schema `1.2.0` and prove that the shipped seed validates.
7. Correct map omission wording to describe internal metadata without changing the existing field or introducing a migration.

## Explicit Exclusions

- No mobile image-evidence schema or validator.
- No validator-of-validator, validation receipt, recovery state, or new workflow.
- No fallback-web source class.
- No local inset or `regional_detail` map mode.
- No scoring, discovery, verification, reader-layout, run-ownership, or recovery redesign.

## Behavior

Mobile-native instructions must never claim that a Python command was executed when no runtime exists. Web search may locate a same-source recovery URL or verification evidence but may not create a canonical discovery candidate. Custom sections use `maps/generated/sections/<CODE>-base.json` and bind event assets to `maps/generated/sections/<CODE>-base.png`. Any unavailable custom base remains an existing map omission or claim-critical failure, not a new state.

## Tests

Tests must first fail against `f44207d9` for each changed contract: mobile command conditionality, web fallback wording, JPN overlay rendering, custom basemap binding, removal of local-detail residues, removal of selected `C-` prose, and validation of the shipped audit seed. Existing full repository and bootstrap-capsule tests remain the final regression surface.
