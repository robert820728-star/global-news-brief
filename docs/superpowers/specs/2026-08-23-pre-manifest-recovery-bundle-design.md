# Pre-Manifest Recovery Bundle Design

## Problem

Daily-news runs can fail after `preprocess-news-candidates` but before a manifest exists. The runtime workspace is ephemeral. The current canonical bundle is only produced after publishing, so a terminal failure can leave `run-logs` with receipts but without the checkpoint, admitted candidate rows, preprocessed rows, or deterministic hydration batch inputs needed for same-run recovery.

## Scope

Add a durable, connector-safe recovery bundle at the boundary between completed preprocessing and the first `select-news-events` hydration batch. Do not change candidate admission, semantic-event rules, scoring, publishing, or any prior run artifact.

## Considered Approaches

1. Extend `manage_canonical_run_bundle.py` with a pre-manifest recovery profile. This reuses the existing lossless base64/chunk transport and integrity verification. Recommended.
2. Embed all recovery data inside the checkpoint. Rejected because candidate data can be large and would mix state with payload ownership.
3. Depend on issue comments or an ephemeral workspace. Rejected because neither provides byte-identical durable recovery inputs.

## Design

`scripts/manage_canonical_run_bundle.py` will gain a `pack-recovery` command and a `pack_pre_manifest_recovery_bundle()` API. The command consumes:

- the current checkpoint;
- complete source candidates;
- the relevance gate;
- admitted/model source candidates;
- preprocessed candidates;
- an output path for a deterministic hydration-batch index;
- the existing connector-safe transport and manifest destinations.

The helper validates that the checkpoint and admitted candidate file belong to the requested run and window. It materializes an ordered batch index with at most 20 article rows per batch. Each item records the candidate id, source id, canonical URL, and summary quality. Ordering follows the admitted candidate artifact, so recovery reconstructs the same batch boundaries without re-running acquisition or preprocessing.

The resulting bundle uses the existing `canonical-run-bundle-v1` transport with a `profile` value of `pre-manifest-recovery`. Its required logical artifacts are stored under `recovery/` and retain byte size, SHA-256, and Git blob SHA closure through the existing verifier and restorer.

## Workflow Contract

After `preprocess-news-candidates` is marked completed, and before `select-news-events` is marked running, the daily workflow must:

1. run `pack-recovery`;
2. persist the bundle manifest and uploads to the same run in `run-logs`;
3. run `verify` and a restore/byte-identity check;
4. write a passed receipt for the recovery-bundle boundary;
5. only then start hydration batch 001.

If persistence or verification fails, the run fails before selection. A later process can restore the exact inputs and resume the same run without rebuilding completed stages.

## Error Handling

The command fails closed for an empty admitted pool, duplicate candidate ids, unsafe paths, run/window mismatches, unsupported batch sizes, or missing required files. It never edits source artifacts. It writes the deterministic index and transport outputs only after validation.

## Tests

- A regression test reproduces the terminal-recovery condition by packing inputs, deleting the originals, restoring the bundle, and verifying the checkpoint, admitted rows, preprocessed rows, and batch index byte-for-byte.
- The batch-index test proves stable ordering, complete candidate conservation, unique ids, and a maximum of 20 rows per batch.
- A contract test proves the workflow invokes the recovery gate before `select-news-events`.
- Existing canonical-delivery bundle tests must remain green.

## Acceptance

The focused red-to-green regression tests pass, all related bundle/checkpoint/contract tests pass, and a fresh capsule contains the changed script and workflow contracts with complete manifest hash closure.
