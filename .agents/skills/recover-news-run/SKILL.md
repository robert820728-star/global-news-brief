---
name: recover-news-run
description: Detect, isolate, retry, and revalidate failed daily-news stages before or after the manifest exists. Use for source scan, preprocessing, selection, candidate audit, manifest materialization, verification, maps, charts, images, rendering, validation, or interrupted scheduled runs.
---

# 每日新聞自主恢復

把失敗視為可定位的工作項目，不把整份簡報視為只能重做的單一任務。恢復流程分成 manifest 前 checkpoint 與 manifest 後事件資料兩層；**沒有 manifest 不是停止條件**。

## 核心規則

1. 本輪一開始必須已有 `news-run-checkpoint.json`；讀取 checkpoint 的 `stage_status`、`stage_evidence`、`recovery`。
2. manifest 尚未存在時執行 `scripts/news_run_checkpoint.py plan --input <checkpoint>`；從最早未完成的 pre-manifest stage 恢復。
3. manifest 已存在時執行 `scripts/news_run_checkpoint.py plan --input <checkpoint> --input <manifest> --brief <brief>`；合併 checkpoint 與事件層失敗目標。
4. 每次只重跑一個「階段＋事件」或一個根層階段；已完成的候選、事件、來源、地圖、圖表、圖片與分析不得清空重建。
5. pre-manifest 恢復成功後用 `record --checkpoint` 或 `news_run_checkpoint.py mark` 更新同一 checkpoint；候選稽核、manifest、讀者草稿必須重新綁定對應 artifact SHA-256。
6. manifest 後修復仍由原欄位擁有技能執行；`recover-news-run` 只負責定位、策略輪替與續行。
7. 每種恢復策略最多三次；單一路徑耗盡即切換下一策略，不得把一次下載、頁面或格式失敗當成整輪終止。
8. 修復後重新驗證並回到唯一發布閘門；只有不可排除的權限／環境硬阻擋才可停止並保存 checkpoint。

## Pre-manifest 路由

| checkpoint 階段 | 恢復目標 |
|---|---|
| `source-scan` | 從已保存快照／翻頁鏈續掃；切換合法 RSS、API、section 或替代頁面路徑；不得把 403／逾時當終點 |
| `preprocess-news-candidates` | 從已驗收 source-scan artifacts 重跑預處理，不重新抓已完成來源 |
| `select-news-events` | 從 ranked pool 重跑聚類、評級、`grading_evidence` 與門檻判斷 |
| `audit-news-candidates` | 從選稿結果重建／修補 candidate audit，重新驗證十站掃描證據與候選連結 |
| `materialize-manifest` | 從已通過 audit 的 selected event ids 重建 manifest；不得重新選稿 |

Checkpoint 新廹後若程序中斷，`running`、`failed`、`pending` 或缺失都視為未完成；恢復器必須返回**最早未完成階段**，不能因為沒有明確 `failed` 就空計畫結束。

## Post-manifest 路由

| 失敗位置 | 只重跑 |
|---|---|
| `verification` | `verify-news-events` 的該事件 |
| `map` | `build-news-maps` 的該事件 |
| `charts` | `build-news-charts` 的該事件 |
| `images` | `collect-news-images` 的該事件 |
| 讀者版缺欄、順序、附件或草稿不存在 | `render` |
| manifest／brief 驗證失敗 | 依錯誤欄位路由；無法定位時重跑 `validate` |

圖片失敗時依序採原圖下載、官方產品頁截圖、官方歷史／存檔頁、地方主管機關、主要媒體引用同一官方圖、其他可靠來源。每輪重新視覺驗收；地圖、圖表或文字不得替代來源圖片或專業圖資。

## 狀態與 artifact 紀錄

Pre-manifest 範例：

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>

python3 scripts/recover_news_run.py record \
  --checkpoint <checkpoint> \
  --output <checkpoint> \
  --stage audit-news-candidates \
  --outcome succeeded \
  --artifact candidate_audit=<candidate-audit> \
  --message "候選稽核已修復並重新驗證"
```

Post-manifest 範例：

```bash
python3 scripts/recover_news_run.py plan \
  --checkpoint <checkpoint> \
  --input <manifest> \
  --brief <brief>

python3 scripts/recover_news_run.py record \
  --input <manifest> \
  --output <manifest> \
  --stage collect-news-images \
  --event-id GLB-02 \
  --outcome failed \
  --error-code image-download-timeout \
  --message "來源頁圖片下載逾時"
```

每次嘗試記錄 `target_stage`、`event_id`、`attempt`、起訖時間、`outcome`、`error_code` 與 `message`。

## 結束條件

- 所有 checkpoint required stages 為 `completed`，candidate audit／manifest／brief 的綁定雜湊仍一致，事件層無 unresolved target，才可進入發布。
- `recovery.status` 不得靠刪除候選、清空失敗附件或改寫 `omitted` 來變成 completed。
- 十四天歷史保存失敗可降級，不改變評級或每日輸出；但本輪 candidate audit 本身、十站來源掃描證據與 selected→manifest 一致性不得跳過。
- 最終不是「有一個看起來完成的 Markdown」就算成功；必須由 `scripts/publish_news_brief.py` 產生 receipt，並由同一 canonical script 的 `--deliver-receipt` 以目前 checkpoint 驗證後直接輸出 reader bytes。
