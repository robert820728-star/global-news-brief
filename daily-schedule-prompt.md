# 每日新聞排程執行契約

本文件是排程執行時的主控契約。所有新聞內容、選稿、驗證、地圖、圖表、圖片、恢復與發布規則，以 repository 內最新版設定、skills、schemas 與 scripts 為準；不得由模型自行另造平行流程。

## 固定輸出設定

- 區域：`TWN`、`CHN`、`GLB`。
- 語言：繁體中文。
- 時區語意：`Asia/Taipei`。
- 新聞時間窗：以本輪**實際執行時間**為 `window_end`，精確向前 24 小時為 `window_start`。不得用「今天 00:00 起」或排程原定時間替代。
- 不設定任意篇數上限；依 `news-brief-settings.md` 的評級、門檻與 continuity 規則決定事件數量。
- 讀者版標題固定為「每日新聞」；若宿主可控制對話標題則使用此名稱。

## Stage -1：先取得可執行 workspace

任何 `scripts/*.py` 執行前，先完整遵守 `bootstrap-workspace.md`。

GitHub connector 可見 repository 不代表 shell 已有 repository。必須使用最新版 `main` 的 verified runtime capsule：

1. connector 解析最新 `main` commit 與 recursive tree；
2. 取得同一 commit 的 `bootstrap/capsule-manifest.json`、`bootstrap/bootstrap_loader.py` 與 manifest 指定 chunks；
3. 依 `bootstrap-workspace.md` 驗證 capsule freshness、runtime Git blob SHA、loader SHA 與 chunks；
4. 將 manifest／loader／chunks 精確寫入 writable staging directory；
5. 由 loader 在 shell 本地解碼、驗 SHA、解壓並建立 executable workspace；
6. loader 成功產生 `bootstrap-workspace.json` 後，才可建立 news checkpoint。

Stage -1 完成後必須先直接執行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/resolve_bundled_python.ps1`。此 canonical resolver 以目前宿主的 Codex bundled runtime 固定位置解析 Python 絕對路徑，並在回傳 `status=ready` 前實際匯入 Pillow；以它回傳的同一個 executable 執行本輪所有 canonical Python scripts。不得先呼叫 workspace dependency locator，不得直接假設 PATH 上的 `python`／`python3` 具有 Pillow 或其他 runtime dependencies；resolver 首次失敗即回報 Stage -1 blocker，不能在同輪改走 locator 掩蓋失敗。Materialized runtime 的 receipt 綁定檔視為唯讀；generated PNG/SVG 可以重建，但 renderer 不得改寫 capsule 內既有的 section metadata 或其他 receipt 綁定檔。

禁止 Stage -1 使用 shell `git clone`、`curl`、`wget`、raw GitHub HTTP，禁止逐 blob 搬完整 repository，也禁止 workspace 失敗後人工直接寫新聞。

若 Stage -1 無法完成，最早 blocker 固定回報為：

`repository materialization / executable workspace acquisition`

此時不得產生 checkpoint、manifest、release receipt 或假讀者版。

## 必讀 runtime 契約

Stage -1 完成後，至少讀取並遵守：

- `.agents/skills/daily-news-brief/SKILL.md`
- `news-brief-settings.md`
- `news-brief-template.md`
- `user-preferences.example.yaml` 或本輪明確偏好
- `news-source-pool.json`
- `schemas/news-event-manifest.schema.json`
- `schemas/news-candidate-audit.schema.json`
- `scripts/news_run_checkpoint.py`
- `scripts/preprocess_news_candidates.py`
- `scripts/validate_selection_freshness.py`
- `scripts/manage_candidate_audit.py`
- `scripts/recover_news_run.py`
- `scripts/validate_map_decisions.py`
- `scripts/validate_news_brief.py`
- `scripts/check_unique_delivery_gate.py`
- `scripts/publish_news_brief.py`
- select / audit / verify / maps / charts / images / recovery skills 與其 references。

只有格式或示例需求時才讀 `news-brief-examples.md`，不得用 examples 取代正式 schema/settings。

## 本輪唯一 checkpoint

以實際執行時間計算精確 24 小時窗後，建立唯一 `<run-id>`，並初始化唯一 checkpoint：

```bash
python3 scripts/news_run_checkpoint.py init \
  --output <checkpoint> \
  --run-id <run-id> \
  --window-start <window-start> \
  --window-end <window-end> \
  --bootstrap-receipt <workspace>/bootstrap-workspace.json
```

所有 pre-manifest 狀態都必須沿用同一份 checkpoint；不得失敗後另開 checkpoint 來抹掉前一輪證據。

## 固定 pipeline

依序執行，不得跳關：

1. `source-scan`
   - 必須先調用 `acquire-news-candidates`，依 `news-source-pool.json` 掃描每板塊5站、合計15個主要來源並產生 `work/source-candidates.json`。
   - Windows shell 來源擷取必須直接執行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/fetch_source_routes.ps1 -RouteConfig source-route-config.json -OutputDir <run-work-dir>`；此腳本使用 `.NET HttpClient` 保存逐站原始 bytes、SHA-256 與 `source-route-coverage.json`。不得先用會被本機 ExecutionPolicy 阻擋的直接 `.ps1` 呼叫，也不得改用 `Invoke-WebRequest`、`Invoke-RestMethod` 或 Node `fetch` 重試同一批路由。
   - `source-route-config.json` 是15站 primary acquisition route 的唯一設定來源；時間邊界仍須按同站入口翻頁或取得同站 boundary witness，不得把 route probe 直接冒充完成的 source scan。
   - route fetch 完成後必須執行 `scripts/materialize_source_scans.py --checkpoint <checkpoint> --source-pool news-source-pool.json --route-coverage <route-coverage> --output-dir <source-scans-dir> --coverage-output <source-coverage.json>`；只有此 canonical materializer 產生的逐站 scans、terminal proof、完整 ranked_items 與六項分數可進入 candidate audit。不得改用 run 目錄內的臨時 helper。
   - materializer 完成後只執行一次 `scripts/validate_source_scan_evidence.py --scan-dir <source-scans-dir> --coverage <source-coverage.json> --source news-source-pool.json`；canonical validator 會以 UTF-8 自行讀取 aggregate coverage/source pool 並驗證其中全部15站。不得用 PowerShell `Get-Content`／`ConvertFrom-Json` 編排來源清單，不得另寫拆分 helper。
   - 每個站內海選條目必須保存 `public_value_v1` 六項 `importance_breakdown`、總分與理由；六項總和必須等於 `importance_score`，並隨十四天候選稽核保存。
   - 直接 API／RSS／HTML 失敗時先切同站替代入口；只有目前工具契約明確允許時才可用完整瀏覽器渲染並保存 DOM。瀏覽器不得是完成排程的必要依賴，不得用別站冒充該站本輪掃描完成。
2. `preprocess-news-candidates`
3. `select-news-events`
   - 事件與候選映射只能由本輪 `source-candidates.json`／`preprocessed-candidates.json` 建立；不得匯入或執行舊 `work/validation-run-*` 的 selection driver、事件常數或 URL 映射，也不得要求本輪保留已無 fresh URL 的歷史事件編號。
   - 產生 `selection-results.json` 後，必須先執行 `scripts/validate_selection_freshness.py --selection <selection-results> --source-candidates <source-candidates>`。此 gate 必須確認每個事件 URL 都在本輪 fresh pool、所有 C 級以上候選都有有效 `selected_event_id`，且映射事件實際存在；首次失敗即停止，不能刪單筆後重跑掩蓋。
4. `audit-news-candidates`
   - 十四天稽核必須保留完整海選清單及每筆六項大分數；本輪所有 C 級以上候選（含合併項）都必須以 `selected_event_id` 對應到 manifest 與讀者版，不得無聲消失。
5. `materialize-manifest`
6. `verify-news-events`
   - 此階段只能用 `scripts/validate_news_brief.py stage --stage verify-news-events --before <before-manifest> --after <after-manifest>` 檢查欄位所有權；不得在此時執行 final-manifest validator，因地圖、圖表與圖片欄位尚未完成。
7. `build-news-maps`
   - 必須以 Stage -1 已解析、確認含 Pillow 的 bundled Python 執行 `scripts/render_base_maps.py`；不得回退到 PATH Python、不得安裝 matplotlib。執行前後都必須重驗 bootstrap integrity，若任何 receipt 綁定檔改變，該 stage 不得完成。
8. `build-news-charts`
9. `collect-news-images`
   - 只有 checkpoint 的 `collect-news-images` completed 後，才可第一次執行 `scripts/validate_news_brief.py manifest --input <final-manifest>`；final-manifest validator 不得提前到 verify、map 或 chart 階段。
10. `render`
   - `images.status=omitted` 的事件必須在讀者版顯示非技術性的「圖片說明」，內容精確等於 manifest 的 `images.reader_omission_note`。
11. validators / unique delivery gate
12. canonical publisher release
13. canonical receipt delivery

### Checkpoint 防跳關標準

每個 pipeline stage 開始前，必須先以 `news_run_checkpoint.py mark --status running` 記錄；只有前一階段已是 `completed` 才能開始下一階段。完成時必須再次執行 `mark --status completed`，並綁定下列階段產物。不得直接把 `pending` 改成 `completed`，不得使用空 evidence，也不得以無關檔案名稱代替必要產物。

| Stage | completed 必要 artifact 名稱 |
|---|---|
| `source-scan` | `source_candidates` |
| `preprocess-news-candidates` | `preprocessed_candidates` |
| `select-news-events` | `selection_results` |
| `audit-news-candidates` | `candidate_audit` |
| `materialize-manifest` | `manifest` |
| `verify-news-events` | `manifest` |
| `build-news-maps` | `manifest` |
| `build-news-charts` | `manifest` |
| `collect-news-images` | `manifest` |
| `render` | `brief`, `manifest`（最終 bytes） |

`news_run_checkpoint.py validate` 與 canonical publisher 都必須拒絕順序不合法、未經 `running`、缺少必要 artifact、artifact binding 格式無效或 evidence 狀態不一致的 checkpoint。

來源掃描必須保存站點、快照／證據、SHA-256、時間邊界、翻頁與停止理由。403、登入牆、timeout、解析失敗或單一來源異常不得假裝成功，也不得因此直接整輪放棄；按 skills/settings 做局部恢復與替代來源處理。

Manifest 建立以前，候選與選稿必須有 candidate audit；manifest 建立後，事件內容只能由 manifest 驅動，不得直接從搜尋結果或模型記憶補事件。

每個已選事件都必須經 verify、map decision、chart decision、image decision。地圖、圖表與圖片互相獨立，不能互相替代。capsule 不搬運可重建的 generated basemap PNG/SVG；需要時由 workspace 內 canonical map source/style 與 renderer 重建。

## 恢復

Manifest 前發生中斷或 stage failure：

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>
```

只從最早未完成 pre-manifest stage 繼續，不清除已完成且 artifact binding 仍有效的 stage。

Manifest 後發生事件級失敗：

```bash
python3 scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

只重跑失敗事件／stage 與必要後續依賴。不得對 `recover_news_run.py` 虛構不存在的 `--checkpoint` 參數。

一般來源、圖片、地圖、圖表、格式與 validator failure 都應先局部恢復；只有無法排除的硬性 execution blocker 才可停止整輪。

## 唯一發布閘門

DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py

Repository 內只有 canonical publisher 可以建立 reader-facing release。其他 script、模型回答、草稿、舊 release、manifest 或中間 renderer stdout 都不是正式交付。

發布前必須：

- 所有 checkpoint required stages = completed；
- candidate audit 與 source-scan 證據有效；
- manifest/schema 有效；
- map decisions、reader brief 與附件 validators 通過；
- unique delivery gate 通過；
- publisher 建立 `release-receipt.json`；
- 交付當下 publisher 再次 revalidate bootstrap binding、checkpoint、manifest、audit、source pool、brief、attachments 與 map decisions。

最後正式輸出只能由以下命令的 stdout 直接交付，不得在 stdout 前後自行添加文字，也不得重新讀取 release 後轉貼：

```bash
python3 scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>
```

若此命令失敗或 stdout 為空，回到對應 recovery stage；不得改用手工摘要或舊 release 冒充成功。

## 成功與失敗的判定

只有 canonical delivery command 成功輸出 reader bytes，才算本輪每日新聞成功。

下列都不算成功：

- 只完成搜尋或整理；
- 只建立 manifest；
- 只完成 render；
- 只建立 release receipt；
- pipeline 未跑但模型直接寫出看似完整的新聞簡報。

若停止，必須回報**最早不可恢復 blocker**及已完成到哪個 stage，不得把後續未執行階段誤報成故障來源。
