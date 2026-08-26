# RC.7 Contract Mode Convergence Design

## Goal

Remove the remaining rc.6 cross-mode and cross-layer contradictions without adding a schema, validator, receipt, recovery state, fallback source class, or compatibility path.

## Verified Findings

1. `news-brief-settings.md` still maps every non-Taiwan/non-China event to `GLB`, while current runs use ordered `section_scopes`.
2. Shared settings and `select-news-events` require Python even when `mobile-native` explicitly has no local runtime.
3. Shared image acquisition and mobile completion prose require local files for a no-runtime host even though the existing native image-card route is valid.
4. Policy `proposal` and `draft` stages require non-empty `window_material_effects`, which can force fabricated realized effects.
5. `taiwan_coverage_sweeps[].same_source_only` is unused and contradicts the single acquisition authority.
6. `news-brief-examples.md` still presents a manual count summary and three-to-five images as correct despite the current Reader contract and `maxItems: 2`.

The `reader_omission_note` field name is historical but behaviorally consistent. It is out of scope.

## Design

### Section resolution

Current semantic events resolve `country_codes` against ordered run-scoped `section_scopes`. The first matching non-fallback scope wins; only the unique fallback scope receives an unmatched event. Remove prose and validator fallback code that recreates `TWN`/`CHN`/else-`GLB`.

### Runtime-dependent executable checks

Shared contracts describe one invariant with two execution mechanisms:

- `full-runtime` or any host with the executable runtime runs the canonical Python validator.
- `mobile-native` performs the already defined structural equivalent and must not claim Python execution.

No validation-method field or second state machine is introduced.

### Image evidence profiles

Use the existing execution mode and delivery fields:

- Runtime profile: source inspection, download, screenshot fallback, local materialization, attachment attempt, pixel/file verification.
- Mobile-native profile: source inspection, native image/card attempt, structured host delivery result. It must not invent local `evidence_path`, `materialized-images.json`, download, screenshot, attachment, or pixel-verification claims.

If a usable image exists but native delivery fails, the existing capability-degraded profile may complete with `NATIVE_MEDIA_UNAVAILABLE`, an image-evidence artifact, and an explicit note that pixel machine verification was unavailable. If source inspection finds no usable image, record source exhaustion rather than a native-media failure.

The Git blob pointer proves persistence only; it is not described as semantic machine validation.

### Policy stage requirements

Keep the existing review object. Require:

- `rumor`: attributable trigger and evidence URL.
- `consideration`: official consideration evidence.
- `proposal`/`draft`: formal text or legal basis, official proposal action, and affected actors; `window_material_effects` may be empty.
- `introduced`/`passed`/`signed`: formal process evidence; window effects remain optional until operational.
- `effective`/`implemented`/`measurable_effect`: non-empty window material effects.

No potential consequence may be written as an actual effect.

### Stale surfaces

Delete the unused `same_source_only` booleans. Update examples to omit manual totals, cap source images at two, and remove all positive three-to-five-image guidance. Do not change runtime image limits.

## Verification

Tests must first fail against rc.6 and then pass after the minimal edits. Required final evidence is: targeted contract and policy tests, full repository suite, generated capsule verification, semantic residue scan, adversarial mobile/profile and proposal fixtures, two unchanged-fingerprint final-state cycles, GitHub `main`, and remote CI.

## Rollback

The remote rollback source is `1e6e073778dd5d7aa6d556759c6315ab3f67f352`. The local reversible baseline is `fa5d1aa34a9cf07fbb3e4cbb864970eda21a5b54`.
