---
name: daily-news-brief
description: Orchestrate the complete daily news brief with verified runtime-capsule bootstrap, audited selection, persistent pre-manifest recovery, event-level recovery, visual validation, and one fail-closed delivery gate.
---

# 每日新聞主控

本技能只負責流程順序、欄位所有權與交付契約。事件資料在 manifest 建立後是唯一事件交換層；manifest 建立以前則以同一份 `news-run-checkpoint.json` 保存 run 狀態。不得從搜尋結果直接跳到讀者版。

## Stage -1：可執行工作區

在本技能任何 Python 流程開始前，必須先依 repo 根目錄 `bootstrap-workspace.md` 完成 verified runtime capsule bootstrap。GitHub connector「看得到 repo」不等於 shell 已有 repo；不得再逐 blob 物化完整 tracked tree，也不得用 shell `git clone`／`curl`／`wget` 當 fallback。唯一允許的 shell 網路入口，是已驗證 loader 對本輪固定 SHA 的 `capsule-payload.tar.xz` 單次請求。

Stage -1 必須從同一個最新 `main` commit 取得並驗證 `bootstrap/capsule-manifest.json` 與 `bootstrap/bootstrap_loader.py`。正常路徑由 loader 一次取得該固定 SHA 的 `bootstrap/capsule-payload.tar.xz`，驗證 size、SHA-256 與 Git blob SHA 後建立 workspace；只有此請求失敗才搬運 manifest 指定的文字 chunks。兩條路徑都由同一 loader 驗證 payload、tar 安全性與每個 runtime file 的 path/size/SHA-256/Git blob SHA。只有 loader 成功產生 `bootstrap-workspace.json` 後，才可進入 checkpoint。

`news_run_checkpoint.py init` 必須收到 `--bootstrap-receipt` 並重新驗證 repository、commit SHA、workspace root、capsule metadata、必要 runtime 檔案、SHA-256 與 Git blob SHA。驗證不通過時不得建立 checkpoint，也不得人工繞過 scripts 直接出新聞。

## 必讀

先讀 `bootstrap-workspace.md`、`news-brief-settings.md`、`news-brief-template.md`、`user-preferences.example.yaml` 或本輪偏好、`news-source-pool.json`、全部 schema、`references/manifest-contract.md`、`scripts/news_run_checkpoint.py`、`scripts/build_source_candidate_list.py`、`scripts/build_news_relevance_gate.py`、`scripts/check_unique_delivery_gate.py`、`scripts/publish_news_brief.py`，以及 `acquire-news-candidates`、`select-news-events`、`audit-news-candidates`、`verify-news-events`、`build-news-maps`、`build-news-charts`、`collect-news-images`、`recover-news-run` 技能。格式驗證失敗才查 `news-brief-examples.md` 對應段落。

## 固定流程

1. Stage -1 bootstrap 已成功後，以實際執行時間計算精確 24 小時窗，建立唯一 `run-id`；任何來源掃描前執行：

```bash
python3 scripts/news_run_checkpoint.py init --output <checkpoint> --run-id <run-id> --window-start <window-start> --window-end <window-end> --bootstrap-receipt <bootstrap-receipt>
```

2. `source-scan`：調用 `acquire-news-candidates` 取得 GDELT、中央社與中新社三個 discovery routes，逐來源保存原始快照、SHA-256、翻頁／停止、邊界與時間證據，並產生 `work/source-candidates.json`。GDELT 先讀官方 15 分鐘 export archives；只有 archives 不可用時才發送一次不阻塞的 DOC API 補充請求，遇到 429 不等待、不重試，最後才使用有時效標記的有效快取。單一介面失敗不得停止發佈。每個成功 route 的精確 24 小時已驗證 discovery row 全部保存，不設固定名額。接著執行 `scripts/build_news_relevance_gate.py`，產生逐列、守恆、無固定 top-N 的 `work/news-relevance-gate.json` 與 `work/model-source-candidates.json`。Gate 只決定哪些 discovery rows 需要內容補齊與模型審查，不做新聞重要性評級；不得因單一關鍵字或單一 heat 指標放行，中央社與中新社全部窗內列一律進入 admitted output。缺少來源摘要時，具 event identity 與來源支持結構脈絡的 GDELT row 明示 `summary_quality=structured_event_context`，其餘明示 `summary_quality=title_only`；兩者都不得把標題字串冒充正文摘要證據。恢復時用 `news_run_checkpoint.py plan --input <checkpoint>` 找最早未完成 stage。
3. `preprocess-news-candidates`：以 `work/model-source-candidates.json` 為輸入，只做時間窗、URL 正規化、完全重複與初步聚類，不做選稿或評級。原始 discovery row 總數、admitted row 總數與每列 gate reason 必須保留在 relevance-gate artifact；只有 admitted rows 成為 `SEMANTIC_EVENT_LEDGER_GATE` 的 article rows。
   - `SEMANTIC_EVENT_LEDGER_GATE`：只有語意事件才算新聞、才可進入六項評分。前處理只產生文章層 `provisional_article_groups`；選稿必須從內容建立唯一 `semantic_event_id` 與完整 `event_identity`，並逐列寫入 `article_dispositions`。每列只能是 `event_evidence`、`non_news` 或 `unresolved`；未歸零的 `unresolved` 阻擋 audit 完成。文章列、網址與標題群組都不得稱為新聞數。
   - `EVENT_REGION_AND_TIME_IDENTITY_GATE`：要求 `select-news-events` 在六項評分前從內容填妥 `event_identity.country_codes`、`primary_country_code`、`location_evidence`、`event_occurred_at`、`material_update_at`、`material_update_type`、`material_update_evidence` 與 `temporal_review`。來源分桶不是事件地區；時間資格由模型比較文章內容與十四天時間線，區分新事件、持續跨窗的當下影響、實質更新及舊事重述；程式只驗證證據一致性。已結束舊事件只是重複舊傷亡、重新整理、回顧、週年、換標題或重刊時為 `non_news`；開始較早但仍在窗內持續造成可驗證影響的事件可保留。缺漏或矛盾維持 `unresolved`，不得進評分、選入或 reader。
4. `select-news-events`：依設定評級與門檻挑選事件；每筆保存 `grading_evidence`。事件與 URL 映射只能由本輪 fresh pool 建立，禁止匯入舊 `work/validation-run-*` 的 driver、事件常數或 URL 映射。輸出後執行 `scripts/validate_selection_freshness.py --selection <selection-results> --source-candidates <source-candidates>`；C 以上不得無故消失，且每個 `selected_event_id` 都必須存在於本輪事件。邊境衝突與長期戰爭例行更新依既定 continuity 規則處理。
   - 內容補齊遵守 `CONTENT_HYDRATION_BATCH_RECEIPT_GATE`：只能對 admitted rows 以最多 20 列的可恢復 connector 批次執行；不得用單一 shell 多網域抓取。每批 append-only 留下 running/terminal receipt、逐 URL 狀態與內容 hash，中斷只續第一個未完成批次。
5. `audit-news-candidates`：所有候選都留下 selected/excluded/merged/deferred 與明確理由，十四天稽核保存三個 discovery routes 的完整海選清單、GDELT acquisition mode、每筆 `public_value_v1` 六項大分數與總分，並完成 source-scan 證據驗證。本輪所有 C 級以上候選（含合併項）都以 `selected_event_id` 對應 manifest／讀者版事件，再把 candidate audit 綁定 checkpoint。
6. `materialize-manifest`：只能把 audit 中 selected event ids 物化為 manifest，兩者必須一一對應；完成後綁定 manifest。從這一步起，事件內容只由 manifest 驅動。
7. `verify-news-events` → `build-news-maps` → `build-news-charts` → `collect-news-images`：各技能只改自己的欄位。驗證結果必須先寫成 stage patch JSON，再用 `scripts/apply_event_stage_patch.py --stage verify-news-events` 合併；禁止用 jq 或 shell 字串插值直接改寫 manifest。`verify-news-events` 完成時只執行 `scripts/validate_news_brief.py stage --stage verify-news-events --before <before-manifest> --after <after-manifest>`；map、chart、image 階段同樣只執行自己的 stage ownership 檢查。地圖、圖表、圖片互相獨立，不得互相替代。來源圖有合格圖片時必須取得並視覺驗收；需要專業官方資訊圖的事件不能用一般照片取代。地圖使用完整 canonical basemap、繁體中文地名、既定 yellow-admin-v2 規格。capsule 不搬運可重建的 generated PNG/SVG；需要時由 capsule 內的 canonical map source/style 與 renderer 在本地重建。
8. 每個 post-manifest stage 結束後使用 `recover_news_run.py plan --input <manifest> --brief <brief>` 檢查事件級失敗；同時更新同一 checkpoint。不得對 `recover_news_run.py` 虛構 `--checkpoint` 參數。
9. 只有 checkpoint 的 `collect-news-images` completed 後，才第一次執行 `scripts/validate_news_brief.py manifest --input <final-manifest>`。它是 final-manifest validator，不得提前到 verify、map 或 chart 階段。若意外提前執行，script 只會輸出 `DEFERRED`；這是可恢復的無副作用誤呼叫，不代表驗證通過，也不得標記整輪失敗。繼續圖片階段並在其 completed 後重跑到輸出 `OK`。通過後從 manifest 渲染讀者版，綁定 `render` 的 `brief` artifact，再跑 `validate_map_decisions.py`、`validate_news_brief.py brief` 與 unique-delivery-gate 檢查。失敗只局部恢復，不直接輸出草稿。
10. 發布只能由 `scripts/publish_news_brief.py` 建立 release 與 receipt。publisher 成功後，先以 `scripts/manage_canonical_run_bundle.py pack` 將本輪所有必要 run artifacts 建立為 connector-safe transport；大檔必須是 `storage.mode=chunked`，每個 upload 必須是 `encoding=base64` 並綁定原始 SHA-256 與預期 Git blob SHA。上傳後以單一 atomic tree/commit 同時發布 bundle 與 `logs/current.json`，再用 `verify`／`restore` 重組並核對 byte identity。最終交付只能執行 `--deliver-receipt ... --checkpoint <checkpoint> --conversation-transport`；receipt 不是通行證本身，canonical publisher 在真正輸出前會再次驗證目前 bootstrap binding、checkpoint、candidate audit/source scan、manifest、讀者版、附件與 map decisions。`NATIVE_MEDIA_CAPABILITY_FALLBACK` 只適用於宿主明確無法產生原生媒體時：保留 verified image evidence 與每則 `reader_omission_note`，允許文字 reader 交付，但不得宣稱原生像素驗收；缺少圖片證據或所需地圖仍須恢復。conversation transport 只能把 Markdown 本機圖片路徑轉成 `sandbox:` URI，不得修改 canonical release 或文字。任何其他失敗 stdout 必須為空並返回恢復流程。

每個 stage 都必須依序經過 `pending → running → completed`；只有 `running` 可轉為 `failed`。下一 stage 只能在前一 stage 已完成後開始。`completed` 必須綁定 `scripts/news_run_checkpoint.py` 內 `REQUIRED_STAGE_ARTIFACTS` 宣告的具名產物；空 evidence、缺少具名產物或直接填寫 completed 均視為跳關並由 checkpoint／publisher 阻擋。

## 恢復邏輯

Checkpoint 前的 Stage -1 失敗：重新執行 `bootstrap-workspace.md` 的 verified runtime capsule bootstrap；先嘗試一次固定 SHA payload，失敗才只重抓缺失／驗證失敗 chunk。不得改用手工新聞、逐 blob full-tree 搬運或 shell 網路 clone。

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

Repository 內只能有一個 canonical publisher：`scripts/publish_news_brief.py`。其他腳本不得建立保留 release 檔名。`daily-schedule-prompt.md` 必須且只能宣告一次 canonical gate 與一次 receipt delivery 命令。最終對話內容只可來自 canonical publisher 的 `--deliver-receipt ... --conversation-transport` stdout；canonical release 與其 SHA-256 保持不變，不得重新讀取 release 後自行轉貼、加前後文、重寫摘要、回退到草稿或舊 release。


## Durable pre-manifest recovery boundary

`PRE_MANIFEST_RECOVERY_BUNDLE_GATE`

After `preprocess-news-candidates` is completed and before selection can become running, execute:

```powershell
python scripts/manage_canonical_run_bundle.py pack-recovery --run-id <run-id> --checkpoint <checkpoint> --source-candidates <source-candidates> --relevance-gate <relevance-gate> --admitted-candidates <model-source-candidates> --preprocessed-candidates <preprocessed-candidates> --batch-index <content-hydration-batches> --transport-dir <transport-dir> --manifest <recovery-bundle-manifest>
python scripts/manage_canonical_run_bundle.py verify --manifest <recovery-bundle-manifest> --transport-dir <transport-dir>
python scripts/manage_canonical_run_bundle.py restore --manifest <recovery-bundle-manifest> --transport-dir <transport-dir> --output-dir <restore-proof-dir>
```

Publish the following six logical artifacts in one `atomic tree/commit`, read the commit back, and prove restored byte identity before selection starts:

- `recovery/checkpoint.json`
- `recovery/source-candidates.json`
- `recovery/news-relevance-gate.json`
- `recovery/model-source-candidates.json`
- `recovery/preprocessed-candidates.json`
- `recovery/content-hydration-batches.json`

If the live workspace disappears, restore these artifacts from the same run's verified recovery bundle and resume only the first incomplete batch. Never create a replacement run to conceal missing recovery inputs.

`FIRST_SELECT_NEWS_EVENTS_EXECUTION`: only after this gate passes may `select-news-events` be marked running or content hydration begin.
