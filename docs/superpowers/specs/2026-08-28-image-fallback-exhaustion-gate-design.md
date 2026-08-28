# Image Fallback Exhaustion Gate Design

## Goal

Prevent a single source-image or native-card failure from being classified as `NATIVE_MEDIA_UNAVAILABLE` or truthful source exhaustion before all required same-event image-source tiers have been inspected.

## Confirmed Failure

The live mobile run can bind an `image-evidence.json` blob and enter visual recovery even though the evidence contains only ad hoc `source_checks`. The existing ledger manager validates the artifact reference but not fallback exhaustion. Active prose also contains one stale sentence that permits non-critical source-image acquisition failure to become omission.

## Design

Keep the existing run ledger, image-evidence artifact, visual recovery state, and delivery profiles. Add no schema file, receipt, recovery state, compatibility mode, or source class.

Each mobile image-evidence event uses these existing-artifact checklist fields:

- `original_source_attempted`
- `official_fallback_attempted`
- `wire_fallback_attempted`
- `reliable_media_fallback_attempted`
- `qualified_image_found`
- `delivery_attempted`
- `delivery_result`

The canonical manager reads the already-bound run-scoped `image-evidence.json` from the run-logs checkout at the transition boundary. It applies the following rules:

1. `delivery_result=delivery_unavailable` requires all four source tiers, a qualified image, and an actual delivery attempt. Only then may `NATIVE_MEDIA_UNAVAILABLE` be recorded.
2. `delivery_result=source_exhausted` requires all four source tiers, no qualified image, and no delivery attempt.
3. `delivery_result=delivered` requires a qualified image and an actual delivery attempt. Fallback tiers after the successful source are not required.
4. Any other combination fails the existing transition. A single failed original URL, download, screenshot, or native card is never exhaustion.

The image used for delivery may come from a different reliable, legally published source than the text-verification source. Event identity, date, people/location, and source traceability remain mandatory.

## Execution-Mode Boundary

The existing Python manager machine-enforces this gate when it is used. A no-runtime mobile-native host cannot truthfully claim that Python validation ran; it must apply the same structural gate when writing the artifact directly. This existing trust boundary is not expanded with another validator or receipt.

## Outer Prompt

The repository's outer daily scheduled-task prompt repeats the no-early-exit rule before the general blocker rule. The rule explicitly requires the four source tiers and permits a different qualified same-event image source.

## Tests

- Reject native-media unavailability when any fallback tier is missing.
- Reject source exhaustion when any fallback tier is missing.
- Accept complete source exhaustion.
- Accept successful delivery without unnecessary later fallback searches.
- Retain the existing rule that qualified-image delivery failure blocks Reader completion regardless of `claim_critical`.
- Scan active contracts for the stale non-critical omission escape.

## Scope Boundary

Do not change scoring, discovery, map/chart behavior, reader layout, run stages, delivery profiles, or full-runtime manifest semantics beyond aligning image-source fallback wording.
