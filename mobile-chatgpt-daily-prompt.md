# 手機 ChatGPT 基礎每日新聞規則

## 執行輸入正規化

`RUN_INPUT_NORMALIZATION_GATE`

- 使用者只需說明依 GitHub 規定執行，並指定本輪區域與監控類型；區域正規化為 `sections`，監控類型正規化為 `topic_weights`。
- 國家優先使用 ISO 3166-1 alpha-3，跨國區域使用穩定三碼；沒有完全相同的監控鍵時保存使用者原詞與最接近的主題映射，不得靜默忽略。
- 未指定部分才使用 repository 預設；輸入正規化不得改變六項評分、C 級門檻或加入篇數上限。

## Discovery first, verification second

`DISCOVERY_THEN_VERIFY`

- Build the 24-hour candidate list from GDELT, CNA, and China News Service. GDELT is the broad global discovery feed; CNA and China News Service are regional supplements for Taiwan and China. `GDELT_RESILIENT_ACQUISITION` uses official GDELT 15-minute export archives as primary discovery. Only when the archive is unavailable may it make one non-blocking DOC API request; never wait or retry after a 429, and label any DOC result as incomplete supplemental coverage. A labeled valid cache remains the last resort. Publication continues in an explicit degraded state if a live GDELT interface remains unavailable. `FULL_DISCOVERY_POOL_UNCAPPED` transfers every verified in-window item from each successful discovery route into deduplication and scoring without a preset top-N cutoff.
- `REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE`：中央社與中新社的全部窗內 provisional groups 必須進入模型 `candidate_groups`。GDELT heat、Google Trends、Google News coverage 與關鍵字只能增加召回或排序，不能排除本地群組。只有可執行 runtime 時，才執行 `python3 scripts/validate_local_source_admission.py --preprocessed <preprocessed-candidates.json> --selection <selection-results.json> --source-pool news-source-pool.json`。`MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT`：mobile-native 直接逐一比對兩個 regional supplements 的 provisional group IDs 與每組 candidate IDs，確認 selection 完整包含且沒有新增未發現列；不符合時不得進入評分，也不得宣稱執行過 Python validator。
- A regional-supplement discovery failure does not block another covered section. When the run includes the fallback/global section, `GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE` additionally requires a successful configured primary aggregator; without it, remain at source-scan even when regional candidates exist. Cross-source web search may support same-source recovery or later verification but cannot inject canonical candidates or satisfy route coverage.
- Merge duplicates, retain source URLs, then score every candidate with the six-part rubric. The required order is: `discover -> deduplicate -> score -> independently verify selected C-or-higher events -> collect images -> render`.
- `PIPELINE_COUNT_RECEIPT`: run-scoped candidate audit 必須保存 `merged_article_row_count`、`in_window_article_row_count`、`canonical_url_count`、`provisional_title_cluster_count`、`semantic_event_count`、`scored_event_count`、`c_or_higher_scored_event_count`、`selected_event_count`，以及 `event_evidence_article_row_count`、`non_news_article_row_count`、`unresolved_article_row_count`、`unresolved_exhausted_article_row_count`，並以當輪 artifact 重算。文章列數不得稱為語意事件數；網址正規化與標題分群不是語意去重。不能取得文章列層證據時，相關欄位標成未驗證，不得捏造補數，也不得因此停止以可核實候選發布讀者版。
- `COUNT_RECEIPT_REPAIR_ONCE`：若 `semantic_event_count`、`scored_event_count`、C 級以上或 selected 小計與同檔 `events` 陣列不符，先直接依 `events` 陣列重算並覆寫這四個小計，再做一次守恆檢查；不得把 32/33 這類可重算差額升級為整輪失敗。只有事件本體、評分或 selected mapping 彼此矛盾且一次修正後仍無法判定時，才將受影響事件標為 unresolved；不重跑 discovery。
- `SEMANTIC_EVENT_LEDGER_GATE`: 只有語意事件才算新聞、才可進入六項評分。前處理的網址正規化與標題分群只產生文章層 `provisional_article_groups`，不得當成事件。選稿必須讀取文章內容或來源支援摘要，為每個真正事件建立唯一 `semantic_event_id` 與完整 `event_identity`，並逐列寫入 `article_dispositions`。每列只能是 `event_evidence`、`non_news`、`unresolved` 或 `unresolved_exhausted`；只有仍在恢復的 `unresolved` 必須歸零，原網址、同站替代路徑與最後瀏覽器證據均失敗者保留為 `unresolved_exhausted`，使內容 coverage 降級但不阻止其他已驗證事件。文章列數、網址數與標題群組數不得稱為新聞數或完成評分數。
- `EVENT_REGION_AND_TIME_IDENTITY_GATE`: 語意聚類完成後、六項評分前，從事件內容獨立建立 `country_codes`、`primary_country_code`、`location_evidence`、`event_occurred_at`、`material_update_at`、`material_update_type`、`material_update_evidence` 與 `temporal_review`。來源分桶及媒體國別不得作為事件地區；事件板塊由 `country_codes` 對照本輪有序 `section_scopes`（成員國與唯一 fallback）決定。時間資格由模型逐事件比較文章內容、十四天時間線、舊數據與本輪事實，判定 `new_event`、`ongoing_current_impact`、`material_update` 或 `old_restatement`；程式不得用文章日期或數字關鍵字代替語意判斷。已結束事件只重複舊傷亡、重新整理、回顧、週年、換標題或重刊時為 `non_news`。開始較早但有內容證明在本輪時間窗仍持續運作或造成當下影響的事件可列 `ongoing_current_impact`，不以開始日久遠自動排除，也不要求新增傷亡。缺漏或矛盾一律 `unresolved`，不得評分或刊出。
- `POLICY_GOVERNANCE_EVIDENCE_GATE`: 事件身分與時間資格確認後、六項評分前，先證明政策／法規／主管機關處置／平台治理事件真正是什麼。最新一輪每個候選必須填 `policy_governance_review`；rumor 保存可歸屬報導與來源限制但不得編法律依據或官方行動，consideration 要有官方正在評估的證據但可無法律文本，proposal 及後續階段才要求相應正式程序證據。未經證實的指控必須放入 `unverified_allegations`，不得併入事件身分、直接後果或六項分數。草評後逐項核對公共影響、範圍、結構意義與窗內增量；任何矛盾或未解都必須退回重審並重新評分。具有官方行動、實際業者效果及跨機關／外溢證據但低於 B 時，必須填具體 `why_not_b`；不得自動升 B，也不得略過反向挑戰。
- The system must score and deduplicate before independent verification. Verification dynamically selects original reporting, official or primary material, and genuinely independent evidence appropriate to the event and claim; those sources need not come from the discovery feed.
- The system must collect images only after verification. A discovery image hint is only a lead and never counts as a verified or delivered image.
- Browser/web search is limited to locating a same-source URL for a configured discovery route or original evidence for later verification. A cross-source search result cannot enter the canonical discovery pool, cannot be scored as a discovered candidate, and cannot satisfy route completeness.

### Category-appropriate verification

`CATEGORY_APPROPRIATE_EVIDENCE_ROUTE`

- Every C-or-higher candidate must be checked with evidence appropriate to the claim category. A generic news rewrite is not a substitute for the closest available primary record.
- `TECH_SCIENCE_EVIDENCE_ROUTE`: for science, medicine, and technology claims, locate the paper, journal or proceedings record, research institution material, and peer-review status. Check independent expert assessment or follow-up research when available; label preprints, press releases, and unreplicated claims explicitly.
- `CONFLICT_MULTI_SIDE_EVIDENCE_ROUTE`: for war and military claims, compare the parties' accounts and add a credible independent or third-party source when available. Casualties, battlefield gains, and attribution that cannot be cross-checked must remain clearly labelled as a party's claim.
- `DISASTER_OFFICIAL_STATISTICS_ROUTE`: for disasters and accidents, prefer timestamped statistics from disaster agencies, local authorities, emergency services, hospitals, or international organizations. Media totals are leads; when counts conflict, state the discrepancy and use the newest attributable official count without presenting it as final.
- `OFFICIAL_SOURCE_BIAS_GUARD`: official publication proves what an authority reported, not that the account is complete or impartial. For China in particular, and for any authority with an interest in the outcome, compare non-official reporting, revisions, omissions, and independent evidence. If concealment or reporting limits cannot be excluded, disclose the limitation and reduce confidence or grade when it affects the claimed significance.
- Other categories follow the same rule: economics uses official statistics, regulatory filings and market data; law uses judgments, indictments or statutes; policy uses the signed or published text; elections use election authorities plus plural observation; public health uses health agencies, international bodies and research evidence.
- `MEDIA_TRANSCRIPTION_IS_NOT_VERIFICATION`: two outlets repeating the same wire copy, press release, anonymous post, or upstream claim count as one evidence chain, not independent confirmation. Trace the shared claim to its earliest attributable record before assigning reliability.
- `DOMAIN_EXPERTISE_MATCH`: an assessment only strengthens verification when its author or institution has relevant expertise and a transparent method. General reporting may establish that a claim circulated, but cannot replace technical, scientific, legal, statistical, medical, military, or other domain evidence.
- `TIMELINESS_WITH_SOURCE_LIMIT_NOTE`: the absence of an official record does not by itself prohibit publication of a timely event. Reliable on-scene reporting, attributable imagery, or multiple genuinely independent observations may support publication, but the reader must be told which official statistics or primary records are still unavailable; disputed numbers, attribution, and technical conclusions remain provisional and receive lower verification confidence until updated.

## Same-source recovery order

`SAME_SOURCE_RECOVERY_ORDER`

The required order for every configured discovery route is: `canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot`.

- Run `scripts/recover_same_source_leads.py` for a verified coverage lead; never inject a search result directly into selection.
- `browser is the final fallback only`. It is permitted only after the direct article fetch and all configured same-site non-browser alternatives have failed and those failures were logged.
- A browser DOM snapshot must pass the same same-source host, SHA-256, publication-window, evidence, coverage, and candidate validators as direct evidence.
- Recovery applies only to the affected configured discovery route. It must not restart routes that already have verified evidence.


本規則供一般 ChatGPT Scheduled Task 使用。目標是以較低消耗完成每日基礎更新，不要求本機程式、命令列、檔案下載、地圖或資料圖表；唯一必要的 repository 寫入是下列小型執行紀錄與最新讀者版。

## 遠端執行紀錄（搜尋前先做）

使用已連接的 GitHub app，將紀錄寫在同一 repository 的 `run-logs` 分支。正常只維護 `logs/current.json`、`logs/previous.json`、`logs/latest-candidate-audit.json` 與 `logs/latest-reader.md`，不得寫入 `main`，也不得逐新聞或逐工具呼叫建立紀錄。

1. 排程外層為取得最新版規則而進行的 `external latest-main resolution` 與 pinned prompt read 不計入本段順序；它們不得讀取新聞或舊成果。載入本 prompt 後，`first runtime GitHub action` 才是讀取 `run-logs/logs/current.json`。同一 `scheduled_for` 是唯一 occurrence key：只要該 occurrence 的 current record 已存在，不論停在 `awaiting_executor`、`running`、`reader-rendered` 或其他非 terminal 階段，都沿用其中的 `run_id`、固定 `window` 與最後階段，從 first incomplete stage 接續；不得建立 replacement run、不得旋轉 current、不得重跑已完成新聞階段。05:58 守望工作已建立當天 `status=awaiting_executor` 時，第一次更新至 `executor-started`、`status=running` 的同時，以當下實際執行時刻固定 `window.end`、倒推精確 24 小時得到 `window.start`，並保存 `timezone=Asia/Taipei`；其後 resume 必須讀回相同 window，不得按恢復時刻重算。
   - `run_id` 固定為 `gnb-YYYYMMDDThhmmssZ-xxxxxxxx`：UTC 精確到秒，加 8 碼小寫十六進位隨機值。格式不符、與 run-scoped candidate audit／讀者版不一致或沿用前輪編號時立即失敗。
2. 只有 `scheduled_for` 嚴格晚於 current 的下一個真實每日 occurrence 才可輪替。此時舊 `current.json` 若仍是非 terminal，標為 `interrupted_by_next_run` 並覆寫 `previous.json`；接著建立新 occurrence 的 `current.json`。相同或較舊 `scheduled_for` 絕不可輪替；更舊的 `previous.json` 直接覆寫，不增加第三份歷史紀錄。
3. 每次用 GitHub contents API 更新同一個 `current.json`，必須先取得目前 blob SHA；檔案更新失敗時只重試一次，仍失敗就改在 Issue #3 建立或更新本輪單一留言，不得因紀錄失敗重跑已完成的新聞搜尋。
4. 每到下一個高階階段時更新一次，因此同一筆紀錄會保留「最後完成階段」和「目前執行階段」。固定順序不得倒退或跳級；每次只可留在原 stage 或前進至緊鄰的下一 stage：`schedule-prepared`、`executor-started`、`main-pinned`、`workspace-ready`、`source-scan`、`candidate-audit`、`selection-verified`、`visuals-completed`、`reader-rendered`、`github-result-saved`、`delivery-handoff`。
5. 只有會使當日本輪事件無法核實、無法完成 C 級以上 mapping 或無法產生讀者文字的錯誤，才將 `status=failed` 並寫入 `last_error`。可重算 count 差額、十四天歷史維護延後及區域補充 route 降級依各自規則處理。`GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE`：本輪包含 fallback／全球板塊時，GDELT 的 archive、一次 DOC API 與有效 cache 全部不可用，必須讓同一 run 保持 `status=running`、`current_stage=source-scan`；不得以 CNA／中新社候選把世界 coverage 缺失表示成零事件或 canonical completed。對話只能明示全球 discovery 尚未完成，不得輸出冒充完整的 Reader。突然中斷時，GitHub 保留最後一次成功更新；同一 `scheduled_for` 必須恢復該紀錄，只有下一個真實 occurrence 才能把仍非 terminal 的前輪標成 `interrupted_by_next_run`。
6. 完成評分後，將本輪精確 24 小時增量寫入 run-scoped candidate audit：`run-logs/logs/runs/<run_id>/candidate-audit.json`。它與十四天 durable history 是兩個 artifact；前者保存本輪所有已取得語意事件、六項分數、總分、等級、決定、理由、來源、`selected_event_id`、可取得的 `article_dispositions` 與 counts，不能因 durable merge 延後而刪除。Verification 完成後保存 `run-logs/logs/runs/<run_id>/verification.json`；地圖需求判定完成後保存 `run-logs/logs/runs/<run_id>/map-decisions.json`；逐則圖片路徑完成後保存 `run-logs/logs/runs/<run_id>/image-evidence.json`。完整讀者版產生後，將同一 bytes 寫入本輪 `reader.md` 與 `logs/latest-reader.md`；同時持久化 mobile-native 確實能產生的 image evidence、map decisions、run-scoped audit、reader 與 ledger reference，最後才原子更新 `logs/current.json`。不得建立或冒充通過只適用 full-runtime 本機附件契約的 `news-event-manifest.json`。進入 `selection-verified` 前 `candidate_audit_artifact` 必須綁定本輪 run-scoped candidate audit；進入 `visuals-completed` 前 `verification_artifact` 必須綁定本輪 `verification.json`；進入 `reader-rendered` 前 `map_decisions_artifact` 與 `image_evidence_artifact` 必須分別綁定本輪 `map-decisions.json` 與 `image-evidence.json`；進入 `github-result-saved` 前 `reader_artifact` 必須綁定 `logs/latest-reader.md`；`durable_audit_artifact` 才指向 `logs/latest-candidate-audit.json`。這些既有 binding 只證明已完成成果可由同一 run 恢復，不宣稱其內容另經新的 machine validator 驗證。
   - `RUN_ARTIFACT_IDENTITY_GATE`：本 mobile occurrence 必須由 watchdog 以 `execution_mode=mobile-native` 建立，mode 此後不可切換。`window` 在 `schedule-prepared` 為 null，第一次進入 `executor-started` 時固定，之後不可更換；`main_sha` 在 `main-pinned` 前必須為 null，進入 `main-pinned` 時必須已設定且之後不可更換。每個 active binding 必須保存與 current 相同的 `run_id`、`main_sha` 與 `window`；candidate audit、verification、map、image 與 Reader 均不得另算時間窗。stage 尚未到達時對應 artifact 必須為 `null`。不一致時拒絕 binding，不得 repin、切換 mode 或沿用前版 artifact。
   - 核心主張在 verification 恢復後仍為 `insufficient` 時，mobile-native 保持 `current_stage=selection-verified`，不得前進 visuals。更新同一 run 的 `candidate-audit.json`，重評或以 `unreliable_or_unverified` 排除受影響候選，更新 `candidate_audit_artifact` 的 Git blob SHA，再重新 verification。不得執行 stage regression，不得建立 mobile checkpoint 或 manifest，也不得重跑 discovery、preprocess 或 semantic selection。
   - 執行編號、程式版本與正式發布狀態只保存在 run-scoped audit、image evidence、ledger 與 `logs/current.json`，不得顯示於讀者版。
   - `READER_TEMPLATE_STRUCTURE_GATE`：產生讀者版前必須讀取同一 pinned main 的 `news-brief-template.md`，並依該檔固定骨架輸出。讀者版必須以「每日新聞讀者版」、統計期間及六項評級說明開頭，其後依序只有 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察`；不得加入十四天海選清單、驗收摘要、執行模式或其他測試／後台內容。結構不符時不得寫入 `latest-reader.md`，也不得進入 `github-result-saved`。
   - `CANONICAL_TODAY_OVERVIEW_NO_OMISSION_GATE`：`## 今日總覽` 內每個有新聞的板塊都必須保留 `編號｜時間｜事件｜等級` 四欄總清單並列出該區全部入選事件。不得省略、跨區集中或重新設計。
   - `CANONICAL_THREE_PART_READER_LAYOUT_GATE`：`## 逐條詳報` 依 run-scoped candidate audit 的 selected event 順序輸出每則事件，標題為「事件編號. 事件名稱 - 等級」，固定欄位順序為 `時間／來源／地圖／資料圖表／圖片／事件細節／各方說法／分析`；時間、來源、事件細節、分析必填，其餘依本輪實際交付條件顯示。沒有實際可見附件時省略對應視覺欄位，不得顯示圖片說明、caption 或占位文字。兩則事件之間必須有 `---`；`## 後續觀察` 必須是由本輪已驗證事實導出的具體追蹤項目，不得使用空泛占位。`MOBILE_READER_STRUCTURE_EQUIVALENT`：mobile-native 直接逐項核對三個二級標題及順序、overview 與 run-scoped candidate audit 的 selected event IDs 守恆、逐事件必填欄位、分隔線數量、具體 follow-up 及零附件零圖說；格式錯誤時只重做 reader render，不重跑新聞階段，也不得宣稱執行過 script validator 或 full-runtime manifest validator。
   - `READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE`：重試、429、archive 切換、去重效能、圖片補救、checkpoint 重建及其他「修復紀錄」只可寫入內部 run log／audit receipt，不得出現在讀者版、`latest-reader.md` 或其逐字對話副本。對話如需附 run receipt，只能在完整 reader 之後以一行列出 run_id 與驗收結果，不得附修復過程。
7. canonical reader、當輪新聞證據、run-scoped candidate audit 與該執行模式可執行的驗證通過後，且不存在未解決的媒體交付失敗時，輸出對話前最後一次持久更新才可為 `delivery-handoff`、`status=completed`、`delivery_status=handoff_started`。十四天 durable history 為 `updated`、`preserved_merge_deferred` 或 `current_run_only` 都不阻擋本輪完成。`MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE`：full-runtime 實際執行下載、失敗後截圖、物化驗收及附件交付；mobile-native 實際執行來源檢查、原生圖片搜尋／圖片卡嘗試並保存宿主結構化結果。`QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL`：若已確認存在合格來源圖片但 mobile-native 交付失敗，不論 `claim_critical`，都記錄 `delivery_profile=reader-canonical-capability-degraded`、`native_media_status=unavailable` 與 `capability_limitations=[NATIVE_MEDIA_UNAVAILABLE]`，保持 `status=running`、`current_stage=visuals-completed` 與 `last_error=null`；只把圖片交付切換到既有 full-runtime，不得標記 canonical completed。`VISUAL_DELIVERY_ONLY_RECOVERY` 禁止在此恢復中重跑 discovery、scoring、verification、建立 new run 或變更 event IDs。完全沒有合格來源圖片才是 source exhaustion，可在不使用該 capability code 的情況下省略圖片。不得捏造本地下載、截圖、檔案、附件或像素驗收。即使已 handoff，沒有外部明確回執時仍不得宣稱 `client_confirmed` 或手機畫面已收到。
   - `CONVERSATION_READER_BYTE_IDENTITY_GATE`：排程最終訊息必須直接交付 `logs/latest-reader.md` 的完整內容，順序與文字不得改成摘要、驗收報告、節錄或僅告知 GitHub 已保存。可以在完整 reader 之後附極短的 run receipt，但不得以 receipt 取代讀者版。若最終訊息未包含完整 reader，`delivery-handoff` 不得視為驗收通過。

紀錄格式必須符合 `schemas/mobile-run-log.schema.json`，並明確寫入 `execution_mode=mobile-native`；詳細輪替規則見 `docs/mobile-run-ledger.md`。紀錄只包含階段、時間、commit、錯誤摘要、完整海選清單位置及讀者版位置，不保存憑證、完整來源頁或圖片二進位內容。

## 固定設定

- 模式：Instant；不得自行切換到 Thinking 或 Pro。
- 排程：每天 06:00，`Asia/Taipei`。
- 預設區域：台灣、中國、全球；以排程對話中使用者最後一次設定為準。
- 加重類型：可留空；以排程對話中使用者最後一次設定為準。
- 語言：繁體中文。
- 時間窗：以實際執行時間往前 24 小時。

## 每日流程

1. 使用網頁搜尋及已連接 app 搜尋監控區域最近 24 小時的新聞。優先採用官方機關、原始資料、通訊社與可靠媒體；不得用模型記憶補新聞。
   - `TAIWAN_DOMESTIC_COVERAGE_GUARD`：中央社清單另補查經濟產業、食藥消費安全、中央政策制度三個領域，每個領域最多 `5 results`。中央社清單不可用或明顯過舊時，網頁搜尋只能定位中央社同站替代網址或供後續 verification 使用；外站搜尋結果不得建立 canonical discovery candidate、不得進入評分，也不得滿足中央社 coverage。
2. 將找到的新聞按底層事件合併，保留本輪完整海選清單。不同來源報導同一事件可合併，但每個來源網址都要保留。
3. 來源海選列只保存 `discovery_priority_score`、`discovery_signals` 與 `discovery_priority_reason`，不得產生正式 importance 或等級。完成文章 hydration、語意去重與事件身分後，才對每個語意事件使用 `public_value_v2`：先建立唯一 `evidence_facts`，分入 realized／ongoing／potential／speculative `consequence_evidence`，再由六項 `dimension_evidence` 引用 fact ID；六項各以 0–100 評分並依設定權重計算。任何單一項都不是最終等級硬上限。`PUBLIC_VALUE_V2_NORMALIZED_WEIGHTED_SCORING` `EVIDENCE_BEFORE_SCORE_GATE`
   - Impact／Scope／Urgency 只能引用 realized／ongoing；Structural 才可引用高可信且有制度機制的 potential；speculative 不得支撐任何分數。
   - Update 70 以上必填相對十四天 continuity 的 `delta_facts`；同一 fact 支撐三項以上必填 `cross_dimension_rationales`；任何單項 70 以上與總分 70 以上都須完成 sustained `high_score_challenges`。`HIGH_SCORE_CHALLENGE_GATE`
   - 政策事件填 `policy_stage`，不得把 proposal 的理論覆蓋人口當成已受影響人口；`evidence_confidence`／`confidence_band` 不乘進總分。只有全部 gate 通過才能標 `grade_status=validated`，Reader 禁止 provisional。
   - Discovery 清單原有分數只用於候選排序；跨來源去重後必須從零按事件具體後果重評六項，禁止複製清單分數或靠「政府／全國／重大」等關鍵字給分。
4. 依加權總分分級：`SS` 97–100、`S+` 94–96、`S` 90–93、`S-` 85–89、`A+` 80–84、`A` 75–79、`A-` 70–74、`B+` 65–69、`B` 60–64、`B-` 55–59、`C+` 50–54、`C` 45–49、`C-` 40–44、`D` 20–39、`E` 0–19。`SCORE_TO_GRADE_BANDS_V2`
   - 死亡、重傷、撤離、公共系統中斷、國家機能喪失、滅國／除名／失去可居住性等後果，要分別進入相應的六項分數，不得由死亡或地域直接指定等級。`INTEGRATED_SIX_DIMENSION_NO_HARD_CAP`
   - 保守確認死亡數只設定 `public_impact` 的最低證據分：1–9 人至少 30、10–49 人至少 45、50–99 人至少 60、100–249 人至少 75、250–2,499 人至少 90、2,500 人以上為 100；這不是最終等級，也不直接設定其他五項。`CASUALTY_PUBLIC_IMPACT_FLOORS_V2`
   - 急迫與安全另按當前危險評分：0 無立即風險、20 有限注意、40 地方應變、60 重大危險持續、80 救援窗口／必要服務承壓／風險擴張、100 失控且需廣泛立即行動。死亡數不自動決定急迫性。`URGENCY_SAFETY_ANCHORS_V2`
   - 重慶市長例行更替會因重要性、範圍、急迫性與結構後果低而自然落到 D；重慶遭隕石摧毀即使只命中一個行政區，也會因大量傷亡、城市毀滅、系統崩潰與不可逆損失自然升到高等級，不需要特例。
   - 小國嚴重災難可綜合達 C；國家機能喪失可達 C+／B；滅國、除名或失去可居住性可達 A。國家大小不作降分理由，以實際人口、公共系統與存續後果給分。
   - Risk Group 4／四級病毒不能自動升 A+，須同時評估傳播途徑、實際擴散與系統後果。`RISK_GROUP_4_NOT_AUTOMATIC_A_PLUS`
   - 大量傷亡會使重要性／嚴重程度接近高分，但醫療崩潰、治理失能、流離失所、跨境衝擊與長期結構改變仍須分別放入相應項目，再由總分得出等級。`MASS_CASUALTY_REQUIRES_INTEGRATED_SCORING`
   - 軍事／衝突事件先判斷是否為長期戰爭的同戰線、同型態、例行傷亡更新；這類更新因本期新進展與新增後果低而通常落到 D。若有戰局反轉、停火變化、新國家／新戰線或外部系統衝擊，按新證據重算六項，不直接繼承或套用母事件等級。
   - `IMPACT_DELTA_CONTINUITY_SCORING`：用十四天清單對照同一 `continuity_key`，本輪評級基準是本日可驗證的影響力變化，不是照抄事件最初或歷史最高等級。無新增公共影響的名人死亡、喪禮或重複報導，應因本期增量、急迫性及其他當輪證據自然下降並只留稽核，不得直接指定 D／E；原始事件的歷史評級仍保留。颱風、地震、疾病與戰爭若出現死傷增加、影響範圍擴大、傳播／戰線擴張、關鍵系統中斷或制度後果，依新增事實重新評級；反之受控、停火、疫情消退或官方下修數字時可下降。不得因事件較舊而自動降級，亦不得因新聞重複刊登而維持高級。
   - 事件年齡本身不得設定日數等級上限。一次性事件若沒有新增後果，應由 `material_new_development`、急迫性及其他六項證據自然降低；只要仍有當下影響或實質變化，就依 `IMPACT_DELTA_CONTINUITY_SCORING` 重新計分。
   - `NO_PARENT_GRADE_INHERITANCE`：合併到舊事件的新消息必須先獨立完成六項評分，不得繼承母事件的歷史最高等級。例如「中國 7 月整體經濟轉弱」可依宏觀數據評 B／B+，但後續一般縣域消費措施不得繼承母事件的 B 或 B+；若措施本身沒有明確預算、強制力、廣泛制度改變或可量化效果，預設低於 C。
   - `CEREMONIAL_AND_SINGLE_COMPANY_ROUTINE_LOW`：喪禮、降半旗、紀念活動、例行訪問、一般人事禮儀、單一公司上市、一般募資、例行財報或產品發布，通常因已實現公共後果、直接範圍、急迫性與制度增量較低而落在門檻下；仍須逐項完成六項評分，禁止依事件類型直接指定等級。全球關鍵供應、金融系統、國安、重大監管或產業控制後果成立時，依實際證據自然升高。
- `SYMBOLIC_CULTURAL_DISPUTE_LOW`：展覽名稱、館名、標示或稱謂爭議，以及主管機關口頭抗議，通常只有象徵性或有限已實現後果；仍須逐項完成六項評分，禁止依事件類型直接指定等級。撤展、參展權受限、正式外交措施、制度改變、制裁、重大跨境影響或可量化損失成立時，依實際證據重算。
- `ROUTINE_DIPLOMATIC_VISIT_LOW`：只有宣布訪問行程、會面安排或一般禮節性出訪時，通常因尚無協議、安全安排、危機處置、政策轉向或可驗證區域後果而落在門檻下；仍須逐項完成六項評分，禁止依事件類型直接指定等級。
5. 維護此排程對話內的十四天滾動海選清單。新增本輪候選、合併同事件更新，並移除超過十四天的項目；每筆仍須保留六項大評分、總分、等級、決定與理由。
   - `FIRST_RUN_14_DAY_AUDIT_BOOTSTRAP`：若 `run-logs/logs/latest-candidate-audit.json` 尚不存在，這是持久化格式第一次啟用，不得要求復原從未保存的前輪淘汰候選，也不得因此直接失敗。只在這一次，使用既有來源路由做一輪純文字十四天回填：按日期取得候選、同事件去重、完成六項評分，並把完整結果建立為第一份 `latest-candidate-audit.json`。圖片仍只在 C 級以上選稿完成後處理；瀏覽器仍是最後備援。
   - `FOURTEEN_DAY_AUDIT_COMPLETENESS_GATE`：空的 `runs` 陣列、只有當日 24 小時資料，或未涵蓋滾動視窗最早日期的資料，都只能標示 `audit_bootstrap_incomplete`；不得宣告十四天清單已完成，也不得把本輪入選數當成十四天候選總數。繼續首次回填或後續可恢復的滾動合併；這個稽核完整性狀態不得刪除或降級已驗證的本日讀者版事件。
   - 首次回填若有來源無法覆蓋，如實記錄缺少的來源與日期範圍並保存目前可核實部分；這不改判當日 run-scoped audit。完成第一份 durable audit 後，後續每日只合併新 24 小時候選並移除超過十四天項目，不得每天重跑十四天。
   - `DISCOVERY_COVERAGE_RECORD`／`SOURCE_SCAN_COVERAGE_SEPARATION`：首次回填與每日增量逐一保留 GDELT、中央社與中新社三個 configured routes。`scan_status=completed` 只表示已取得部分成功物化與驗證，不代表 coverage 完整；另保存 `coverage_complete`、`coverage_status`（`complete`／`degraded_partial`／`degraded_cached`／`unavailable`）、`coverage_reason`、`missing_segments` 與 `missing_date_variants`。failed route 使用 `scan_status=failed`、`coverage_status=unavailable` 且不得有 scan evidence。部分來源仍可貢獻已驗證候選，但不得在後段洗成 full coverage；不要求所有驗證來源逐站完成才開始評分。候選仍必須保留實際文章網址與發現來源。
   - `TYPE_CONSISTENT_COVERAGE_SANITY`：不得拿前輪來源掃描的 `raw_item_count` 與本輪去重評分後的 `deduplicated_candidate_count` 互相比較；只有同欄位、同口徑、同時間窗的數量才可作完整性警示，數量本身不得取代逐站證據。
   - `RECOVERABLE_14_DAY_BASELINE_WITHOUT_READER_BLOCK`：若舊資料沒有完整十四天 provenance，不得宣稱來源絕對窮盡，但也不得因此阻止本日讀者版。能安全合併時，保留仍在十四天內、可核對來源且已有六項評分的候選，合併本輪 24 小時 discovery 候選、去重與評分，並移除逾期項目；歷史候選只作 continuity 基準，只有本輪有實質更新且本輪評分達 C 級以上者才進本輪讀者版。
   - `MOBILE_NATIVE_AUDIT_ROLLING_MERGE`／`CURRENT_SCHEMA_ONLY_DURABLE_AUDIT`：`latest-candidate-audit.json` 已存在時，mobile-native 直接以該檔為滾動基底。canonical durable audit 只保留符合目前 schema 與 `public_value_v2` 的 run；不相容物件不合併，由 Git history 保存追溯資訊。移除超過十四天項目、按 `dedup_key`／`continuity_key` 合併本輪增量，並只重評本輪新增或有實質更新的候選。需要更新 durable audit 時，允許使用 GitHub contents API 整檔 replacement 寫回語意等同的合併結果，不要求本機程式；C 級以上事件仍須依本輪證據政策獨立驗證。這項 mobile-native 合併不得冒充 script validation，但也不得因此阻止本日讀者版。
   - `FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE`：若宿主無法安全 materialize 或合併既有 durable audit，保留其原 blob，不得覆寫、不建立新 run、不重跑 discovery／評分／驗證。把本輪 24 小時 run-scoped candidate audit 獨立保存，將 `durable_audit_status=preserved_merge_deferred` 與舊 blob 記入 `durable_audit_artifact`，繼續本輪驗證與 reader。這是歷史維護延後，不得設為 `last_error`，也不得把 `status` 改成 failed。
   - `MOBILE_NATIVE_COMPACT_DURABLE_AUDIT`：mobile-native 的 durable 十四天清單保存每日合併與 V2 重驗必要欄位：`candidate_id`、`dedup_key`、可用時的 `continuity_key`、`event_date`、`section`、`title`、`scoring_method`、`importance_breakdown`、`weighted_score`、`importance_score`、fact-ID 形式的 `dimension_evidence`、`consequence_evidence`、`evidence_facts`、`policy_stage`、`delta_facts`、challenge／rationale、`evidence_confidence`、`confidence_band`、`grade_status`、`provisional_grade`、`decision`、`reason`、`source_ids`、`selected_event_id`，以及精簡的 `continuity` 狀態與本輪影響變化。`MUST_OMIT_VERBOSE_GRADING_EVIDENCE`：此 mobile artifact 不得重複保存 verbose `grading_evidence`、逐頁 `source_audit`、`candidate_urls`、`reason_code`、`grade_reason`、文章全文或無助重驗的敘述；C 級以上仍須完成類別相稱的獨立驗證。full-runtime 可把它當成歷史 continuity profile 接回並重驗保留的 V2 facts、算式、grade status、來源 ID 與 selected mapping，但不得把精簡 profile 當成最新 run；最新 run 仍須使用完整 run-scoped audit，既有 full-runtime 接續需要完整證據時讀取對應 checkpoint。壓縮既有檔案時不得改變候選集合、六項分數、總分、grade status 或 C 級以上映射。
   - `DAILY_COVERAGE_IS_NOT_HISTORICAL_PROOF`：本日 24 小時 source coverage 只能證明本日掃描，不得冒充過去十四天逐站掃描；內部 audit 必須如實保留 `bootstrap_mode` 與各 run 的時間窗。這項限制只禁止誇大證據，不得把可用、來源可核對且符合模板的每日讀者版改判失敗。
6. 本輪 run-scoped candidate audit 內所有 C 級以上新聞都必須出現在本輪讀者版；同事件可合併成一則，但不得漏掉本輪重要更新與來源。十四天 durable history 只供 continuity 比較，沒有本輪實質更新的歷史 C 級以上事件不得被迫每日重刊。
7. 圖片內容沿用原先為該則新聞選定的圖片，不得為了縮小檔案改換另一張圖。`IMAGE_DEFAULT_ONE_ASSET`：每則預設一張內嵌圖片；`IMAGE_SECOND_ASSET_REQUIRES_INCREMENTAL_INFORMATION`：只有第二張能補充第一張未呈現的範圍、數字、現場或時間變化時才追加，並記錄新增資訊理由，每則最多兩張：
   - `IMAGE_ONE_ASSET_MAY_SATISFY_BOTH_SOURCE_AND_PROFESSIONAL`：同一張官方或專業圖若同時來自已引用來源、內容合格且能滿足專業圖資要求，可同時通過兩組檢查，不必為了形式再附一張重複新聞照；兩組檢查紀錄仍須保留。
   - `IMAGE_SHA256_REUSE`：取得圖片後先計算 SHA-256；同一輪遇到相同內容時，直接沿用已下載檔、縮圖與驗收結果，不重複下載或轉檔。
   - `IMAGE_VISUAL_CHECK_ONCE_PER_HASH`：先以 MIME、解碼、尺寸與 SHA-256 做程式檢查；每個唯一 SHA-256 只開啟並視覺驗收一次，只有相關性、日期或內容仍不確定時才再次判讀。
   - 優先使用發布者在 `srcset`、縮圖欄位或官方 CDN 明確提供的同一張圖小尺寸版本。
   - 若本輪可確實轉檔，將同一張圖縮至最長邊 `640px`，使用 JPEG 或 WebP、品質約 `75–82`，目標 `200KB` 以下；不得只改網址參數就宣稱已完成壓縮。
   - 若沒有小尺寸版本且本輪無法實際轉檔，但原始圖片是可公開讀取且不會短期失效的 HTTPS 網址，允許改放同一張原圖；「有圖可看」優先於檔案大小，不得因此中止整份新聞。
   - 圖片只以對話中可直接觀看的內嵌圖片或圖片卡呈現，並附描述畫面的替代文字；不得用圖片網址或圖片來源頁連結代替圖片。新聞事實的來源連結仍照常保留。標題、摘要與來源不得依賴圖片才能理解。
   - 不使用需要登入、限制外站引用、防盜連、含短效簽名或到期 token 的圖片網址，也不使用 `data:` 或 `blob:` 網址。
   - `MOBILE_PER_STORY_VISIBLE_IMAGE_GATE`（取代整份層級的 `MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE`）：每一則本輪入選新聞都必須逐則執行圖片搜尋與顯示驗收，一則新聞的圖片不得替其他新聞通過。逐則先檢查已引用來源頁的內文圖片、`og:image`／`srcset`、縮圖欄位與官方圖資；仍無結果時，依序檢查官方機關／當事組織、原始通訊社及其他可靠媒體的同事件報導，可檢查多個來源，不限一個，也不要求必須是完全相同像素。每張候選圖都必須保存實際圖片來源頁並核對事件與日期；不得用無法追溯的搬運站、搜尋縮圖、無關示意圖、人物舊照或來源標誌湊數。找到可用圖片卻無法顯示時，只重做該則圖片取得／交付，不重跑 discovery、評分、驗證或 reader 文字。
   - 同一張原圖不適合公開內嵌或完全沒有可確認圖片時，不換無關圖、不留下破圖、不輸出圖片網址，也不以文字描述畫面冒充附件；reader 直接省略整個圖片區塊，原因只保存於本輪 image evidence。
   - `IMAGE_READER_VISIBLE_DELIVERY_GATE`：宿主宣告具備原生媒體能力時，圖片只有在本輪排程對話的最終訊息中實際顯示為可見圖片或圖片卡，才算圖片交付成功。Markdown 圖片語法、本機絕對路徑、`sandbox:` 路徑、外部圖片網址、空白方框或破圖圖示都不算可見圖片。
   - `NATIVE_MEDIA_BLOCK_DELIVERY_GATE`：圖片先保存為實體 JPEG／WebP，完成 MIME、解碼、尺寸與內容驗收後，必須先實際嘗試宿主支援的本機附件、本機媒體呈現、`image/media content block` 或原生圖片卡。外部 HTTPS 網址與只有文字的 Markdown 不能冒充已交付圖片；但不得因工具清單中沒有某個特定名稱的 media API，就禁止已驗證的本機檔案或預先宣告無法交付。
   - `NATIVE_IMAGE_SEARCH_CARD_ROUTE`：mobile-native 對每則既有選圖使用 ChatGPT 原生圖片搜尋／媒體工具，查詢必須同時包含事件、發布者與日期，交付原生圖片卡；不得在 reader 內產生 `![alt](https://...)`。`read_thread` 可把這類原生卡表示為 `async_image_group`，但該標記本身仍不是像素驗收。
   - 若宿主提供結構化 `read_thread` 與唯讀畫面擷取，外部驗收器應確認存在非文字的 `image/media content block` 或原生 `async_image_group`，並確認實際 `rendered pixel` 區域寬高非零。若結構結果只有一般 `agentMessage text`，圖片仍未交付。沒有這些能力時必須明記 pixel machine verification 未執行；不得要求使用者目視補驗，也不得假稱已通過。
   - `NATIVE_MEDIA_CAPABILITY_FALLBACK`：不得根據工具名稱或預檢結果直接宣告 `NATIVE_MEDIA_UNAVAILABLE`。能執行 runtime 時先用 `scripts/materialize_news_images.py --input <image-candidates.json> --output-dir <materialized-image-dir> --manifest <materialized-images.json>`；原圖下載失敗才截圖，取得合格本機 JPEG／WebP 後實際嘗試附件或原生媒體交付。沒有 runtime 的 mobile-native 則逐則執行來源檢查、`NATIVE_IMAGE_SEARCH_CARD_ROUTE` 與宿主可提供的結構化交付檢查；不得捏造本地路徑、下載、截圖、物化、附件或像素驗收。完全找不到合格圖片必須記為 source exhaustion，不得冒充 `NATIVE_MEDIA_UNAVAILABLE`。若已確認存在合格來源圖片但仍需 full-runtime，保持 `status=running` 與 `current_stage=visuals-completed`，只把圖片交付切換到既有 full-runtime，不得標記 canonical completed。將 verified image evidence、取得／交付嘗試與內部 `reader_omission_note` 寫入本輪 `image-evidence.json`，並以 `image_evidence_artifact` 保存其 Git blob SHA；該 SHA只證明 evidence 已保存，不代表內容或像素已經 machine-verified。不得建立新 run或重跑新聞流程，也不得把未執行的媒體步驟寫成已完成。
   - 若無法在送出前確認圖片可見，必須移除圖片標記及其 caption，reader 不留下圖片說明、沿用前輪選圖、前輪同圖、不重新驗收或圖片待補等占位文字。
8. reader 只使用 `news-brief-template.md` 的「今日總覽＋逐條詳報＋後續觀察」三段式版型；逐條詳報必須保留事件編號與 `時間／來源／事件細節／分析` 必填欄位，不得改成簡化分區新聞卡。
9. 每則新聞的地圖、資料圖表與來源圖片依序直向排列；每張附件的下一個非空白行必須是對應的地圖一／資料圖表一／圖一／圖二圖說。禁止圖廊、輪播、同列圖片、疊圖及新聞區塊外圖片。原生圖片卡只屬對話交付層，保存於既有 image evidence／ledger，不得寫入 `images.assets`，也不得在 reader 內以外部圖片網址或虛構附件冒充。
10. `mobile-native` 無法產生地圖或圖表等本機生成資產時，可依既有非關鍵視覺規則記錄 omission；但已確認存在的合格來源圖片交付失敗時必須依 `NATIVE_MEDIA_CAPABILITY_FALLBACK` 停在同一 run 的視覺恢復。日後由 full-runtime 接續時只做該視覺階段，不得重跑新聞或改變既有 reader 事實。
11. 十四天海選清單保留在 audit artifact，不附加到 canonical reader；每筆仍保存日期、區域、標題、六項評分、總分、等級、決定、理由與來源。

只提供有來源支持的內容。GitHub 規則、搜尋或來源無法讀取時，回報實際缺口，不得假裝完成。
