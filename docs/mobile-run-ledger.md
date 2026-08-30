# Mobile diagnostic and historical-run ledger

This ledger preserves resumable ChatGPT Scheduled Task records on the `run-logs` branch. `EVERY_DAILY_NEWS_EXECUTION_GATE` applies the same news and reader-visible image requirements to manual, single-run, test, first-run, recurring, and resume executions. A no-local-Python Scheduled Task may create, advance, and complete a run only after the same host has passed the native image-card or direct page-screenshot smoke gate; it must not substitute URLs, captions, or broken placeholders for visible images.

`IMAGE_PROXY_ORIGINAL_URL_UNWRAP_GATE` requires resize/redirect/proxy URLs to be decoded through common `url`, `u`, `src`, `source`, or `image` parameters and the embedded original media to be attempted before `direct_media_url_attempted=true`. `NON_SHORT_CIRCUIT_IMAGE_DELIVERY_GATE` requires every selected event to complete its own image acquisition/delivery attempt even when an earlier event remains unresolved; an available native image ref cannot be skipped because the canonical Reader is blocked. The final recovery set is aggregated only after every event is processed.

## Retention

- `logs/current.json` is the active or most recently completed run.
- `logs/previous.json` is the immediately preceding run.
- `logs/runs/<run_id>/candidate-audit.json` is the run-scoped candidate audit for the current 24-hour window and is the completion artifact.
- `logs/runs/<run_id>/verification.json` preserves completed mobile verification before the run crosses into visuals.
- `logs/runs/<run_id>/map-decisions.json` preserves completed mobile map decisions before the run crosses into Reader rendering.
- `logs/latest-candidate-audit.json` is the optional rolling fourteen-day continuity cache. It is replaced only after a safe merge; an unavailable merge preserves the prior blob and does not block the current reader.
- `logs/latest-reader.md` is replaced only after a new reader edition has been rendered successfully.
- `scheduled_for` is the occurrence key. Re-entering the same occurrence returns the existing `current.json` and resumes its first incomplete stage, including when a reader is already saved but handoff is incomplete. Only a strictly later scheduled occurrence rotates `current.json`; a non-terminal older occurrence is then preserved as `interrupted_by_next_run` in `previous.json`.


Durable mobile-native diagnostics or historical-run recovery require GitHub write access to `run-logs`; read-only/no-write execution may produce a one-shot diagnostic but has no durable resume semantics and is not this ledger profile.

The branch tip exposes only two run records. Git commit history is not rewritten and must never contain credentials, connector diagnostics, private source content, or binary images.

## Persistence points

The existing ledger binds the run-scoped candidate audit, verification, map decisions, image evidence, and Reader at the stage where each completed result first becomes a resume dependency. Mobile-native may enter `selection-verified` only after `candidate_audit_artifact` is bound, `visuals-completed` only after `verification_artifact` is bound, `reader-rendered` only after both map decisions and image evidence are bound, and `github-result-saved` only after `reader_artifact` is bound. A transition may stay on the current stage or advance exactly one stage; forward skips and stage regression are rejected. These Git blob references prove durable identity for same-run resume; they do not add a content-level validator or claim semantic machine verification.

`RUN_ARTIFACT_IDENTITY_GATE`: the Scheduled Task must actually fire and finish capability routing before `prepare`; the selected actual executor then fixes `execution_mode` for the occurrence, and it is immutable thereafter. No future occurrence is pre-created. The ledger `window` is null at `schedule-prepared`; the first `executor-started` transition records the actual execution time as `end`, derives `start` exactly 24 hours earlier, saves the task time zone, and makes the window immutable for the occurrence. Resume reads this saved window and never recalculates it. `main_sha` must be null before `main-pinned`, present when entering `main-pinned`, and immutable thereafter for one `scheduled_for`. Every active artifact reference carries the same `run_id`, `main_sha`, and `window` as `current.json`. Candidate audit, verification, map/image, and Reader references are forbidden before `candidate-audit`, `selection-verified`, `visuals-completed`, and `reader-rendered` respectively. This is identity conservation in the existing ledger and references, not a new receipt or content-level validator.

The task performs one compact update at each high-level boundary: schedule preparation, executor start, main pinning, workspace readiness, source scan, candidate audit, selection verification, visuals, reader rendering, GitHub reader storage, and delivery handoff. A transition records the newly active stage and thereby identifies the last completed stage without doubling the write count.

Historical records may contain the former mobile image-evidence fields. They must not be used to justify a new execution. For any capable full-runtime recovery, `VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE` allows either direct download or an immediate screenshot of a traceable same-event image; original-file quality is not required, and screenshot use does not wait for download failure. A bare external URL is still not delivery.

Count receipts are derived data. If an event subtotal differs from the actual run-scoped `events` array, rewrite the subtotal once from the array and recheck it. A repairable 32/33 mismatch is not a fatal run error and does not justify rerunning discovery.

## Trigger-owned occurrence

There is no pre-trigger watchdog or future reservation. Single-run and recurring Scheduled Tasks create or resume `current.json` only when the configured task occurrence actually fires, regardless of whether that time is 04:00, 06:00, or another configured clock time. Missing scheduled executions are therefore absence-of-execution evidence, not synthetic `awaiting_executor` runs.

If `run-logs` writes are unavailable, durable mobile-native resume is unavailable and must fail closed before discovery. An Issue comment may record diagnostics, but it is not a substitute for `current.json` and must never be treated as durable occurrence state.


