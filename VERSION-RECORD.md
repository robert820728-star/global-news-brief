# 版本紀錄 / Version Record

## v0.2.3-fresh-main-resolution — 2026-08-17

- 建立原因 / Reason: 排程在 GitHub `main` 已更新後仍解析到舊的 `e08d99c`，並執行該舊版的 PowerShell-only 路徑。 / The scheduled run resolved old commit `e08d99c` after GitHub `main` had advanced, then executed that old version's PowerShell-only path.
- 確認原因 / Confirmed cause: 舊契約只要求「解析最新 main」，未定義防快取端點、交叉確認方式，也未禁止分支列舉、模型記憶或既有 workspace 成為版本來源。 / The old contract only said to resolve the latest main; it defined neither cache-busting endpoints nor cross-checking and did not prohibit branch enumeration, model memory, or an existing workspace from becoming the version authority.
- 實作方式 / Approach: 每輪以兩個不同 fresh UTC nonce 直接讀取 GitHub `git/ref/heads/main` 與 `commits/main` API，要求 SHA 一致；一致後只在本輪固定該 SHA，下一輪重新解析。 / Each run directly reads the GitHub `git/ref/heads/main` and `commits/main` APIs with distinct fresh UTC nonces and requires matching SHAs; the SHA is pinned only within that run and resolved again next run.
- 變更入口 / Changed entry points: `daily-schedule-prompt.md`, `bootstrap-workspace.md`, `INSTALL.md`, `README.md`, `tests/test_pipeline_contract.py`.
- 重要設定 / Important configuration: 不得列舉 repository branches，不得沿用前次 SHA、排程建立時 SHA、舊 workspace 或模型記憶；雙端點不一致只可用全新 nonce 重試一次。 / Repository branches must not be enumerated, and no previous/setup SHA, old workspace, or model memory may be reused; endpoint disagreement permits only one retry with new nonces.
- 驗證方式 / Validation: freshness contract RED→GREEN、capsule 重建與驗證、完整 unittest、Ubuntu CI、GitHub remote blob 與最新 `main` 查核。 / Freshness contract red-green, capsule rebuild and verification, full unittest, Ubuntu CI, and GitHub remote blob/latest-main checks.
- 結果 / Result: freshness focused test 通過，完整回歸 121/121 通過；capsule verify 通過，runtime 55 檔、44 chunks，fingerprint `e285b940153e51b9caad49ffea18baf83bdf8ab0e5714189c0818050763d440b`。 / The focused freshness test passes, the full regression passes 121/121, and capsule verification passes with 55 runtime files, 44 chunks, and fingerprint `e285b940153e51b9caad49ffea18baf83bdf8ab0e5714189c0818050763d440b`.
- 下一決定 / Next decision: 更新既有手機 Scheduled Task 的保存指令一次，再立即重跑；之後每輪會自行解析最新 `main`。 / Update the existing mobile Scheduled Task's saved instruction once and rerun immediately; later runs will resolve fresh `main` automatically.

## v0.2.2-cross-platform-runtime — 2026-08-17

- 建立原因 / Reason: 手機排程已成功建立 capsule workspace，但 canonical runtime 強制執行 Windows `powershell.exe`，在非 Windows 宿主於新聞搜尋前停止。 / The mobile task materialized the capsule workspace but the canonical runtime required Windows `powershell.exe`, so a non-Windows host stopped before news search.
- 確認原因 / Confirmed cause: `daily-schedule-prompt.md` 將 PowerShell resolver 與 route fetcher 寫成唯一必經路徑；capsule 也只提供這兩個入口。 / `daily-schedule-prompt.md` made the PowerShell resolver and route fetcher mandatory, and the capsule exposed only those entry points.
- 實作方式 / Approach: 新增標準庫 `resolve_bundled_python.py` 與 `fetch_source_routes.py`；所有宿主都以 Python canonical path 執行，PowerShell 只保留在 repository 歷史且不進 capsule。 / Added standard-library `resolve_bundled_python.py` and `fetch_source_routes.py`; every host uses the canonical Python path while PowerShell remains only as repository history and is excluded from the capsule.
- 變更入口 / Changed entry points: `scripts/resolve_bundled_python.py`, `scripts/fetch_source_routes.py`, `daily-schedule-prompt.md`, `bootstrap-workspace.md`, `.github/workflows/build-bootstrap-capsule.yml`.
- 重要設定 / Important configuration: 宿主提供的 bundled-runtime 路徑優先；每個候選必須實際匯入 Pillow；PATH `python3` 只可啟動 loader／resolver，不可自動成為 pipeline runtime。 / The host-provided bundled-runtime path has priority; every candidate must actually import Pillow; PATH `python3` may only launch the loader/resolver and cannot automatically become the pipeline runtime.
- 驗證方式 / Validation: Resolver 與 route fetcher RED→GREEN、本機 HTTP bytes／SHA-256、capsule closure／verify、完整 unittest、Ubuntu CI contract。 / Resolver and route-fetcher red-green tests, local HTTP bytes/SHA-256, capsule closure/verification, full unittest, and Ubuntu CI contract.
- 結果 / Result: Resolver／fetcher focused tests 4/4、完整回歸 120/120 通過；capsule verify 通過，runtime 55 檔、44 chunks、無 PowerShell 或 generated images，fingerprint `296c5883832de21e6b8ef95655b1da813a6dc63d1ea9fbb3abab32001324af34`。 / Resolver/fetcher focused tests pass 4/4 and the full regression passes 120/120; capsule verification passes with 55 runtime files, 44 chunks, no PowerShell or generated images, and fingerprint `296c5883832de21e6b8ef95655b1da813a6dc63d1ea9fbb3abab32001324af34`.
- 下一決定 / Next decision: 發布 GitHub `main` 後讓 capsule workflow 產生最新 verified commit，再立即重跑手機排程。 / After publishing to GitHub `main`, let the capsule workflow produce the latest verified commit, then rerun the mobile task immediately.

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
- 目前結果 / Current result: live 15/15 source scans、388 筆 ranked items、六項分數完整，evidence validator 0 erߎ6��$z{-���jם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
