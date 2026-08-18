# Daily news executable workspace bootstrap

This file is the **pre-checkpoint entrypoint** for scheduled runs. Stage -1 must create a real executable workspace before any repository Python script is allowed to run.

## Design

The scheduled environment may let the GitHub connector read repository objects while the shell has no GitHub network path and no checked-out worktree. Therefore Stage -1 uses a **verified runtime capsule** instead of trying to materialize the full repository blob-by-blob through the model channel.

The capsule is generated in GitHub Actions from the repository runtime closure and compressed as deterministic `tar.xz`. The verified binary is checked in as `bootstrap/capsule-payload.tar.xz` for one-request materialization. The same bytes are also Base64-encoded and split into small UTF-8 text chunks as a connector-only fallback. Large generated PNG/SVG files and tests are not transported. Canonical map source data and render scripts are included so derived basemaps can be rebuilt locally.

Connector responses can truncate long single lines, so capsule schema `1.1.0` uses explicit transport framing: each logical chunk remains at most 8192 Base64 characters, but chunk files are wrapped at 256 ASCII characters per LF-terminated line and grouped into verified retrieval blocks of at most 8 lines. See `bootstrap/TRANSPORT_FORMAT.md` for the framing contract.

## Stage -1: verified runtime capsule

Before executing any `scripts/*.py`, do all of the following:

1. `PRE_CONTRACT_MAIN_RESOLUTION`: the schedule wrapper uses a fresh UTC nonce for `/branches/main?cache_bust=<nonce-a>` and `/commits/main?cache_bust=<nonce-b>`, then reads this file from the agreed SHA. These are the **only permitted pre-contract GitHub reads** because no repository contract can govern steps that occur before it is loaded. This is a single named `main` branch lookup; do not read the tree, manifest, sources, or prior artifacts in this envelope.
2. `EARLY_DIAGNOSTIC_MAIN_PINNED`: the two endpoints must return the same SHA. If they differ, repeat both reads once with two new nonces. If the second pair still differs, fail Stage -1 closed. The wrapper must not enumerate repository branches and must not reuse a commit SHA from an earlier run. It must pin all repository reads for this run to the agreed SHA.
3. `EARLY_DIAGNOSTIC_RUN_ID`: immediately after loading the pinned contract, generate the unique `<run-id>`, UTC `started_at`, and later-request nonce values in task memory **without a tool call**. Validate the format with `scripts/run_identity.py` after workspace creation. The required pre-contract main resolution is not an ordering violation.
4. `EARLY_DIAGNOSTIC_RUN_STARTED`: immediately after generating the run id and **before any recursive tree read**, create this run's only comment in GitHub issue #3. The compact body contains `run_id`, `commit`, `status=running`, `stage=bootstrap-main-pinned`, `progress=0/unknown`, `updated_at`, and `last_error=null`. Wait for the write call to return and retain the comment id in task context before reading the tree. Attempt this initial write once; if it is unavailable, remember `external_ledger: unavailable` and continue without blocking news.
5. `EARLY_DIAGNOSTIC_TREE_VERIFIED`: fetch the pinned commit's recursive Git tree, retain only the path/blob-SHA entries required for verification, and do not quote the full tree in the response. On success, **update the same comment** to `stage=bootstrap-tree-verified`.
6. `EARLY_DIAGNOSTIC_MANIFEST_VERIFIED`: from that exact commit, fetch `bootstrap/capsule-manifest.json` and its Git blob SHA. Require:
   - `schema_version = 1.1.0`
   - `repository = robert820728-star/global-news-brief`
   - `materialization_method = github-connector-capsule`
   - `materialization_scope = verified-runtime-capsule`
   - positive `line_width` and `retrieval_block_lines`
   - a `payload` record for `capsule-payload.tar.xz` with size, SHA-256, and Git blob SHA;
   - non-empty `runtime_files` and `chunks` lists.
7. Fail stale capsules closed. Compare every `runtime_files[].path` and `source_blob_sha` in the manifest with the same path in the resolved SHA's recursive tree. Require the tree blob for `bootstrap/capsule-payload.tar.xz` to equal `manifest.payload.source_blob_sha`. Also fetch that commit's metadata and require `manifest.source_commit` to be either the resolved commit itself or its first parent. If any runtime path or payload blob is missing/different, or the source-commit relation is stale, stop with `repository materialization / executable workspace acquisition`. After validation, update the same comment to `stage=bootstrap-manifest-verified` and `progress=0/<chunks_total>`.
8. `EARLY_DIAGNOSTIC_HELPERS_VERIFIED`: fetch `bootstrap/bootstrap_loader.py`, `bootstrap/bootstrap_progress.py`, and `bootstrap/bootstrap-progress.schema.json` from the same resolved commit. Validate each connector-returned Git blob SHA against the resolved tree; also validate the loader against `manifest.loader.source_blob_sha`. Write them to a temporary writable staging directory, then update the same comment to `stage=bootstrap-helpers-verified`. The progress helper uses only the Python standard library and is allowed before the news runtime exists.
9. Initialize the separate pre-checkpoint record with `python3 <staging>/bootstrap_progress.py init --output <staging>/bootstrap-progress.json --run-id <run-id> --resolved-commit <latest-main-commit-sha> --chunks-total <count>`, then use its `ledger` command to import the early ledger status and comment id. This file is diagnostic evidence, not the news checkpoint.
10. Attempt the low-pressure primary transport once. Run the verified loader against the exact pinned URL `https://raw.githubusercontent.com/robert820728-star/global-news-brief/<latest-main-commit-sha>/bootstrap/capsule-payload.tar.xz`. The loader downloads the bytes with the Python standard library, then requires the manifest size, SHA-256, and Git blob SHA before extracting anything:

```bash
python3 <staging>/bootstrap_loader.py \
  --manifest <staging>/capsule-manifest.json \
  --payload-url https://raw.githubusercontent.com/robert820728-star/global-news-brief/<latest-main-commit-sha>/bootstrap/capsule-payload.tar.xz \
  --workspace <workspace> \
  --commit-sha <latest-main-commit-sha> \
  --manifest-blob-sha <manifest-git-blob-sha>
```

11. If and only if the direct request is unavailable or fails payload verification, record that single failure and use the existing segmented connector transport below. Do not retry the direct URL and do not ask the user to intervene.
12. **Do not fetch an entire fallback chunk in one connector response.** For every chunk in `manifest.chunks[]`, iterate its `blocks[]` in order. The normal fallback requests a **16-line** range spanning two adjacent declared blocks. Save the exact canonical-LF response and run `bootstrap/bootstrap_progress.py verify-grouped` with the two original block specifications. The helper splits the response and independently verifies both original block sizes and SHA-256 values. If either half is missing or altered, discard the grouped response and fall back to the exact 8-line request for each affected block.
13. Every exact block request uses the same pinned commit and same declared `start_line` / `end_line` for **one initial attempt plus at most three retries**. Use backoff delays of **2, 5, and 10 seconds**, or the host's smallest safe equivalents, and record every attempt's byte size, SHA-256, and error with the progress helper. After the fourth failure, stop. Never restart or re-download earlier verified chunks.
14. After all blocks for one chunk validate, concatenate the verified block files in order into the canonical chunk file. Locally verify the complete chunk `size` and `sha256`, then verify the unwrapped Base64 `encoded_size` and `encoded_sha256`. Only then atomically advance `chunks_completed` by one with the progress helper. Only after every chunk passes may Stage -1 continue.
15. For the fallback only, write the exact manifest JSON to the staging directory as `capsule-manifest.json` and run the loader locally. This initial `python3` needs only the standard library and is not yet the verified news runtime:

```bash
python3 <staging>/bootstrap_loader.py \
  --manifest <staging>/capsule-manifest.json \
  --chunks-dir <staging> \
  --workspace <workspace> \
  --commit-sha <latest-main-commit-sha> \
  --manifest-blob-sha <manifest-git-blob-sha>
```

Both transports converge in the same loader. It verifies the payload before tar safety and every runtime file by path, size, SHA-256 and Git blob SHA, then writes `<workspace>/bootstrap-workspace.json` with `transport=direct-payload` or `transport=segmented-chunks`.

16. Only after the loader returns success, change the shell working directory to `<workspace>`. Resolve the pipeline runtime before initializing a checkpoint. Prefer a host-provided bundled-runtime Python absolute path when the host dependency locator exposes one:

```bash
python3 scripts/resolve_bundled_python.py --preferred-python <host-bundled-python>
```

If the host does not provide a path, run `python3 scripts/resolve_bundled_python.py`; it searches declared environment variables and cross-platform Codex runtime cache locations. The resolver must return `status=ready` after actually importing Pillow with the selected executable. The `python3` that launched the resolver is not accepted as the pipeline runtime merely because it is on PATH.

17. Initialize the checkpoint and run every subsequent canonical script with the exact `<bundled-python>` returned by the resolver:

```bash
<bundled-python> scripts/news_run_checkpoint.py init \
  --output <checkpoint> \
  --run-id <run-id> \
  --window-start <window-start> \
  --window-end <window-end> \
  --bootstrap-receipt <workspace>/bootstrap-workspace.json
```

`news_run_checkpoint.py init` is fail-closed and rechecks the bootstrap receipt plus current executable workspace bytes. No checkpoint means no news pipeline and no reader-facing brief.

## Transport policy

The primary transport is the one-request pinned raw payload executed only by the verified loader. The segmented connector chunks remain the final fallback when the host blocks that request.

Never use shell `git clone`, `curl`, `wget`, an unpinned URL, or arbitrary raw GitHub HTTP for Stage -1. The sole shell-network exception is the loader's exact pinned `capsule-payload.tar.xz` URL above; its bytes are accepted only after manifest size, SHA-256, and Git blob verification.

## Capsule maintenance

Repository changes are followed by `.github/workflows/build-bootstrap-capsule.yml`. The workflow builds the capsule, verifies it against the checked-out runtime closure, runs focused bootstrap/checkpoint tests, and commits only the generated payload, manifest, and chunks back to `main`. Python bytecode and cache directories must never be committed.

The capsule is intentionally runtime-only. It includes settings, schemas, skills, cross-platform Python scripts, map source/style/reference inputs, state seed, and bootstrap loader. It excludes tests, PowerShell legacy scripts, documentation not needed at runtime, old releases, and derived map PNG/SVG outputs.

## Reuse rule

A pre-existing workspace may be reused only after this run independently resolves fresh `main` through both nonce-bearing endpoints and its `bootstrap-workspace.json` validates against that exact resolved SHA and all current local bytes. Never use the workspace receipt to decide what the latest SHA is; always resolve fresh `main` again on the next run. If `main` changed, the receipt is stale, or any required runtime file changed, rerun materialization.

## Failure semantics

Any failure before `news_run_checkpoint.py init` is reported as:

`repository materialization / executable workspace acquisition`

Every controlled exit, successful or failed, must print one stable `RUN_RECEIPT` generated by `bootstrap/bootstrap_progress.py`. It includes the run id, resolved main SHA, last completed stage, chunk and block position, last error, retry count, external-ledger status, and canonical-delivery status. If GitHub write access is absent or the best-effort ledger update fails, record and print `external_ledger: unavailable`; ledger failure must never block the news pipeline.

When GitHub write access is available, follow `bootstrap/RUN_LEDGER_PROTOCOL.md`: use **one comment per run_id** in issue #3, update after verification and **every 8 completed chunks**, and debounce routine news-stage writes to **at most once every 3 minutes**. This ledger is **best-effort** and **must never block the news pipeline**. Failure and final updates are immediate.

Retain `bootstrap-progress.json` on failure so the final report can diagnose the earliest boundary. After successful canonical reader delivery, print the final receipt first and then clear the local progress file. The compact final external ledger record may remain.

Do not mislabel it as source-scan, preprocessing, validation, image, map, or publisher failure. Do not bypass the repository pipeline by manually producing a news brief.
