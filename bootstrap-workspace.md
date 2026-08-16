# Daily news executable workspace bootstrap

This file is the **pre-checkpoint entrypoint** for scheduled runs. Stage -1 must create a real executable workspace before any repository Python script is allowed to run.

## Design

The scheduled environment may let the GitHub connector read repository objects while the shell has no GitHub network path and no checked-out worktree. Therefore Stage -1 uses a **verified runtime capsule** instead of trying to materialize the full repository blob-by-blob through the model channel.

The capsule is generated in GitHub Actions from the repository runtime closure, compressed as deterministic `tar.xz`, base64-encoded, split into small UTF-8 text chunks, and checked into `bootstrap/`. Large generated PNG/SVG files and tests are not transported. Canonical map source data and render scripts are included so derived basemaps can be rebuilt locally.

Connector responses can truncate long single lines, so capsule schema `1.1.0` uses explicit transport framing: each logical chunk remains at most 8192 Base64 characters, but chunk files are wrapped at 256 ASCII characters per LF-terminated line and grouped into verified retrieval blocks of at most 8 lines. See `bootstrap/TRANSPORT_FORMAT.md` for the framing contract.

## Stage -1: verified runtime capsule

Before executing any `scripts/*.py`, do all of the following:

1. Use the GitHub connector to resolve the latest `main` commit SHA and fetch its recursive Git tree. Do not assume connector visibility means the shell already has a repository.
2. From that exact commit, fetch `bootstrap/capsule-manifest.json` and its Git blob SHA. Require:
   - `schema_version = 1.1.0`
   - `repository = robert820728-star/global-news-brief`
   - `materialization_method = github-connector-capsule`
   - `materialization_scope = verified-runtime-capsule`
   - positive `line_width` and `retrieval_block_lines`
   - non-empty `runtime_files` and `chunks` lists.
3. Fail stale capsules closed. Compare every `runtime_files[].path` and `source_blob_sha` in the manifest with the same path in the latest `main` recursive tree. Also fetch latest commit metadata and require `manifest.source_commit` to be either the latest commit itself or its first parent. If any runtime path is missing/different, or the source-commit relation is stale, stop with `repository materialization / executable workspace acquisition`.
4. Fetch `bootstrap/bootstrap_loader.py` from the same latest commit. Validate its connector-returned Git blob SHA against both the latest tree and `manifest.loader.source_blob_sha`. Write it to a temporary writable staging directory.
5. **Do not fetch an entire chunk in one connector response.** For every chunk in `manifest.chunks[]`, iterate its `blocks[]` in order. Fetch `bootstrap/<chunk-name>` from the same latest commit with the exact `start_line` and `end_line` declared by that block. Each block is intentionally at most 8 lines / 2048 Base64 characters plus LF bytes. Write the returned block bytes to a temporary block file using canonical LF endings, then locally verify the block `size` and `sha256`. A truncated or altered block must be retried by the same line range; never accept partial text.
6. After all blocks for one chunk validate, concatenate the verified block files in order into the canonical chunk file. Locally verify the complete chunk `size` and `sha256`, then verify the unwrapped Base64 `encoded_size` and `encoded_sha256`. Only after every chunk passes may Stage -1 continue. This makes connector truncation a small-block retry instead of a whole-run failure.
7. Write the exact manifest JSON to the staging directory as `capsule-manifest.json` and run the loader locally. This initial `python3` needs only the standard library and is not yet the verified news runtime:

```bash
python3 <staging>/bootstrap_loader.py \
  --manifest <staging>/capsule-manifest.json \
  --chunks-dir <staging> \
  --workspace <workspace> \
  --commit-sha <latest-main-commit-sha> \
  --manifest-blob-sha <manifest-git-blob-sha>
```

The loader independently revalidates canonical line framing, every retrieval block, every complete chunk, the reconstructed Base64 stream, payload SHA-256, tar safety, and every runtime file by path, size, SHA-256 and Git blob SHA before writing `<workspace>/bootstrap-workspace.json`.

8. Only after the loader returns success, change the shell working directory to `<workspace>`. Resolve the pipeline runtime before initializing a checkpoint. Prefer a host-provided bundled-runtime Python absolute path when the host dependency locator exposes one:

```bash
python3 scripts/resolve_bundled_python.py --preferred-python <host-bundled-python>
```

If the host does not provide a path, run `python3 scripts/resolve_bundled_python.py`; it searches declared environment variables and cross-platform Codex runtime cache locations. The resolver must return `status=ready` after actually importing Pillow with the selected executable. The `python3` that launched the resolver is not accepted as the pipeline runtime merely because it is on PATH.

9. Initialize the checkpoint and run every subsequent canonical script with the exact `<bundled-python>` returned by the resolver:

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

Preferred future transport, when the host exposes it, is a direct connector file/artifact -> mounted filesystem path. Until then, the supported fallback is the checked-in compressed text capsule with segmented line-range retrieval.

Never use shell `git clone`, `curl`, `wget`, raw GitHub HTTP, or another shell-network fallback for Stage -1. The connector is the only GitHub transport authority in the scheduled sandbox.

## Capsule maintenance

Repository changes are followed by `.github/workflows/build-bootstrap-capsule.yml`. The workflow builds the capsule, verifies it against the checked-out runtime closure, runs focused bootstrap/checkpoint tests, and commits only the generated manifest/chunks back to `main`. Python bytecode and cache directories must never be committed.

The capsule is intentionally runtime-only. It includes settings, schemas, skills, cross-platform Python scripts, map source/style/reference inputs, state seed, and bootstrap loader. It excludes tests, PowerShell legacy scripts, documentation not needed at runtime, old releases, and derived map PNG/SVG outputs.

## Reuse rule

A pre-existing workspace may be reused only if its `bootstrap-workspace.json` validates against the exact latest `main` commit and all current local bytes. If `main` changed, the receipt is stale, or any required runtime file changed, rerun Stage -1.

## Failure semantics

Any failure before `news_run_checkpoint.py init` is reported as:

`repository materialization / executable workspace acquisition`

Do not mislabel it as source-scan, preprocessing, validation, image, map, or publisher failure. Do not bypass the repository pipeline by manually producing a news brief.
