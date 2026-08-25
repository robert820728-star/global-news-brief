# Mobile scheduled-run ledger

The mobile ChatGPT task remains the news executor. GitHub stores a compact, durable run envelope on the `run-logs` branch without triggering the bootstrap-capsule workflow.

## Retention

- `logs/current.json` is the active or most recently completed run.
- `logs/previous.json` is the immediately preceding run.
- `logs/runs/<run_id>/candidate-audit.json` is the run-scoped candidate audit for the current 24-hour window and is the completion artifact.
- `logs/latest-candidate-audit.json` is the optional rolling fourteen-day continuity cache. It is replaced only after a safe merge; an unavailable merge preserves the prior blob and does not block the current reader.
- `logs/latest-reader.md` is replaced only after a new reader edition has been rendered successfully.
- Starting a new scheduled run replaces the older `previous.json`. If the former `current.json` was still awaiting or running, it is preserved as `interrupted_by_next_run` before rotation.

The branch tip exposes only two run records. Git commit history is not rewritten and must never contain credentials, connector diagnostics, private source content, or binary images.

## Persistence points

The task performs one compact update at each high-level boundary: schedule preparation, executor start, main pinning, workspace readiness, source scan, candidate audit, selection verification, visuals, reader rendering, GitHub reader storage, and delivery handoff. A transition records the newly active stage and thereby identifies the last completed stage without doubling the write count.

Before handing the response to ChatGPT, the task saves the run-scoped candidate audit, then replaces `logs/latest-reader.md`, records both blob SHAs, and moves to `delivery-handoff`. The ledger keeps `candidate_audit_artifact` for the run-scoped candidate audit and separate `durable_audit_status` / `durable_audit_artifact` fields for the rolling history. `FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE` means preserve the prior durable blob, set `durable_audit_status=preserved_merge_deferred`, and continue; it must not be set as `last_error`. Every run record declares `execution_mode` as `full-runtime` or `mobile-native`, plus a separate `delivery_profile`, `native_media_status`, and `capability_limitations` list. A mobile-native run that actually attempted download, screenshot fallback, and a supported local/native attachment route may complete as `reader-canonical-capability-degraded` when only final-mile media delivery is unavailable. `NATIVE_MEDIA_UNAVAILABLE` is then a capability limitation, not `last_error`; it never justifies rerunning news stages. The ChatGPT scheduled-task interface does not provide a client-render acknowledgement. Therefore `client_confirmed` is forbidden unless a future external acknowledgement mechanism supplies explicit evidence.

Count receipts are derived data. If an event subtotal differs from the actual run-scoped `events` array, rewrite the subtotal once from the array and recheck it. A repairable 32/33 mismatch is not a fatal run error and does not justify rerunning discovery.

## Watchdog

`.github/workflows/prepare-mobile-run-ledger.yml` runs at 05:58 Asia/Taipei and can also be dispatched manually. It performs only log rotation and initialization; it does not search news, call a model, or require an OpenAI API key. If the mobile executor never starts, `current.json` remains at `awaiting_executor` and the next run preserves that evidence as interrupted.

If file writes are unavailable, the mobile task falls back to one updated comment in Issue #3. Logging failure is diagnostic degradation and must not cause fabricated news or a false delivery claim.
