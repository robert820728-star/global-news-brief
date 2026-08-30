# 新聞簡報設定

`EVERY_DAILY_NEWS_EXECUTION_GATE`：本設定只可由已通過本機附件 smoke test 的 full-runtime 用於 manual, single-run, test, first-run, recurring, or resume。文件內既有 mobile 欄位僅供解析歷史 artifacts，不授權 mobile-native 開始或推進 discovery、評分、驗證、圖片或 Reader。

## Discovery and verification split

`DISCOVERY_THEN_VERIFY`

The initial list comes from GDELT, CNA, and China News Service. `GDELT_RESILIENT_ACQUISITION` uses GDELT's official 15-minute export archives as primary discovery, permits one non-blocking DOC API request only when the archive is unavailable, and then uses a labeled last-known-good cache. A regional supplement failure degrades only its covered section. If every configured primary aggregator is unavailable, a run containing the fallback/global section may recover with verified `web_fallback` rows; those rows remain explicitly incomplete and cannot satisfy configured-route completeness. `FULL_DISCOVERY_POOL_UNCAPPED` sends every verified in-window item from a successful route into deduplication and scoring without a preset per-source top-N cutoff.

`REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE`：中央社與中新社等 `regional_supplement` 的所有精確窗內 provisional groups 必須完整出現在模型 `candidate_groups`，不得因沒有 GDELT heat、Google Trends、Google News coverage 或關鍵字命中而省略。熱度只能增加召回或安排處理順序，不能決定重要性或排除。模型輸入建立後、語意合併與六項評分前，執行 `python3 scripts/validate_local_source_admission.py --preprocessed <preprocessed-candidates.json> --selection <selection-results.json> --source-pool news-source-pool.json`；驗證失敗不得繼續。

## Same-source recovery order

`SAME_SOURCE_RECOVERY_ORDER`

The required order for every configured discovery route is: `canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot`.

- Run `scripts/recover_same_source_leads.py` for a verified coverage lead; never inject a search result directly into selection.
- `browser is the final fallback only`. It is permitted only after the direct article fetch and all configured same-site non-browser alternatives have failed and those failures were logged.
- A browser DOM snapshot must pass the same same-source host, SHA-256, publication-window, evidence, coverage, and candidate validators as direct evidence.
- Recovery applies only to the affected configured discovery route and must not restart verified routes.


## 目的

保存每日新聞簡報的編輯偏好、板塊、分級與收納標準。執行流程、候選取得、候選稽核、來源複查、地圖、資料圖表、圖片、自主恢復及欄位所有權由 repo 內九個技能負責，避免單一提示詞同時搜尋、判斷、製圖與排版。

## 排程與時間窗

- 每次以實際執行時間往前精確 24 小時搜尋新聞，不得改用自然日、昨日／今日分界或只抓凌晨至今。
- 每次執行重新讀取 repo 最新規則與排程保存的個人偏好。
- 排程與結果對話名稱依 `daily-schedule-prompt.md`；讀者版第一行固定為 `# 每日新聞讀者版`，下一個非空白行是 manifest 衍生的 `統計期間：...`。
- 測試排程不得修改或取代既有正式排程。

## 執行輸入正規化

`RUN_INPUT_NORMALIZATION_GATE`

- 使用者只需指定「依 GitHub 規定執行」、區域與監控類型；未重述的流程與品質門檻全部沿用 repository。
- 區域寫入 `sections`，監控類型寫入 `topic_weights`。國家使用 ISO 3166-1 alpha-3；跨國區域使用穩定三碼。
- 未指定區域時才使用台灣、中國、世界預設板塊；沒有完全相同主題鍵時，保留使用者原詞及最接近的主題映射，不得靜默忽略。
- 輸入正規化不得設定候選或新聞篇數上限，也不得改變六項評分公式。

## 固定模組

依下列順序執行，不得跳過、合併成一次自由寫稿或讓後段重建前段資料：

1. `daily-news-brief`：建立事件清單、調度模組、保存欄位、輸出與驗收。
2. `acquire-news-candidates`：執行三條 discovery routes、保存快照與完整窗內候選。
3. `select-news-events`：候選海選、事件聚類去重、偏好篩選與重要性評級。
4. `audit-news-candidates`：保存十四天候選決定、排除理由與持續事件比較。
5. `verify-news-events`：依事件／主張角色搜尋原始、官方與獨立證據並處理不確定性。
6. `build-news-maps`：判斷空間意義並由 full-runtime 產生需要的自製定位地圖。
7. `build-news-charts`：判斷數值比較、趨勢、比例或分布是否有助理解；依 execution mode 執行可用路徑，只有 full-runtime 可宣稱產生本機資料圖表。
8. `collect-news-images`：取得官方資訊圖與新聞配圖；full-runtime 可直接下載或直接截圖並視覺驗收，不要求原始檔或原畫質。
9. `recover-news-run`：偵測失敗或中斷，只調度失敗事件與模組重跑並重新驗證。
10. 套用 `news-brief-template.md` 並執行 `scripts/validate_news_brief.py`。

post-selection event exchange 必須遵守 `schemas/news-event-manifest.schema.json`。每個模組只能修改自己擁有的欄位；不得重新生成整份事件清單，也不得清空其他模組已完成的來源、地圖或圖片。

`news-brief-examples.md` 只在格式驗收失敗、規則維護或需要正反例時讀取，不得每次預設全文載入，也不得照抄其中事件。

## 成本、Token 與模型路由

- 可由程式確定的工作不得交給大型模型：精確時間窗、網址正規化、完全重複、十四天裁切、固定欄位檢查、理由完整性、格式與 schema 驗證。
- 海選先執行 `scripts/preprocess_news_candidates.py`；其輸出只是候選索引，不能直接決定入選或評級。
- 可選小模型只處理主題、板塊、實體與低風險標籤。預設流程不得要求使用者安裝 Ollama；未設定小模型時直接使用規則與高階模型。
- 高階模型負責所有重大或不確定候選、語意去重、公共價值、評級、最小主張、多來源矛盾、官方說法定位及最終編纂。
- 暫定 B 以上，以及政治、選舉、軍事、外交、金融市場、重大企業、重大科技、災害、疫情、公共安全、跨境或跨產業事件，必須由高階模型複核；小模型不得單獨排除。
- 使用高召回、晚淘汰原則。成本最佳化不得成為排除理由，也不得變更既有評級與收納標準。
- 每個事件獨立處理；失敗只重跑該事件與原欄位技能。避免整份候選、十四天歷史與所有來源在每次請求重複載入。
- 所有 C 級以上新聞仍完整納入，不以節省圖片成本縮減新聞或來源覆蓋。
- `IMAGE_DEFAULT_ONE_ASSET`：每則事件預設一張來源圖片；`IMAGE_SECOND_ASSET_REQUIRES_INCREMENTAL_INFORMATION`：第二張必須提供第一張沒有的範圍、數字、現場或時間資訊，最多兩張。
- `IMAGE_SOURCE_FILE_IDENTITY_GATE`：每張來源圖片同時保存文章頁 `source_url` 與實際媒體檔 `source_image_url`；實際圖片網址必須出現在同一來源頁的 `detected_image_urls` 且不得等於文章頁。直接截圖時則保存可信來源頁、截圖輸入路徑與畫面相關性證據。canonical materializer 的 `materialized-images.json` 綁定本機檔案、SHA-256 與尺寸。
- `IMAGE_PROXY_ORIGINAL_URL_UNWRAP_GATE`：來源頁圖片使用 resize／redirect／代理 URL 時，逐層解碼 `url`、`u`、`src`、`source` 或 `image` 參數並嘗試內嵌原始媒體；代理失敗而原圖未嘗試時，不得把 `direct_media_url_attempted` 設為 true。
- `VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE`／`PER_STORY_VISIBLE_IMAGE_GATE`：full-runtime 對每一則本輪入選新聞逐則執行圖片搜尋、下載或立即截圖、物化與可見性驗收；一則新聞的圖片不得替其他新聞通過。先查已引用來源，再依序查官方機關／當事組織、原始通訊社與其他可靠媒體的同事件報導，可查多個來源而不限一個。每張候選圖都要保存來源頁並核對事件與日期，不要求完全相同像素或原畫質；無法追溯的搬運站、搜尋縮圖、舊照或無關示意圖不合格。截圖是第一級合法交付路徑，不必等待原圖或 CDN 下載失敗。找到可用圖片但顯示失敗時只重做該則圖片取得／交付，不重跑新聞流程。
- `DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE`：原生圖片搜尋／圖片卡不是唯一取得路徑。原引用文章的 `img`、`srcset`、`og:image` 或等價欄位若暴露當期直接 JPEG／WebP URL，必須以宿主可用媒體路徑開啟／取得並嘗試可見交付；搜尋卡沒有 image ref 不等於不可取得，URL／Markdown 本身不算可見交付。
- `IMAGE_FALLBACK_EXHAUSTION_GATE`：上述四層是依序必查 checklist。每則 image evidence 保存 `original_source_attempted`、`direct_media_url_attempted`、`official_fallback_attempted`、`wire_fallback_attempted`、`reliable_media_fallback_attempted`、`qualified_image_found`、`delivery_attempted` 與 `delivery_result`；宣告 `NATIVE_MEDIA_UNAVAILABLE` 或 source exhaustion 前，`direct_media_url_attempted` 必須為 `true`，任一來源層未實際搜尋時不得停止圖片 stage。圖片證據來源與文字驗證來源可以不同，且可使用另一張同事件合法刊載／轉載圖片，但必須可信、可追溯，並符合事件、日期、人物／地點。直接文章原圖已成功可見交付時，不必再做無增量的後續來源搜尋。
- `NON_SHORT_CIRCUIT_IMAGE_DELIVERY_GATE`：單一事件圖片失敗不得中斷其他入選事件。所有事件都要完成自己的圖片取得與交付嘗試；已有 native image ref 的後續事件不得因前一事件 blocker 而跳過，整輪只在逐則完成後彙整全部未交付事件。
- `IMAGE_ONE_ASSET_MAY_SATISFY_BOTH_SOURCE_AND_PROFESSIONAL`：同一張合格官方／專業圖可同時滿足引用來源圖片與專業圖資要求，但兩組來源檢查紀錄都要保留。
- `IMAGE_SHA256_REUSE`：同一輪以圖片內容 SHA-256 去重，相同內容沿用一次下載、一次 `640px` 縮圖與一次驗收結果。
- `IMAGE_VISUAL_CHECK_ONCE_PER_HASH`：先做 MIME、解碼、尺寸與 SHA-256 程式檢查；每個唯一 hash 只開啟驗收一次，只有內容、日期或相關性不確定時才加深判讀。

## 動態板塊與編號

`EVENT_REGION_AND_TIME_IDENTITY_GATE`

- 候選來源的來源分桶、媒體所在地與首頁分類都不是事件地區；它們不得複製到語意事件的主要板塊。
- 每個新語意事件先保存 `event_identity.country_codes`、`primary_country_code` 與 `location_evidence`。事件板塊由 `country_codes` 對照本輪有序 `section_scopes` 決定；只有未命中任何非 fallback scope 時才進入唯一 fallback。來源是中央社、中新社或其他媒體都不得改變此映射。
- 同時保存 `event_occurred_at` 與 `material_update_at`。前者是底層事件真正發生時間，後者是本輪可驗證實質變化時間，不得用文章 `published_at` 自動代填任一欄。
- 同時保存模型產生的 `temporal_review`，逐項區分本輪新增／變更事實、重複舊事實與仍在窗內持續的當下影響。模型必須比較文章內容與十四天事件時間線；程式只驗證欄位與結論一致，不得靠文章發布日或傷亡數字關鍵字自行決定新舊。
- 已結束的舊事件若只是重新整理、回顧、週年、重刊、換標題或重複舊傷亡數字，標為 `non_news`。事件雖開始較早但確實持續跨越本輪時間窗並仍造成可驗證影響時，可列 `ongoing_current_impact`，不要求一定有新增傷亡。地區或時間無法確認則保持 `unresolved`，不得進入六項評分。
- 地區閘門通過後才計算 `core_section_relevance`；修改地區必須重做該項及總分，不得沿用錯誤板塊下的分數。

`POLICY_GOVERNANCE_EVIDENCE_GATE`

- 完成事件身分與時間資格後、六項評分前，先判斷是否涉及政策、法規、主管機關處置、平台治理或文化產業制度影響。最新一輪每個候選都要填 `policy_governance_review`；不適用時明確填 `{"applies": false}`。
- 適用時必須把法律／規範依據、主管機關行動、業者或平台實際處置、受影響行為者類別、跨機關影響、先例或外溢範圍、本輪時間窗內效果及證據網址分開記錄。先證明事件真正是什麼，再依這些事實評六項；輿論反應只能當背景。
- 未經證實的歷史指控或醜聞說法必須列入 `unverified_allegations`，與已證實事件身分、直接後果及六項分數分離，不得用來加分。
- 六項草評後必須逐項做一致性檢查。任何 `contradiction`、`unresolved` 或非 `consistent` 結果都必須退回重審，修正事件身分或重新評分後才可完成 audit。
- 同時具有官方行動、業者／平台實際效果，以及跨機關或規則外溢證據的強制度治理事件若仍低於 B，必須在 `why_not_b` 提供可核實的反向理由。這是重審要求，不是自動 B 級下限。

- 板塊由使用者偏好驅動，數量不限，可以是國家、區域、洲別、國際組織範圍或全球。
- 台灣、中國及其他國家或地區預設各自獨立；只有使用者明確要求才可合併。
- 同一事件只放入一個主要板塊。跨國系統性事件或未被其他板塊涵蓋的重要事件才放全球板塊。
- 每個板塊使用唯一的三個大寫英文字母。國家優先使用 ISO 3166-1 alpha-3；區域使用穩定且不衝突的三碼。
- 事件編號固定為 `XXX-01`、`XXX-02`。未設定偏好時使用台灣 `TWN`、中國 `CHN`、世界 `GLB`。
- 每個板塊可設定關注權重、最低等級與主題偏好；禁止設定篇數上限或總篇數目標。

## 語言與時間

- 輸出語言優先採用使用者設定；未設定時沿用當前對話主要語言。
- 繁體中文輸出時，公開欄位、標題、內文、地圖及圖片圖說皆使用繁體中文。
- 已有通行繁體中文譯名的颱風、地名、機構、疾病、政策與科技名詞，必須使用通行譯名；必要時僅在第一次出現時以括號保留原文。
- 今日總覽時間只放一個短新聞時間或統計截止時間，優先格式為 `M/D HH:MM`、`M/D 上午／下午／晚間`、`M/D`、`截至 M/D`。
- 跨日事件的發生時間、期間與階段進展放在逐條詳報，不得塞入總覽時間欄。
- 詳報時間依序使用新聞時間、事件時間、期間、更新節點；不適用者省略。
- 所有讀者可見時間先換算為本輪 `run.timezone` 指定的使用者時區；未另行設定時使用排程的 `Asia/Taipei`。
- 讀者版只顯示換算後的日期與時間，不附加 `UTC`、`GMT`、`+08:00`、`Asia/Taipei` 等時區標記；manifest 與稽核資料的 ISO 時間仍保留時區偏移供驗證。

## 候選海選

- 前期 canonical 候選優先由設定中的 discovery routes 及其同站恢復路徑取得。`GDELT` 是主要彙整入口；中央社與中新社是台灣、中國的區域補充。`GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE`：本輪包含 fallback／全球板塊時，優先要求 `role=primary_aggregator` 的 configured route 成功 materialize；GDELT 的 archive、一次 DOC API 與有效 cache 全部不可用後，可啟動受控跨來源全球搜尋。只有保存可重算 search snapshot、精確時間窗、原始文章網址與完整 article dispositions 的 `web_fallback` row 才可加入 canonical pool；該 row 必須維持 `coverage_complete=false`、`coverage_status=degraded_partial`，不得補足失敗 route 的 completeness 或冒充 GDELT。區域補充來源本身仍不能把世界零筆解釋成零事件；primary 與 `web_fallback` 都無可核實候選時，同一 run 才停在 source-scan。
- `GDELT_RESILIENT_ACQUISITION`：GDELT 官方 15 分鐘 export archives 是主要 discovery。只有預期分片全部成功才可標 `coverage_complete`；部分分片成功必須標 `degraded_partial`，不得冒充 ready/full coverage。只有 archive 不可用時才允許一次不阻塞的 DOC API 補充請求；不得為 429 等待或重試，DOC API 成功也必須標為非完整補充。兩者都不可用才採最近一次有效快取並明確標示 degraded。
- `SOURCE_SCAN_COVERAGE_SEPARATION`：`scan_status=completed` 只表示既有頁面已成功物化與驗證，不代表 coverage 完整。每條 configured discovery route 都必須保留在 candidate audit；另以 `coverage_complete`、`coverage_status`、`coverage_reason`、`missing_segments` 與 `missing_date_variants` 保存完整、部分降級、快取降級或不可用狀態。部分來源仍可貢獻已驗證候選，但不得在下游洗成 full coverage；release receipt 必須保存摘要。
- 中新社日索引固定取得執行日與前一日後再套精確 24 小時窗；中央社依 `NextPageIdx` 連續翻頁，直到跨過窗起點或來源明確耗盡。固定只抓當日頁或第一頁 500 筆都不得宣稱完整 coverage。
- `FULL_DISCOVERY_POOL_UNCAPPED`：每個成功取得的 discovery route 保存時間窗內數量、完整排序數量、實際入池數量及全部入池網址；精確 24 小時窗內已驗證的清單條目全部進入去重與評分，不設前 30、前 100 或其他預設名額。
- `TAIWAN_DOMESTIC_COVERAGE_GUARD`：中央社另對經濟／貿易／產業、食藥／消費安全、中央預算／立法／憲政三個領域各執行一次同一 24 小時窗搜尋，每個領域最多 `5 results`。中央社不可用或明顯過舊時，網頁搜尋只可尋找中央社同站文章並經同一 source-scan 證據路徑恢復，或留作後段驗證線索；不得把其他站結果直接加入 canonical 候選、繞過去重／六項評分或觸發圖片流程。
- Discovery route 條目只產生 `discovery_priority_score`、`discovery_signals` 與 `discovery_priority_reason`，用於抓取／hydration 排序，不得稱為 importance 或 `public_value_v2`。只有完成語意去重、事件身分與證據分類後的語意事件才使用 `public_value_v2`：六項各自按 0–100 給分，再依 `news-source-pool.json` 權重計算 `weighted_score`；`importance_score` 必須與加權結果完全一致。`PUBLIC_VALUE_V2_NORMALIZED_WEIGHTED_SCORING`
- Regional supplements 全數進模型；GDELT 強 signal 直接 hydration，弱 signal 進 `lightweight_semantic_review` 並仍保留在模型輸入。關鍵字與 heat 只能安排處理順序，不得在模型判讀前刪除科學、科技、資安、醫學或文化事件。
- `CURRENT_SCHEMA_ONLY_DURABLE_AUDIT`：canonical durable audit 只保留符合目前 schema 與 `public_value_v2` 的 run。不相容物件不得合併；追溯資訊由 Git history 保存。最新 run、首次出現及發生實質更新的事件都必須重新取證、評分並取得 validated status。
- `EVIDENCE_BEFORE_SCORE_GATE`：先建立唯一 `evidence_facts.fact_id`，再以 `consequence_evidence` 分成 `realized`、`ongoing`、`potential`、`speculative`，最後由六項 `dimension_evidence` 引用 fact ID。`public_impact`、直接範圍與急迫性只能引用 realized／ongoing；結構意義可引用高可信且列明制度機制的 potential；speculative 不得支撐任何分數。政策的理論覆蓋人口不得冒充已受影響人口，預期後果也不得冒充現況後果。`ACTUAL_POTENTIAL_SEPARATION_GATE`
- `material_new_development >= 70` 必須提供相對十四天 continuity 的 `delta_facts`（previous state、current state、why material）。同一 fact 支撐三個以上維度必須填 `cross_dimension_rationales`；任何單項達 70 必須有 `high_score_challenges` 且結果為 sustained；總分達 70 另須 `overall_high_score_challenge` 說明為何不能降到 B+。`HIGH_SCORE_CHALLENGE_GATE`
- 政策事件另填 `policy_stage`：rumor、consideration、proposal、draft、introduced、passed、signed、effective、implemented、measurable_effect。不得設 proposal 硬上限；但 proposal 若要取得高 Impact，仍只能引用已實際發生的後果。尚無操作效果時 `direct_operational_effects` 必須為空陣列，潛在效果留在 `consequence_evidence.potential`，不得編造 actual effect。`evidence_confidence` 與 importance 分開，僅映射 high／medium／low `confidence_band`，不得乘進總分。只有事件身分、時序、十四天 continuity、六項證據、政策審查（適用時）、高分反查、算式與級距都通過時，`grade_status` 才可為 validated；Reader 不接受 provisional。
- `border_conflict_review` 與 `ongoing_conflict_review` 各自保留其語義，但改為條件式；不適用事件只填 `{"applies": false}`，只有適用時才要求詳細分類與連續性欄位。
- Discovery route 的站內排序分數只用來維持高召回候選順序，不是最終事件分數。跨來源去重後必須依事件本身的具體後果重新完成六項評分；禁止複製來源排名分數、以「政府／全國／重大」等關鍵字代替證據，或因媒體刊登量提高最終等級。
- 所有窗內已驗證候選都進入去重與六項評分，不存在名次 cutoff、名次外強制例外或事件類型保底。大型評選活動首次停辦可作為 `structural_or_policy_significance` 與 `material_new_development` 的證據；重複停辦若沒有新增原因、制度變化或擴散影響，應依十四天 continuity 降低增量分。最終等級仍只由六項加權總分決定。
- 所有成功取得的候選清單與台灣 coverage guard 線索合併後，先按底層事件跨站、跨語言去重；去重後每個候選都必須評為 `SS` 至 `E` 並保存獨立的 `grade_reason`。
- 廣泛搜尋時間窗內的公共政策、經濟、科技、資安、國際關係、災害、公衛、公共安全、科學、自然史、文化與產業事件。
- 海選階段只建立候選資料，不撰寫讀者版段落。
- 每個候選至少保存暫定標題、來源網址、板塊、類別、新聞時間、事件時間、影響範圍及一句可能重要的原因。
- 搜尋可以分批避免工具失控，但不得設定候選總數或最終篇數上限。

## 事件去重

- 在評級前，先合併描述同一底層事件的不同標題、語言、股票代碼、更新稿與報導角度。
- 多家媒體轉載同一通訊社或新聞稿，來源網址可以保留，但證據源頭只算一個。
- 同一事件的後續更新合併成時間線；若出現新的政策決定、重大傷亡跳升、跨境擴散或結構轉折，才可視為新的發展。
- 報導數量不得直接提高重要性，也不得擠掉報導較少但更有公共價值的事件。

## 候選稽核與持續事件

- 每輪海選後使用 `audit-news-candidates` 保存全部聚類候選，滾動保留十四天。
- 每筆至少記錄暫定等級、選入／排除／合併決定、明確理由、來源覆蓋、去重關係及持續事件比較；每個 C 級以上候選（包含合併項）都必須用 `selected_event_id` 映射到本輪讀者版事件。
- `D` 是有資訊但未達簡報門檻；`E` 是低價值、舊聞、宣傳、未查證或不適合。D／E 僅供內部稽核，不得出現在讀者版。
- 讀者版自動接受 `SS` 至 `C`；`C-` 固定進候補池，不得進入 manifest 或讀者版。D／E 僅供稽核。
- 不設各等級配額，不得以同級太多、版面不足或固定篇數排除通過門檻的事件。
- 入選是逐事件絕對判定，不是候選之間的相對排名：達到板塊最低等級者全部入選，無論有 1 則或 30 則；低於最低等級者全部排除，無論當日是否沒有其他新聞。
- 單一可靠來源只記來源限制，不得單獨造成排除或降級。
- 暫定 B 以上但未入選者必須有可機讀理由；缺少理由即局部重跑海選與稽核。
- 持續事件以 `continuity_key` 比較最近十四天，記錄新增、未變、狀態轉折及本輪是否入選。
- `IMPACT_DELTA_CONTINUITY_SCORING`：持續事件的本輪評級看本日可驗證的影響力變化，不沿用最初或歷史最高等級。無新增公共影響的名人死亡、喪禮或重複報導應隨時效下降並只留稽核；颱風、地震、疾病或戰爭若有死傷增加、影響範圍擴大、傳播／戰線擴張、系統中斷或制度後果，則按新增事實上調。受控、停火、消退或數字下修可降級。不得因事件較舊而自動降級，也不得因重複刊登而維持高級；理由必須標示相對十四天基準為上升、持平或下降。
- 事件年齡本身不得設定日數等級上限。一次性事件若沒有新增後果，應由 `material_new_development`、急迫性及其他六項證據自然降低；只要仍有當下影響或實質變化，就依 `IMPACT_DELTA_CONTINUITY_SCORING` 重新計分。
- 事後發現本輪漏搜的重大事件，記為 `search_recall_failure`，供後續調整搜尋覆蓋。
- 十四天歷史是增強功能，不是執行門檻。優先讀取目前可用歷史，並保存至可持久工作區；工作區不可用但有 repository 寫入權限時才回寫 repository。
- 沒有 GitHub 帳號、寫入權限或持久工作區時，仍完成本輪候選稽核與每日簡報；持續事件比較只使用目前可讀歷史或本輪資料，不得因此中止、降級或排除事件。
- 無法保存歷史時可輸出本輪稽核附件供日後匯入；附件也不可用時只標記內部歷史未延續，不得在讀者版加入後台說明。

## 入選門檻

事件必須至少符合一項：

- 影響公共安全、治理、政策、民生、國際關係或區域穩定。
- 對經濟、市場、重大公司、供應鏈或產業結構有明確影響。
- 對科技、資安、科研、自然史或公共知識有實質意義。
- 反映平台治理、勞動條件、創作者經濟、文化制度或社會趨勢。
- 雖影響範圍有限，但具明確預警、轉折或後續追蹤價值。

不得只因新聞很新、搜尋結果很多、情緒強烈、圖片震撼或社群聲量高而入選。通過門檻就納入；未通過就刪除，不為板塊對稱或固定篇數補新聞。

## 來源搜尋原則

- 所有入選事件（C 以上）都必須主動嘗試尋找多個獨立可靠來源；C− 固定留在 reserve，不進入發布查證路徑。
- B 以上事件提高搜尋深度，優先取得官方／原始資料、主要權威媒體及有意義的不同角色觀點。
- 來源數量不決定事件等級，也不是入選硬門檻。若搜尋後只有一個可靠來源，事件仍可照常入選且評級不變。
- 單一可靠來源時，讀者版必須寫明：`目前僅找到一個可靠來源，尚無其他獨立來源交叉確認。`
- 單一來源事件使用「據某來源報導／某機構指出」等歸屬式語氣，不得將尚未交叉確認的責任歸因或因果關係寫成定論。
- 多個轉載頁面不算多來源；依證據源頭、採訪來源與資料產生者判斷獨立性。
- 詳細流程與事件類型驗證源以 `verify-news-events` 技能為準。

## 嚴重度與收納標準

評級衡量事件的公共影響、範圍、持續性與結構意義，不衡量來源數量、圖片震撼度或寫作篇幅。

- `SS`：極端全球性或系統性危機，短期內可能改變全球安全、秩序或人類發展路徑。
- `S`：嚴重國際／區域危機或重大結構轉折，可能長期改變政策、安全、產業或研究方向。
- `A`：必須注意的重大事件，例如嚴重戰爭升級、多國疾病擴散、高傷亡災害或重大政治經濟衝擊。
- `B`：重要但影響範圍仍有限的政策、經濟、科技、公衛、災害或衝突發展。
- `C`：公共影響較低但仍具明確產業、文化、平台、制度或趨勢訊號。
- `C-`：低權重但有具體資訊價值的短報。

可使用 `+`、`-` 表示相鄰級距，例如 `A+`、`A-`、`B+`、`C-`。

### 評級證據與衝突降權

- 最終等級同時評估事件整體嚴重度、精確 24 小時的實質增量、板塊相關性與結構影響，再扣除常態事件及重複更新折扣。死亡、戰爭、災害或疫情關鍵字不得單獨決定等級。
- 每個候選必須提交 fact-ID `dimension_evidence`、當輪 `delta_facts` 及適用的政策／衝突／continuity review；高分或級距邊界事件才額外要求反向 challenge。不得用模板化 `grade_reason` 或重複的上下級敘述代替證據。
- 邊境或長期衝突不得依事件類型固定為任何等級。例行小衝突通常因已實現後果、直接範圍、急迫性、制度意義與本期增量都低而自然得到低分；若實際造成重大傷亡、領土／戰線改變或外部系統中斷，必須依證據重評。
- 母事件的嚴重度不得直接繼承給本期更新；來源數量也不得升降事件等級。

### 災害、疫情與公共安全量化證據

- 相關事件必須套用 `.agents/skills/select-news-events/references/severity-rubric.md`，分別評估人命、重傷、直接受影響人口、地理範圍及關鍵系統。
- 死亡、重傷、撤離、公共系統中斷與不可逆損失是 `public_impact`、急迫性及結構影響的證據，不是直接指定最終等級的獨立門檻。未滿 50 人也可因大規模撤離、國家機能喪失或其他已驗證後果達到 C 以上；大量死亡若缺乏其他影響，也只能取得與六項證據相稱的總分。`INTEGRATED_SIX_DIMENSION_NO_HARD_CAP`
- 保守確認死亡數只設定 `public_impact` 的最低證據分：1–9 人至少 30、10–49 人至少 45、50–99 人至少 60、100–249 人至少 75、250–2,499 人至少 90、2,500 人以上為 100。這不是最終等級，也不會直接改寫其他五項。`CASUALTY_PUBLIC_IMPACT_FLOORS_V2`
- `urgency_and_safety` 另按當前危險給分：0 無立即風險、20 有限注意、40 地方應變、60 重大危險持續、80 救援窗口／必要服務承壓／風險擴張、100 失控且需要廣泛立即行動。死亡數不自動決定急迫性，避免同一傷亡重複計分。`URGENCY_SAFETY_ANCHORS_V2`
- 最終加權總分級距：E 0、D 20、C- 40、C 45、C+ 50、B- 55、B 60、B+ 65、A- 70、A 75、A+ 80、S- 85、S 90、S+ 94、SS 97。`SCORE_TO_GRADE_BANDS_V2`
- Risk Group 4／四級病毒只證明高危與控制難度之一，不能自動升 `A+`；必須同時評估傳播方式、實際擴散速度與系統後果。`RISK_GROUP_4_NOT_AUTOMATIC_A_PLUS`
- 數萬至數十萬人死傷會使重要性／嚴重程度接近最高區間，但仍須把醫療崩潰、治理失能、流離失所、跨境衝擊或長期結構改變分別放入相應項目後依總分評級，不設自動 S 級。`MASS_CASUALTY_REQUIRES_INTEGRATED_SCORING`
- 疫情若要由六項總分達 S-，通常需要全球大流行、全球制度／社會運作劇變或文明與人類存續風險等足以在多個項目取得高分的證據；病毒名稱或風險群本身不構成硬門檻。`PANDEMIC_S_MINUS_WORLD_CHANGE_EVIDENCE`
- COVID-19 的全球封控、旅行與供應鏈中斷及長期制度改變是高分校正案例，但實際等級仍由六項總分決定。`COVID_GLOBAL_LOCKDOWN_INTEGRATED_REFERENCE`
- 同一套六項算法不因事件位於外國、地方或非核心板塊而改變；只有證據更正、核心事實不可靠或事件分類錯誤時才改分並說明。
- 特殊意義包含但不限於：極大量異常失蹤、重傷或撤離；醫療、電力、交通等大規模公共系統中斷；災情迅速擴大且具成長性；跨國影響或罕見災害機制；明顯監管／救援失靈或制度性風險；可能引發監控／指定區域內的軍事或其他衝突。
- 上述後果要分別寫入相應 `dimension_evidence` 並給相稱分數；`special_significance_triggers` 只作證據索引，不另加分。媒體聲量、圖片震撼度或只因位於監控板塊不得增加分數。
- 涉及戰爭、交戰、軍事打擊、區域安全升級或國際對抗時，先做軍事／衝突分類與連續性判定，再以本輪實際新增後果完成相同六項評分。
- 大範圍必須是跨第一級行政區、全國關鍵系統或多國的直接影響；警戒覆蓋、行政區總人口、圖片震撼度及媒體形容不得代替實際影響。
- 最新一輪每個候選都必須填寫 `local_disaster_review`；不適用者只需 `{"applies": false}`。普通地方災害需記錄保守確認死亡數、特殊意義觸發與調整理由。

## 產業型文化與娛樂

- 普通藝人戀情、粉圈衝突、宣傳活動、新劇、新綜藝、一般票房或收視率原則上不列入。
- 事件若涉及平台治理、創作者收入、產業制度、勞動壓力、法規、審查、資金模型或廣泛文化影響，可依公共性收錄。
- 大型評選活動首次停辦、網文平台收費或分潤改革、遊戲法規與國際電競賽制改革等事件，必須把已發生的產業後果、制度機制及本期增量分別放入對應維度；重複事件沒有實質新增訊息時，`material_new_development` 應按十四天 continuity 降低。事件名稱與類型不得直接指定最終等級。
- 國民級、跨世代人物的重大疾病、死亡或法律事件可以短報；一般單一藝人個案除非具有制度性公共意義，否則降權。
- 高品質科普、自然史、古生物、演化、地球史與科學紀錄片可作例外短報，重點放在科學可信度與科普價值。

## 事件資料與欄位所有權

- 主控技能擁有執行資訊、板塊順序、最終狀態及讀者版輸出。
- 海選技能擁有事件編號、主要板塊、去重鍵、標題、等級及入選理由。
- 驗證技能擁有來源、主張比對、獨立來源群組、不確定性、來源限制及各方說法素材。
- 地圖技能只擁有 `map`；不得修改來源、等級、圖片或詳報內容。
- 所有板塊地圖固定保留完整板塊底圖：`TWN` 顯示完整台灣、`CHN` 顯示完整中國、`GLB` 顯示完整世界，自訂國家或區域亦顯示其完整板塊。只能疊加事件標記、標籤、路線或影響範圍；禁止裁切、局部放大或以局部定位圖替代。manifest 必須記錄完整畫布 `canvas_scope` 與 canonical `base_map`，否則發布器阻擋交付。
- 資料圖表技能只擁有 `charts`；不得製作純文字摘要卡，也不得修改或取代來源圖片。
- 圖片技能只擁有 `images`；不得修改來源、等級、地圖或詳報內容。
- 所有入選事件均固定執行來源頁圖片檢查並保存本地證據；可直接下載或直接截圖。評級只影響新聞重要度，不影響是否查圖。
- 圖片與地圖都必須另填 `claim_critical`。只有視覺本身直接支撐核心新聞主張時才可設為 `true`；來源確實沒有合格圖片或非關鍵本機生成視覺無法產生時可標記 `omitted`。已確認合格來源圖片的交付失敗不得因 `claim_critical=false` 降級成正式完成。
- `QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL`：已確認合格來源圖片後，`claim_critical` 不再參與交付決定；true 與 false 的 delivery failure 都必須停在視覺恢復，只有完整 source exhaustion 才允許非關鍵圖片 omitted。
- 地震、疫情、氣象、災害、戰爭、航運、漏油與海洋污染等類型固定啟用官方專業圖資要求；判定依事件內容，不得硬編碼事件編號。
- 地圖、資料圖表與來源圖片三組附件路徑必須兩兩獨立，任一組不得替代另一組。
- 地圖標籤必須符合輸出語言；繁體中文輸出時不得只有英文地名。
- 地圖、自製資料圖表與官方／媒體來源圖片互相獨立。任一類成功都不得讓其他類跳過檢查；自製圖表不得冒充來源圖片。非主張關鍵的圖片或地圖取得失敗可降級省略。
- 恢復技能只擁有 `recovery`、階段狀態與最終狀態；不得直接修改其他技能的事件欄位。
- 後段技能發現上游錯誤時，回報主控技能處理，不得自行重建整個事件物件。
- 單一來源限制不得導致自動降級或刪除；只有證據顯示事件內容錯誤、互相矛盾或來源本身不可靠時，才由主控重新判斷表述或收納。

## 讀者版

- 唯一 canonical reader 為 `news-brief-template.md` 的三段式版型，二級標題固定依序為 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察`；簡化的分區單項新聞版型不再是發布路徑。
- 開頭固定為 `# 每日新聞讀者版`、由 manifest 換算的統計期間與六項評級說明。
- `## 今日總覽` 依板塊列完整 `編號 | 時間 | 事件 | 等級` 表格；`## 逐條詳報` 再依 manifest 事件順序輸出所有事件，不得漏列、跨區混放或改成卡片。
- 每則固定為 `### 事件編號. 事件名稱 - 評級`，依序輸出 `時間／來源／地圖／資料圖表／圖片／事件細節／各方說法／分析`；時間、來源、事件細節與分析必填，其餘依 manifest 條件式顯示。
- 每張附件獨立成行並由下一個非空白行的圖說緊接；多張來源圖片固定為圖一、圖二直向排列，不得使用圖廊、輪播、同列圖片或疊圖。
- manifest 沒有的圖片不得出現在 reader；頁首、統計期間、板塊表格、兩則新聞之間及 reader 結尾均不得另放圖片。
- 沒有合格來源圖片時，讀者版完整省略圖片與圖說；`images.reader_omission_note` 只保留於內部 evidence／receipt。
- `## 後續觀察` 只列 manifest `detail.follow_up` 的具體條件並逐字一致，不為每則新聞硬湊通用句。

## 最終品質門檻

送出前，以 `scripts/validate_news_brief.py` 驗證事件資料與讀者版。不符合時不得送出。至少確認：

- 所有入選事件同時存在於今日總覽與逐條詳報，編號、標題、等級及順序一致。
- 後段技能沒有刪除或覆寫其他技能欄位。
- 單一可靠來源事件已顯示來源限制，但沒有因此自動降級。
- 地圖、資料圖表與圖片各自保留；前兩者不計入圖片張數，三者不得互相取代。
- 事件資料中已驗收的每張地圖、資料圖表與圖片，都按 manifest 順序實際出現在所屬新聞內，並由緊接附件的編號圖說逐一說明。
- `claim_critical=true` 的必要地圖或圖片不得省略，必須為 `ready` 且至少有一張附件；非關鍵視覺只有在來源確實沒有合格圖片或本機生成資產無法產生時可降級為 `omitted`，已確認圖片的交付失敗必須恢復。
- reader 不得包含 manifest 以外或新聞區塊以外的圖片。
- 不存在只有圖說沒有附件、空白圖、破圖、錯誤頁、過期圖資或與事件不符的圖片。
- 板塊順序、表格、空行、分隔線與繁體中文格式正確。

驗證失敗時只修正失敗欄位，再重新驗證；不得從頭重寫整份簡報。


