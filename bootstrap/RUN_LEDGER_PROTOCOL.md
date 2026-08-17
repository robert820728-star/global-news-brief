# Mobile scheduled-run ledger protocol

The persistent ledger is GitHub issue [#3](https://github.com/robert820728-star/global-news-brief/issues/3), `Daily News Run Ledger / 每日新聞執行台帳`. It supplements local `bootstrap-progress.json`; it is not a news checkpoint and cannot authorize publication.

## Write policy

- Generate `run_id` before the first tool call. Use **one comment per run_id** and create it immediately after resolving and pinning the fresh `main` SHA, before any recursive tree, manifest, or helper read. Store its comment id in task context first, then in local progress when the helper becomes available, and update that same comment for the rest of the run.
- Treat every ledger operation as **best-effort**. Missing GitHub write permission, connector errors, and rate limits must set `external_ledger: unavailable` locally and **must never block the news pipeline**.
- Do not create one comment per block or chunk. Update the same comment after the recursive tree, manifest, and loader/helper verification boundaries, **every 8 completed chunks**, at the declared total, after workspace creation, after each news pipeline stage, and immediately on failure or final success.
- News-stage updates are debounced to **at most once every 3 minutes**. A newer milestone replaces the pending older one; failure and final success bypass the debounce.
- Keep the same resolved commit, run id, and comment id across retries. Do not expose credentials, connector internals, full article text, or binary content.

## Comment body

During execution, use a compact JSON object with `run_id`, `automation_id` when available, `commit`, `status`, `stage`, `progress`, `updated_at`, and `last_error`. On failure, append the full generated `RUN_RECEIPT`. After canonical reader delivery, replace the body with only the final `RUN_RECEIPT` plus an ISO-8601 completion time.

If the ledger cannot be written, the local and final receipt must contain `external_ledger: unavailable`. This is diagnostic degradation, not a delivery failure.
