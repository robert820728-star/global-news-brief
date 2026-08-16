# 版本紀錄 / Version Record

## v0.2.1-mobile-image-stability — 2026-08-17

- 建立原因 / Reason: 手機排程內嵌原始新聞圖片時常因解析度與檔案過大而載入失敗。 / Original news images embedded by the mobile task were often too large to load reliably.
- 實作方式 / Approach: 保留每則新聞原本選圖，優先使用發布者提供的同圖小尺寸版本；可實際轉檔時才縮小，否則允許同一張原圖；原圖不適合公開內嵌時只顯示圖片說明，不以圖片網址或原網站連結代替。 / Preserve the selected image, prefer its publisher-provided small variant, resize when conversion is genuinely available, otherwise allow the same original image; when it cannot be embedded, show only an image explanation rather than an image URL or source-page substitute.
- 變更入口 / Changed entry points: `mobile-chatgpt-daily-prompt.md`, `mobile-chatgpt-start-prompt.md`, `README.md`.
- 重要設定 / Important configuration: 每則最多一張；優先最長邊 `640px`、JPEG/WebP 品質 `75–82`、目標 `200KB` 以下；做不到時允許同一張原圖；不得換圖。 / At most one image per item; prefer a `640px` longest edge, JPEG/WebP quality `75–82`, and a target below `200KB`; allow the same original when unavailable; never substitute another image.
- 驗證方式 / Validation: RED→GREEN 手機圖片契約、完整 pipeline contract、GitHub 遠端 blob 一致性。 / Red-green mobile image contract, full pipeline contract, and GitHub remote blob verification.
- 結果 / Result: 手機圖片契約與完整 pipeline contract 共 4/4 通過；規則未改動十四天、六項評分或 C 級以上讀者版門檻。 / The mobile image and complete pipeline contracts pass 4/4; the fourteen-day, six-score, and C-or-higher reader thresholds remain unchanged.
- 下一決定 / Next decision: 使用者若特別需要某張高解析圖片，再於對話中個別提供該張原尺寸圖片。 / If the user wants a particular image in high resolution, provide that original-size image individually in the conversation.

## v0.2.0-mobile-basic — 2026-08-17

- 建立原因 / Reason: 支援使用者直接在手機一般 ChatGPT 對話建立每日排程，並降低日常模型消耗。 / Support creating the daily schedule from a normal mobile ChatGPT conversation while reducing routine model usage.
- 實作方式 / Approach: 新增獨立的手機起始指令與基礎每日規則，使用 Instant 並移除本機執行、地圖、圖表與發布器依賴。 / Added separate mobile setup and basic daily prompts using Instant without local execution, maps, charts, or publisher dependencies.
- 變更入口 / Changed entry points: `mobile-chatgpt-start-prompt.md`, `mobile-chatgpt-daily-prompt.md`, `README.md`.
- 重要設定 / Important configuration: 每天 `Asia/Taipei` 06:00；保留十四天海選、六項大評分、所有 C 級以上讀者版及無圖說明。 / Daily at 06:00 Asia/Taipei; preserves the fourteen-day candidate list, six scores, all C-or-higher reader items, and no-image explanations.
- 驗證方式 / Validation: RED→GREEN mobile contract test, full pipeline contract test, and remote Git tree verification. / Red-green mobile contract test, full pipeline contract test, and remote Git tree verification.
- 結果 / Result: 手機 contract 與既有 pipeline contract 共 3/3 通過，直接發布目標為 GitHub `main`。 / The mobile and existing pipeline contracts pass 3/3; the direct publication target is GitHub `main`.
- 下一決定 / Next decision: 從手機 ChatGPT 貼上起始指令，建立排程後立即執行一次。 / Paste the setup prompt in mobile ChatGPT, create the schedule, and run it once immediately.

## v0.1.0-child — 2026-08-16

- 建立原因 / Reason: 強制十四天清單包含完整海選與六項大分數，並保證本輪 C 級以上事件全部進入讀者版；無圖事件提供讀者說明。 / Enforce complete shortlist scoring, current-run C-or-above reader coverage, and reader explanations for omitted images.
- 實作方式 / Approach: 在子候選版本以 TDD 修改 audit schema、audit validator、manifest schema、brief validator、canonical publisher 及相關契約。 / Implemented in an isolated child candidate with TDD across schemas, validators, publisher, and contracts.
- 變更入口 / Changed entry points: `manage_candidate_audit.py validate`, `validate_news_brief.py manifest/brief`, `publish_news_brief.py`, `daily-schedule-prompt.md`.
- 重要設定 / Important configuration: `public_value_v1` 六項權重維持 30/20/15/15/10/10；C 級以上門檻不變；十四天保存期不變。 / Six score weights remain 30/20/15/15/10/10; C threshold and 14-day retention are unchanged.
- 驗證方式 / Validation: 5 個新增 RED→GREEN 測試、完整 unittest 回歸、runtime capsule 驗證、五分鐘後本地排程實跑。 / Five new red-green tests, full unittest regression, runtime capsule verification, and a local scheduled run after five minutes.
- 目前結果 / Current result: 新增測試 5/5 通過；完整回歸發現 2 個既有 Windows 測試夾具問題，另需重建 capsule。 / New tests pass 5/5; full regression exposed two pre-existing Windows fixture failures and requires a capsule rebuild.
- 下一決定 / Next decision: 重建本地候選 capsule、完成實跑驗收；通過後提升至主線候選。 / Rebuild the local candidate capsule, run scheduled acceptance, and promote after passing.

## v0.1.1-child — 2026-08-16

- 建立原因 / Reason: 第 1 輪排程在 `source-scan` 因 shell TLS／舊版網頁命令與瀏覽器逾時而停止。 / Round 1 stopped at `source-scan` because of shell TLS/legacy web-command failures and a browser timeout.
- 回復來源 / Rollback source: `43aa951`（v0.1.0 最終 capsule）。 / `43aa951` (the final v0.1.0 capsule).
- 實作方式 / Approach: 新增以 `.NET HttpClient` 執行的 canonical route fetcher，將15站 primary route 集中於 `source-route-config.json`，保存原始 bytes、SHA-256 與 route coverage。 / Added a canonical `.NET HttpClient` route fetcher and centralized all 15 primary routes in `source-route-config.json`, preserving raw bytes, SHA-256, and route coverage.
- 變更入口 / Changed entry points: `scripts/fetch_source_routes.ps1`, `source-route-config.json`, `daily-schedule-prompt.md`.
- 重要設定 / Important configuration: 中國新聞網使用執行日前一日的捲動頁；路由探測不取代24小時邊界證據。 / China News uses the prior-day scroll page; a route probe does not replace 24-hour boundary evidence.
- 驗證方式 / Validation: 本機 HTTP RED→GREEN 整合測試 3 項；15站 live route probe；完整 unittest；capsule rebuild/verify；修改後五分鐘排程實跑。 / Three local HTTP red-green integration tests; 15-source live route probe; full unittest; capsule rebuild/verify; scheduled live run five minutes after modification.
- 目前結果 / Current result: 路由整合測試 3/3、live probe 15/15 通過；完整回歸 92/93，唯一失敗為待重建 capsule。 / Route integration tests pass 3/3 and the live probe passes 15/15; full regression is 92/93 with only the pending capsule rebuild failing.
- 下一決定 / Next decision: 依本 commit 重建 capsule，五分鐘後執行第 2 輪完整排程驗收。 / Rebuild the capsule from this commit, then run Round 2 scheduled acceptance after five minutes.

## v0.1.2-child — 2026-08-16

- 建立原因 / Reason: 第 2 輪已完成15站 route fetch，但 runtime 缺少把 snapshots 轉成可稽核 source scans、邊界證據與完整 ranked items 的正式程式。 / Round 2 fetched all 15 routes, but the runtime lacked a canonical materializer for auditable source scans, boundary evidence, and complete ranked items.
- 回復來源 / Rollback source: `bc00015`（v0.1.1 route fetcher capsule）。 / `bc00015` (the v0.1.1 route-fetcher capsule).
- 實作方式 / Approach: 新增 `scripts/materialize_source_scans.py`，從原始快照重算逐站24小時條目、terminal proof、public_value_v1 六項分數及 source coverage。 / Added `scripts/materialize_source_scans.py` to recompute per-source 24-hour items, terminal proof, six public_value_v1 scores, and source coverage from raw snapshots.
- 變更入口 / Changed entry points: `scripts/materialize_source_scans.py`, `daily-schedule-prompt.md`.
- 重要設定 / Important configuration: 每站 ranked_items 保存完整24小時海選；每項六分數總和精確等於 importance_score；route probe 不直接視為 source scan。 / Each source retains the full 24-hour shortlist; six scores sum exactly to importance_score; a route probe is not treated as a source scan.
- 驗證方式 / Validation: 2 個 RED→GREEN materializer 測試；重用第2輪15站 snapshots 的 live materialization；逐站 evidence validator；完整 unittest；capsule rebuild/verify；五分鐘後第3輪排程。 / Two materializer red-green tests; live materialization from Round 2's 15 snapshots; per-source evidence validation; full unittest; capsule rebuild/verify; Round 3 scheduling after five minutes.
- 目前結果 / Current result: live 15/15 source scans、388 筆 ranked items、六項分數完整，evidence validator 0 errors；完整回歸 94/95，唯一失敗為待重建 capsule。 / Live materialization produced 15/15 source scans and 388 ranked items with complete six-part scores and zero evidence errors; regression is 94/95 with only the pending capsule rebuild failing.
- 下一決定 / Next decision: 重建 capsule，五分鐘後執行第3輪完整下游驗收。 / Rebuild the capsule and run Round 3 end-to-end downstream acceptance after five minutes.

- 追加修正 / Follow-up fix: 排程前 live coverage 發現 TVBS、新華與半島三站為0筆；改為解析 TVBS 首頁序列化 article props、新華世界頁 URL 日期、半島當日 sitemap，並修正中國新聞網 `M-D HH:MM` 時間。 / A pre-schedule live check found zero items for TVBS, Xinhua, and Al Jazeera; the fix parses TVBS serialized article props, Xinhua World URL dates, the Al Jazeera daily sitemap, and China News `M-D HH:MM` timestamps.
- 追加驗證 / Follow-up validation: 15/15 來源皆有候選，共451筆 ranked items；六項分數完整，逐站 evidence validator 0 errors。 / All 15 sources now contain candidates, totaling 451 ranked items; six-part scores are complete and per-source evidence validation reports zero errors.

## v0.1.3-child — 2026-08-16

- 建立原因 / Reason: 第3輪 source-scan 已完成488筆，但 canonical preprocessor 只讀 `candidates`，而正式 source list 使用 `items`，導致輸出0筆。 / Round 3 completed 488 source items, but the canonical preprocessor read only `candidates` while the source list uses `items`, producing zero output.
- 回復來源 / Rollback source: `c1cf849`（完整15站 source capsule）。 / `c1cf849` (the complete 15-source capsule).
- 實作方式 / Approach: preprocessor 優先讀取正式 `items`，並保留舊 `candidates` 相容性；非陣列輸入明確失敗。 / The preprocessor now prefers canonical `items`, retains legacy `candidates` compatibility, and explicitly rejects non-array input.
- 變更入口 / Changed entry points: `scripts/preprocess_news_candidates.py`.
- 驗證方式 / Validation: 2個 RED→GREEN schema tests；重放第3輪正式 source list；完整 unittest；capsule rebuild/verify；五分鐘後第4輪排程。 / Two schema red-green tests; replay of the Round 3 canonical source list; full unittest; capsule rebuild/verify; Round 4 scheduled after five minutes.
- 目前結果 / Current result: 488/488 candidates、480 clusters、0筆遺失。 / 488/488 candidates, 480 clusters, zero dropped items.
- 下一決定 / Next decision: 重建 capsule 並重跑完整下游驗收。 / Rebuild the capsule and rerun full downstream acceptance.

## v0.1.4-child — 2026-08-16

- 建立原因 / Reason: 第4輪已通過 verify，但 canonical map renderer 依賴未安裝的 matplotlib，停在 `build-news-maps`。 / Round 4 passed verification but stopped at `build-news-maps` because the canonical renderer depended on unavailable matplotlib.
- 回復來源 / Rollback source: `d46eba5`（preprocessor 修正版 capsule）。 / `d46eba5` (the fixed-preprocessor capsule).
- 實作方式 / Approach: 以 verified runtime 已有的 Pillow 重寫同一 canonical renderer，維持 GeoJSON、投影、style、PNG/SVG 與 metadata 契約。 / Reimplemented the same canonical renderer with Pillow already present in the verified runtime, preserving GeoJSON, projections, styles, PNG/SVG, and metadata contracts.
- 變更入口 / Changed entry points: `scripts/render_base_maps.py`.
- 驗證方式 / Validation: matplotlib 缺失 RED；Pillow fixture GREEN；台灣／中國／世界三份正式 GeoJSON live render；完整 unittest；capsule rebuild/verify；五分鐘後第5輪排程。 / Missing-matplotlib red test; Pillow fixture green test; live rendering of the Taiwan, China, and world GeoJSON maps; full unittest; capsule rebuild/verify; Round 5 after five minutes.
- 目前結果 / Current result: 三組 PNG/SVG 均成功產生；世界圖 1800×1044，無 matplotlib import。 / All three PNG/SVG pairs render successfully; the world map is 1800×1044 with no matplotlib import.
- 下一決定 / Next decision: 重建 capsule 並從新 run 驗收 maps 以後的流程。 / Rebuild the capsule and validate the post-map pipeline in a new run.

## v0.1.5-child — 2026-08-16

- 建立原因 / Reason: 第5輪內容、地圖、圖片與讀者版已通過，但發現 capsule 缺少 route config、audit 首次輸出不建父目錄、renderer 改寫 receipt 綁定 metadata，以及 CRLF 分隔線在 publisher 中被誤判。 / Round 5 passed content, maps, images, and reader validation, but exposed a missing route config in the capsule, missing parent-directory creation for first audit output, renderer mutation of receipt-bound metadata, and CRLF separator miscounting in the publisher.
- 回復來源 / Rollback source: `6af66e5`（v0.1.4 Pillow renderer capsule）。 / `6af66e5` (the v0.1.4 Pillow-renderer capsule).
- 實作方式 / Approach: 將 route config 納入 runtime closure；audit append 自建父目錄；renderer 將 section metadata 視為唯讀；brief validator 同時接受 LF／CRLF 分隔線；排程固定使用 workspace bundled Python。 / Added the route config to the runtime closure, made audit append create its parent directory, made section metadata read-only to the renderer, accepted both LF and CRLF separators, and pinned scheduled execution to the workspace bundled Python.
- 變更入口 / Changed entry points: `scripts/build_bootstrap_capsule.py`, `scripts/manage_candidate_audit.py`, `scripts/render_base_maps.py`, `scripts/validate_news_brief.py`, `daily-schedule-prompt.md`.
- 驗證方式 / Validation: 4個針對第5輪 blocker 的 RED→GREEN 測試、完整 unittest、capsule rebuild/verify、修改後五分鐘第6輪排程。 / Four red-green tests for the Round 5 blockers, full unittest, capsule rebuild/verify, and Round 6 scheduled five minutes after modification.
- 目前結果 / Current result: 4/4 blocker regression tests、105/105 完整回歸與 capsule verify 全部通過；runtime closure 為53檔，fingerprint `1bd201e80c549e81f25303fcd9cad262a116428ffa81b3ad157e97c12e653719`。 / All 4 blocker regressions, the full 105/105 suite, and capsule verification pass; the runtime closure contains 53 files with fingerprint `1bd201e80c549e81f25303fcd9cad262a116428ffa81b3ad157e97c12e653719`.
- 下一決定 / Next decision: 修改後五分鐘以全新 run 執行第6輪 canonical publisher 驗收。 / Run Round 6 canonical publisher acceptance from a fresh run five minutes after the modification.

## v0.1.6-child — 2026-08-16

- 建立原因 / Reason: 第6輪已正式發布，但首次操作仍遇到 ExecutionPolicy、aggregate validator 輸入與早期 manifest checkpoint binding 三個可恢復警告。 / Round 6 published successfully but still encountered three recoverable first-attempt warnings involving ExecutionPolicy, aggregate validator inputs, and an early manifest checkpoint binding.
- 回復來源 / Rollback source: `b512af4`（第6輪已驗證 capsule）。 / `b512af4` (the Round 6 verified capsule).
- 實作方式 / Approach: 固定 PowerShell bypass 啟動方式；validator 直接從 aggregate coverage/source pool 解析來源；render 階段強制綁定最終 brief 與 manifest，publisher 僅驗最終 binding。 / Pinned the PowerShell bypass invocation, made the validator resolve sources from aggregate coverage/source pool files, and required render to bind the final brief and manifest so the publisher checks only the final binding.
- 變更入口 / Changed entry points: `scripts/validate_source_scan_evidence.py`, `scripts/news_run_checkpoint.py`, `scripts/publish_news_brief.py`, `daily-schedule-prompt.md`.
- 驗證方式 / Validation: 3個 RED→GREEN 零恢復測試、完整 unittest、capsule rebuild/verify、修改後五分鐘第7輪排程。 / Three red-green zero-recovery tests, full unittest, capsule rebuild/verify, and Round 7 scheduled five minutes after modification.
- 目前結果 / Current result: 3/3 零恢復測試、108/108 完整回歸與 capsule verify 全部通過；fingerprint `891b2dbb7a151628bcf1585e0ac433f0229e5c75cdee375e092226371b3f650c`。 / All 3 zero-recovery tests, the full 108/108 suite, and capsule verification pass; fingerprint `891b2dbb7a151628bcf1585e0ac433f0229e5c75cdee375e092226371b3f650c`.
- 下一決定 / Next decision: 以全新 run 驗證 source scan、validator 與 publisher 均第一次成功。 / Verify in a fresh run that source scan, validation, and publishing all succeed on the first attempt.

## v0.1.7-child — 2026-08-16

- 建立原因 / Reason: 第7輪 canonical fetch 與 materializer 首次成功，但 PowerShell 未指定 UTF-8 解析 aggregate source pool，逐站 validator 在0/15時首敗停止。 / Round 7 passed canonical fetch and materialization on the first attempt, but PowerShell parsed the aggregate source pool without explicit UTF-8 and stopped before any of the 15 validators ran.
- 回復來源 / Rollback source: `ca97a65`（第7輪 capsule）。 / `ca97a65` (the Round 7 capsule).
- 實作方式 / Approach: 為 canonical evidence validator 新增 `--scan-dir` 批次模式，由 Python 以 UTF-8 直接讀 aggregate coverage/source pool 並依 source_id 驗證全部站點。 / Added a `--scan-dir` batch mode to the canonical evidence validator so Python directly reads aggregate coverage/source pool files as UTF-8 and validates every source by source_id.
- 變更入口 / Changed entry points: `scripts/validate_source_scan_evidence.py`, `daily-schedule-prompt.md`.
- 驗證方式 / Validation: 1個 RED→GREEN 批次 CLI 測試、完整 unittest、capsule rebuild/verify、修改後五分鐘第8輪排程。 / One red-green batch CLI test, full unittest, capsule rebuild/verify, and Round 8 scheduled five minutes after modification.
- 目前結果 / Current result: 批次 CLI 測試、109/109 完整回歸與 capsule verify 全部通過；fingerprint `9a489646356f7fdb0eb599a86e110fbd7b8f659b96011280bdd2122961742426`。 / The batch CLI test, full 109/109 suite, and capsule verification pass; fingerprint `9a489646356f7fdb0eb599a86e110fbd7b8f659b96011280bdd2122961742426`.
- 下一決定 / Next decision: 全新 run 驗證15站批次 evidence gate 與其後完整發布鏈。 / Verify the 15-source batch evidence gate and full downstream publication chain in a fresh run.

## v0.1.8-child — 2026-08-16

- 建立原因 / Reason: 第8輪在新聞流程開始前，workspace dependency locator 超過 Stage -1 的3分36秒硬停止時間。 / Round 8 hit the 3-minute-36-second Stage -1 hard stop while waiting for the workspace dependency locator, before the news pipeline began.
- 回復來源 / Rollback source: `d1fe0e1`（第8輪 capsule）。 / `d1fe0e1` (the Round 8 capsule).
- 實作方式 / Approach: 新增 canonical PowerShell resolver，從目前宿主的 Codex runtime 固定位置解析 bundled Python，並在回傳前實際匯入 Pillow；排程不得先等待 locator。 / Added a canonical PowerShell resolver that finds bundled Python at the current host's stable Codex runtime path and imports Pillow before returning; scheduled runs no longer wait for the locator first.
- 變更入口 / Changed entry points: `scripts/resolve_bundled_python.ps1`, `daily-schedule-prompt.md`.
- 重要設定 / Important configuration: resolver 首次失敗即停止 Stage -1；不得在同輪改走 locator 掩蓋失敗。 / A first resolver failure stops Stage -1; the same run must not hide it by falling back to the locator.
- 驗證方式 / Validation: 1個 Windows RED→GREEN resolver 整合測試、完整 unittest、capsule rebuild/verify、修改後五分鐘第9輪排程。 / One Windows red-green resolver integration test, full unittest, capsule rebuild/verification, and Round 9 scheduled five minutes after modification.
- 目前結果 / Current result: resolver 定向測試、110/110 完整回歸與 capsule verify 全部通過；runtime closure 為54檔，fingerprint `cce53272190fe7074b4b5fcff75d02bf75962babfcf9f5233dd6563764b7023b`。 / The targeted resolver test, full 110/110 suite, and capsule verification pass; the runtime closure contains 54 files with fingerprint `cce53272190fe7074b4b5fcff75d02bf75962babfcf9f5233dd6563764b7023b`.
- 下一決定 / Next decision: 以全新 run 驗證 resolver、15站批次 evidence gate 與完整發布鏈均第一次成功。 / Verify in a fresh run that the resolver, 15-source batch evidence gate, and full publication chain all succeed on the first attempt.

## v0.1.9-child — 2026-08-16

- 建立原因 / Reason: 第9輪通過來源、十四天稽核與 manifest materialization，但在圖片階段前誤用 final-manifest validator，22個事件皆因尚未建立 `images.source_checks` 而被拒絕。 / Round 9 passed sources, the 14-day audit, and manifest materialization, but invoked the final-manifest validator before image collection, so all 22 events were rejected because `images.source_checks` did not yet exist.
- 回復來源 / Rollback source: `3941949`（第9輪 capsule）。 / `3941949` (the Round 9 capsule).
- 實作方式 / Approach: 明確區分中間 stage ownership validation 與 final-manifest validation；verify/map/chart/image 各階段只驗欄位所有權，final-manifest validator 只能在 image collection completed 後首次執行。 / Explicitly separated intermediate stage ownership validation from final-manifest validation; verify/map/chart/image stages validate ownership only, and the final-manifest validator runs for the first time only after image collection is completed.
- 變更入口 / Changed entry points: `daily-schedule-prompt.md`, `.agents/skills/daily-news-brief/SKILL.md`.
- 驗證方式 / Validation: 1個 RED→GREEN pipeline contract 測試、完整 unittest、capsule rebuild/verify、修改後五分鐘第10輪排程。 / One red-green pipeline-contract test, full unittest, capsule rebuild/verification, and Round 10 scheduled five minutes after modification.
- 目前結果 / Current result: pipeline contract 測試、111/111 完整回歸與 capsule verify 全部通過；runtime closure 為54檔，fingerprint `026d965dd0a094be82b6bfcb8a04a500ecb91bd846aafcabc4fe70787edd45ac`。 / The pipeline contract test, full 111/111 suite, and capsule verification pass; the runtime closure contains 54 files with fingerprint `026d965dd0a094be82b6bfcb8a04a500ecb91bd846aafcabc4fe70787edd45ac`.
- 下一決定 / Next decision: 以全新 run 驗證中間 stages 不會提前呼叫 final-manifest validator，並完成圖片、讀者版與發布。 / Verify in a fresh run that intermediate stages do not invoke the final-manifest validator early, then complete images, the reader brief, and publication.

## v0.1.10-child — 2026-08-16

- 建立原因 / Reason: 第10輪通過15站與全量 preprocess，但 selection adapter 匯入舊 run 的 hard-coded event mapping，導致 `GLB-09` 沒有本輪 fresh pool URL。 / Round 10 passed all 15 sources and full preprocessing, but its selection adapter imported a hard-coded event mapping from an old run, leaving `GLB-09` without a current fresh-pool URL.
- 回復來源 / Rollback source: `ee973bf`（第10輪 capsule）。 / `ee973bf` (the Round 10 capsule).
- 實作方式 / Approach: 新增 canonical fresh-selection gate，禁止匯入舊 run driver，並檢查每個事件與候選 URL 皆屬本輪 pool、所有 C 級以上候選都有存在的 `selected_event_id`。 / Added a canonical fresh-selection gate, prohibited prior-run drivers, and verify that every event/candidate URL belongs to the current pool and every C-or-above candidate maps to an existing event.
- 變更入口 / Changed entry points: `scripts/validate_selection_freshness.py`, `daily-schedule-prompt.md`, `.agents/skills/daily-news-brief/SKILL.md`.
- 驗證方式 / Validation: 4個 RED→GREEN freshness/contract 測試、第9輪有效 selection 重放、完整 unittest、capsule rebuild/verify、修改後五分鐘第11輪排程。 / Four red-green freshness/contract tests, replay of the valid Round 9 selection, full unittest, capsule rebuild/verification, and Round 11 scheduled five minutes after modification.
- 目前結果 / Current result: 定向測試5/5、第9輪重放22事件/316候選、115/115完整回歸與 capsule verify 全部通過；runtime closure 為55檔，fingerprint `798c3054b18ac72235844f494c775d706a6ac08e698996217654953337dc021f`。 / Targeted tests pass 5/5, the Round 9 replay passes with 22 events/316 candidates, and the full 115/115 suite plus capsule verification pass; the runtime closure contains 55 files with fingerprint `798c3054b18ac72235844f494c775d706a6ac08e698996217654953337dc021f`.
- 下一決定 / Next decision: 全新 run 只從 current pool 建立 selection，通過 freshness gate 後繼續驗證 post-manifest 時序與發布。 / Build selection only from the current pool in a fresh run, then continue through post-manifest timing and publication after the freshness gate passes.
