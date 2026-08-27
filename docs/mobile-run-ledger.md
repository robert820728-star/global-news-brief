# Mobile scheduled-run ledger

The mobile ChatGPT task remains the news executor. GitHub stores a compact, durable run envelope on the `run-logs` branch without triggering the bootstrap-capsule workflow.

## Retention

- `logs/current.json` is the active or most recently completed run.
- `logs/previous.json` is the immediately preceding run.
- `logs/runs/<run_id>/candidate-audit.json` is the run-scoped candidate audit for the current 24-hour window and is the completion artifact.
- `logs/runs/<run_id>/verification.json` preserves completed mobile verification before the run crosses into visuals.
- `logs/runs/<run_id>/map-decisions.json` preserves completed mobile map decisions before the run crosses into Reader rendering.
- `logs/latest-candidate-audit.json` is the optional rolling fourteen-day continuity cache. It is replaced only after a safe merge; an unavailable merge preserves the prior blob and does not block the current reader.
- `logs/latest-reader.md` is replaced only after a new reader edition has been rendered successfully.
- `scheduled_for` is the occurrence key. Re-entering the same occurrence returns the existing `current.json` and resumes its first incomplete stage, including when a reader is already saved but handoff is incomplete. Only a strictly later scheduled occurrence rotates `current.json`; a non-terminal older occurrence is then preserved as `interrupted_by_next_run` in `previous.json`.

The branch tip exposes only two run records. Git commit history is not rewritten and must never contain credentials, connector diagnostics, private source content, or binary images.

## Persistence points

The existing ledger binds the run-scoped candidate audit, verification, map decisions, image evidence, and Reader at the stage where each completed result first becomes a resume dependency. Mobile-native may enter `selection-verified` only after `candidate_audit_artifact` is bound, `visuals-completed` only after `verification_artifact` is bound, `reader-rendered` only after both map decisions and image evidence are bound, and `github-result-saved` only after `reader_artifact` is bound. A transition may stay on the current stage or advance exactly one stage; forward skips and stage regression are rejected. These Git blob references prove durable identity for same-run resume; they do not add a content-level validator or claim semantic machine verification.

`RUN_ARTIFACT_IDENTITY_GATE`: `execution_mode` is fixed by `prepare` and immutable for the occurrence; the mobile watchdog explicitly prepares `mobile-native`. `main_sha` must be null before `main-pinned`, present when entering `main-pinned`, and immutable thereafter for one `scheduled_for`. Every active artifact reference carries the same `run_id` and `main_sha` as `current.json`. The candidate-audit reference establishes the fixed window; every later verification, map, image, and Reader reference must carry that identical window. Candidate audit, verification, map/image, and Reader references are forbidden before `candidate-audit`, `selection-verified`, `visuals-completed`, and `reader-rendered` respectively. This is identity conservation on the existing reference, not a new receipt or content-level validator.

The task performs one compact update at each high-level boundary: schedule preparation, executor start, main pinning, workspace readiness, source scan, candidate audit, selection verification, visuals, reader rendering, GitHub reader storage, and delivery handoff. A transition records the newly active stage and thereby identifies the last completed stage without doubling the write count.

Before handing the response to ChatGPT, the task saves the run-scoped candidate audit, then replaces `logs/latest-reader.md`, records both blob SHAs, and moves to `delivery-handoff`. The ledger keeps `candidate_audit_artifact` for the run-scoped candidate audit, `image_evidence_artifact` for `logs/runs/<run_id>/image-evidence.json`, and separate `durable_audit_status` / `durable_audit_artifact` fields for the rolling history. `FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE` means preserve the prior durable blob, set `durable_audit_status=preserved_merge_deferred`, and continue; it must not be set as `last_error`. Every run record declares `execution_mode` as `full-runtime` or `mobile-native`, plus a separate `delivery_profile`, `native_media_status`, and `capability_limitations` list. `MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE` uses the existing fields: full-runtime records source inspection, download, screenshot fallback, local materialization, and attachment delivery; mobile-native records source inspection, a native image/card attempt, and the host's structured delivery result. Mobile-native must not invent local files, downloads, screenshots, attachments, or pixel verification. `QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL`: when a qualified source image is confirmed but its native delivery fails, `NATIVE_MEDIA_UNAVAILABLE` is a capability limitation regardless of `claim_critical`, not `last_error`; it may exist only while the same run is `running` at `visuals-completed` with run-scoped image evidence. `VISUAL_DELIVERY_ONLY_RECOVERY` lets existing full-runtime complete visible delivery from the bound news artifacts and confirmed source URL, but forbids discovery, scoring, verification, a new run, or event-ID changes. It cannot advance to reader delivery or canonical completed. No usable image after source exhaustion is a different outcome and must not use that capability code. Git blob SHA 只證明 evidence 已持久化，不代表內容或像素已經 machine-verified. Missing visible media leaves no image-description placeholder in the Reader. The ChatGPT scheduled-task interface does not provide a client-render acknowledgement. Therefore `client_confirmed` is forbidden unless a future external acknowledgement mechanism supplies explicit evidence.

Count receipts are derived data. If an event subtotal differs from the actual run-scoped `events` array, rewrite the subtotal once from the array and recheck it. A repairable 32/33 mismatch is not a fatal run error and does not justify rerunning discovery.

## Watchdog

`.github/workflows/prepare-mobile-run-ledger.yml` runs at 05:58 Asia/Taipei and can also be dispatched manually. It performs only log rotation and initialization; it does not search news, call a model, or require an OpenAI API key. If the mobile executor never starts, `current.json` remains at `awaiting_executor` and the next run preserves that evidence as interrupted.

If file writes are unavailable, the mobile task falls back to one updated comment in Issue #3. Logging failure is diagnostic degradation and must not cause fabricated news or a false delivery claim.
