# 每日新聞安裝與操作指引

本文件是本 repository 的唯一安裝入口，也是新對話第一次使用時的操作教程。它負責說明讀取順序、排程安裝、兩種執行模式、完整每日流程、必填產物、驗證與局部恢復。每日讀者版不得包含本文件的安裝或後台內容。

## 安裝目標

1. 只詢問必要偏好，建立名為「每日新聞」的每日獨立排程。
2. 每輪重新解析最新 `main`，同一輪固定使用一個經雙端點確認的 commit。
3. 正式循環排程的強制可見圖片 profile 只可在已通過本機附件實測的 desktop/local-project `full-runtime` 啟用；`mobile-native` 只保留一次性診斷與候選整理用途。
4. 新聞發現使用 GDELT、中央社與中新社三條 discovery routes；事件驗證依事件與主張角色動態選取原始、官方／主要及真正獨立的證據。
5. 首次安裝時先完成真實本機附件實測，通過後才啟用循環排程；再立即執行一次完整測試，驗證排程、讀者版、執行紀錄及可見圖片交付。

## 使用者啟動指令

在全新對話貼上：

> 請使用以下 GitHub 專案建立我的每日新聞簡報：
>
> https://github.com/robert820728-star/global-news-brief
>
> 請先完整閱讀最新版 `INSTALL.md`，再依照其中的讀取順序、技能、設定、產物、驗證與恢復規則執行，不要自行簡化或重新發明流程。

收到後，以本文件為入口直接開始。使用者不必理解 YAML、三碼代碼、排程語法、schema 或 Git blob。

## 文件權責與讀取順序

同一主題只以表中「權責文件」為準；其他文件可補充但不得覆寫。若兩份現行文件有矛盾，停止安裝並指出精確路徑與衝突句，不能自行挑一份。

| 順序 | 權責文件 | 正確用途 |
|---:|---|---|
| 1 | `INSTALL.md` | 安裝入口、檔案清單、模式選擇、完整步驟、產物、驗證與恢復 |
| 2 | `bootstrap-workspace.md` | fresh-main 解析、capsule 物化、bootstrap receipt 與 checkpoint 前置條件 |
| 3 | `daily-schedule-prompt.md` | full-runtime 的詳細每日執行契約 |
| 4 | `mobile-chatgpt-daily-prompt.md` | 一次性診斷、候選整理或歷史 run recovery 的 mobile-native 執行契約；不是正式循環排程入口 |
| 5 | `.agents/skills/daily-news-brief/SKILL.md` | 主控順序、stage ownership 與發布流程 |
| 6 | 各 stage skill | 只負責該 stage 的輸入、欄位與完成條件 |
| 7 | `news-brief-settings.md`、`news-source-pool.json`、`source-route-config.json` | 編輯／評級設定、三條 discovery routes 與取得路徑 |
| 8 | `schemas/*.json` 與 `scripts/*.py` | 可機器檢查的資料契約與 validator；與 prose 衝突時必須修正衝突，不能繞過 validator |
| 9 | `news-brief-template.md` | 唯一讀者版骨架 |
| 10 | `news-brief-examples.md` | 只在格式驗證失敗或維護規則時查正反例，不是每日必讀 |
| 11 | `VERSION-RECORD.md`、`docs/news-rule-matrix.json`、`docs/superpowers/**` | 版本、S5 局部驗收與設計紀錄；只供追溯，不是完整現行規則清單，也不覆寫現行契約 |

## 一、安裝前驗證

先確認 repo 可讀取，並確認下列現行必要檔案全部存在。

### 九個技能

- `.agents/skills/daily-news-brief/SKILL.md`
- `.agents/skills/acquire-news-candidates/SKILL.md`
- `.agents/skills/select-news-events/SKILL.md`
- `.agents/skills/audit-news-candidates/SKILL.md`
- `.agents/skills/verify-news-events/SKILL.md`
- `.agents/skills/build-news-maps/SKILL.md`
- `.agents/skills/build-news-charts/SKILL.md`
- `.agents/skills/collect-news-images/SKILL.md`
- `.agents/skills/recover-news-run/SKILL.md`

### 設定、模板與契約

- `bootstrap-workspace.md`
- `daily-schedule-prompt.md`
- `mobile-chatgpt-daily-prompt.md`
- `news-brief-settings.md`
- `news-brief-template.md`
- `news-brief-examples.md`
- `user-preferences.example.yaml`
- `news-source-pool.json`
- `source-route-config.json`
- `schemas/news-event-manifest.schema.json`
- `schemas/news-candidate-audit.schema.json`
- `schemas/news-source-candidate-list.schema.json`
- `schemas/news-relevance-gate.schema.json`
- `schemas/mobile-run-log.schema.json`

### 核心工具與地圖資產

- `scripts/news_run_checkpoint.py`
- `scripts/fetch_source_routes.py`
- `scripts/materialize_source_scans.py`
- `scripts/validate_source_scan_evidence.py`
- `scripts/build_source_candidate_list.py`
- `scripts/build_news_relevance_gate.py`
- `scripts/validate_local_source_admission.py`
- `scripts/preprocess_news_candidates.py`
- `scripts/manage_candidate_audit.py`
- `scripts/materialize_event_manifest.py`
- `scripts/apply_event_stage_patch.py`
- `scripts/validate_news_brief.py`
- `scripts/validate_map_decisions.py`
- `scripts/materialize_news_images.py`
- `scripts/recover_news_run.py`
- `scripts/manage_canonical_run_bundle.py`
- `scripts/check_unique_delivery_gate.py`
- `scripts/publish_news_brief.py`
- `scripts/initialize_section_basemaps.py`
- `scripts/fetch_admin_boundaries.py`
- `scripts/render_base_maps.py`
- `maps/style.json`
- `maps/source/world-countries.geojson`

### Bootstrap infrastructure

- `bootstrap/capsule-manifest.json`
- `bootstrap/bootstrap_loader.py`
- `bootstrap/bootstrap_progress.py`
- `bootstrap/bootstrap-progress.schema.json`
- `bootstrap/RUN_LEDGER_PROTOCOL.md`
- `scripts/resolve_bundled_python.py`
- `scripts/run_identity.py`

### Mobile execution support

- `scripts/manage_mobile_run_log.py`
- `schemas/mobile-run-log.schema.json`
- `mobile-chatgpt-start-prompt.md`
- `mobile-chatgpt-daily-prompt.md`

### Recovery／validation support

- `scripts/recover_same_source_leads.py`
- `scripts/validate_selection_freshness.py`

以上是 operator-facing necessary closure；完整 capsule runtime closure 以 `bootstrap/capsule-manifest.json` 裡的 `runtime_files` 欄位為機器權威，不在 INSTALL 重複列出全部 runtime files。

`news-source-pool.json` 必須只預先設定 GDELT、CNA、China News Service 三條 `discovery_sources`。評分後的驗證來源由事件與主張角色決定，不得另設一組預先固定的驗證來源清單。

## 二、只詢問必要偏好

1. 監控板塊：是否自訂國家或區域？未自訂使用台灣（TWN）、中國（CHN）、世界（GLB）。
2. 主題偏好：是否提高或降低特定主題權重？未指定沿用 repository 預設，偏好不能降低證據、安全或驗證門檻。
3. 排程時間與時區：由 ChatGPT Scheduled Task 本身的單次／循環設定決定；使用者已指定就直接沿用，未指定才詢問，仍無偏好時預設每日 06:00 並優先採帳號／裝置時區。repository 不預先建立 future occurrence，也不綁定特定鐘點。國家板塊使用 ISO 3166-1 alpha-3；區域使用穩定不衝突的三碼。本輪 normalized audit 以有序 `section_scopes` 保存每個板塊的 `code`、`member_country_codes` 與唯一 `fallback`；事件板塊只能由其內容確認的 `country_codes` 對照這份權威決定，不得硬編碼成 TWN／CHN／其他皆 GLB。取得建立排程的授權後，直接完成安裝與首次測試，不再分階段重複詢問同一決定。

輸出語言沿用使用者既有設定；未設定時使用安裝對話主要語言。

## 三、執行模式與完成條件

`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE`

本產品的正式循環排程要求所有已確認存在合格圖片的入選事件都完成實際可見附件交付，因此只能建立在 ChatGPT desktop／Codex 的 desktop/local project 或其隔離 worktree，並以 `full-runtime` 執行。一般 web／mobile ChatGPT 的 `mobile-native` 可用於一次性診斷、候選整理或檢查來源，但不得作為正式循環排程、不得被描述成能保證 canonical Reader 圖片交付，也不得依賴一個未實際存在的未來 full-runtime worker 接手。

`VISIBLE_LOCAL_ATTACHMENT_INSTALL_SMOKE_GATE`

建立或啟用「每日新聞」循環排程前，安裝對話必須先取得當下 verified workspace，將其中的 `maps/generated/taiwan-counties-yellow-v2.png` 以本機實體檔附件交付到目前對話，並確認該訊息中實際顯示圖片。只貼本機路徑、`sandbox:` 字串、外部 URL、Markdown 熱連結、圖片說明或破圖框都不算通過。未通過時不得啟用、不得宣稱排程安裝完成，也不得退回建立 production `mobile-native` 排程；應明確要求改在支援本機專案與附件的 desktop/local project 建立。

| 項目 | `full-runtime` | `mobile-native` |
|---|---|---|
| 適用環境 | 可執行 bundled Python、物化檔案與 canonical publisher；正式循環排程唯一合格模式 | 無本機 runtime 的一般 ChatGPT 宿主；只供一次性診斷／候選整理，不是正式循環排程 |
| 持久化前提 | 外部 ledger 可依 full-runtime 規則 best-effort 降級 | 可恢復的 durable Scheduled Task 必須使用具此 repository `run-logs` 寫入權限的 GitHub app；無寫入權限只可做一次性、不可跨執行恢復的 reader，不得宣稱 durable mobile profile |
| 新聞流程 | 完整執行 | 完整執行；不得因缺少本機工具省略 discovery、語意評分、驗證或 reader |
| 地圖／圖表／圖片 | `claim_critical=true` 的視覺必須物化並完成檔案／像素驗證；來源確實沒有合格圖片時可 omitted | 先執行宿主可用的原生媒體路徑；來源確實沒有合格圖片時可 omitted，已確認有合格圖片但交付失敗時必須停在視覺恢復 |
| canonical 完成 | `full-assets`，所有宣稱的附件通過 | 只有沒有未解決媒體交付失敗時可 `status=completed`；`reader-canonical-capability-degraded` 是可恢復中間狀態，不是正式完成 |
| `NATIVE_MEDIA_UNAVAILABLE` | 若已確認圖片仍未交付，屬未完成的視覺 stage | 逐則依 `IMAGE_FALLBACK_EXHAUSTION_GATE` 搜完四層來源，至少找到一張合格圖片，且該模式所有可用可見交付方式均已實際失敗時才可記錄；保持同一 run 的 `status=running`、`current_stage=visuals-completed`，不是 `last_error`，不得捏造本地下載、截圖、物化或像素驗收 |
| 後續補圖 | 局部恢復該視覺 stage | 可由 full-runtime 只補缺少視覺；不得建立新 run 或重跑新聞、評分與驗證 |

不能因工具清單沒有特定名稱的 media API，就預先宣告無法交付。已有可解碼、尺寸與 SHA-256 通過的本機 JPEG／WebP 時，必須先實際嘗試宿主支援的本機附件或本機媒體呈現方式。外部圖片網址不能冒充附件；但合格本機檔案也不能被規則無條件禁止。

`NO_EXTERNAL_IMAGE_URL_DELIVERY_GATE`：外部圖片網址、Markdown 熱連結、來源頁面連結、CDN URL、路徑文字、caption 或破圖占位都只能作為圖片取得線索，不能算讀者可見的圖片交付。正式 Reader 的圖片必須是目前對話中實際可見的本機／原生附件；若來源圖片 URL 可開啟，執行器必須沿既有 fallback 與 materialization 路徑取得實體媒體，而不是把「看得到網址」誤判為「無法取得圖片」。

## 四、建立排程與板塊底圖

### Scheduled Task 排程指令唯一契約

`SCHEDULED_TASK_FULL_INSTRUCTION_GATE`

ChatGPT Scheduled Task 不得只收到「請讀 INSTALL」的短 launcher。建立或修正每日排程時，必須讀取當下最新 `main` 的 [scheduled-task-prompt-template.md](scheduled-task-prompt-template.md)，將該檔全文原樣完整複製為 task prompt；只有使用者明確指定的「區域」與「監控類型」兩個 placeholder 可以替換。排程時間與時區由 Scheduled Task 的 schedule 欄位保存，不寫進新聞規則文字。

複製 task prompt 前必須先通過 `VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE` 與 `VISIBLE_LOCAL_ATTACHMENT_INSTALL_SMOKE_GATE`。排程必須綁定目前 desktop/local project 或其 worktree，不能建立成只能使用 web／mobile `mobile-native` 的正式循環工作。

這份完整 task prompt 直接攜帶不可省略的最低執行包絡，包括 fresh main、單一 run、全球 coverage、Public Value V2、獨立驗證、逐則圖片取得與四層 fallback、可見圖片交付、三段式 Reader、同 run 恢復及回覆原對話；同時每輪仍須讀取最新版 repository 取得完整細節。建立者不得摘要、縮短、重寫成一句「嚴格依 INSTALL 執行」，也不得只貼檔案連結。

排程設定規則：

1. task 標題固定為 `每日新聞`；若宿主為方便顯示時間而既有標題含時間，可在下一次修正時正規化回 `每日新聞`，時間只由 schedule 表示。
2. 使用者指定明確鐘點時使用 exact schedule；未指定鐘點但只指定 morning／afternoon／evening 等日段時依宿主任務規則使用 flexible schedule。未指定任何時間時預設每日 06:00，優先採帳號／裝置時區。
3. task prompt 不得固定 commit SHA、run id、workspace、checkpoint、reader、候選清單、圖片 ref、來源 URL、工具名稱或任何當輪產物。
4. task prompt 必須保留完整範本中的執行 gate；不得刪除圖片 fallback、全球 discovery、評分、Reader 格式、恢復或對話交付段落。
5. 修正排程時必須「重新由最新版完整範本生成 task prompt」，不得在舊 prompt 後追加 patch、例外條款或臨時 hotfix。永久行為先改 repository 範本與權責文件，再用完整新範本取代舊 task prompt。
6. task prompt 與最新版完整範本不一致時視為 configuration drift；應修正 task prompt，不得遷就 drift 或回退成短 launcher。

單次與循環 Scheduled Task 都以該 task 真正觸發的 `scheduled_for` 作 occurrence key；04:00、06:00 或其他時間完全走同一流程。repository 不設 pre-trigger watchdog，也不得在 task 實際觸發前寫入 future `current.json`。每輪先 fresh-resolve `main` 並做一次 capability routing。只有本機執行／可寫能力與 `VERIFIED_BOOTSTRAP_SEED_ROUTE` 都成功，才以 `execution_mode=full-runtime` 建立／接續該輪執行狀態。一次性診斷可在本機執行不存在，或 pinned loader seed 無法取得且宿主也沒有 lossless connector-to-local handoff 時走 `mobile-native`；正式循環排程若得到此 routing 結果，表示安裝資格不成立，必須在 occurrence 建立與新聞 discovery 前停止並要求改用 desktop/local project，不得建立一個等待不存在之 full-runtime 接手的 doomed run。bootstrap transport 不可用是 capability routing 結果，不得誤報成 repository materialization defect。mode 自 actual occurrence 的 `prepare` 起不可切換。兩種模式的 24 小時窗都從實際 executor 啟動時刻精確倒推，個人偏好不回寫公共 `main`。

板塊確定後：

1. 檢查 `maps/generated/sections/<CODE>-base.json`。
2. 缺少時以 `scripts/initialize_section_basemaps.py` 建規格；國家板塊由 `scripts/fetch_admin_boundaries.py` 取得 geoBoundaries gbOpen ADM1，不寫國家特例。
3. 可執行 runtime 時產生 PNG／SVG 並視覺驗收；未實際產圖只能標 `spec_ready`，不能標 `ready`。
4. 每日事件仍由 `build-news-maps` 判斷點位、範圍或路線；事件標記必須疊加在完整板塊底圖，板塊底圖不能直接冒充事件地圖。

## 五、完整每日執行流程

下表是不可省略的主順序。`stage completed` 必須有具名 artifact 與 SHA-256；不能只寫一個完成字串。

| 階段 | 必讀／輸入 | 必填產物與驗證 | 完成或恢復條件 |
|---|---|---|---|
| -1 fresh main 與 bootstrap | `bootstrap-workspace.md`、雙端點 current main、fresh nonce；full-runtime 另需 pinned loader seed／capsule manifest／payload | 先完成 capability routing；full-runtime 必須由已核對 Git blob SHA 的 loader seed 開始，產生經 manifest blob、payload SHA-256、runtime fingerprint 驗證的 workspace 與 `bootstrap-receipt.json`；一次性診斷在 seed transport 不可用且沒有 lossless connector-to-local handoff 時才可走 mobile-native | 正式循環排程的 full-runtime receipt 未通過前不得建立 news checkpoint 或 occurrence；不得只因 Python／可寫 probe 成功便強制進入一條無法物化 loader 的 full-runtime，也不得改建 production mobile-native；歷史 mobile run 才從同一 actual occurrence 的 first incomplete stage 接續 |
| 0 checkpoint init | run id、精確 24 小時窗；full-runtime 另需 bootstrap receipt | full-runtime 執行 canonical checkpoint CLI：`<bundled-python> scripts/news_run_checkpoint.py init ...`；mobile-native 在 capability routing 選定後建立或 resume `logs/current.json`，保存 run id、窗、main 與 first incomplete stage | 兩種模式都綁定同一輪 main 與時間窗；mobile-native 不宣稱執行 `news_run_checkpoint.py` |
| 1 source-scan | `news-source-pool.json`、`source-route-config.json` | 三條 configured discovery route 的 snapshots、scan evidence、truthful coverage；必要時另有受控 `web_fallback` row；`source-candidates.json`、`news-relevance-gate.json`、`model-source-candidates.json` | `SOURCE_SCAN_COVERAGE_SEPARATION`：`scan_status` 只表示掃描程序是否完成，`coverage_status`／`coverage_complete` 另表示來源覆蓋是否完整；每條 configured route 都留在 audit。`GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE`：本輪有 fallback／全球板塊時，優先要求 `primary_aggregator` 成功；GDELT 的 archive、一次 DOC、有效 cache 全部不可用後，只有保存可重算搜尋快照、精確時間窗、原始文章網址與逐列處置的 `web_fallback` 可恢復全球召回。它永遠是 `degraded_partial`，不得冒充 GDELT 或補足 configured-route completeness；primary 與備援都無可核實候選時才停在 source-scan。`FULL_DISCOVERY_POOL_UNCAPPED`：已取得列完整入池，弱 signal 仍進模型 |
| 2 preprocess | model-admitted rows | `preprocessed-candidates.json`；時間窗、canonical URL、provisional article groups | 這些群組不是語意事件；失敗只重跑 preprocess |
| 3 conditional recovery | source、gate、preprocess、content hydration receipts | full-runtime 預設只保存 local hash 與 checkpoint binding；`CONDITIONAL_RECOVERY_BUNDLE_POLICY` 僅在 cross-host handoff、ephemeral workspace 或 warning/timeout boundary 時，以 `manage_canonical_run_bundle.py pack-recovery` 建立六份 artifact bundle；mobile-native 使用既有 occurrence ledger 與 run-scoped artifacts | durable workspace 可直接進入 `FIRST_SELECT_NEWS_EVENTS_EXECUTION`；必要時 full-runtime 用 bundle `restore`，mobile-native 從 ledger 的 first incomplete stage 接續 |
| 4 select-news-events | hydrated rows、偏好、十四天 timeline | `selection-results.json`、唯一 `semantic_event_id`／`event_identity`、每列 `article_dispositions` | `event_evidence`、`non_news`、`unresolved`、`unresolved_exhausted` 逐列守恆；full-runtime 執行 `validate_local_source_admission.py`，mobile-native 執行既有 `MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT`，不得冒充 Python 已執行 |
| 5 audit-news-candidates | selection、上一份 durable audit（若有）、`news-source-pool.json.ranking` | 本輪 run-scoped candidate audit、十四天 merge status、`public_value_v2` 的 facts／Actual-Potential 分類／六項 0–100 分數／加權總分／delta／challenge／confidence／`grade_status`／決定／`selected_event_id` | 依下方 V2 順序逐 gate 驗證；先修正可重算 counts。十四天歷史無法合併時保留舊 blob 並延後維護，但不得把 provisional 冒充 validated |
| 6 publication event authority | audit 中 selected C 以上且 `grade_status=validated` 的事件 | full-runtime 物化並驗證 `news-event-manifest.json`，事件集合精確等於 selected ids；mobile-native 以同一 run-scoped candidate audit 的 selected events 作唯一事件集合 | full-runtime 只能一對一物化並綁定 checkpoint；mobile-native 不建立或聲稱通過 full-runtime manifest schema，也不得另加／漏掉新聞 |
| 7 verify-news-events | 事件與主張類型 | full-runtime 以 stage patch 寫入 manifest；mobile-native 保存 `verification.json` 並以 `verification_artifact` 綁定本輪 Git blob；兩者均保存原始報導、官方／主要記錄、獨立證據鏈、claim status 與 source limits | full-runtime 只合併 verify 欄位並執行 stage ownership validator；mobile-native 進入 `visuals-completed` 前必須先保存 `verification.json`，resume 讀回它而不重跑已完成 verification |
| 8 build-news-maps | 已驗證事件、map policy | full-runtime 保存 map decision、必要 overlay、canonical basemap 與 PNG／SVG；mobile-native 保存 `map-decisions.json` 並以 `map_decisions_artifact` 綁定本輪 Git blob | full-runtime 執行 `validate_map_decisions.py` 且只修失敗事件地圖；mobile-native 不執行本機 renderer，進入 `reader-rendered` 前讀回既有 map decisions |
| 9 build-news-charts | 已驗證數據與 chart policy | full-runtime 只在比較、趨勢、比例、分布或查表有增量時建立 chart assets；mobile-native 保存可執行的判定，不宣稱產生本機 chart | 圖表不能替代地圖或來源圖片；full-runtime 只修失敗圖表，mobile-native 無本機資產時依既有 capability omission 繼續文字 reader |
| 10 collect-news-images | 已驗證來源頁與官方產品頁 | 每則 source checks 與 `claim_critical`；full-runtime 另保存 download／screenshot attempts、`materialized-images.json`、MIME、尺寸、SHA-256 與 visual check；mobile-native 保存文章直接媒體 URL、原生圖片／圖片卡及後續來源嘗試與宿主結構化結果 | full-runtime 先下載原圖、失敗才截圖；mobile-native 不假裝具備本機物化能力；來源確實沒有合格圖片時可 omitted；已確認有合格圖片但未能顯示時不得完成視覺 stage 或正式 reader |
| 11 final authority 與 render | collect stage 已 completed／依 profile 合法 omission | full-runtime 首次執行 `validate_news_brief.py manifest` 到 `OK`，由 manifest 渲染 reader 並執行 brief validator；mobile-native 由 run-scoped selected events 與已驗證事實渲染 reader，再執行既有 `MOBILE_READER_STRUCTURE_EQUIVALENT` | full-runtime 提前取得 `DEFERRED` 時繼續原 stage；mobile-native 不宣稱 script 或 manifest schema 已通過，結構錯誤只重做 render |
| 12 publish 與 bundle | final checkpoint、manifest、audit、source pool、reader、map decisions、宣稱交付的附件 | 依下方實際 CLI 由 `publish_news_brief.py` 建立 release／receipt；再以 `manage_canonical_run_bundle.py pack` 建立 transport，與 `logs/current.json` 一次 atomic 發布後執行 `verify`／`restore` 核對 byte identity | full-runtime 由 canonical publisher fail-closed；mobile-native 依 mobile ledger schema 保存 reader/audit 與 delivery profile |
| 13 conversation delivery | release receipt 或 mobile saved reader | 完整 reader bytes、附件／能力限制 receipt、`delivery-handoff` | 不能只交摘要或驗收報告；`client_confirmed` 只有外部明確回執才可使用 |

`SCHEDULED_OCCURRENCE_SINGLE_RUN_GATE`：mobile ledger 以 Scheduled Task 真正觸發的 `scheduled_for` 作 occurrence key；repository 不預建 future key。同一 occurrence 的 `current.json` 只要存在，就沿用原 `run_id` 並從 first incomplete stage 接續；即使 reader 已保存但尚未 `delivery-handoff`，也不得 rotate、建立 replacement run 或重跑新聞階段。只有 `scheduled_for` 嚴格較晚的下一個實際觸發 occurrence 才可 rotate，且非 terminal 前輪才標為 `interrupted_by_next_run`；相同 key resume、較舊 key 一律拒絕。同一 run 只能留在原 stage 或前進至緊鄰的下一 stage，不得跳級，也不得執行 stage regression。

`VERIFICATION_FEEDBACK_REWIND_GATE`：核心主張 `finding=insufficient` 時，verification 必須 `status=failed`，不得進 ready reader。full-runtime 完成既定驗證恢復後仍不足，執行 `<bundled-python> scripts/news_run_checkpoint.py rewind --input <checkpoint> --output <checkpoint> --stage audit-news-candidates --reason "<evidence failure>"`；只清除 audit 與其後 stage bindings，保留 source-scan、preprocess 與 semantic selection，將受影響候選重評或排除後重新物化 manifest。mobile-native 保持 `current_stage=selection-verified`，不得前進 `visuals-completed`；直接更新同一 run 的 `candidate-audit.json`，重評或排除受影響候選，更新 `candidate_audit_artifact` 的 Git blob SHA，再重新查證。查證成功並保存新的 `verification.json` 後才可前進。mobile-native 不得執行 stage regression，也不得建立 mobile checkpoint 或 manifest；兩種模式都不得建立新 run 或重跑 discovery。

Stage 12 與 13 的 full-runtime 指令介面如下；`--artifact` 對每個必要 run artifact 重複一次。`release` 是 publisher 產物，不是子命令：

```bash
<bundled-python> scripts/publish_news_brief.py --checkpoint <checkpoint> --manifest <final-manifest> --audit <candidate-audit> --source-pool news-source-pool.json --brief <reader> --output-dir <release-dir>
<bundled-python> scripts/manage_canonical_run_bundle.py pack --run-id <run-id> --transport-dir <transport-dir> --manifest <bundle-manifest> --artifact checkpoint=<checkpoint> --artifact reader=<reader> --artifact release-receipt=<release-dir>/release-receipt.json
<bundled-python> scripts/manage_canonical_run_bundle.py verify --manifest <bundle-manifest> --transport-dir <transport-dir>
<bundled-python> scripts/manage_canonical_run_bundle.py restore --manifest <bundle-manifest> --transport-dir <transport-dir> --output-dir <restore-proof-dir>
<bundled-python> scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint> --conversation-transport
```

`pack` 命令列出的三個 `--artifact` 只是語法示例，不是完整清單；實際發布必須把本輪 candidate audit、完整 `article_dispositions`、image evidence、materialized images、map decisions、checkpoint、counts、event manifest、reader、attachments index、release receipt 及其他宣稱交付的附件全部逐項加入。完成 `pack` 後先 `verify`，上傳 transport 與 `logs/current.json` 的單一 atomic commit，再從該 commit 下載並 `restore`；只有重組後 byte identity 一致才可執行 Stage 13。

`SOURCE_BEFORE_CAPSULE_RELEASE_ORDER`：版本實作、測試、active tracked source 與最終雙語 `VERSION-RECORD.md` 必須先合併為同一 source candidate，再只觸發一次完整 CI 與 capsule generation。不得在 capsule commit 後再修改 active tracked source 或補寫 version record，否則該 capsule 已不再代表最新 source，必須重新走完整 source→CI→capsule 順序。CI 的瞬時 queued／success 狀態留在交付摘要、Release 或 Issue，不以 post-capsule source commit 追記。

## 六、必填產物與驗證

### Candidate audit counts

`PIPELINE_COUNT_RECEIPT`：以下欄位一律由本輪 artifact 重算；文章列、canonical URL、標題分群與語意事件是不同層級，不得互相冒充。

本輪必須從 artifact 重算並保存：

- `merged_article_row_count`
- `in_window_article_row_count`
- `canonical_url_count`
- `provisional_title_cluster_count`
- `semantic_event_count`
- `scored_event_count`
- `c_or_higher_scored_event_count`
- `selected_event_count`
- `event_evidence_article_row_count`
- `non_news_article_row_count`
- `unresolved_article_row_count`
- `unresolved_exhausted_article_row_count`

文章列、canonical URL、標題群組與語意事件是不同口徑，不能互相冒充。所有 C 級以上事件都必須映射到 reader；不設篇數上限。

`COUNT_RECEIPT_REPAIR_ONCE`：事件小計與同一 run-scoped candidate audit 的 `events` 陣列不符時，直接依陣列重算並覆寫一次，再驗證 selected mapping。像 32/33 這類純小計差額不是 fatal blocker；只有事件本體、評分或 mapping 仍矛盾時，才把受影響項目退回 unresolved。

`FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE`：`logs/runs/<run_id>/candidate-audit.json` 是本輪 24 小時 run-scoped candidate audit，也是完成門檻；`logs/latest-candidate-audit.json` 只是十四天 continuity cache。宿主無法安全 materialize／merge 後者時，保留原 blob、記錄 `durable_audit_status=preserved_merge_deferred`，繼續當輪驗證與 reader。這個狀態不得設為 `last_error`、不得標 failed，也不得重跑 discovery、評分或驗證。

`CURRENT_SCHEMA_ONLY_DURABLE_AUDIT`：canonical durable audit 內每個保留 run 都必須符合目前 schema 與 `public_value_v2`。不相容物件不得合併進 canonical durable audit；其追溯資訊由 Git history 保存。當輪候選仍依目前證據重新評分，不得以不相容歷史資料阻止本日 reader。

`MOBILE_COMPACT_HISTORY_SCHEMA_RULE`：mobile-native durable audit 的精簡 V2 candidate 是歷史 continuity cache profile，可省略 verbose `grading_evidence`、逐頁 `source_audit`、`candidate_urls`、`reason_code` 與 `grade_reason`；full-runtime 載入時仍重驗保留的六項分數、fact-ID 證據、加權總分、grade status、來源 ID 與 selected mapping。此精簡 profile 永遠不得作為最新 run；最新 run 必須保存完整 run-scoped candidate audit，缺少上述完整證據即驗證失敗。每個 source coverage row 都保存 scan／coverage 狀態欄位；歷史本機 scan 路徑可為 `null`，validator 只對最新且 `scan_status=completed` 的 row 強制可讀 evidence path。

### Public Value V2 填寫與驗證順序

`PUBLIC_VALUE_V2_NORMALIZED_WEIGHTED_SCORING`

`news-source-pool.json.ranking` 是唯一評分設定來源；程式不得另外寫死權重。每個去重後語意事件依下列順序填寫，順序不可倒置：

1. 完成 `semantic_event_id`、`event_identity` 與 `temporal_review`，確認事件是本輪新事件、持續現況或實質更新。
2. 對照十四天 `continuity`，先寫出可核實 facts；每筆指定唯一 `fact_id`、fact type、來源、信心與 consequence class。
3. 將 fact ID 完整且互斥地放入 `consequence_evidence.realized`、`ongoing`、`potential`、`speculative`。預期／推測不可改寫成現況。
4. 六項 `dimension_evidence` 只能引用 fact ID：Impact／Scope／Urgency 只接受 realized 或 ongoing；Structural 才可接受高可信且列明制度機制的 potential；speculative 一律不可計分。
5. 六項各填 0–100，標準使用 10 分錨點；使用 5 分中點時填 `midpoint_rationales`。以 30%／20%／15%／15%／10%／10% 計算 `weighted_score`，並令 `importance_score` 完全相同。
6. Update 達 70 時填 `delta_facts` 的 previous state、current state、why material；同一 fact 支撐三項以上時填 `cross_dimension_rationales`。
7. 任一單項達 70，為該項填 `high_score_challenges`；總分達 70，另填 `overall_high_score_challenge`，具體回答相較 B+ 多出的已發生後果。只能以 `outcome=sustained` 保留高分；`rescore_required` 必須先重評。
8. 政策事件填 `policy_stage` 與既有 `policy_governance_review`。證據按階段要求：rumor 只需可歸屬報導與來源限制，不得編法律依據或官方行動；consideration 必須有官方正在評估的證據，但可無法律文本；proposal 及後續階段才要求相應法律／正式程序證據。proposal 沒有硬上限，但高 Impact 必須有已發生後果；尚無操作效果時 `direct_operational_effects=[]`，潛在效果只放在 `consequence_evidence.potential`，不能為過 schema 編造 actual effect。
9. `border_conflict_review` 與 `ongoing_conflict_review` 各自保留語義但只在適用時填詳細欄位；不適用事件只填 `{"applies": false}`。
10. 另填 `evidence_confidence` 0–100 與 high 80–100／medium 60–79／low 0–59 `confidence_band`；信心不得乘進 importance。
11. event identity、temporal review、十四天 continuity、dimension evidence、政策審查（適用時）、高分反查、算式與 grade mapping 全部通過後，才可寫 `grade_status=validated`。degraded run 可保留 provisional candidate pool，但 Reader、manifest 與 publisher 只接受 validated。

六項加權後仍使用既有級距：E 0、D 20、C- 40、C 45、C+ 50、B- 55、B 60、B+ 65、A- 70、A 75、A+ 80、S- 85、S 90、S+ 94、SS 97。災害死亡只設定 Impact floor：1–9／10–49／50–99／100–249／250–2,499／2,500+ 分別為 30／45／60／75／90／100，不直接指定總等級。

正式 manifest 的每個事件必須保存並與 audit 一致：`scoring_method=public_value_v2`、`validated_importance_score`、`validated_grade`、`grade_status=validated`、`evidence_confidence`、`confidence_band`。`scripts/manage_candidate_audit.py` 驗證證據與計分，`scripts/validate_news_brief.py` 拒絕非 validated Reader 事件，`scripts/publish_news_brief.py` 驗證 audit／manifest 完全相等。

先建立只含本輪 selected event skeleton 的 manifest，再以唯一 canonical binder 寫入正式分數；不得手抄或由後段 stage 重算：

```bash
<bundled-python> scripts/materialize_event_manifest.py \
  --audit <run-scoped-candidate-audit.json> \
  --manifest <event-manifest-skeleton.json> \
  --output <news-event-manifest.json>
```

### Source and verification evidence

- Discovery coverage 只記 GDELT、CNA、China News Service 的實際成功／失敗與快照；事件驗證來源依主張角色動態選取。
- 每個 selected event 依類型使用原始／官方／專業／獨立證據。多家媒體轉載同一 wire、新聞稿或匿名說法只算一條證據鏈。
- 一個可靠來源仍可發布，但必須顯示來源限制；缺官方紀錄不自動否決即時事件，爭議數字與歸因保持暫定。

### Reader structure

canonical reader 固定依 `news-brief-template.md`：

1. 第一行：`# 每日新聞讀者版`
2. 下一個非空白行：manifest 衍生的 `統計期間：...`
3. 六項評級說明
4. `## 今日總覽`：按板塊用 `編號｜時間｜事件｜等級` 表格列出全部 selected events
5. `## 逐條詳報`：每則使用 `事件編號. 標題 - 等級`，依序輸出 `時間／來源／地圖／資料圖表／圖片／事件細節／各方說法／分析`；時間、來源、事件細節與分析必填，視覺與各方說法依 manifest 條件式顯示
6. `## 後續觀察`：逐項逐字使用 manifest `detail.follow_up` 的具體條件

`CANONICAL_THREE_PART_READER_LAYOUT_GATE`：上述三個二級標題與順序是唯一發布路徑。簡化的「分區標題 → 標題｜評級 → 摘要 → 評級評論」版型不得發布。兩則詳報間固定一條 `---`；最後一則後不放分隔線。

reader 不顯示 run id、commit、後台 counts、十四天 audit 或修復紀錄。對話名稱可為「每日新聞」，但不能在 reader 前另加 `YYYY/MM/DD 每日新聞` 或手填總數摘要。沒有實際可見附件時省略對應視覺欄位，不得顯示圖片說明或其他占位文字。

### Media evidence and completion

`IMAGE_PROXY_ORIGINAL_URL_UNWRAP_GATE`：圖片 URL 若為 resize、redirect、縮圖或媒體代理，必須逐層 URL-decode 其 `url`、`u`、`src`、`source`、`image` 等常見參數，並嘗試內嵌原始 JPEG／WebP及保留內嵌來源參數的最小代理 URL。代理 URL timeout／拒絕不代表原圖失敗；所有已偵測候選尚未實際開啟前，`direct_media_url_attempted` 不得為 `true`，也不得進入圖片 blocker。

`NON_SHORT_CIRCUIT_IMAGE_DELIVERY_GATE`：較早事件的圖片未交付不得中止後續事件的圖片取得或交付嘗試。所有入選事件都必須各自完成 delivered、source exhaustion 或 delivery unavailable 判定；已有 native image ref／圖片卡的事件必須實際嘗試，禁止以 `native_card_available_but_canonical_reader_blocked_by_prior_event` 或同義狀態跳過。整輪 blocker 與恢復清單只能在逐則處理完成後彙整，且必須列出所有未交付事件。

`MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE`：圖片證據依執行模式走兩條既有能力路徑，不新增狀態機。full-runtime 逐則完成來源檢查、下載、失敗後的同來源截圖、檔案驗收與附件交付；無本機 runtime 的 mobile-native 逐則完成來源檢查、文章直接媒體 URL、原生圖片搜尋／圖片卡及後續來源嘗試與宿主可提供的結構化交付結果。mobile-native 不得捏造本地路徑、下載、截圖、物化、附件或像素驗收。

`DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE`：圖片搜尋結果／原生圖片卡不是唯一合法取得路徑。檢查原引用文章時，必須解析與核對內文 `img`、`srcset`、`og:image` 或等價媒體欄位；若其中存在與當期事件相符的直接 JPEG／WebP URL，必須實際以宿主可用的媒體路徑開啟／取得該媒體並嘗試可見交付。搜尋卡沒有 image ref 不等於圖片不可取得；已知原圖 URL 卻未實際嘗試此路徑時，不得宣告 `NATIVE_MEDIA_UNAVAILABLE` 或 source exhaustion。外部 URL、Markdown 圖片字串或純文字連結本身仍不算可見交付。

`IMAGE_FALLBACK_EXHAUSTION_GATE`：原引用來源、原始圖片 URL、原生圖片卡或單一媒體交付失敗都不是圖片 blocker。每則事件在宣告 `NATIVE_MEDIA_UNAVAILABLE`、`source_exhausted` 或停止視覺 stage 前，必須依序實際搜尋原引用來源、官方機關／當事組織、原始通訊社及其他可靠媒體的同事件合法刊載／轉載圖片。圖片可以不是原文同一張，只要來源可信、合法公開刊載、可追溯，且事件、日期、人物／地點一致；圖片證據來源與文字驗證來源不必相同。每則 `image-evidence.json` 必須保存 `original_source_attempted`、`direct_media_url_attempted`、`official_fallback_attempted`、`wire_fallback_attempted`、`reliable_media_fallback_attempted`、`qualified_image_found`、`delivery_attempted` 與 `delivery_result`。`delivery_unavailable` 或 `source_exhausted` 的 `direct_media_url_attempted` 必須為 `true`；任一來源層尚未實際搜尋時，不得宣告 fallback exhaustion、圖片不可取得或不可恢復 blocker。直接文章原圖已成功可見交付時，不必再做無增量的後續來源搜尋。

`NATIVE_MEDIA_CAPABILITY_FALLBACK`：兩種模式都只有在完成 `IMAGE_FALLBACK_EXHAUSTION_GATE` 的四層來源搜尋、至少找到一張合格圖片，且自身所有可執行交付路徑均已實際失敗後，才可把最後一哩宿主限制記為 capability limitation；不得把它寫成 `last_error`，也不得重跑新聞流程。完成四層搜尋後仍沒有合格圖片是 `no_usable_image_after_source_exhaustion`，不是 `NATIVE_MEDIA_UNAVAILABLE`。一旦已確認存在合格來源圖片而交付失敗，同一 run 必須保持 `status=running`、`current_stage=visuals-completed`，不得進入 reader 正式交付或 canonical completed；只把圖片交付切換到既有 full-runtime，以已確認的來源圖片 URL 下載、失敗後截圖及本機附件接續。

- 每則先檢查已引用來源的 `og:image`、`src/srcset`、內文圖與官方產品圖；仍無結果時依序查官方機關／當事組織、原始通訊社與其他可靠媒體的同事件報導，可查多個來源而不限一個。
- full-runtime 先下載實際媒體檔；下載失敗才截取同一來源頁／官方產品頁的合規畫面。取得的本機檔必須通過 MIME、解碼、尺寸、SHA-256、時間與內容相關性檢查，再實際使用宿主支援的附件／媒體路徑。
- mobile-native 先依 `DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE` 嘗試文章原圖，再使用原生圖片搜尋／圖片卡與後續來源；保存來源、事件與日期核對、交付嘗試及宿主結構化結果。不能僅因搜尋卡沒有 image ref 或未看到特定工具名稱就判 `NATIVE_MEDIA_UNAVAILABLE`，也不能聲稱已完成本機檔案或像素驗收。
- 圖片來源可與文字驗證來源不同；合格條件是可信、合法公開刊載、可追溯，且與同一事件、日期、人物或地點一致。找到某來源頁有圖，不代表後續只能從該頁取得；單一路徑失敗必須繼續下一層 fallback。
- capability-degraded mobile recovery 必須保存逐則來源檢查與原生交付嘗試，`last_error=null`，並清楚表示未完成 pixel machine verification。`image_evidence_artifact` 的 Git blob SHA 只證明 evidence 已持久化，不證明內容已通過語義或像素機器驗證。
- manifest 對 `map` 與 `images` 都必須保存 `claim_critical`。來源確實沒有合格圖片時，一般配圖可 `omitted` 並只保存後台原因；但只要已確認存在合格來源圖片，是否 `claim_critical` 都不能把交付失敗降級成正式完成。

## 七、局部恢復指令

### full-runtime：Manifest 前

```bash
<bundled-python> scripts/news_run_checkpoint.py plan --input <checkpoint>
```

只重跑回報的最早未完成 stage。source route、hydration batch、selection 或 audit 已完成且 hash 未變的產物不得清空。

### full-runtime：Manifest 後

```bash
<bundled-python> scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

只修 `verification`、`map`、`charts`、`images` 或 `render/validate` 中的失敗事件／欄位。stage patch 以 `scripts/apply_event_stage_patch.py` 合併；不得用 shell 字串直接改 manifest。`recover_news_run.py` 沒有 `--checkpoint` 參數，checkpoint 由 `news_run_checkpoint.py` 維護。

### mobile-native：既有 ledger 內恢復

mobile-native 沒有 checkpoint 或 manifest。查證不足時依 `VERIFICATION_FEEDBACK_REWIND_GATE` 停留在 `selection-verified` 並更新同一份 run-scoped audit；視覺或 Reader 中斷時由 ledger 綁定的 candidate audit、verification、map decisions、image evidence 與 Reader 從 first incomplete stage 接續。不得倒退 stage、不得跳級、不得建立替代 run。

`RUN_ARTIFACT_IDENTITY_GATE`：排程實際觸發後先完成 capability routing，再由 actual executor 的 `prepare` 以 `full-runtime` 或 `mobile-native` 一次性固定 `execution_mode`；repository 不建立 future reservation，mode 其後不可切換。`window` 在 `schedule-prepared` 必須為 null；第一次進入 `executor-started` 時，以該次實際執行時刻固定 `end`、倒推精確 24 小時得到 `start`，並保存該 task 的時區，之後同一 occurrence 不得重新計算或修改。`main_sha` 在 `main-pinned` 前必須為 null，進入 `main-pinned` 時必須已設定，且同一 `scheduled_for` 不可再改變。每個 active artifact binding 都必須攜帶並符合 current ledger 的 `run_id`、`main_sha` 與 `window`；candidate audit、verification、map decisions、image evidence 與 Reader 不得另行建立時間窗。任何身分不一致或尚未到對應 stage 卻綁定未來 artifact 時立即拒絕，不得 repin、mode switch、migration 或 compatibility bypass。

`VISUAL_DELIVERY_ONLY_RECOVERY`：只有已完成四層圖片來源 fallback、至少找到一張合格圖片，且所有宿主可用交付方式均實際失敗後，`NATIVE_MEDIA_UNAVAILABLE` 才能存在於同一歷史或診斷 run 的 `status=running`、`current_stage=visuals-completed`，且必須已有本輪 image evidence binding。此 run 的 `execution_mode` 仍保持 `mobile-native`；若使用者明確在具能力環境接續，full-runtime 只讀既有 candidate audit、verification、map decisions、image evidence 與已確認的來源圖片 URL，只補下載／截圖／物化／可見附件交付。這不是 mode switch，也不代表系統保證存在未來 worker；不得重跑 discovery、scoring、verification、建立 new run 或變更 event IDs。

`QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL`：所有 C 級以上事件只要已確認存在合格來源圖片，交付失敗就必須停在上述視覺恢復；`claim_critical=false` 不得把 delivery failure 改寫成 omitted 或完成文字 Reader。只有完整 source exhaustion 證明不存在合格圖片時，非關鍵圖片才可 omitted。

`FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE` 同樣不是新聞 recovery target。保留既有 `logs/latest-candidate-audit.json`，保存本輪 run-scoped candidate audit，將 durable merge 交給日後具備適合 runtime 的維護步驟；當輪仍從 manifest／驗證繼續。

## 八、首次測試

排程建立後立即手動執行一次，至少檢查：

- `VISIBLE_LOCAL_ATTACHMENT_INSTALL_SMOKE_GATE` 已在啟用 recurrence 前，以 verified workspace 的 `maps/generated/taiwan-counties-yellow-v2.png` 完成本機附件交付，且圖片在目前對話中實際可見；否則不得啟用排程。

- fresh main 經雙端點與 fresh nonce 解析，同輪沒有混用 SHA。
- bootstrap receipt 在 checkpoint 前通過；checkpoint init 含 `--bootstrap-receipt`。
- 三條 discovery routes 如實記錄，沒有另一組預先固定的驗證來源池要求。
- 語意事件、scored／selected counts 已由本輪事件陣列重算；可取得文章列層證據時再檢查 source-row 守恆，無法取得時明確標未驗證而不捏造。
- run-scoped candidate audit 與 durable 十四天 cache 分開記錄；durable merge 延後不會進入 `last_error`。
- 所有 C 級以上事件都在 canonical reader，且第一行為 `# 每日新聞讀者版`。
- reader 依序只有 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察`，事件 ID 與必填欄位完整，沒有日期前綴、手填數量摘要或後台修復文字。
- map decision、chart decision 與每則 image check 均已執行；full-runtime 下載失敗有截圖備援證據，mobile-native 有文章直接媒體 URL、原生圖片／圖片卡及後續來源嘗試結果。
- 各執行模式已實際嘗試自身可用的附件／原生圖片交付；不能未嘗試就宣告 `NATIVE_MEDIA_UNAVAILABLE`，mobile-native 也不得捏造本地流程。
- full-runtime 的宣稱附件實際存在且像素驗證通過；mobile-native 的 capability degradation 記在 delivery profile、不是 `last_error`，但只要包含 `NATIVE_MEDIA_UNAVAILABLE` 就必須停在同一 run 的視覺恢復，不可 `status=completed`。
- 最終訊息包含完整 saved reader，不是摘要或只說 GitHub 已保存。

可執行 runtime 時，installation completion 只跑 capsule 內實際存在的 runtime smoke validation，並一律使用已驗證的 `<bundled-python>`：

```bash
<bundled-python> scripts/validate_news_brief.py manifest --input <manifest>
<bundled-python> scripts/validate_news_brief.py brief --manifest <manifest> --input <reader>
<bundled-python> scripts/validate_map_decisions.py --input <manifest>
```

`tests/` 明確不屬於 runtime capsule；完整 `python3 -m unittest discover -s tests -v` 只適用完整 source checkout／repository maintenance／CI，不是 Scheduled Task 安裝完成 gate。runtime smoke validation 失敗只修失敗環節，不重新詢問已確認偏好，不重跑已完成新聞階段。若 real runtime 不可用，必須明確標示未執行的驗證；不能假稱通過。

## 分享方式

接收者在自己的 desktop/local-project 新對話貼上 repo 網址與啟動指令，各自授權建立排程並保存個人偏好。公開 repo 的讀取不要求 GitHub 帳號。full-runtime 的外部 diagnostic ledger 可依既有規則 best-effort 降級；可恢復的 durable mobile-native 診斷或歷史 run recovery 必須具備 `run-logs` 寫入權限，缺少寫入權限時不得宣稱 durable resume／continuity。一次性 reader 可在當前執行完成，但不屬於正式循環排程 profile。

