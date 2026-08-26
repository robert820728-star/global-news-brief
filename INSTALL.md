# 每日新聞安裝與操作指引

本文件是本 repository 的唯一安裝入口，也是新對話第一次使用時的操作教程。它負責說明讀取順序、排程安裝、兩種執行模式、完整每日流程、必填產物、驗證與局部恢復。每日讀者版不得包含本文件的安裝或後台內容。

## 安裝目標

1. 只詢問必要偏好，建立名為「每日新聞」的每日獨立排程。
2. 每輪重新解析最新 `main`，同一輪固定使用一個經雙端點確認的 commit。
3. 依宿主能力選擇 `full-runtime` 或 `mobile-native`，兩者都必須產生可驗證的 canonical reader。
4. 新聞發現使用 GDELT、中央社與中新社三條 discovery routes；事件驗證依事件與主張角色動態選取原始、官方／主要及真正獨立的證據。
5. 首次安裝後立即執行一次測試，驗證排程、完整讀者版、執行紀錄及目前模式可交付的視覺。

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
| 4 | `mobile-chatgpt-daily-prompt.md` | Scheduled Task／mobile-native 的詳細每日執行契約 |
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

`news-source-pool.json` 必須只預先設定 GDELT、CNA、China News Service 三條 `discovery_sources`。評分後的驗證來源由事件與主張角色決定，不得另設一組預先固定的驗證來源清單。

## 二、只詢問三件事

1. 監控板塊：是否自訂國家或區域？未自訂使用台灣（TWN）、中國（CHN）、世界（GLB）。
2. 主題偏好：是否提高或降低特定主題權重？未指定沿用 repository 預設，偏好不能降低證據、安全或驗證門檻。
3. 執行時間：每天幾點？優先使用帳號／裝置時區；無法判斷才追問時區，預設每日 06:00。

輸出語言沿用使用者已設定語言，否則使用安裝對話主要語言。國家板塊使用 ISO 3166-1 alpha-3；區域使用穩定不衝突的三碼。本輪 normalized audit 以有序 `section_scopes` 保存每個板塊的 `code`、`member_country_codes` 與唯一 `fallback`；事件板塊只能由其內容確認的 `country_codes` 對照這份權威決定，不得硬編碼成 TWN／CHN／其他皆 GLB。取得建立排程的授權後，直接完成安裝與首次測試，不再分階段重複詢問同一決定。

## 三、執行模式與完成條件

| 項目 | `full-runtime` | `mobile-native` |
|---|---|---|
| 適用環境 | 可執行 bundled Python、物化檔案與 canonical publisher | Scheduled Task／無本機 runtime 的一般 ChatGPT 宿主 |
| 新聞流程 | 完整執行 | 完整執行；不得因缺少本機工具省略 discovery、語意評分、驗證或 reader |
| 地圖／圖表／圖片 | `claim_critical=true` 的視覺必須物化並完成檔案／像素驗證；非關鍵視覺失敗可 omitted | 同一規則；先執行宿主可用的原生／本機媒體路徑，不支援的非關鍵視覺以 capability omission 記錄 |
| canonical 完成 | `full-assets`，所有宣稱的附件通過 | `full-assets` 或 `reader-canonical-capability-degraded` 均可 `status=completed` |
| `NATIVE_MEDIA_UNAVAILABLE` | 若必要附件仍缺少，屬未完成的視覺 stage | 只能在「原圖下載 → 下載失敗才截圖 → 已取得檔案後實際附件交付」均有證據且最後一哩仍失敗時記錄；它是 `capability_limitations`，不是 `last_error` |
| 後續補圖 | 局部恢復該視覺 stage | 可由 full-runtime 只補缺少視覺；不得建立新 run 或重跑新聞、評分與驗證 |

不能因工具清單沒有特定名稱的 media API，就預先宣告無法交付。已有可解碼、尺寸與 SHA-256 通過的本機 JPEG／WebP 時，必須先實際嘗試宿主支援的本機附件或本機媒體呈現方式。外部圖片網址不能冒充附件；但合格本機檔案也不能被規則無條件禁止。

## 四、建立排程與板塊底圖

依 [daily-schedule-prompt.md](daily-schedule-prompt.md) 建立每日獨立排程：名稱與結果對話名稱均為「每日新聞」，每次建立新結果對話；24 小時窗從實際執行時刻精確倒推。個人偏好保存在使用者自己的排程設定，不回寫公共 `main`。

板塊確定後：

1. 檢查 `maps/generated/sections/<CODE>-base.json`。
2. 缺少時以 `scripts/initialize_section_basemaps.py` 建規格；國家板塊由 `scripts/fetch_admin_boundaries.py` 取得 geoBoundaries gbOpen ADM1，不寫國家特例。
3. 可執行 runtime 時產生 PNG／SVG 並視覺驗收；未實際產圖只能標 `spec_ready`，不能標 `ready`。
4. 每日事件仍由 `build-news-maps` 判斷點位、範圍、路線或局部圖；板塊底圖不能直接冒充事件地圖。

## 五、完整每日執行流程

下表是不可省略的主順序。`stage completed` 必須有具名 artifact 與 SHA-256；不能只寫一個完成字串。

| 階段 | 必讀／輸入 | 必填產物與驗證 | 完成或恢復條件 |
|---|---|---|---|
| -1 fresh main 與 bootstrap | `bootstrap-workspace.md`、雙端點 current main、fresh nonce、capsule manifest／payload | 經 blob SHA、payload SHA-256、runtime fingerprint 驗證的 workspace 與 `bootstrap-receipt.json` | receipt 未通過前不得建立 news checkpoint；修 bootstrap 本身，不得開始新聞搜尋 |
| 0 checkpoint init | run id、精確 24 小時窗、bootstrap receipt | `python3 scripts/news_run_checkpoint.py init --output <checkpoint> --run-id <run-id> --window-start <start> --window-end <end> --bootstrap-receipt <bootstrap-receipt>` | checkpoint 綁定本輪 main 與窗；用 `news_run_checkpoint.py plan` 找最早未完成 stage |
| 1 source-scan | `news-source-pool.json`、`source-route-config.json` | 三條 discovery route 的 snapshots、scan evidence、truthful coverage、`source-candidates.json`、`news-relevance-gate.json`、`model-source-candidates.json` | `SOURCE_SCAN_COVERAGE_SEPARATION`：`scan_status` 只表示掃描程序是否完成，`coverage_status`／`coverage_complete` 另表示來源覆蓋是否完整；每條 configured route 都留在 audit。`FULL_DISCOVERY_POOL_UNCAPPED`：中新社抓當日＋前一日日索引；CNA 依 `NextPageIdx` 翻頁；GDELT 全部分片才 `complete`，部分成功標 `degraded_partial`。已取得列完整入池，弱 signal 仍進模型 |
| 2 preprocess | model-admitted rows | `preprocessed-candidates.json`；時間窗、canonical URL、provisional article groups | 這些群組不是語意事件；失敗只重跑 preprocess |
| 3 conditional recovery | source、gate、preprocess、content hydration receipts | 預設只保存 local hash 與 checkpoint binding；`CONDITIONAL_RECOVERY_BUNDLE_POLICY` 僅在 cross-host handoff、ephemeral workspace 或 warning/timeout boundary 時，以 `manage_canonical_run_bundle.py pack-recovery` 建立六份 artifact bundle | durable workspace 可直接進入 `FIRST_SELECT_NEWS_EVENTS_EXECUTION`；必要時用 bundle `restore` 從最早缺失 artifact 繼續 |
| 4 select-news-events | hydrated rows、偏好、十四天 timeline | `selection-results.json`、唯一 `semantic_event_id`／`event_identity`、每列 `article_dispositions` | `event_evidence`、`non_news`、`unresolved`、`unresolved_exhausted` 逐列守恆；仍在恢復的 unresolved 歸零才可完成，已窮盡列保留降級證據但不阻塞其他事件；執行 `validate_local_source_admission.py` |
| 5 audit-news-candidates | selection、上一份 durable audit（若有）、`news-source-pool.json.ranking` | 本輪 run-scoped candidate audit、十四天 merge status、`public_value_v2` 的 facts／Actual-Potential 分類／六項 0–100 分數／加權總分／delta／challenge／confidence／`grade_status`／決定／`selected_event_id` | 依下方 V2 順序逐 gate 驗證；先修正可重算 counts。十四天歷史無法合併時保留舊 blob 並延後維護，但不得把 provisional 冒充 validated |
| 6 materialize-manifest | audit 中 selected C 以上且 `grade_status=validated` 的事件 | `news-event-manifest.json`，事件集合精確等於 selected ids；保存 validated score、grade、status、confidence | 只能一對一物化，不得另加／漏掉新聞；manifest 值必須精確等於 candidate audit 並綁定 checkpoint |
| 7 verify-news-events | 事件與主張類型 | stage patch、原始報導、官方／主要記錄、獨立證據鏈、claim status、source limits | 只合併 verify 欄位並執行 stage ownership validator；證據依事件與主張角色動態選取 |
| 8 build-news-maps | 已驗證事件、map policy | map decision、必要 overlay、canonical basemap、PNG／SVG | `validate_map_decisions.py`；只修失敗事件地圖 |
| 9 build-news-charts | 已驗證數據與 chart policy | 只有在比較、趨勢、比例、分布或查表有增量時建立 chart assets | 圖表不能替代地圖或來源圖片；只修失敗圖表 |
| 10 collect-news-images | 已驗證來源頁與官方產品頁 | 每則 source checks、`claim_critical`、download／screenshot attempts、`materialized-images.json`、MIME、尺寸、SHA-256、visual check、附件或 omission note | 先下載原圖，下載失敗才截圖；主張關鍵視覺未完成保持 pending，非關鍵視覺兩種方式都失敗則 omitted；兩種 runtime 都可交付已驗證文字 reader |
| 11 final manifest 與 render | collect stage 已 completed／依 profile 合法 omission | 首次執行 `validate_news_brief.py manifest` 到 `OK`；由 manifest 渲染 reader，綁定 `render.manifest` 與 `render.brief`；reader 以 `validate_news_brief.py brief --reader-layout canonical-sectioned` 驗證 | 提前呼叫 manifest validator 回 `DEFERRED` 不算通過也不算失敗；繼續原 stage 後重跑 |
| 12 publish 與 bundle | final checkpoint、manifest、audit、source pool、reader、map decisions、宣稱交付的附件 | 依下方實際 CLI 由 `publish_news_brief.py` 建立 release／receipt；再以 `manage_canonical_run_bundle.py pack` 建立 transport，與 `logs/current.json` 一次 atomic 發布後執行 `verify`／`restore` 核對 byte identity | full-runtime 由 canonical publisher fail-closed；mobile-native 依 mobile ledger schema 保存 reader/audit 與 delivery profile |
| 13 conversation delivery | release receipt 或 mobile saved reader | 完整 reader bytes、附件／能力限制 receipt、`delivery-handoff` | 不能只交摘要或驗收報告；`client_confirmed` 只有外部明確回執才可使用 |

`SCHEDULED_OCCURRENCE_SINGLE_RUN_GATE`：mobile ledger 以 `scheduled_for` 作 occurrence key。同一 occurrence 的 `current.json` 只要存在，就沿用原 `run_id` 並從 first incomplete stage 接續；即使 reader 已保存但尚未 `delivery-handoff`，也不得 rotate、建立 replacement run 或重跑新聞階段。只有 `scheduled_for` 嚴格較晚的下一個真實每日 occurrence 才可把仍非 terminal 的前輪標為 `interrupted_by_next_run`。

`VERIFICATION_FEEDBACK_REWIND_GATE`：核心主張 `finding=insufficient` 時，verification 必須 `status=failed`，不得進 ready reader。完成既定驗證恢復後仍不足，執行 `python3 scripts/news_run_checkpoint.py rewind --input <checkpoint> --output <checkpoint> --stage audit-news-candidates --reason "<evidence failure>"`；只清除 audit 與其後 stage bindings，保留 source-scan、preprocess 與 semantic selection，將受影響候選重評或排除後重新物化 manifest。不得建立新 run 或重跑 discovery。

Stage 12 與 13 的 full-runtime 指令介面如下；`--artifact` 對每個必要 run artifact 重複一次。`release` 是 publisher 產物，不是子命令：

```bash
python3 scripts/publish_news_brief.py --checkpoint <checkpoint> --manifest <final-manifest> --audit <candidate-audit> --source-pool news-source-pool.json --brief <reader> --output-dir <release-dir>
python3 scripts/manage_canonical_run_bundle.py pack --run-id <run-id> --transport-dir <transport-dir> --manifest <bundle-manifest> --artifact checkpoint=<checkpoint> --artifact reader=<reader> --artifact release-receipt=<release-dir>/release-receipt.json
python3 scripts/manage_canonical_run_bundle.py verify --manifest <bundle-manifest> --transport-dir <transport-dir>
python3 scripts/manage_canonical_run_bundle.py restore --manifest <bundle-manifest> --transport-dir <transport-dir> --output-dir <restore-proof-dir>
python3 scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint> --conversation-transport
```

`pack` 命令列出的三個 `--artifact` 只是語法示例，不是完整清單；實際發布必須把本輪 candidate audit、完整 `article_dispositions`、image evidence、materialized images、map decisions、checkpoint、counts、event manifest、reader、attachments index、release receipt 及其他宣稱交付的附件全部逐項加入。完成 `pack` 後先 `verify`，上傳 transport 與 `logs/current.json` 的單一 atomic commit，再從該 commit 下載並 `restore`；只有重組後 byte identity 一致才可執行 Stage 13。

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
python3 scripts/materialize_event_manifest.py \
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
4. 唯一一個 `## 今日總覽`，按板塊列出全部 selected events
5. 依相同板塊順序輸出單項新聞：`標題｜評級 → 實際可見附件（若有）→ 新聞摘要 → 評級評論與段末來源`；沒有附件時不得顯示圖片說明或其他視覺占位文字。

reader 不顯示 run id、commit、後台 counts、十四天 audit、修復紀錄或「逐條詳報」欄位卡。對話名稱可為「每日新聞」，但不能在 reader 前另加 `YYYY/MM/DD 每日新聞` 或手填總數摘要。

### Media evidence and completion

`NATIVE_MEDIA_CAPABILITY_FALLBACK`：只有在逐則完成來源圖片取得、下載失敗後的同來源截圖備援、檔案驗收與實際附件交付嘗試後，mobile-native 才可把最後一哩宿主限制記為 capability limitation；不得把它寫成 `last_error`，也不得重跑新聞流程。

- 每則先檢查已引用來源的 `og:image`、`src/srcset`、內文圖與官方產品圖；仍無結果時依序查官方機關／當事組織、原始通訊社與其他可靠媒體的同事件報導，可查多個來源而不限一個。
- 先下載實際媒體檔；下載失敗才截取同一來源頁／官方產品頁的合規畫面。
- 取得的本機檔必須通過 MIME、解碼、尺寸、SHA-256、時間與內容相關性檢查。
- 通過後先實際使用宿主支援的本機附件／本機媒體／原生媒體路徑；不能僅因未看到特定工具名稱就判 `NATIVE_MEDIA_UNAVAILABLE`。
- capability-degraded mobile completion 必須保存逐則取得與交付嘗試，`last_error=null`，並清楚表示未完成附件／像素驗收。
- manifest 對 `map` 與 `images` 都必須保存 `claim_critical`。只有視覺本身直接支撐核心主張時，缺少附件才阻擋；一般配圖／定位圖取得失敗改為 `omitted`，保存後台原因及讀者說明，文字 reader 繼續完成。

## 七、局部恢復指令

### Manifest 前

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>
```

只重跑回報的最早未完成 stage。source route、hydration batch、selection 或 audit 已完成且 hash 未變的產物不得清空。

### Manifest 後

```bash
python3 scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

只修 `verification`、`map`、`charts`、`images` 或 `render/validate` 中的失敗事件／欄位。stage patch 以 `scripts/apply_event_stage_patch.py` 合併；不得用 shell 字串直接改 manifest。`recover_news_run.py` 沒有 `--checkpoint` 參數，checkpoint 由 `news_run_checkpoint.py` 維護。

`NATIVE_MEDIA_UNAVAILABLE` 在 mobile-native 是非阻塞 capability limitation，不是 recovery target；補圖時沿用同一 run 與既有 checkpoint，只續做視覺交付。

`FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE` 同樣不是新聞 recovery target。保留既有 `logs/latest-candidate-audit.json`，保存本輪 run-scoped candidate audit，將 durable merge 交給日後具備適合 runtime 的維護步驟；當輪仍從 manifest／驗證繼續。

## 八、首次測試

排程建立後立即手動執行一次，至少檢查：

- fresh main 經雙端點與 fresh nonce 解析，同輪沒有混用 SHA。
- bootstrap receipt 在 checkpoint 前通過；checkpoint init 含 `--bootstrap-receipt`。
- 三條 discovery routes 如實記錄，沒有另一組預先固定的驗證來源池要求。
- 語意事件、scored／selected counts 已由本輪事件陣列重算；可取得文章列層證據時再檢查 source-row 守恆，無法取得時明確標未驗證而不捏造。
- run-scoped candidate audit 與 durable 十四天 cache 分開記錄；durable merge 延後不會進入 `last_error`。
- 所有 C 級以上事件都在 canonical reader，且第一行為 `# 每日新聞讀者版`。
- reader 只有一個 `## 今日總覽`，沒有日期前綴、手填數量摘要、事件 ID 或後台修復文字。
- map decision、chart decision 與每則 image check 均已執行；下載失敗有截圖備援證據。
- 已下載圖片確實先嘗試本機／原生附件交付；不能未嘗試就宣告 `NATIVE_MEDIA_UNAVAILABLE`。
- full-runtime 的宣稱附件實際存在且像素驗證通過；mobile-native 的 capability degradation 記在 delivery profile，不是 `last_error`，而且 run 可 `status=completed`。
- 最終訊息包含完整 saved reader，不是摘要或只說 GitHub 已保存。

可執行 runtime 時，使用已驗證 bundled Python 執行：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_news_brief.py manifest --input <manifest>
python3 scripts/validate_news_brief.py brief --manifest <manifest> --input <reader>
python3 scripts/validate_map_decisions.py --input <manifest>
```

測試失敗只修失敗環節，不重新詢問已確認偏好，不重跑已完成新聞階段。若 real runtime 不可用，必須明確標示未執行的驗證；不能假稱通過。

## 分享方式

接收者在自己的新對話貼上 repo 網址與啟動指令，各自授權建立排程並保存個人偏好。公開 repo 的讀取不要求 GitHub 帳號；跨日 audit 與 run ledger 的持久化依工作區或 repository 寫入權限降級，但不能阻止有效的當日 reader。
