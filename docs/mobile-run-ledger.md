# Mobile scheduled-run ledger

The mobile ChatGPT task remains the news executor. GitHub stores a compact, durable run envelope on the `run-logs` branch without triggering the bootstrap-capsule workflow.

## Retention

- `logs/current.json` is the active or most recently completed run.
- `logs/previous.json` is the immediately preceding run.
- `logs/latest-reader.md` is replaced only after a new reader edition has been rendered successfully.
- Starting a new scheduled run replaces the older `previous.json`. If the former `current.json` was still awaiting or running, it is preserved as `interrupted_by_next_run` before rotation.

The branch tip exposes only two run records. Git commit history is not rewritten and must never contain credentials, connector diagnostics, private source content, or binary images.

## Persistence points

The task performs one compact update at each high-level boundary: schedule preparation, executor start, main pinning, workspace readiness, source scan, candidate audit, selection verification, visuals, reader rendering, GitHub reader storage, and delivery handoff. A transition records the newly active stage and thereby identifies the last completed stage without doubling the write count.

Before handing the response to ChatGPT, the task replaces `logs/latest-reader.md`, records its blob SHA, and moves to `delivery-handoff`. The ChatGPT scheduled-task interface does not provide a client-render acknowledgement. Therefore `client_confirmed` is forbidden unless a future external acknowledgement mechanism supplies explicit evidence.

## Watchdog

`.github/workflows/prepare-mobile-run-ledger.yml` runs at 05:58 Asia/Taipei and can also be dispatched manually. It performs only log rotation and initialization; it does not search news, call a model, or require an OpenAI API key. If the mobile executor never starts, `current.json` remains at `awaiting_executor` and the next run preserves that evidence as interrupted.

If file writes are unavailable, the mobile task falls back to one updated comment in Issue #3. Logging failure is diagnostic degradation and must not cause fabricated news or a false delivery claim.
