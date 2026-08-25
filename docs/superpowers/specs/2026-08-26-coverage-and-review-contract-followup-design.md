# Coverage and Review Contract Follow-up Design

## Goal

Remove the remaining information-loss and forced-evidence contradictions without expanding into speculative media or map redesign.

## Decisions

### Coverage is two independent facts

Replace the ambiguous source-coverage `status` field with:

- `scan_status`: whether the available snapshots were successfully materialized (`completed` or `failed`);
- `coverage_complete`: whether the configured route actually covered its required window/variants/segments;
- `coverage_status`: `complete`, `degraded_partial`, `degraded_cached`, or `unavailable`;
- `coverage_reason`, `missing_segments`, and `missing_date_variants`.

Every configured discovery route must remain visible in the latest candidate audit. A failed route has zero counts and no scan evidence; a partial but usable route has `scan_status=completed` and contributes every verified row while retaining `coverage_complete=false`. Source-scan evidence stores the same coverage fields and the validator compares them with the audit row. The publisher exposes a compact discovery-coverage summary in its release receipt; the reader body remains free of backend diagnostics.

This is a breaking audit shape, so the candidate-audit schema moves from `1.1.0` to `1.2.0`. No compatibility branch retains the overloaded `status` field.

### Policy proposals may have no realized operational effect

`direct_operational_effects` remains a required array when policy review applies, but it may be empty. Its items, when present, must remain nonempty evidence strings. Potential effects continue to live in the existing `consequence_evidence.potential` fact-ID channel rather than creating a duplicate policy-only field.

### Relevance routing is lossless

`lightweight_semantic_review` changes hydration depth/order only. Every discovery row remains in model input. Remove the retired `structured_review` prose. Replace the regional-only model-admission configuration with explicit all-row admission fields while retaining `candidate_transfer_policy=all_verified_in_window` as the earlier transfer contract.

### Conflict reviews are conditional, not merged

Keep border-conflict and ongoing-conflict reviews separate because they answer different questions. Each review requires only `{"applies": false}` for unrelated events; detailed fields are required only when `applies=true`. Local-disaster and policy reviews already use this minimal conditional shape and are not otherwise redesigned.

### CI and small naming cleanup

Keep focused capsule tests for diagnosis and add the full repository unittest discovery before any generated capsule commit. Rename the remaining discovery-ranking error text and the daily skill description so they cannot reintroduce importance or mandatory pre-manifest recovery semantics.

## Explicit non-goals

- Do not redesign image collection without runtime cost measurements.
- Do not change the full-world map policy in this patch.
- Do not add a second potential-effects field.
- Do not merge all review objects into one polymorphic structure.

## Verification

Use test-first regressions for partial coverage propagation, unavailable-route retention, policy proposals with empty operational effects, lossless model admission, conditional conflict reviews, release-receipt coverage, and workflow full-suite presence. Then run targeted tests, full repository tests, capsule rebuild/verification, and the repository final-state audit Skill with two consecutive complete cycles on one unchanged final fingerprint.

