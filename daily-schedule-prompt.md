# 每日新聞排程執行契約

+## Same-source recovery order

`SAME_SOURCE_RECOVERY_ORDER`

The required order for every configured source is: `canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot`.

- Run `scripts/recover_same_source_leads.py` for a verified coverage lead; never inject a search result directly into selection.
- `browser is the final fallback only`. It is permitted only after the direct article fetch and all configured same-site non-browser alternatives have failed and those failures were logged.
- A browser DOM snapshot must pass the same same-source host, SHA-256, publication-window, evidence, coverage, and candidate validators as direct evidence.
- Recovery applies to all configured sources. It updates only the affected source scan and coverage record; it must not restart already verified sources.


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

GitHub connector 可見 repository 不代表 shell 已有 repository。每輪都必須重新解析當下最新版 `main`，再使用該輪 SHA 的 verified runtime capsule：

1. `EARLY_DIAGNOSTIC_RUN_ID`：在任何 connector、GitHub 或 shell tool call 前，立即用 `scripts/run_identity.py generate` 的同一規格產生本輪唯一 `<run-id>`，格式固定為 `gnb-YYYYMMDDThhmmssZ-xxxxxxxx`（UTC 精確到秒＋8 碼小寫十六進位隨機值），並產生 UTC started_at 與兩個 **fresh UTC nonce**；不得等 tree、manifest、loader 或 workspace，也不得沿用前次 run id／nonce。
2. connector 直接讀取 `https://api.github.com/repos/robert820728-star/global-news-brief/git/ref/heads/main?cache_bust=<nonce-a>`，取得 `object.sha`；同輪再用另一個新 nonce 讀取 `https://api.github.com/repos/robert820728-star/global-news-brief/commits/main?cache_bust=<nonce-b>`，取得 `sha`。
3. `EARLY_DIAGNOSTIC_MAIN_PINNED`：兩個端點必須回傳 same SHA。若不一致，以兩個全新 nonce 各重讀一次；第二次仍不一致就停止 Stage -1，不得猜測何者較新。The task must not enumerate repository branches, must not reuse a commit SHA、前次 workspace、排程建立時的固定 SHA 或模型記憶來決定本輪版本。
4. `EARLY_DIAGNOSTIC_RUN_STARTED`：SHA 一致後，**before any recursive tree read**，立即在 GitHub Issue #3 建立本輪唯一 run-started comment，內容只含 `run_id`、`commit`、`status=running`、`stage=bootstrap-main-pinned`、`progress=0/unknown`、`updated_at`、`last_error=null`。等待此留言呼叫回傳並在工作記憶保存 comment id 後，才可讀 tree。此步只嘗試一次；無寫入權限或呼叫失敗就記住 `external_ledger: unavailable` 並繼續，不得阻擋新聞。
5. `EARLY_DIAGNOSTIC_TREE_VERIFIED`：從固定 SHA 取得 recursive tree；只保留後續驗證所需的 path／blob SHA，不得在回答中重印 tree。成功後 **update the same comment** 為 `stage=bootstrap-tree-verified`。
6. `EARLY_DIAGNOSTIC_MANIFEST_VERIFIED`：從固定 SHA 取得並驗證 `bootstrap/capsule-manifest.json`；成功後 update the same comment 為 `stage=bootstrap-manifest-verified` 與 `progress=0/<chunks_total>`。
7. `EARLY_DIAGNOSTIC_HELPERS_VERIFIED`：從固定 SHA 取得並驗證 `bootstrap/bootstrap_loader.py`、`bootstrap/bootstrap_progress.py`、`bootstrap/bootstrap-progress.schema.json`；成功後 update the same comment 為 `stage=bootstrap-helpers-verified`。
8. 立即建立獨立的 `bootstrap-progress.json`，它是 Stage -1 診斷紀錄，不是 news checkpoint；將早期 external-ledger available／unavailable 狀態與 comment id 匯入本地紀錄。
9. 手機低壓力正常路徑一次讀取相鄰兩個既有 block 的 **16-line** 範圍，再由 progress helper 切開並分別核對兩個原始 block 的 size/SHA-256。任一半失敗才退回原本 8-line 逐 block 讀取，不得放寬驗證，也不得重新下載先前已驗證 chunks。
10. 每個固定 SHA、固定 line range 使用 **one initial attempt plus at most three retries**；允許時依序退避 **2, 5, and 10 seconds**。每次記錄 byte size、SHA-256 與錯誤；第 4 次仍失敗才停止。
11. 將 manifest／loader／progress helper／chunks 精確寫入 writable staging directory；每個 chunk 完整通過後才原子更新一次進度。
12. 由 loader 在 shell 本地解碼、驗 SHA、解壓並建立 executable workspace；
13. loader 成功產生 `bootstrap-workspace.json` 後，才可建立 news checkpoint。下一輪必須重新執行上述解析，不得直接重用本輪 SHA。

Stage -1 loader 可用宿主的 `python3` 執行，因 loader 與 resolver 只依賴標準庫；它不得直接成為新聞 pipeline runtime。Workspace 建立後，若宿主提供的 bundled-runtime Python 絕對路徑可取得，必須優先傳入 `python3 scripts/resolve_bundled_python.py --preferred-python <host-bundled-python>`；否則執行 `python3 scripts/resolve_bundled_python.py`，由 resolver 依環境變數及跨平台 Codex runtime 位置尋找。Resolver 回傳 `status=ready` 前必須實際以候選 executable 匯入 Pillow；以它回傳的同一個 `<bundled-python>` 執行 checkpoint、route fetcher 與本輪所有 canonical Python scripts。不得直接假設 PATH 上的 `python`／`python3` 具有 Pillow，不得把啟動 resolver 的 Python 當成已驗證 runtime；所有候選皆失敗才回報 Stage -1 blocker。Materialized runtime 的 receipt 綁定檔視為唯讀；generated PNG/SVG 可以重建，但 renderer 不得改寫 capsule 內既有的 section metadata 或其他 receipt 綁定檔。

禁止 Stage -1 使用 shell `git clone`、`curl`、`wget`、raw GitHub HTTP，禁止逐 blob 搬完整 repository，也禁止 workspace 失敗後人工直接寫新聞。

若 Stage -1 無法完成，最早 blocker 固定回報為：

`repository materialization / executable workspace acquisition`

此時不得產生 checkpoint、manifest、release receipt 或假讀者版。

所有可控制的成功或失敗結束都必須由 `bootstrap/bootstrap_progress.py` 輸出固定 `RUN_RECEIPT`，至少包含 run id、main SHA、最後完成 stage、chunk／block、last error、retry count、external ledger 與 canonical delivery。GitHub 外部台帳沒有寫入權限或更新失敗時，必須顯示 `external_ledger: unavailable`，但不得因此中止新聞流程。失敗時保留完整本地進度；只有正式讀者版 canonical delivery 成功、最終 receipt 已輸出後才清除本地進度。

若具 GitHub 留言權限，依 `bootstrap/RUN_LEDGER_PROTOCOL.md` 將 issue #3 作為 **best-effort** 外部台帳：每輪使用 **one comment per run_id**，manifest/helper 驗證後更新、之後 **every 8 completed chunks**、全部 chunks、workspace、新聞 stages、失敗與成功時更新同一則 comment。一般新聞階段 **at most once every 3 minutes**，失敗與最終成功立即更新。任何台帳錯誤都改記 `external_ledger: unavailable`，且 **must never block the news pipeline**。

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
<bundled-python> scripts/news_run_checkpoint.py init \
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
   - 來源擷取必須以 Stage -1 回傳的 `<bundled-python> scripts/fetch_source_routes.py --route-config source-route-config.json --output-dir <run-work-dir>` 執行；此跨平台 canonical fetcher 保存逐站原始 bytes、SHA-256 與 `source-route-coverage.json`。不得改用 PowerShell web cmdlet、Node `fetch` 或臨時 helper 重試同一批路由。
   - `source-route-config.json` 是15站 primary acquisition route 的唯一設定來源；時間邊界仍須按同站入口翻頁或取得同站 boundary witness，不得把 route probe 直接冒充完成的 source scan。
   - route fetch 完成後必須執行 `scripts/materialize_source_scans.py --checkpoint <checkpoint> --source-pool news-source-pool.json --route-coverage <route-coverage> --output-dir <source-scans-dir> --coverage-output <source-coverage.json>`；只有此 canonical materializer 產生的逐站 scans、terminal proof、完整 ranked_items 與六項分數可進入 candidate audit。不得改用 run 目錄內的臨時 helper。
   - materializer 完成後只執行一次 `scripts/validate_source_scan_evidence.py --scan-dir <source-scans-dir> --coverage <source-coverage.json> --source news-source-pool.json`；canonical validator 會以 UTF-8 自行讀取 aggregate coverage/source pool 並驗證其中全部15站。不得用 PowerShell `Get-Content`／`ConvertFrom-Json` 編排來源清單，不得另寫拆分 helper。
   - 每個站內海選條目必須保存 `public_value_v1` 六項 `importance_breakdown`、總分與理由；六項總和必須等於 `importance_score`，並隨十四天候選稽核保存。
   - 直接 API／RSS／HTML 失敗時先切同站替代入口；只有目前工具契約明確允許時才可用完整瀏覽器渲染並保存 DOM。瀏覽器不得是完成排程的必要依賴，不得用別站冒充該站本輪掃描完成。
   - `TAIWAN_DOMESTIC_COVERAGE_GUARD`：台灣五站 materialize 後，依 `news-source-pool.json.taiwan_coverage_sweeps` 對經濟產業、食藥消費安全、中央政策制度各做一次最多 `5 results` 的 24 小時補漏搜尋。只接受五站本身網域；命中時必須 `same-source recovery` 回填所屬 source scan、重新 materialize 與驗證，再進 `canonical candidate audit`。不得把搜尋結果直接塞入 selection、不得新增圖片工作，除非該事件完成評級後真正入選。
2. `preprocess-news-candidates`
3. `select-news-events`
   - 事件與候選映射只能由本輪 `source-candidates.json`／`preprocessed-candidates.json` 建立；不得匯入或執行舊 `work/validation-run-*` 的 selection driver、事件常數或 URL 映射，也不得要求本輪保留已無 fresh URL 的歷史事件編號。
   - 產生 `selection-results.json` 後，必須先執行 `scripts/validate_selection_freshness.py --selection <selection-results> --source-candidates <source-candidates>`。此 gate 必須確認每個事件 URL 都在本輪 fresh pool、所有 C 級以上候選都有有效 `selected_event_id`，且映射事件實際存在；首次失敗即停止，不能刪單筆後重跑掩蓋。
4. `audit-news-candidates`
   - 十四天稽核必須保留完整海選清單及每筆六項大分數；本輪所有 C 級以上候選（含合併項）都必須以 `selected_event_id` 對應到 manifest 與讀者版，不得無聲消失。
   - 最新一輪每個候選必須完成 `local_disaster_review`。普通地方災害以未滿 50 人低於 C、50–99 人 C、100–249 人 B、250 人以上 A- 為基準；上調必須保存特殊意義與理由。軍事／衝突事件必須沿用既有邊境及長期戰爭規則，不得改套地方事故門檻。
5. `materialize-manifest`
   - 完成條件是將本輪 audit 選中事件一對一物化並綁定 checkpoint 的 `manifest` artifact；此處不需要執行 final-manifest validator。
6. `verify-news-events`
   - 此階段只能用 `scripts/validate_news_brief.py stage --stage verify-news-events --before <before-manifest> --after <after-manifest>` 檢查欄位所有權；不得在此時執行 final-manifest validator，因地圖、圖表與圖片欄位尚未完成。
7. `build-news-maps`
   - 必須以 Stage -1 已解析、確認含 Pillow 的 bundled Python 執行 `scripts/render_base_maps.py`；不得回退到 PATH Python、不得安裝 matplotlib。執行前後都必須重驗 bootstrap integrity，若任何 receipt 綁定檔改變，該 stage 不得完成。
   - 先執行一次無參數 renderer，確認三個 canonical 底圖 `taiwan-counties-yellow-v2.png`、`china-provinces-yellow-v2.png`、`world-countries-pacific-robinson-yellow-v2.png` 都由本輪 workspace 產生。每個 `map.required=true` 事件再建立 overlay JSON，依行政區精確鍵值著色並提供繁中 `label`，以 `<bundled-python> scripts/render_base_maps.py --overlay-spec <file>` 產生事件圖；不得直接引用 workspace 外殘留的舊 PNG。
8. `build-news-charts`
9. `collect-news-images`
   - 只有 checkpoint 的 `collect-news-images` completed 後，才可第一次執行 `scripts/validate_news_brief.py manifest --input <final-manifest>`；final-manifest validator 不得提前到 verify、map 或 chart 階段。
   - 若執行者誤在圖片階段完成前呼叫該命令，script 會輸出 `DEFERRED` 並以成功狀態返回；這不是 validator 通過，也不得標記整輪失敗。立即繼續原定 pipeline，並在 `collect-news-images` completed 後重新執行到真正輸出 `OK`。
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
<bundled-python> scripts/news_run_checkpoint.py plan --input <checkpoint>
```

只從最早未完成 pre-manifest stage 繼續，不清除已完成且 artifact binding 仍有效的 stage。

Manifest 後發生事件級失敗：

```bash
<bundled-python> scripts/recover_news_run.py plan --input <manifest> --brief <brief>
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
<bundled-python> scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>
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
