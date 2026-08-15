# Daily news executable workspace bootstrap

This file is the **pre-checkpoint entrypoint** for scheduled runs. Stage -1 must create a real executable workspace before any repository Python script is allowed to run.

## Design

The scheduled environment may let the GitHub connector read repository objects while the shell has no GitHub network path and no checked-out worktree. Therefore Stage -1 uses a **verified runtime capsule** instead of trying to materialize the full repository blob-by-blob through the model channel.

The capsule is generated in GitHub Actions from the repository runtime closure, compressed as deterministic `tar.xz`, base64-encoded, split into small UTF-8 text chunks, and checked into `bootstrap/`. Large generated PNG/SVG files and tests are not transported. Canonical map source data and render scripts are included so derived basemaps can be rebuilt locally.

## Stage -1: verified runtime capsule

Before executing any `scripts/*.py`, do all of the following:

1. Use the GitHub connector to resolve the latest `main` commit SHA and fetch its recursive Git tree. Do not assume connector visibility means the shell already has a repository.
2. From that exact commit, fetch `bootstrap/capsule-manifest.json` and its Git blob SHA. Require:
   - `repository = robert820728-star/global-news-brief`
   - `materialization_method = github-connector-capsule`
   - `materialization_scope = verified-runtime-capsule`
   - a non-empty `runtime_files` list and `chunks` list.
3. Fail stale capsules closed. Compare every `runtime_files[].path` and `source_blob_sha` in the manifest with the same path in the latest `main` recursive tree. Also fetch latest commit metadata and require `manifest.source_commit` to be either the latest commit itself or its first parent. If any runtime path is missing/different, or the source-commit relation is stale, stop with `repository materialization / executable workspace acquisition`.
4. Fetch `bootstrap/bootstrap_loader.py` from the same latest commit. Validate its connector-returned Git blob SHA against both the latest tree and `manifest.loader.source_blob_sha`. Write it to a temporary writable staging directory.
5. Fetch every chunk named by `manifest.chunks[]` from `bootstrap/<chunk-name>` as UTF-8 text from the same latest commit. Write each exact returned string to the staging directory. Do not synthesize, truncate, concatenate in the model response, or use shell network access.
6. Write the exact manifest JSON to the staging directory as `capsule-manifest.json` and run the loader locally:

```bash
python3 <staging>/bootstrap_loader.py \
  --manifest <staging>/capsule-manifest.json \
  --chunks-dir <staging> \
  --workspace <workspace> \
  --commit-sha <latest-main-commit-sha> \
  --manifest-blob-sha <manifest-git-blob-sha>
```

The loader verifies every chunk SHA-256 and size, reconstructs/decodes the payload, validates payload SHA-256, rejects unsafe tar members, extracts to a fresh workspace, and validates every runtime file by path, size, SHA-256 and Git blob SHA before writing `<workspace>/bootstrap-workspace.json`.

7. Only after the loader returns success, change the shell working directory to `<workspace>` and initialize the news checkpoint:

```bash
python3 scripts/news_run_checkpoint.py init \
  --output <checkpoint> \
  --run-id <run-id> \
  --window-start <window-start> \
  --window-end <window-end> \
  --bootstrap-receipt <workspace>/bootstrap-workspace.json
```

`news_run_checkpoint.py init` is fail-closed and rechecks the bootstrap receipt plus current executable workspace bytes. No checkpoint means no news pipeline and no reader-facing brief.

## Transport policy

Preferred future transport, when the host exposes it, is a direct connector file/artifact -> mounted filesystem path. Until then, the supported fallback is the checked-in compressed text capsule described above.

Never use shell `git clone`, `curl`, `wget`, raw GitHub HTTP, or another shell-network fallback for Stage -1. The connector is the only GitHub transport authority in the scheduled sandbox.

## Capsule maintenance

Repository changes are followed by `.github/workflows/build-bootstrap-capsule.yml`. The workflow applies the checkpoint migration if needed, builds the capsule, verifies it against the checked-out runtime closure, runs focused bootstrap/checkpoint tests, and commits the generated manifest/chunks back to `main`.

The capsule is intentionally runtime-only. It includes settings, schemas, skills, executable scripts, map source/style/reference inputs, state seed, and bootstrap loader. It excludes tests from the payload, documentation not needed at runtime, old releases, and derived map PNG/SVG outputs.

## Reuse rule

A pre-existing workspace may be reused only if its `bootstrap-workspace.json` validates against the exact latest `main` commit and all current local bytes. If `main` changed, the receipt is stale, or any required runtime file changed, rerun Stage -1.

## Failure semantics

Any failure before `news_run_checkpoint.py init` is reported as:

`repository materialization / executable workspace acquisition`

Do not mislabel it as source-scan, preprocessing, validation, image, map, or publisher failure. Do not bypass the repository pipeline by manually producing a news brief.