# Visible Source Image Delivery Gate

## Goal

Prevent a mobile-native run from becoming canonical-completed when any selected event has a verified usable current image but the host failed to deliver a visible image.

## Decision

Use the existing run-level `NATIVE_MEDIA_UNAVAILABLE` signal as a recovery gate. A run carrying that limitation remains at `visuals-completed`; it cannot enter `reader-rendered` or become `completed`. The same run is resumed by a full-runtime host, which uses the already-existing direct image URL, download, screenshot fallback, materialization, and attachment path.

True source exhaustion remains nonblocking: when all checked sources genuinely contain no qualified current image, no `NATIVE_MEDIA_UNAVAILABLE` is recorded and the event may omit its image. No schema version, field, validator, receipt, manifest, recovery state, or compatibility path is added.

## Contract changes

- A verified source image plus failed visible delivery is a recovery target regardless of `claim_critical`.
- `reader-canonical-capability-degraded` cannot be used to publish around that delivery failure.
- Mobile-native must not pretend to download or materialize locally; it preserves the same run and hands the visual stage to full-runtime.
- The already completed 2026-08-27 run is corrected once to `status=running`, `current_stage=visuals-completed`, and `delivery_status=not_ready`, preserving all evidence and artifacts.

## Tests

- Reject advancing a degraded `NATIVE_MEDIA_UNAVAILABLE` run beyond `visuals-completed`.
- Reject completed status for that limitation.
- Preserve normal completion when image checks truthfully end in source exhaustion without the capability limitation.
- Lock active documents to the same distinction.
