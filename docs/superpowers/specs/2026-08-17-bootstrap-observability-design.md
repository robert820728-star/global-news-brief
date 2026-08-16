# Bootstrap Observability and Mobile Transport Design

## Goal

Make a mobile ChatGPT scheduled run diagnosable before the news checkpoint exists, while reducing successful-path connector pressure and preserving the existing fail-closed workspace and publication contracts.

## Constraints

- Stage -1 must not create the news checkpoint before the verified workspace exists.
- The scheduled path must be cross-platform and must not require PowerShell.
- GitHub writes are best-effort observability only and must never become a news-pipeline dependency.
- A platform termination may destroy local files, so externally persisted progress is needed when the connected GitHub App permits unattended comment mutations.
- Successful runs should leave little diagnostic residue; failed runs should retain enough evidence to identify the first failing boundary.
- The checked-in chunk transport remains the supported fallback until the mobile host proves it can download a GitHub Actions artifact directly into an executable workspace.

## Selected Approach

Use a lightweight diagnostic layer plus adaptive capsule retrieval.

1. Fetch a standalone standard-library bootstrap progress helper from the same resolved commit as the loader and validate its Git blob SHA against the pinned recursive tree.
2. Create `bootstrap-progress.json` before capsule retrieval. It is not a news checkpoint.
3. Keep successful block state in memory and atomically persist after each completed chunk. Persist immediately on every block retry or failure.
4. Bound the current block attempt history to the initial attempt plus three retries. Use backoffs of 2, 5, and 10 seconds, or the host's smallest safe equivalent.
5. Prefer a 16-line connector read that spans two adjacent manifest retrieval blocks. Split and validate the two declared 8-line blocks locally. If the grouped read is truncated or invalid, fall back to the original 8-line block reads and retry only the failing block. Never redownload verified prior chunks.
6. Maintain one GitHub Issue comment per run when write capability exists. Locate it by a stable run marker and update it in place.
7. Emit one deterministic `RUN_RECEIPT` on every success or controlled failure.

## Local Progress Record

The atomic JSON record uses schema `1.0.0` and includes:

- run identity and resolved commit;
- current stage and status;
- completed and total chunks;
- current chunk and block counts;
- last success timestamp and last error;
- retry count and a bounded current-block attempt list containing byte size, SHA-256, outcome, error, and timestamp;
- last completed news stage;
- external-ledger availability and comment identity;
- canonical-delivery status.

Atomic updates write a temporary sibling, flush and fsync it, and replace the target. A successful canonical delivery emits the final receipt and removes the local progress record. Failures retain it.

## External Run Ledger

Use one repository Issue named `Daily News Run Ledger`. Each run creates one comment with a machine-readable run marker. The same comment is updated at these milestones:

- latest `main` resolved and pinned;
- manifest, loader, progress helper, and runtime tree validated;
- every eight completed chunks and at 44/44;
- workspace creation;
- news-stage progress, debounced to at most once every three minutes;
- every failure immediately;
- final success or controlled stop.

The external comment contains technical progress only, not news content. On success it is replaced with a compact final receipt. On failure it retains the diagnostic fields. If issue read, comment creation, or comment update is unavailable, the task records `external_ledger: unavailable`, continues locally, and states that sudden platform termination cannot be diagnosed externally.

## Unified Receipt

Every controlled exit prints:

```text
RUN_RECEIPT
run_id:
main_sha:
last_completed_stage:
bootstrap_chunks:
current_chunk:
current_block:
last_error:
retry_count:
external_ledger:
canonical_delivery:
```

The receipt is diagnostic evidence, not reader-facing news and not a substitute for canonical delivery.

## Failure Handling

- A grouped 16-line read failure does not consume an individual block retry. It only switches that pair to 8-line reads.
- Each 8-line block gets one initial attempt and at most three retries against the same commit and line range.
- A failed attempt records its actual byte size and SHA-256 when bytes exist.
- Exhaustion stops Stage -1 at `repository materialization / executable workspace acquisition` and emits the receipt.
- Loader, runtime resolver, Pillow, checkpoint, pipeline-stage, release-receipt, and canonical-delivery failures update the same local and external run identity.

## Test Strategy

The acceptance set is fixed to:

1. Atomic progress initialization, update, reload, receipt, and success cleanup.
2. A simulated interruption after 40 completed chunks leaves a valid running record.
3. Chunk 41 grouped-read truncation falls back without changing verified chunks 1-40.
4. The initial block attempt plus three failed retries records all four bounded attempts and emits the exact blocker receipt.
5. The schedule and bootstrap contracts require the cross-platform helper, grouped-read fallback, retry limits, external-ledger degradation, and unified receipt.
6. Capsule build and verification include the progress helper without PowerShell or generated images.
7. Full local regression and Ubuntu CI pass.
8. A real GitHub ledger issue/comment create-and-update probe passes with the connected App used for repository publication. This proves repository permission, but the final mobile run remains the authority for unattended mobile-host capability.

## Deferred Artifact Transport

Artifact-first transport is not part of this implementation. A later read-only capability probe may test whether the mobile scheduled environment can resolve the successful workflow for the pinned SHA, download the artifact directly to a filesystem path, and verify manifest and payload hashes. The chunk transport remains mandatory fallback until all three operations are demonstrated in the mobile host.

## Inspection Timing

Future observer tasks run 30 and 60 minutes after the main test's scheduled start. They are read-only and inspect, in order: automation backend, external ledger, local bootstrap progress when accessible, news checkpoint, release receipt, and canonical reader bytes. They never rerun or modify the main task.
