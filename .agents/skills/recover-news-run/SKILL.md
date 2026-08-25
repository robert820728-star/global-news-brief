---
name: recover-news-run
description: Recover interrupted or failed daily-news stages before or after a manifest exists, without restarting completed work or silently dropping events.
---

# 每日新聞自主恢復

把失敗視為可定位的工作項目，不把整份簡報當成只能從頭重跑的單一任務。**沒有 manifest 不是停止條件。** 本輪一開始就必須存在 `news-run-checkpoint.json`，manifest 前後使用不同的恢復入口，但都回寫同一個 run checkpoint。

## 1. Manifest 前

本輪建立 checkpoint：

```bash
python3 scripts/news_run_checkpoint.py init --output <checkpoint> --run-id <run-id> --window-start <window-start> --window-end <window-end> --bootstrap-receipt <bootstrap-receipt>
```

manifest 尚未建立時，唯一恢復規劃命令是：

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>
```

它依序檢查 `source-scan`、`preprocess-news-candidates`、`select-news-events`、`audit-news-candidates`、`materialize-manifest`，回報最早未完成、`running`、`failed` 或缺失的 stage。只重跑該 stage 與其尚未完成的後續依賴；已完成且 artifact SHA-256 仍一致的工作不得清空重做。

每次 stage 開始、成功或失敗都用實際 CLI 更新同一 checkpoint：

```bash
python3 scripts/news_run_checkpoint.py mark \
  --input <checkpoint> --output <checkpoint> \
  --stage <stage> --status running

python3 scripts/news_run_checkpoint.py mark \
  --input <checkpoint> --output <checkpoint> \
  --stage <stage> --status completed \
  --artifact <name>=<path> --message "<result>"
```

`source-scan` 必須保存三條 discovery routes 的原始快照、連續翻頁／停止證據、邊界證據與 SHA-256。取得順序固定為 `canonical route → same-site direct fetch → same-site alternate non-browser route → browser-rendered snapshot`；瀏覽器永遠是最後備援。單一路徑失敗時記錄 degraded coverage，只要仍有可驗證當輪候選就繼續；不得把別站證據冒充為失敗 route。`audit-news-candidates` 完成後把 candidate audit 綁定到 checkpoint；`materialize-manifest` 只可由 audit 中的 selected event ids 物化 manifest，完成後綁定 manifest。

## 2. Manifest 後

manifest 已存在時，用既有事件級恢復器定位失敗欄位：

```bash
python3 scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

這個工具負責 `verification`、`map`、`charts`、`images`、`render/validate` 等事件級目標；同時把對應 stage 狀態同步到 `news-run-checkpoint.json`。修復紀錄使用目前實際支援的 CLI，例如：

```bash
python3 scripts/recover_news_run.py record \
  --input <manifest> --output <manifest> \
  --stage collect-news-images --event-id GLB-02 \
  --outcome failed --error-code image-download-timeout \
  --message "來源頁圖片下載逾時"
```

不要在 `recover_news_run.py` 上虛構 `--checkpoint` 參數；checkpoint 是由 `news_run_checkpoint.py` 維護。

## 3. 重試原則

同一事件／stage 最多三次。第一輪修原路徑；第二輪切換同級合法替代來源或取得方法；第三輪仍失敗時，只有不可排除的硬性權限、網路、來源不存在等阻擋才可停止。`mobile-native` 的 `NATIVE_MEDIA_UNAVAILABLE` 是已完成實際交付嘗試後的能力限制，不是 stage error；它使用 `reader-canonical-capability-degraded` 完成 reader，不能寫入 `last_error`。其他格式、證據或宣稱已交付之資產驗證失敗仍必須保留 `recovering/failed`。

恢復成功後重新跑該 stage 的驗證，再繼續後續 stage。若任何前置 artifact 在恢復期間被修改，必須重新綁定 SHA-256，不能沿用舊 checkpoint 證明。

## 4. 發布前條件

只有所有 required stages 都為 `completed`、candidate audit 與 manifest selected ids 一一對應、讀者版與 manifest 一致、所有宣稱 ready 或 `claim_critical=true` 的附件存在且視覺驗證通過、沒有 unresolved recovery target 時，才可交給 `scripts/publish_news_brief.py`。非關鍵 omitted 視覺不是 recovery target。恢復工具本身永遠不直接對使用者輸出草稿或 release。


## Conditional pre-manifest recovery boundary

`CONDITIONAL_RECOVERY_BUNDLE_POLICY`

After `preprocess-news-candidates` completes, record each artifact's local hash in the checkpoint. `FIRST_SELECT_NEWS_EVENTS_EXECUTION` may start immediately when the workspace is durable and the local hash/checkpoint binding validates. Do not make a remote recovery bundle a routine selection gate.

Create and verify the recovery bundle only for a real `cross-host handoff`, an `ephemeral workspace`, or an approaching `warning or timeout boundary`:

```powershell
python scripts/manage_canonical_run_bundle.py pack-recovery --run-id <run-id> --checkpoint <checkpoint> --source-candidates <source-candidates> --relevance-gate <relevance-gate> --admitted-candidates <model-source-candidates> --preprocessed-candidates <preprocessed-candidates> --batch-index <content-hydration-batches> --transport-dir <transport-dir> --manifest <recovery-bundle-manifest>
python scripts/manage_canonical_run_bundle.py verify --manifest <recovery-bundle-manifest> --transport-dir <transport-dir>
python scripts/manage_canonical_run_bundle.py restore --manifest <recovery-bundle-manifest> --transport-dir <transport-dir> --output-dir <restore-proof-dir>
```

The optional bundle contains these six logical artifacts:

- `recovery/checkpoint.json`
- `recovery/source-candidates.json`
- `recovery/news-relevance-gate.json`
- `recovery/model-source-candidates.json`
- `recovery/preprocessed-candidates.json`
- `recovery/content-hydration-batches.json`

If a handoff or workspace loss occurs, `restore` these artifacts from the same run's verified bundle and resume only the first incomplete batch. Never create a replacement run to conceal missing recovery inputs. Bundle creation failure is blocking only when the declared handoff or workspace-risk condition makes that bundle necessary.
