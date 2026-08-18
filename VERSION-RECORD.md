# 版本紀錄 / Version Record

## v0.3.5-material-update-selection — 2026-08-18

- 建立原因 / Reason: 十四天舊聞每天重播，小型政策措施繼承宏觀母事件高評級，喪禮、普通單一公司上市、純象徵性文化爭議與例行外交行程也被誤判為 C 級以上。 / Fourteen-day old stories were republished daily, minor policy measures inherited a macro parent grade, and funerals, routine single-company listings, symbolic cultural disputes, and routine diplomatic itineraries were promoted to C or above.
- 確認原因 / Confirmed cause: 規則沒有要求本日更新獨立達到門檻，人物、公司或官員層級與媒體聲量也替代了可驗證公共影響。 / The rules did not require the day's update to independently meet the threshold, while prominence and media attention substituted for verifiable public impact.
- 作法 / Approach: 舊事件只有獨立達 C 的實質更新才能重刊；合併更新獨立評分；禮儀、單一公司例行事件、無實質後果的文化稱謂爭議與單純外交行程預設 D。 / Republish old events only when a material update independently reaches C; score merged updates independently; default ceremonial, routine single-company, consequence-free cultural naming disputes, and itinerary-only diplomatic items to D.
- 案例 / Calibration: 朱鎔基喪禮 D；縣域消費不能繼承 B+；宇樹上市 D；光州台灣館名稱加口頭抗議 D；僅宣布王毅訪韓 D。 / Zhu Rongji's funeral D; county consumption cannot inherit B+; Unitree listing D; Gwangju Taiwan-pavilion naming plus verbal protest D; announcement-only Wang Yi Korea visit D.
- 過度設計檢查 / Overdesign check: 僅新增五條選稿規則與案例測試，未增加數量上限、分類器、服務或發布流程。 / Added only five selection rules and case tests—no count cap, classifier, service, or publishing layer.
- 驗證 / Validation: 五項案例測試先失敗，實作後連同四項既有關鍵契約共 9/9 通過。 / Five case tests failed first; after implementation, all five plus four existing critical contract tests passed, 9/9.

## v0.3.4-recoverable-audit-without-reader-block — 2026-08-18

- 建立原因 / Reason: 嚴格要求手機排程在單輪重建並證明十五站完整十四天歷史，導致來源可核對的本日讀者版也被阻擋。 / Requiring a mobile run to rebuild and prove complete fourteen-day history for all fifteen sources blocked even a source-backed current reader edition.
- 確認原因 / Confirmed cause: 完整性檢查錯把前輪原始來源池數量與本輪去重評分候選數相比，且把缺失的歷史 provenance 當成每日發布的致命錯誤。 / The completeness check compared a prior raw source-pool count with a deduplicated scored-candidate count and treated missing historical provenance as fatal to daily publication.
- 作法 / Approach: 只比較同口徑數量；保留可恢復的十四天候選並合併每日十五站 24 小時掃描，舊的不完整部分隨十四天保留期自然退出；不得誇大歷史 coverage，但不阻擋合規讀者版。 / Compare only like-for-like counts; retain recoverable fourteen-day candidates and merge each complete fifteen-source daily scan so unverifiable legacy data ages out naturally; do not overstate historical coverage or block a compliant reader edition.
- 過度設計檢查 / Overdesign check: 移除阻擋式歷史重建要求，未新增 schema、服務、checkpoint 或工作流。 / Removed the blocking historical rebuild requirement without adding a schema, service, checkpoint, or workflow.
- 驗證 / Validation: 四個目標契約測試涵蓋模板、對話交付、逐站 coverage 與非阻擋式滾動 audit。 / Four targeted contract tests cover the reader template, conversation delivery, per-source coverage, and nonblocking rolling audit.

## v0.3.3-reader-template-and-baseline-validity — 2026-08-18

- 建立原因 / Reason: 行動驗收把不完整的 40 筆舊 audit 當成有效基線續接，且 GitHub reader 與 GPT 對話輸出都偏離既有讀者模板。 / Mobile acceptance extended an incomplete 40-item audit as a valid baseline, while both the GitHub reader and GPT delivery diverged from the existing reader template.
- 確認原因 / Confirmed cause: 逐站 coverage 僅覆蓋本日 24 小時，沒有可驗證的十四天 baseline provenance；mobile prompt 也未在寫入前核對 `news-brief-template.md` 的固定三段骨架。 / Per-source coverage covered only the current 24 hours with no verifiable fourteen-day baseline provenance, and the mobile prompt did not validate the fixed three-section `news-brief-template.md` structure before writing.
- 作法 / Approach: 無效或缺失的十四天基線只重建一次並在保留期內保存 provenance；reader 寫入與對話交付前必須符合既有模板的身分行與三個二級標題。 / Rebuild an invalid or missing fourteen-day baseline once and retain its provenance during the retention window; require the reader identity lines and three template headings before repository write and conversation delivery.
- 過度設計檢查 / Overdesign check: 只增加兩個既有流程條件與兩個契約測試；不新增 schema、服務、renderer 或發布管道。 / Only two existing-flow conditions and two contract tests were added; no schema, service, renderer, or delivery channel was introduced.
- 驗證 / Validation: 目標測試涵蓋模板骨架、完整對話交付、十四天基線有效性與逐站 coverage。 / Targeted tests cover template structure, complete conversation delivery, fourteen-day baseline validity, and per-source coverage.

## v0.3.2-source-coverage-and-conversation-delivery — 2026-08-18

- 建立原因 / Reason: 首次回填只留下三個區域彙總與40筆候選，且GPT只交付驗收摘要而非完整讀者版。 / The first backfill stored only three regional aggregates and 40 candidates, while GPT delivered an acceptance summary instead of the complete reader edition.
- 作法 / Approach: 要求15/15逐來源證據、以前輪24小時候選量做完整性下限，並要求對話直接交付完整reader內容。 / Require per-source evidence for all 15 sources, use the prior 24-hour candidate count as a completeness floor, and deliver the complete reader content in the conversation.
- 過度設計檢查 / Overdesign check: 僅強化既有coverage與handoff契約，未新增服務或發布管道。 / Only the existing coverage and handoff contracts were strengthened; no service or publishing channel was added.
- 驗證 / Validation: 新增逐來源完整性與完整reader交付兩項契約測試。 / Added two contract tests for per-source completeness and full reader delivery.


## v0.3.1-first-audit-bootstrap — 2026-08-18

- 建立原因 / Reason: 第一次啟用完整十四天 audit 時沒有前輪持久檔，mobile-native 因無法復原從未保存的淘汰候選而停止。 / The first complete mobile audit had no predecessor artifact and stopped because never-persisted rejected candidates could not be reconstructed.
- 作法 / Approach: 僅首次做純文字十四天回填並建立基線；之後每日只做 24 小時增量與十四天淘汰。 / Perform one text-only fourteen-day backfill to create the baseline, then use daily 24-hour increments and retention expiry.
- 過度設計檢查 / Overdesign check: 未新增資料庫、圖片工作或永久回填服務。 / No database, image workload, or permanent backfill service was added.
- 驗證 / Validation: 首次回填契約與圖片可見性契約共 2 項目標測試通過。 / Two targeted bootstrap and reader-visible-image contract tests passed.


## v0.3.0-mobile-reader-visible-delivery — 2026-08-18

- 建立原因 / Reason: 手機 ChatGPT 可能發布空白圖片框、未持久保存完整十四天海選，並輸出通用後續觀察。 / Mobile ChatGPT could publish blank image placeholders, omit the durable fourteen-day audit, and emit generic follow-up text.
- 確認原因 / Confirmed cause: 前輪選圖或內部路徑即使讀者看不到仍被算成圖片；驗證器未把後續觀察綁定 manifest；手機執行紀錄未宣告模式與海選產物。 / A prior-run image choice or internal path was counted as delivered even when the reader could not see it; the validator did not bind follow-up text to the manifest; the mobile run-log schema did not declare execution mode or the audit artifact.
- 作法 / Approach: 要求圖片在讀者端實際可見，否則提供非技術性無圖說明；後續觀察必須逐字對應事件條件；持久保存執行模式與完整海選清單位置。 / Require reader-visible image delivery or a nontechnical no-image explanation, exact event-specific follow-up conditions, and persisted execution-mode plus full candidate-audit pointers.
- 過度設計檢查 / Overdesign check: 未新增圖片服務、資料庫、重試框架或發布管道。 / No new image service, database, retry framework, or publishing channel was added.
- 驗證 / Validation: 先確認 5 項測試失敗，再通過 90 項相關契約、台帳、驗證器與海選測試。 / Five tests failed first; then 90 relevant contract, ledger, validator, and audit tests passed.


## v0.2.9-scheduled-host-capability-routing — 2026-08-18

- 建立原因 / Reason: 手機 ChatGPT 排程被導向完整 capsule 契約；宿主沒有可寫 workspace 或 Python 時，在新聞搜尋前直接失敗。 / The mobile ChatGPT schedule was routed into the full capsule contract and failed before news collection whenever the host lacked a writable workspace or Python runtime.
- 確認原因 / Confirmed cause: 圖片縮圖規則只降低圖片負擔，沒有造成 Stage -1 錯誤；真正缺陷是把本地 executable runtime 當成手機排程唯一入口。 / The thumbnail rules only reduce image workload and did not cause the Stage -1 error; the actual defect was treating a local executable runtime as the mobile scheduler's only entry path.
- 實作方式 / Approach: 在高壓 bootstrap 前增加一次無網路能力探測；有 runtime 走完整模式，沒有 runtime 就讀取同一 SHA 的手機原生規則並完成可用讀者版，不抓 capsule、不停用每日排程。 / Add one no-network capability probe before bootstrap; use the full path when runtime exists, otherwise use the same-SHA mobile-native rules to deliver a usable reader edition without fetching the capsule or disabling the daily schedule.
- 過度設計檢查 / Overdesign check: 沒有新增服務、capsule、重試框架或發布 gate；只增加兩條既有入口間的能力路由。 / No service, capsule, retry framework, or publication gate was added; this only routes between two existing entry paths.
- 驗證方式 / Validation: 新增契約測試，確認 fallback 標記位於 recursive tree 與 helpers 前，且禁止因 runtime 缺失停用排程。 / Added a contract test proving the fallback appears before recursive-tree/helper work and forbids disabling the schedule for missing runtime.

## v0.2.8-connector-compatible-main-pin — 2026-08-18

- 建立原因 / Reason: 手機 ChatGPT 的 GitHub connector 拒絕 `/git/ref/heads/main`，使 Stage -1 在建立 workspace 前停止。 / The mobile ChatGPT GitHub connector rejects `/git/ref/heads/main`, stopping Stage -1 before workspace creation.
- 確認原因 / Confirmed cause: 同一 connector 可讀精確的 `/branches/main` 與 `/commits/main`，且兩者回傳相同 SHA；問題是契約選用了 connector allowlist 之外的端點，而非 repository 或 capsule 損壞。 / The same connector accepts exact `/branches/main` and `/commits/main` reads and returns the same SHA; the contract selected an endpoint outside the connector allowlist, while the repository and capsule were intact.
- 實作方式 / Approach: 以單一具名 `main` branch lookup 取代 git-ref lookup，同時保留獨立 nonce、與 `commits/main` 的 same-SHA 驗證、一次不一致重試，以及禁止列舉分支。 / Replace the git-ref lookup with a named `main` branch lookup while retaining independent nonces, same-SHA confirmation against `commits/main`, one mismatch retry, and the branch-enumeration prohibition.
- 過度設計檢查 / Overdesign check: 沒有新增第三端點、服務、重試框架或權限；只替換不可用的第一個查詢。 / No third endpoint, service, retry framework, or permission was added; only the unusable first lookup was replaced.
- 驗證方式 / Validation: connector 端點實測、契約測試 RED→GREEN、完整 unittest、deterministic capsule 驗證，以及手機端循環驗收。 / Connector endpoint probe, contract RED-to-GREEN, full unittest, deterministic capsule verification, and mobile loop acceptance.

## v0.2.7-taiwan-domestic-coverage-guard — 2026-08-17

- 建立原因 / Reason: 台灣經濟、食安與中央制度新聞可能未進入海選，國內覆蓋明顯弱於國際結構化來源；聯合新聞路由另有大量純數字標題。 / Taiwan economy, consumer-safety, and central-institution stories could disappear before grading, while the UDN route emitted many numeric titles.
- 確認原因 / Confirmed cause: 一次實際日報的 300 筆海選中，兩類事件完全不存在，預算事件只以混合週報出現；UDN 37 筆中 20 筆為數字標題。 / In one audited run, two event types were absent, the budget event appeared only inside a weekly roundup, and 20 of 37 UDN titles were numeric.
- 實作方式 / Approach: 保留每板塊五站；修復 HTML anchor 標題優先序，並新增三個台灣領域、各最多五筆、限定既有來源的 same-source coverage sweep。 / Kept five primary sources per section, repaired HTML anchor title precedence, and added three Taiwan same-source coverage sweeps capped at five leads each.
- 評級校準 / Calibration: 全國企業實際營運衝擊、跨通路民生產品回收、中央預算／憲政實際後果必須重新評估 C 至 B；只有口水或沒有新後果的延續爭議維持 C-／D。 / Verified broad business impact, nationwide consumer recalls, and concrete central-budget or constitutional consequences require C-to-B reassessment; rhetoric without new consequences remains C-/D.
- 驗證方式 / Validation: HTML title 與契約測試先 RED 後 GREEN，完成完整 unittest、deterministic capsule 與 GitHub Actions 後發布。 / HTML-title and contract tests run RED then GREEN before the full unittest suite, deterministic capsule, and GitHub Actions release.

## v0.2.6-local-disaster-floor — 2026-08-17

- 建立原因 / Reason: 普通地方災害只要少量死亡就可能被評為 B／B+，造成所有 C 級以上必刊登時資訊過量；既有世越號、梨泰院與斯波坎案例也互相矛盾。 / Ordinary local disasters with small death tolls could be graded B/B+, overwhelming the reader edition under the mandatory C-or-higher rule; the Sewol, Itaewon, and Spokane examples also contradicted one another.
- 確認原因 / Confirmed cause: 規則只定義入選後的升級錨點，沒有獨立的刊登資格基準，且候選稽核沒有結構化死亡數、特殊意義與調整理由。 / The rules defined post-selection upgrade anchors but not a publication-eligibility baseline, and the audit lacked structured deaths, special-significance triggers, and adjustment reasons.
- 實作方式 / Approach: 新增最新一輪 `local_disaster_review` 與可執行基準：未滿 50 人低於 C、50–99 人 C、100–249 人 B、250 人以上 A-；正常直接採基準，上調須有可驗證特殊意義與理由，軍事／衝突規則優先。 / Added newest-run `local_disaster_review` and executable baselines: under 50 below C, 50–99 C, 100–249 B, and 250+ A-; normal events use the baseline, upward changes require verified special significance and reasons, and military/conflict rules take precedence.
- 重要案例 / Calibration: 世越號由 304 人死亡的 A- 基準因救援與監管失靈上調至 A；梨泰院由 B 基準因罕見機制與制度影響上調至 A-；斯波坎可由零死亡基準因大規模撤離與住宅損失上調。 / Sewol rises from its 304-death A- baseline to A for rescue and regulatory failure; Itaewon rises from B to A- for its rare mechanism and institutional impact; Spokane may rise from a zero-death baseline for mass evacuation and housing loss.
- 驗證方式 / Validation: 10 個門檻／案例測試先 RED 後 GREEN，並加入手機與完整排程文字契約；完整 unittest 與 deterministic capsule 驗證後發布。 / Ten threshold/calibration tests were observed RED then GREEN, with mobile/full-schedule text contracts; publication follows the full unittest suite and deterministic capsule verification.
- 下一決定 / Next decision: 由手機排程使用最新 main 執行一次新聞驗收，確認十四天海選中的普通未滿 50 人地方事故不再進讀者版，而特殊意義案例仍可上調。 / Run one mobile scheduled-news acceptance against latest main and confirm ordinary sub-50 local events stay out of the reader edition while verified special-significance cases can still rise.

## v0.2.5-earliest-run-ledger — 2026-08-17

- 建立原因 / Reason: 手機排程已鎖定 main 並讀取部分 bootstrap 物件，但在本輪 run id、Issue 台帳與本地 progress 建立前遭平台終止。 / The mobile task pinned main and read some bootstrap objects but was terminated before creating this run's id, issue ledger, or local progress.
- 確認原因 / Confirmed cause: 診斷契約把 run-started 台帳排在 recursive tree、manifest 與 helpers 之後，因此無法觀察這段早期死亡區間；平台終止的底層原因仍無錯誤碼可判定。 / The diagnostic contract placed the run-started ledger after the recursive tree, manifest, and helpers, leaving that early termination window unobservable; the platform's underlying termination cause still has no error code.
- 實作方式 / Approach: 在任何 tool call 前產生 run id；雙端點鎖定 SHA 後、recursive tree 前立即建立 Issue #3 comment，接著在 tree、manifest、helpers 各邊界更新同一則 comment。 / Generate the run id before any tool call; immediately create the Issue #3 comment after dual-endpoint SHA pinning and before the recursive tree, then update the same comment at the tree, manifest, and helper boundaries.
- 重要設定 / Important configuration: 早期台帳仍為單次 best-effort 寫入；失敗不重試、不阻擋新聞。只保留驗證需要的 tree path/blob SHA，避免在回答重印完整 tree。 / The early ledger remains a single best-effort write; failure is not retried and never blocks news. Retain only required tree path/blob SHAs and never reprint the full tree in the response.
- 驗證方式 / Validation: 新增順序契約 RED→GREEN，要求 `run_id < SHA < run-started < tree < manifest < helpers`，並回歸 fresh-main 與外部台帳契約。 / Added a red-green ordering contract requiring `run_id < SHA < run-started < tree < manifest < helpers`, plus regressions for fresh-main and external-ledger behavior.
- 下一決定 / Next decision: GitHub CI 重建 verified capsule 後由手機重跑；依 Issue #3 最後 milestone 判定下一個真實失敗邊界。 / Rerun on mobile after GitHub CI rebuilds the verified capsule; use the final Issue #3 milestone to identify the next real failure boundary.

## v0.2.4-mobile-bootstrap-observability — 2026-08-17

- 建立原因 / Reason: 手機排程可能在 capsule 40/44 時被回收，而正式 checkpoint 尚未建立，無法知道最後成功位置。 / A mobile run could be reclaimed at capsule 40/44 before the news checkpoint existed, leaving no durable last-success boundary.
- 實作方式 / Approach: 新增原子 bootstrap progress、16-line 雙 block 驗證與 8-line fallback、有限重試、統一 RUN_RECEIPT，以及 GitHub issue 單一 comment 的 best-effort 外部台帳。 / Added atomic bootstrap progress, verified 16-line paired-block transport with 8-line fallback, bounded retries, a stable RUN_RECEIPT, and a best-effort one-comment GitHub ledger.
- 變更入口 / Changed entry points: `bootstrap/bootstrap_progress.py`, `bootstrap/bootstrap-progress.schema.json`, `bootstrap/RUN_LEDGER_PROTOCOL.md`, `bootstrap-workspace.md`, `daily-schedule-prompt.md`, capsule builder and Linux CI.
- 重要設定 / Important configuration: 正常搬運請求約減半；每個 block 最多初次加三次重試，退避 2/5/10 秒；台帳每 8 chunks 與關鍵 stage 更新，新聞 stage 最多每 3 分鐘一次，台帳錯誤永不阻擋新聞。 / Normal transport calls are roughly halved; each block gets an initial attempt plus three retries with 2/5/10-second backoff; the ledger updates every 8 chunks and key stages, with news-stage updates limited to once per 3 minutes, and ledger errors never block news.
- 驗證方式 / Validation: chunk 41 截斷、第三次重試失敗、原子更新、成功清除、grouped split/SHA、ledger 權限 create/update、capsule closure、完整 unittest 與 Ubuntu CI。 / Chunk-41 truncation, third-retry failure, atomic updates, successful cleanup, grouped split/SHA, ledger create/update permission, capsule closure, full unittest, and Ubuntu CI.
- 下一決定 / Next decision: GitHub CI 產生 verified capsule 後，以手機 Scheduled Task 對最新 `main` 執行驗收。 / After GitHub CI produces the verified capsule, run acceptance from the mobile Scheduled Task against fresh `main`.

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

## v0.1.11-child — 2026-08-17

- 建立原因 / Reason: 手機 ChatGPT 排程後端完成新聞流程，但對話未顯示輸出，且手機精簡提示未啟用 GitHub 持久台帳，因此該輪沒有可排查紀錄。 / The mobile ChatGPT scheduler completed the news flow in the backend, but the conversation did not display the output and the compact mobile prompt did not enable the persistent GitHub ledger, leaving no diagnosable record for that run.
- 回復來源 / Rollback source: `8ccb5cc019832ebcb4b64bc4cbb10fb851104376`（已驗證 capsule 的最新 main）。 / `8ccb5cc019832ebcb4b64bc4cbb10fb851104376` (the latest main with a verified capsule).
- 實作方式 / Approach: 在獨立 `run-logs` 分支輪替 `current.json`／`previous.json`；05:58 GitHub Actions 只預建執行收據；手機排程依十一個高階階段更新同一筆紀錄，先保存 `latest-reader.md` 再開始對話交付。 / Rotate `current.json` and `previous.json` on an isolated `run-logs` branch; use a 05:58 GitHub Actions watchdog only to prepare the run receipt; have the mobile task update one record across eleven high-level stages and save `latest-reader.md` before starting conversation delivery.
- 變更入口 / Changed entry points: `.github/workflows/prepare-mobile-run-ledger.yml`, `scripts/manage_mobile_run_log.py`, `schemas/mobile-run-log.schema.json`, `docs/mobile-run-ledger.md`, `mobile-chatgpt-daily-prompt.md`, `mobile-chatgpt-start-prompt.md`, `README.md`.
- 重要設定 / Important configuration: GitHub 分支固定為 `run-logs`；守望排程為每天 `21:58 UTC`（台北 05:58）；手機客戶端沒有顯示回執時，最後只可記為 `handoff_started`，不得宣稱 `client_confirmed`。 / The ledger branch is fixed at `run-logs`; the watchdog runs daily at `21:58 UTC` (05:58 Taipei); without a mobile-client display acknowledgement, the final state may only be `handoff_started`, never `client_confirmed`.
- 驗證方式 / Validation: 六個 RED→GREEN 輪替、中斷、階段單調性、守望契約及客戶端回執防誤報測試；推送 main 後確認 GitHub workflow 為 active，並以同一腳本初始化、推送及由 GitHub connector 讀回 `run-logs/logs/current.json`。 / Six red-green tests for rotation, interruption, stage monotonicity, watchdog contract, and client-acknowledgement truthfulness; after pushing main, confirm the GitHub workflow is active, then use the same script to initialize and push `run-logs/logs/current.json` and read it back through the GitHub connector.
- 目前結果 / Current result: 本地六項定向測試與十三項既有契約共19/19通過；main capsule CI 成功；workflow 狀態為 active；遠端 `current.json` 已讀回並符合 `awaiting_executor`。手動 Actions API 派發因本機 credential helper 不提供 API token 而未執行，首次排程觸發仍待 05:58 驗證。 / The six focused tests and thirteen existing contract tests pass 19/19; main capsule CI succeeds; the workflow is active; and remote `current.json` was read back in `awaiting_executor`. Manual Actions API dispatch was unavailable because the local credential helper does not expose an API token, so the first scheduled trigger remains to be observed at 05:58.
- 下一決定 / Next decision: 由手機排程接手遠端 `current.json`；下一次 05:58 後查驗自動輪替，若手機輸出再次遺失，直接以 GitHub 的最後階段與 `latest-reader.md` 驗收。 / Let the mobile scheduler take over remote `current.json`; after the next 05:58 run, verify automatic rotation, and if mobile output disappears again, inspect GitHub's last stage and `latest-reader.md` directly.

## v0.1.12-child — 2026-08-17

- 建立原因 / Reason: 行動排程在候選稽核後偵測到 canonical map contract mismatch；renderer 仍輸出舊檔名且沒有事件行政區著色輸入，但 validator 要求三個 yellow-v2 基底圖。既有生成檔掩蓋了乾淨 capsule 的錯誤。 / The mobile run detected a canonical map contract mismatch after candidate audit: the renderer still emitted legacy filenames and had no event administrative-area overlay input, while the validator required three yellow-v2 basemaps. Stale generated files masked the clean-capsule defect.
- 回復來源 / Rollback source: `76ea407a1ca0c00f4202a9919b705184304c3bba`（偵測到契約不一致的 main capsule）。 / `76ea407a1ca0c00f4202a9919b705184304c3bba` (the main capsule that exposed the contract mismatch).
- 實作方式 / Approach: 將三個 renderer 輸出名稱直接統一為 canonical yellow-v2；新增 TWN/CHN/GLB overlay JSON，依 GeoJSON 行政區屬性精確著色並疊加繁體中文地名；renderer 回傳可直接寫入 manifest 的 base_map、place_labels、style 與尺寸。 / Unified renderer outputs with the canonical yellow-v2 names; added TWN/CHN/GLB overlay JSON that exactly matches GeoJSON administrative properties, applies event colors, and overlays Traditional Chinese place labels; the renderer now returns manifest-ready base-map, labels, style, and dimensions.
- 變更入口 / Changed entry points: `scripts/render_base_maps.py`, `daily-schedule-prompt.md`, `.agents/skills/build-news-maps/SKILL.md`, `maps/README.md`.
- 驗證方式 / Validation: 三區 canonical 檔名、事件著色、繁中標籤與 manifest validator 整合測試；另由當前原始碼重建 capsule，在乾淨解壓 workspace 內實際執行 renderer 與 extracted validator。 / Integration tests cover canonical filenames, event coloring, Traditional Chinese labels, and the manifest validator for all three regions; a second test rebuilds the capsule from current sources and executes the renderer plus extracted validator in a clean workspace.
- 目前結果 / Current result: 本地 49/49 項相關回歸已通過，包含乾淨 capsule 重建、解壓、renderer 與 extracted validator；GitHub Linux capsule CI 尚待本輪最終驗證。 / All 49/49 local focused regressions pass, including clean-capsule rebuild, extraction, renderer execution, and the extracted validator; GitHub Linux capsule CI remains pending for this round.
- 下一步 / Next decision: 通過本地相關測試後推送 main，等待 Linux CI 重建並驗證 capsule；成功後再寄 Gmail 驗收通知。 / After local focused tests pass, push main and wait for Linux CI to rebuild and verify the capsule; send the Gmail acceptance notice only after success.

## v0.1.13-child — 2026-08-17

- 建立原因 / Reason: 完整執行在 `materialize-manifest` 後誤呼叫 final-manifest validator，雖然該命令只讀且沒有損壞產物，執行者仍將它判定為不可恢復 integrity blocker，導致圖片階段開始前整輪報廢。 / A full run invoked the final-manifest validator after `materialize-manifest`; although this was a read-only call that damaged no artifact, the executor classified it as an unrecoverable integrity blocker and discarded the run before image collection.
- 回復來源 / Rollback source: `f5c9bfc9a698fc9cd33abf845762afb03ca95c74`（地圖契約修復後的 verified capsule）。 / `f5c9bfc9a698fc9cd33abf845762afb03ca95c74` (the verified capsule after the map-contract fix).
- 實作方式 / Approach: final-manifest CLI 在 `collect-news-images` 尚未 completed 時回傳 `DEFERRED` 而非 `OK`，且不造成 run failure；排程契約明確要求繼續圖片階段，完成後再重跑到真正的 `OK`。 / The final-manifest CLI now returns `DEFERRED`, not `OK`, while `collect-news-images` is incomplete and does not fail the run; the schedule contract explicitly continues image collection and reruns the validator afterward until it returns a real `OK`.
- 變更入口 / Changed entry points: `scripts/validate_news_brief.py`, `daily-schedule-prompt.md`, `.agents/skills/daily-news-brief/SKILL.md`.
- 驗證方式 / Validation: 真實呼叫 CLI 的提前驗證 RED→GREEN 測試，以及排程契約不得將 `DEFERRED` 標記為整輪失敗的回歸測試。 / A real CLI early-validation RED→GREEN test plus a schedule-contract regression that forbids treating `DEFERRED` as a whole-run failure.
- 目前結果 / Current result: 兩項定向測試 2/2 通過；相關全套、capsule CI 與下一輪完整客戶版尚待驗證。 / Both focused tests pass 2/2; the related suite, capsule CI, and the next full customer-edition run remain pending.
- 下一步 / Next decision: 推送 main 並通過 Linux capsule CI 後立即啟動完整新聞輪次；未達 canonical delivery 不寄 Gmail。 / Push main, pass Linux capsule CI, then immediately start a complete news run; do not send Gmail before canonical delivery succeeds.

## v0.1.14-child — 2026-08-18

- 建立原因 / Reason: canonical release 的圖片與地圖檔案皆存在，但對話交付沿用執行環境絕對路徑，手機 ChatGPT 無法渲染；讀者可見時間也可能殘留 `UTC` 等時區標記。 / Canonical image and map files existed, but conversation delivery preserved executor-local absolute paths that mobile ChatGPT could not render; reader-visible times could also retain timezone labels such as `UTC`.
- 回復來源 / Rollback source: `7eda3bf9ddbd391cd92e7ca35e4997630e21a34e`（本輪修改前的最新 verified main）。 / `7eda3bf9ddbd391cd92e7ca35e4997630e21a34e` (the latest verified main before this change).
- 實作方式 / Approach: 唯一 canonical publisher 在 receipt 與原始 bytes 驗證通過後，以 `--conversation-transport` 僅把 Markdown 本機圖片路徑轉為 `sandbox:` URI；release、receipt 與 SHA-256 不變。所有讀者時間先轉換為 `run.timezone` 的使用者時區，再以短格式輸出且隱藏時區標記。 / After receipt and canonical-byte validation, the sole publisher uses `--conversation-transport` only to convert local Markdown image targets to `sandbox:` URIs; release, receipt, and SHA-256 remain unchanged. All reader times are first converted to the user's `run.timezone`, then shown in short form without timezone labels.
- 變更入口 / Changed entry points: `scripts/publish_news_brief.py`, `scripts/validate_news_brief.py`, `scripts/check_unique_delivery_gate.py`, `daily-schedule-prompt.md`, `news-brief-settings.md`, `news-brief-template.md`, `.agents/skills/daily-news-brief/SKILL.md`.
- 重要設定 / Important configuration: C 級沒有等級式免圖；所有等級只有在可靠來源檢查完成且確無合格圖片時才可顯示圖片說明。 / Grade C has no grade-based image exemption; every grade may use an image explanation only after reliable-source checks confirm that no qualified image exists.
- 驗證方式 / Validation: RED→GREEN 對話 URI、canonical bytes 不變、使用者時區顯示及唯一交付閘門定向測試，另執行完整回歸與 Linux capsule CI。 / Red-green focused tests cover conversation URIs, unchanged canonical bytes, user-timezone display, and the unique delivery gate, followed by the full regression suite and Linux capsule CI.
- 目前結果 / Current result: 定向測試 6/6、非 capsule 完整回歸 179/179 通過；tracked capsule 預期在功能 commit 後由 Linux CI 以新 SHA 重建並驗證。 / Focused tests pass 6/6 and the full non-capsule regression passes 179/179; Linux CI is expected to rebuild and verify the tracked capsule against the new SHA after the functional commit.
- 下一步 / Next decision: 完整回歸通過後直接推送 main，確認遠端 capsule 重建成功。 / Push directly to main after the full regression suite passes, then confirm the remote capsule rebuild succeeds.

## v0.1.15-child — 2026-08-18

- 建立原因 / Reason: 行動排程在事件較多時可能交付約 45 張來源圖片；既有契約又要求專業圖與新聞配圖不得共用，造成重複下載、轉檔、視覺驗收與對話附件負擔。 / Mobile runs could deliver roughly 45 source images on busy days, while the prior contract prevented a professional visual from also satisfying the cited-source image check, causing duplicate downloads, conversions, visual reviews, and chat attachments.
- 回復來源 / Rollback source: `19d6bd7442a6050c7c15ad7bd2c08c907dc089bc`（對話圖片路徑與使用者時區修復後的 verified main）。 / `19d6bd7442a6050c7c15ad7bd2c08c907dc089bc` (the verified main after conversation-image transport and user-timezone fixes).
- 實作方式 / Approach: 每則預設一張、最多兩張；第二張必須說明新增資訊；同一張合格官方圖可同時滿足來源與專業圖資檢查；以 SHA-256 共用一次下載、640px 縮圖與視覺驗收。 / Default to one and cap at two images per event; require an incremental-information reason for the second; allow one qualified official image to satisfy both source and professional checks; reuse one download, 640px thumbnail, and visual acceptance by SHA-256.
- 變更入口 / Changed entry points: `.agents/skills/collect-news-images/SKILL.md`, `schemas/news-event-manifest.schema.json`, `scripts/validate_news_brief.py`, `mobile-chatgpt-daily-prompt.md`, `news-brief-settings.md`, `news-brief-template.md`.
- 重要設定 / Important configuration: 所有 C 級以上新聞與來源覆蓋不變；瀏覽器仍是最後備援；不新增外部快取、資料庫或服務。 / All C-or-above news and source coverage remain unchanged; browser rendering remains the final fallback; no external cache, database, or service is added.
- 驗證方式 / Validation: RED→GREEN 圖片上限、重複 hash、第二張理由與低負擔契約測試，接著執行完整非 capsule 回歸、Linux capsule CI 與乾淨 clone 驗證。 / Red-green tests cover image count, duplicate hashes, second-image rationale, and low-pressure contracts, followed by the full non-capsule regression, Linux capsule CI, and clean-clone verification.
- 目前結果 / Current result: 定向與圖片契約測試 52/52 通過；完整回歸與遠端 capsule 尚待本輪驗證。 / Focused and image-contract tests pass 52/52; full regression and the remote capsule remain pending for this round.
- 下一步 / Next decision: 完整回歸通過後直接推送 main，等待 capsule workflow 成功，再由乾淨 clone 驗證最新 commit。 / Push directly to main after the full regression passes, wait for the capsule workflow, then verify the latest commit from a clean clone.

## v0.1.16-child — 2026-08-18

- 建立原因 / Reason: 手機排程透過模型逐段搬運 48 個 capsule chunks 時，即使 GitHub connector 回傳內容正確，connector 回應到本機 block 的物化仍可能產生無法重現的雜湊差異。 / Mobile runs could report an unreproducible block hash after the GitHub connector returned the correct bytes, because the model-mediated connector-response-to-local-block materialization remained fragile across 48 chunks.
- 回復來源 / Rollback source: `ffb40acbba5f7493384dca53a151050f3c6f64d6`（本輪修正前的遠端 verified main）。 / `ffb40acbba5f7493384dca53a151050f3c6f64d6` (the remote verified main before this repair).
- 實作方式 / Approach: GitHub Actions 同時提交一份 deterministic `capsule-payload.tar.xz`；Stage -1 由既有 loader 對固定 main SHA 執行一次下載並驗證 size、SHA-256 與 Git blob SHA，失敗才使用原有 segmented chunks。 / GitHub Actions also commits one deterministic `capsule-payload.tar.xz`; Stage -1 asks the existing loader to download it once from the pinned main SHA and verify size, SHA-256, and Git blob SHA, falling back to the existing segmented chunks only on failure.
- 變更入口 / Changed entry points: `scripts/build_bootstrap_capsule.py`, `bootstrap/bootstrap_loader.py`, `scripts/verify_bootstrap_capsule.py`, `.github/workflows/build-bootstrap-capsule.yml`, `bootstrap-workspace.md`, `daily-schedule-prompt.md`, `bootstrap/TRANSPORT_FORMAT.md`, `.agents/skills/daily-news-brief/SKILL.md`.
- 過度設計檢查 / Overdesign check: 未加入 artifact、外部服務、新權限或第二套解壓流程；兩種傳輸共用同一 manifest、loader、runtime 驗證與 checkpoint。 / No artifact service, external dependency, new permission, or second extraction pipeline was added; both transports share the same manifest, loader, runtime validation, and checkpoint.
- 驗證方式 / Validation: 兩項 RED→GREEN 測試固定單檔產出與無 chunks 的 URL materialization；其後重建 capsule、驗證 direct/chunk payload 完全相同並執行既有回歸。 / Two RED-to-GREEN tests cover single-payload generation and URL materialization with no chunks, followed by capsule rebuild, exact direct/chunk payload equivalence, and existing regressions.
- 目前結果 / Current result: 本機完整回歸 `192/192` 通過，direct payload 與 segmented chunks 驗證為相同 bytes；等待推送 main 與 Linux capsule workflow。 / The full local regression passes `192/192`, and direct payload plus segmented chunks verify as identical bytes; the main push and Linux capsule workflow are pending.
- 下一步 / Next decision: 通過後直接推送 main，等待 workflow 建立新的 verified payload／manifest／chunks commit，再以最新 main 執行手機驗收。 / After passing, push directly to main, wait for the workflow to create the verified payload/manifest/chunks commit, then run mobile acceptance from the latest main.

## v0.1.17-child — 2026-08-18

- 建立原因 / Reason: 手機排程把十五個媒體站的完整 24 小時覆蓋當成前期硬門檻；任一網站快取過期便阻止整份新聞，且媒體報導在評分前即被誤當成驗證。 / The mobile schedule treated complete 24-hour coverage of fifteen publisher sites as an early hard gate; one stale site could block the whole brief, while media reports were mistaken for verification before scoring.
- 回復來源 / Rollback source: `7a2bd016f14514b824554d4060abc50fb1493312`（來源層改造前的 verified main）。 / `7a2bd016f14514b824554d4060abc50fb1493312` (the verified main before discovery-layer redesign).
- 實作方式 / Approach: 前期只用 GDELT、中央社與中新網形成互補發現池，任一可用即可繼續；去重與評分後，才依科學、戰爭、災害、經貿、法律／政策／選舉及醫療等類別尋找適當原始或獨立證據。缺少官方資料不自動阻擋即時新聞，但必須說明來源限制並把未核實細節標為暫定。 / Use GDELT, CNA, and China News as a compact complementary discovery pool where any available route can continue; after deduplication and scoring, seek category-appropriate original or independent evidence for science, conflict, disaster, economics, law/policy/elections, health, and other categories. Missing official data does not automatically block timely reporting, but source limitations must be disclosed and unverified details marked provisional.
- 變更入口 / Changed entry points: `news-source-pool.json`, `source-route-config.json`, `scripts/fetch_source_routes.py`, `scripts/materialize_source_scans.py`, `scripts/manage_candidate_audit.py`, `scripts/validate_source_scan_evidence.py`, `daily-schedule-prompt.md`, `mobile-chatgpt-daily-prompt.md`, `news-brief-settings.md`, `.agents/skills/acquire-news-candidates/SKILL.md` and targeted tests.
- 重要設定 / Important configuration: GDELT 只作廣域發現，不作單一真相來源；中國官方來源須與外部證據比較；轉載同稿只算一條證據鏈；圖片仍在評分與驗證後處理。 / GDELT is broad discovery rather than a sole source of truth; Chinese official sources require comparison with outside evidence; syndicated copies count as one evidence chain; images remain after scoring and verification.
- 過度設計檢查 / Overdesign check: 刪除十五站前期硬門檻，沒有新增服務、資料庫、分類器或發布管道；沿用現有 candidate audit、來源驗證與圖片流程。 / Removed the fifteen-site early hard gate without adding a service, database, classifier, or publication channel; existing candidate audit, source verification, and image stages are reused.
- 驗證方式 / Validation: RED→GREEN 契約、路由、GDELT 時間解析、部分來源失敗、候選 materialization 與 audit 測試，接著執行 bundled Python 的完整回歸與 capsule 重建。 / Red-to-green tests cover contracts, routing, GDELT time parsing, partial source failure, candidate materialization, and audit handling, followed by the full bundled-Python regression and capsule rebuild.
- 目前結果 / Current result: 83/83 目標測試通過；完整 210 項測試中 206 項通過，剩餘四項均為 tracked capsule 尚待重建。 / All 83 targeted tests pass; 206 of the full 210 tests pass, with the remaining four solely due to the tracked capsule awaiting rebuild.
- 下一步 / Next decision: 提交功能版本後重建 capsule，完整回歸通過再推送 main，之後只建立一個同對話五分鐘驗收。 / Commit the functional version, rebuild the capsule, pass the full regression, push main, and then create only one five-minute acceptance run in the same conversation.

## v0.1.18-child — 2026-08-18

- 建立原因 / Reason: 排程必須先解析最新 main 才能讀取契約，但契約又要求在任何 GitHub 讀取前建立 run id，形成無法遵守的啟動悖論。 / The schedule had to resolve latest main before reading the contract, while the contract required a run id before any GitHub read, creating an impossible bootstrap paradox.
- 實作方式 / Approach: 將 latest-main pin 與 pinned prompt read 明確定義為唯一 pre-contract envelope；契約載入後立即在工作記憶建立 run id，接著才允許 tree、ledger、來源與新聞工作。Mobile runtime 的第一個 GitHub 動作仍是讀取 current ledger。 / Define latest-main pin and pinned-prompt retrieval as the sole pre-contract envelope; immediately generate the run id in task memory after contract load, before tree, ledger, sources, or news work. The first mobile runtime GitHub action remains the current-ledger read.
- 過度設計檢查 / Overdesign check: 只修正三份既有契約與一項順序測試；沒有新增 schema、服務、stage、權限或重試。 / Only three existing contracts and one ordering test changed; no schema, service, stage, permission, or retry was added.
- 驗證方式 / Validation: 兩項 RED→GREEN pipeline-contract 測試確認 pre-contract 例外範圍、main pin、run id 與 ledger 順序，並執行相關 identity／ledger 回歸。 / Two red-to-green pipeline-contract tests verify the pre-contract exception boundary and the main-pin, run-id, and ledger order, followed by the related identity and ledger regression suites.
- 目前結果 / Current result: 相關測試 40/40 通過；等待 capsule workflow 與下一輪同對話驗收。 / Relevant tests pass 40/40; capsule workflow and the next same-conversation acceptance run remain pending.

## v0.1.19-child — 2026-08-18

- 建立原因 / Reason: mobile-native 已完成來源發現，卻把未變更的六項評分格式誤判為新版 rubric，並因無法執行本機 audit script 而拒絕合併既有 69 筆十四天候選。 / Mobile-native completed discovery but misclassified the unchanged six-score format as a new rubric and refused to merge the existing 69-candidate audit because the local audit script was unavailable.
- 實作方式 / Approach: 明確允許 mobile-native 保留未實質更新的有效歷史候選，只重評本輪新增／更新候選，裁切、去重後以 GitHub contents API 整檔覆寫；C 級以上仍按新版證據政策驗證。 / Explicitly allow mobile-native to retain valid unchanged history, rescore only new or materially updated candidates, prune and deduplicate, then replace the JSON through the GitHub contents API; C-or-higher events still follow the new evidence policy.
- 過度設計檢查 / Overdesign check: 只補充既有 prompt、既有 audit skill 與一項契約測試；未新增 schema、script、服務、stage 或第二份 audit。 / Only the existing prompt, audit skill, and one contract test changed; no schema, script, service, stage, or second audit was added.
- 驗證方式 / Validation: RED→GREEN 契約測試確認 full-runtime 與 mobile-native 的責任邊界，以及歷史候選不需無謂重算。 / A red-to-green contract test verifies the full-runtime/mobile-native boundary and prevents needless historical rescoring.
- 目前結果 / Current result: 相關測試 69/69 通過；等待 capsule workflow 與下一輪同對話驗收。 / Relevant tests pass 69/69; capsule workflow and the next same-conversation acceptance run remain pending.

