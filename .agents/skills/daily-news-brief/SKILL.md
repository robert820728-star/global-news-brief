---
name: daily-news-brief
description: Orchestrate the complete daily news brief with verified runtime-capsule bootstrap, audited selection, persistent pre-manifest recovery, event-level recovery, visual validation, and one fail-closed delivery gate.
---

# 每日新聞主控

本技能只負責流程順序、欄位所有權與交付契約。事件資料在 manifest 建立後是唯一事件交換層；manifest 建立以前則以同一份 `news-run-checkpoint.json` 保存 run 狀態。不得從搜尋結果直接跳到讀者版。

## Stage -1：可執行工作區

在本技能任何 Python 流程開始前，必須先依 repo 根目錄 `bootstrap-workspace.md` 完成 verified runtime capsule bootstrap。GitHub connector「看得到 repo」不等於 shell 已有 repo；不得再逐 blob 物化完整 tracked tree，也不得用 shell `git clone`／`curl`／`wget` 當 fallback。

Stage -1 必須從同一個最新 `main` commit 取得 `bootstrap/capsule-manifest.json`、`bootstrap/bootstrap_loader.py` 與 manifest 指定的所有文字 chunks；先用最新 recursive tree 驗證 manifest 的 runtime blob SHA 與 capsule freshness，再把 chunks 精確寫到 shell staging directory，由 loader 在本地驗 chunk SHA-256、payload SHA-256、tar 安全性與每個 runtime file 的 path/size/SHA-256/Git blob SHA。只有 loader 成功產生 `bootstrap-workspace.json` 後，才可進入 checkpoint。

`news_run_checkpoint.py init` 必須收到 `--bootstrap-receipt` 並重新驗證 repository、commit SHA、workspace root、capsule metadata、必要 runtime 檔案、SHA-256 與 Git blob SHA。驗證不通過時不得建立 checkpoint，也不得人工繞過 scripts 直接出新聞。

## 必讀

先讀 `bootstrap-workspace.md`、`news-brief-settings.md`、`news-brief-template.md`、`user-preferences.example.yaml` 或本輪偏好、`news-source-pool.json`、全部三份 schema、`references/manifest-contract.md`、`scripts/news_run_checkpoint.py`、`scripts/build_source_candidate_list.py`、`scripts/check_unique_delivery_gate.py`、`scripts/publish_news_brief.py`，以及 `acquire-news-candidates`、`select-news-events`、`audit-news-candidates`、`verify-news-events`、`build-news-maps`、`build-news-charts`、`collect-news-images`、`recover-news-run` 技能。格式驗證失敗才查 `news-brief-examples.md` 對應段落。

## 固定流程

1. Stage -1 bootstrap 已成功後，以實際執行時間計算精確 24 小時窗，建立唯一 `run-id`；任何來源掃描前執行：

```bash
python3 scripts/news_run_checkpoint.py init --output <checkpoint> --run-id <run-id> --window-start <window-start> --window-end <window-end> --bootstrap-receipt <bootstrap-receipt>
```

2. `source-scan`：調用 `acquire-news-candidates` 掃描每板塊5站、合計15個主要來源，逐站保存原始快照、SHA-256、翻頁／停止、邊界與時間證據，並產生 `work/source-candidates.json`。直接讀取失敗立即改用完整瀏覽器；瀏覽器仍失敗才切同站替代入口。恢復時用 `news_run_checkpoint.py plan --input <checkpoint>` 找最早未完成 stage。
3. `preprocess-news-candidates`：只做時間窗、URL 正規化、完全重複與初步聚類，不做選稿或評級。
4. `select-news-events`：依設定評級與門檻挑選事件；每筆保存 `grading_evidence`。C 以上不得無故消失；邊境衝突與長期戰爭例行更新依既定 continuity 規則處理。
5. `audit-news-candidates`：所有候選都留下 selected/excluded/merged/deferred 與明確理由，完成15站 source-scan 證據驗證及十四天候選歷史。本輪 candidate audit 綁定 checkpoint。
6. `materialize-manifest`：只能把 audit 中 selected event ids 物化為 manifest，兩者必須一一對應；完成後綁定 manifest。從這一步起，事件內容只由 manifest 驅動。
7. `verify-news-events` → `build-news-maps` → `build-news-charts` → `collect-news-images`：各技能只改自己的欄位。地圖、圖表、圖片互相獨立，不得互相替代。來源圖有合格圖片時必須取得並視覺驗收；需要專業官方資訊圖的事件不能用一般照片取代。地圖使用完整 canonical basemap、繁體中文地名、既定 yellow-admin-v2 規格。capsule 不搬運可重建的 generated PNG/SVG；需要時由 capsule 內的 canonical map source/style 與 renderer 在本地重建。
8. 每個 post-manifest stage 結束後使用 `recover_news_run.py plan --input <manifest> --brief <brief>` 檢查事件級失敗；同時更新同一 checkpoint。不得對 `recover_news_run.py` 虛構 `--checkpoint` 參數。
9. 從 manifest 渲染讀者版，綁定 `render` 的 `brief` artifact，再跑 `validate_map_decisions.py`、`validate_news_brief.py brief` 與 unique-delivery-gate 檢查。失敗只局部恢復，不直接輸出草稿。
10. 發布只能由 `scripts/publish_news_brief.py` 建立 release 與 receipt。最終交付只能執行 `--deliver-receipt ... --checkpoint <checkpoint>`；receipt 不是通行證本身，canonical publisher 在真正輸出 bytes 前會再次驗證目前 bootstrap binding、checkpoint、candidate audit/source scan、manifest、讀者版、附件與 map decisions。任何一項失敗 stdout 必須為空並返回恢復流程。

每個 stage 都必須依序經過 `pending → running → completed`；只有 `running` 可轉為 `failed`。下一 stage 只能在前一 stage 已完成後開始。`completed` 必須綁定 `scripts/news_run_checkpoint.py` 內 `REQUIRED_STAGE_ARTIFACTS` 宣告的具名產物；空 evidence、缺少具名產物或直接填寫 completed 均視為跳關並由 checkpoint／publisher 阻擋。

## 恢復邏輯

Checkpoint 前的 Stage -1 失敗：重新執行 `bootstrap-workspace.md` 的 verified runtime capsule bootstrap，只重抓缺失／驗證失敗 chunk；不得改用手工新聞、逐 blob full-tree 搬運或 shell 網路 clone。

Manifest 前：

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>
```

Manifest 後：

```bash
python3 scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

只重跑失敗事件／stage 與必要的後續依賴。已完成且 SHA 綁定仍一致的工作不得清空。只有不可排除的硬性環境阻擋才可停止；一般來源失敗、圖片失敗、地圖失敗、格式失敗與驗證失敗都不是無聲結束理由。

## 交付不變式

Repository 內只能有一個 canonical publisher：`scripts/publish_news_brief.py`。其他腳本不得建立保留 release 檔名。`daily-schedule-prompt.md` 必須且只能宣告一次 canonical gate 與一次 receipt delivery 命令。最終 reader bytes 只可來自 canonical publisher 的 `--deliver-receipt` stdout；不得重新讀取 release 後自行轉貼、加前後文、重寫摘要、回退到草稿或舊 release。

