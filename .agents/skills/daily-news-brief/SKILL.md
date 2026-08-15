---
name: daily-news-brief
description: Orchestrate the complete daily news brief with audited selection, persistent pre-manifest recovery, event-level recovery, visual validation, and one fail-closed delivery gate.
---

# 每日新聞主控

本技能只負責流程順序、欄位所有權與交付契約。事件資料在 manifest 建立後是唯一事件交換層；manifest 建立以前則以同一份 `news-run-checkpoint.json` 保存 run 狀態。不得從搜尋結果直接跳到讀者版。

## 必讀

先讀 `news-brief-settings.md`、`news-brief-template.md`、`user-preferences.example.yaml` 或本輪偏好、`news-source-pool.json`、兩份 schema、`references/manifest-contract.md`、`scripts/news_run_checkpoint.py`、`scripts/check_unique_delivery_gate.py`、`scripts/publish_news_brief.py`，以及 `select-news-events`、`audit-news-candidates`、`verify-news-events`、`build-news-maps`、`build-news-charts`、`collect-news-images`、`recover-news-run` 技能。格式驗證失敗才查 `news-brief-examples.md` 對應段落。

## 固定流程

1. 以實際執行時間計算精確 24 小時窗，建立唯一 `run-id` 與 checkpoint；任何來源掃描前先執行 `news_run_checkpoint.py init`。
2. `source-scan`：逐站保存原始快照、SHA-256、翻頁／停止、邊界與時間證據。403、登入牆、逾時或解析失敗不得假裝完成；恢復時用 `news_run_checkpoint.py plan --input <checkpoint>` 找最早未完成 stage。
3. `preprocess-news-candidates`：只做時間窗、URL 正規化、完全重複與初步聚類，不做選稿或評級。
4. `select-news-events`：依設定評級與門檻挑選事件；每筆保存 `grading_evidence`。C 以上不得無故消失；邊境衝突與長期戰爭例行更新依既定 continuity 規則處理。
5. `audit-news-candidates`：所有候選都留下 selected/excluded/merged/deferred 與明確理由，完成十站 source-scan 證據驗證及十四天候選歷史。本輪 candidate audit 綁定 checkpoint。
6. `materialize-manifest`：只能把 audit 中 selected event ids 物化為 manifest，兩者必須一一對應；完成後綁定 manifest。從這一步起，事件內容只由 manifest 驅動。
7. `verify-news-events` → `build-news-maps` → `build-news-charts` → `collect-news-images`：各技能只改自己的欄位。地圖、圖表、圖片互相獨立，不得互相替代。來源圖有合格圖片時必須取得並視覺驗收；需要專業官方資訊圖的事件不能用一般照片取代。地圖使用完整 canonical basemap、繁體中文地名、既定 yellow-admin-v2 規格。
8. 每個 post-manifest stage 結束後使用 `recover_news_run.py plan --input <manifest> --brief <brief>` 檢查事件級失敗；同時更新同一 checkpoint。不得對 `recover_news_run.py` 虛構 `--checkpoint` 參數。
9. 從 manifest 渲染讀者版，綁定 `render` 的 `brief` artifact，再跑 `validate_map_decisions.py`、`validate_news_brief.py brief` 與 unique-delivery-gate 檢查。失敗只局部恢復，不直接輸出草稿。
10. 發布只能由 `scripts/publish_news_brief.py` 建立 release 與 receipt。最終交付只能執行 `--deliver-receipt ... --checkpoint <checkpoint>`；receipt 不是通行證本身，canonical publisher 在真正輸出 bytes 前會再次驗證目前 checkpoint、candidate audit/source scan、manifest、讀者版、附件與 map decisions。任何一項失敗 stdout 必須為空並返回恢復流程。

## 恢復邏輯

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
