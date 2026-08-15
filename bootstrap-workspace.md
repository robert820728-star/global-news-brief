# Daily news executable workspace bootstrap

This file is the **pre-checkpoint entrypoint** for scheduled runs. It exists to close the gap where the GitHub connector can read repository content but the execution shell does not yet have a repository filesystem.

## Stage -1: repository materialization

Before executing any `scripts/*.py`, do all of the following:

1. Use the GitHub connector to resolve the latest `main` commit SHA for `robert820728-star/global-news-brief`.
2. Do not assume that a repository visible through the GitHub connector already exists in the shell. Inspect the writable execution filesystem for a usable `global-news-brief` workspace.
3. If the workspace is absent, incomplete, or belongs to a different commit, create a fresh writable workspace. **Do not use `git clone`, `curl`, `wget`, raw GitHub HTTP from the shell, or any other shell-network fallback.** The scheduled sandbox may allow the GitHub connector while denying shell DNS/network access.
4. Through the GitHub connector, fetch the recursive Git tree at the exact resolved commit and materialize the **full tracked commit tree** into the local workspace. Fetch text as exact UTF-8 bytes when available; fetch binary blobs as base64/blob bytes and decode locally. Preserve repository-relative paths. Never synthesize missing scripts or copy files from an older run.
5. For every materialized blob, record:
   - repository-relative `path`
   - GitHub `source_blob_sha`
   - local `sha256`
   - local byte `size`
6. Write `<workspace>/bootstrap-workspace.json` with this shape:

```json
{
  "schema_version": "1.0.0",
  "status": "completed",
  "repository": "robert820728-star/global-news-brief",
  "ref": "main",
  "commit_sha": "<resolved-main-commit-sha>",
  "materialization_method": "github-connector",
  "materialization_scope": "full-commit-tree",
  "workspace_root": "<absolute-workspace-path>",
  "materialized_at": "<ISO-8601 timestamp>",
  "files": [
    {
      "path": "scripts/news_run_checkpoint.py",
      "source_blob_sha": "<git-blob-sha>",
      "sha256": "<local-sha256>",
      "size": 12345
    }
  ]
}
```

7. Change the shell working directory to that workspace. Only then initialize the news checkpoint:

```bash
python3 scripts/news_run_checkpoint.py init \
  --output <checkpoint> \
  --run-id <run-id> \
  --window-start <window-start> \
  --window-end <window-end> \
  --bootstrap-receipt <workspace>/bootstrap-workspace.json
```

`news_run_checkpoint.py init` is fail-closed: it rechecks the bootstrap receipt, required runtime files, local SHA-256 values, Git blob SHA values, repository identity, commit identity, and workspace root. If bootstrap validation fails, no news checkpoint may be created.

## Reuse rule

A pre-existing workspace may be reused only when its bootstrap receipt validates against the same exact `main` commit and the current local bytes. If `main` changed, if any required file changed, or if the receipt is missing/stale, rematerialize the workspace from the connector before starting the run.

## Failure semantics

If the GitHub connector cannot provide a required tree/blob, or the execution environment cannot write the workspace, report the earliest failure as:

`repository materialization / executable workspace acquisition`

This is a hard environment blocker and occurs **before** `news-run-checkpoint.json` initialization. Do not mislabel it as source-scan, preprocessing, validation, image, map, or publisher failure. Do not bypass the repository pipeline by manually producing a news brief.
