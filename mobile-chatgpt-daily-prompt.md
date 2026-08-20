# 手機 ChatGPT 基礎每日新聞規則

## Discovery first, verification second

`DISCOVERY_THEN_VERIFY`

- Build the 24-hour candidate list from GDELT, CNA, and China News Service. GDELT is the broad global discovery feed; CNA and China News Service are regional supplements for Taiwan and China. `GDELT_RESILIENT_ACQUISITION` makes at most five total DOC API requests; after a 429, wait at least 120 秒, or longer when required by `Retry-After`. After a fifth failure, do not send a sixth request: fall back to official GDELT 15-minute export archives, and only then use a labeled valid cache. Publication continues in an explicit degraded state if a live GDELT interface remains unavailable. `FULL_DISCOVERY_POOL_NO_FIXED_LIMIT` transfers every verified in-window item from each successful discovery route into deduplication and scoring, with no top-30 or other fixed cutoff.
- A discovery source failure must not block the whole brief. Record the degraded source and continue when at least one discovery route or the final web-search fallback yields verifiable current candidates. Stop only when no current candidate can be verified at all.
- Merge duplicates, retain source URLs, then score every candidate with the six-part rubric. The required order is: `discover -> deduplicate -> score -> independently verify selected C-or-higher events -> collect images -> render`.
- `PIPELINE_COUNT_RECEIPT_V1`: latest candidate audit 必須保存 `merged_article_row_count`、`in_window_article_row_count`、`canonical_url_count`、`provisional_title_cluster_count`、`semantic_event_count`、`scored_event_count`、`c_or_higher_scored_event_count`、`selected_event_count`，以及 `event_evidence_article_row_count`、`non_news_article_row_count`、`unresolved_article_row_count`，並以當輪 artifact 重算。文章列數不得稱為語意事件數；網址正規化與標題分群不是語意去重。任何小計差額都必須標為未驗證，不得捏造補數，也不得因此停止以可核實候選發布讀者版。
- `SEMANTIC_EVENT_LEDGER_GATE`: 只有語意事件才算新聞、才可進入六項評分。前處理的網址正規化與標題分群只產生文章層 `provisional_article_groups`，不得當成事件。選稿必須讀取文章內容或來源支援摘要，為每個真正事件建立唯一 `semantic_event_id` 與完整 `event_identity`，並逐列寫入 `article_dispositions`。每列只能是 `event_evidence`、`non_news` 或 `unresolved`；`event_evidence` 必須指向事件，`non_news` 必須保存具體理由，`unresolved` 必須排查歸零才能完成 audit。文章列數、網址數與標題群組數不得稱為新聞數或完成評分數。
- The system must score and deduplicate before independent verification. Verification may use the original report, official material, or another reliable source from the wider source pool; it is not required to come from the discovery feed.
- The system must collect images only after verification. A discovery image hint is only a lead and never counts as a verified or delivered image.
- Browser/web search is the last discovery fallback after the three feeds, and may also be used to locate original evidence for a scored event. Search results must still be deduplicated and scored before selection.

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

+## Same-source recovery order

`SAME_SOURCE_RECOVERY_ORDER`

The required order for every configured source is: `canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot`.

- Run `scripts/recover_same_source_leads.py` for a verified coverage lead; never inject a search result directly into selection.
- `browser is the final fallback only`. It is permitted only after the direct article fetch and all configured same-site non-browser alternatives have failed and those failures were logged.
- A browser DOM snapshot must pass the same same-source host, SHA-256, publication-window, evidence, coverage, and candidate validators as direct evidence.
- Recovery applies to all configured sources. It updates only the affected source scan and coverage record; it must not restart already verified sources.


本規則供一般 ChatGPT Scheduled Task 使用。目標是以較低消耗完成每日基礎更新，不要求本機程式、命令列、檔案下載、地圖或資料圖表；唯一必要的 repository 寫入是下列小型執行紀錄與最新讀者版。

## 遠端執行紀錄（搜尋前先做）

使用已連接的 GitHub app，將紀錄寫在同一 repository 的 `run-logs` 分支。正常只維護 `logs/current.json`、`logs/previous.json`、`logs/latest-candidate-audit.json` 與 `logs/latest-reader.md`，不得寫入 `main`，也不得逐新聞或逐工具呼叫建立紀錄。

1. 排程外層為取得最新版規則而進行的 `external latest-main resolution` 與 pinned prompt read 不計入本段順序；它們不得讀取新聞或舊成果。載入本 prompt 後，`first runtime GitHub action` 才是讀取 `run-logs/logs/current.json`。05:58 守望工作已建立當天 `status=awaiting_executor` 時，沿用其中的 `run_id`，立即把目前階段更新成 `executor-started`、`status=running`。
   - `run_id` 固定為 `gnb-YYYYMMDDThhmmssZ-xxxxxxxx`：UTC 精確到秒，加 8 碼小寫十六進位隨機值。格式不符、與 manifest／讀者版不一致或沿用前輪編號時立即失敗。
2. 若當天紀錄不存在，才由本任務執行相同輪替：舊 `current.json` 若仍是 `awaiting_executor` 或 `running`，先標為 `interrupted_by_next_run` 並覆寫 `previous.json`；接著建立本輪 `current.json`。更舊的 `previous.json` 直接覆寫，不增加第三份歷史紀錄。
3. 每次用 GitHub contents API 更新同一個 `current.json`，必須先取得目前 blob SHA；檔案更新失敗時只重試一次，仍失敗就改在 Issue #3 建立或更新本輪單一留言，不得因紀錄失敗重跑已完成的新聞搜尋。
4. 每到下一個高階階段時更新一次，因此同一筆紀錄會保留「最後完成階段」和「目前執行階段」。固定順序不得倒退：`schedule-prepared`、`executor-started`、`main-pinned`、`workspace-ready`、`source-scan`、`candidate-audit`、`selection-verified`、`visuals-completed`、`reader-rendered`、`github-result-saved`、`delivery-handoff`。
5. 任一步驟失敗時，立即將 `status=failed`，並在 `last_error.code` 與 `last_error.message` 寫入精簡、可排查且不含憑證的原因。突然中斷時，GitHub 保留最後一次成功更新；下一輪會把它標成 `interrupted_by_next_run`。
6. 完成評分後，先以 UTF-8 JSON 覆寫 `run-logs/logs/latest-candidate-audit.json`，內容必須是本輪完整十四天海選清單、每筆六項分數、總分、等級、決定、理由、來源與 `selected_event_id`；將其 blob SHA 記入 `current.json.candidate_audit_artifact`。完整讀者版產生後，再以 UTF-8 Markdown 覆寫 `run-logs/logs/latest-reader.md`，並把其 blob SHA 記入 `current.json.reader_artifact`，階段才可進入 `github-result-saved`。完成這一步後才嘗試把同一份內容輸出至排程對話。
   - 讀者版日期後必須依序顯示 `執行編號：<run_id>`、`程式版本：<main_sha>`、`正式發布：是`。任何十四天清單與新聞內容都屬於這三行所識別的同一輪；不得混用舊清單。
   - `READER_TEMPLATE_STRUCTURE_GATE`：產生讀者版前必須讀取同一 pinned main 的 `news-brief-template.md`，並依該檔固定骨架輸出。讀者版必須以「每日新聞讀者版」、統計期間及六項評級說明開頭，再依設定順序逐區輸出；不得加入十四天海選清單、驗收摘要、執行模式或其他測試／後台內容。結構不符時不得寫入 `latest-reader.md`，也不得進入 `github-result-saved`。
   - `LEGACY_TODAY_OVERVIEW_NO_OMISSION_GATE`：每個有新聞的板塊開頭都必須原樣保留既有 `時間｜事件｜評級` 三欄總清單並列出該區全部入選事件；這就是今日總清單，不是可選摘要。不得省略、跨區集中或重新設計。
   - `LEGACY_SECTIONED_READER_LAYOUT_GATE`：總清單後必須在同一板塊內依序放該區新聞；每則固定為「標題｜評級 → 可見圖片或圖片說明 → 新聞摘要 → 評為X級的評論與段末來源」。不得改成欄位式逐條詳報，不得顯示事件編號，也不得產生 `時間／來源／事件細節／分析` 欄位組。送出前必須執行 `scripts/validate_news_brief.py brief --reader-layout legacy-sectioned`；格式錯誤時只重做 reader render，不重跑新聞階段。
   - `READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE`：重試、429、archive 切換、去重效能、圖片補救、checkpoint 重建及其他「修復紀錄」只可寫入內部 run log／audit receipt，不得出現在讀者版、`latest-reader.md` 或其逐字對話副本。對話如需附 run receipt，只能在完整 reader 之後以一行列出 run_id 與驗收結果，不得附修復過程。
7. 輸出對話前最後一次持久更新為 `delivery-handoff`、`status=completed`、`delivery_status=handoff_started`。這只證明新聞流程完成、讀者版已存 GitHub並開始交給 ChatGPT；目前排程沒有手機客戶端顯示回執，因此沒有外部明確回執時不得宣稱 `client_confirmed` 或手機畫面已收到。
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
   - `TAIWAN_DOMESTIC_COVERAGE_GUARD`：中央社清單另補查經濟產業、食藥消費安全、中央政策制度三個領域，每個領域最多 `5 results`。只有中央社清單不可用或明顯過舊時，才使用網頁搜尋補候選；命中仍須先查重與評分，不得因搜尋命中就直接入選或抓圖片。
2. 將找到的新聞按底層事件合併，保留本輪完整海選清單。不同來源報導同一事件可合併，但每個來源網址都要保留。
3. 海選清單每一筆都要列出六項大評分、總分及一句具體理由：
   - 重要性／嚴重程度（`public_impact`）：0–30
   - 地理／人口／公共系統直接範圍：0–20
   - 急迫與安全：0–15
   - 結構／政策意義：0–15
   - 本期實質新進展：0–10
   - 核心板塊關聯：0–10
   六項總和必須等於 0–100 的總分，且每項都要有 `dimension_evidence`。任何單一項都不是最終等級硬上限，也不得另建地域例外補丁。
   - Discovery 清單原有分數只用於候選排序；跨來源去重後必須從零按事件具體後果重評六項，禁止複製清單分數或靠「政府／全國／重大」等關鍵字給分。
4. 依總分分級：`SS` 97–100、`S+` 94–96、`S` 90–93、`S-` 85–89、`A+` 80–84、`A` 75–79、`A-` 70–74、`B+` 65–69、`B` 60–64、`B-` 55–59、`C+` 50–54、`C` 45–49、`C-` 40–44、`D` 20–39、`E` 0–19。`SCORE_TO_GRADE_BANDS_V1`
   - 死亡、重傷、撤離、公共系統中斷、國家機能喪失、滅國／除名／失去可居住性等後果，要分別進入相應的六項分數，不得由死亡或地域直接指定等級。`INTEGRATED_SIX_DIMENSION_NO_HARD_CAP`
   - 保守確認死亡數只設定 `public_impact` 的最低證據分：1–9 人至少 8、10–49 人至少 14、50–99 人至少 18、100–249 人至少 23、250–2,499 人至少 27、2,500 人以上為 30；這不是最終等級，也不直接設定其他五項。`CASUALTY_PUBLIC_IMPACT_FLOORS_V1`
   - 急迫與安全另按當前危險評分：0–3 危險已結束／無立即行動需求；4–7 地方應變進行中但風險受限；8–11 重大危險持續、仍在救援窗口或必要服務承壓；12–15 威脅擴大／失控且需要廣泛立即行動。死亡數不自動決定急迫性。`URGENCY_SAFETY_ANCHORS_V1`
   - 重慶市長例行更替會因重要性、範圍、急迫性與結構後果低而自然落到 D；重慶遭隕石摧毀即使只命中一個行政區，也會因大量傷亡、城市毀滅、系統崩潰與不可逆損失自然升到高等級，不需要特例。
   - 小國嚴重災難可綜合達 C；國家機能喪失可達 C+／B；滅國、除名或失去可居住性可達 A。國家大小不作降分理由，以實際人口、公共系統與存續後果給分。
   - Risk Group 4／四級病毒不能自動升 A+，須同時評估傳播途徑、實際擴散與系統後果。`RISK_GROUP_4_NOT_AUTOMATIC_A_PLUS`
   - 大量傷亡會使重要性／嚴重程度接近高分，但醫療崩潰、治理失能、流離失所、跨境衝擊與長期結構改變仍須分別放入相應項目，再由總分得出等級。`MASS_CASUALTY_REQUIRES_INTEGRATED_SCORING`
   - 軍事／衝突事件先判斷是否為長期戰爭的同戰線、同型態、例行傷亡更新；這類更新因本期新進展與新增後果低而通常落到 D。若有戰局反轉、停火變化、新國家／新戰線或外部系統衝擊，按新證據重算六項，不直接繼承或套用母事件等級。
   - `MATERIAL_UPDATE_48_HOUR_REENTRY_GATE`（延伸原 `MATERIAL_UPDATE_REENTRY_GATE`）：以同一事件上次進入讀者版的交付時間起算 48 小時冷卻期；不得只因仍在十四天內每天重刊。48 小時內，只有本輪新增的數字、正式決策、執行結果、制度改變、衝突升降級或其他實質進展，而且本日新增部分必須獨立達到 C 級門檻，才重新進入讀者版；但颱風、地震、疾病、戰爭、公共安全、政策或市場事件若發生死傷、範圍、傳播、戰線、關鍵系統或制度後果的實質惡化，必須立即依新增事實重新評級，不得等滿 48 小時。滿 48 小時後，必須按當下可驗證影響重新完成六項評分；仍獨立達到 C 級才可再次刊登，低於 C 則只留十四天稽核或依既有規則退場。時間經過本身不得自動重刊，也不得繼承上次或母事件等級；紀念日、重述背景或媒體回顧不算更新。
   - `IMPACT_DELTA_CONTINUITY_SCORING`：用十四天清單對照同一 `continuity_key`，本輪評級基準是本日可驗證的影響力變化，不是照抄事件最初或歷史最高等級。無新增公共影響的名人死亡、喪禮或重複報導隨時效衰退，當日本身應下調到 D／E 並只留稽核；原始事件的歷史評級仍保留。颱風、地震、疾病與戰爭若出現死傷增加、影響範圍擴大、傳播／戰線擴張、關鍵系統中斷或制度後果，依新增事實重新評級，可高於前輪；反之受控、停火、疫情消退或官方下修數字時可下降。不得因事件較舊而自動降級，亦不得因新聞重複刊登而維持高級，必須說明本輪影響力相對十四天基準上升、持平或下降。
   - `PASSIVE_ONE_OFF_FIVE_DAY_DECAY`：五日衰減只適用於事件本身已結束、沒有持續公共／制度／安全影響的一次性個人或禮儀事件，例如自然死亡、喪禮、追悼與回顧；它是評級上限，不是強迫升到該級。自首次可驗證事件日起：當日依事件本身獨立評級、次日最高 B、第三日最高 C、第四日 D、第五日 E，五個日曆日後移出活躍滾動稽核。颱風、地震、疾病、戰爭及任何仍在發展的事件不得套用機械式日數衰減；死傷、範圍、傳播、戰線、系統中斷、權力重組、暗殺證據或制度後果一有實質變化，就退出本規則，依 `IMPACT_DELTA_CONTINUITY_SCORING` 當成新實質更新重新評級，可升級。朱鎔基自然死亡若沒有權力或制度後果，依本規則退場；日後若另有實質影響，仍會以新原因重新入池。
   - `NO_PARENT_GRADE_INHERITANCE`：合併到舊事件的新消息必須先獨立完成六項評分，不得繼承母事件的歷史最高等級。例如「中國 7 月整體經濟轉弱」可依宏觀數據評 B／B+，但後續一般縣域消費措施不得繼承母事件的 B 或 B+；若措施本身沒有明確預算、強制力、廣泛制度改變或可量化效果，預設低於 C。
   - `CEREMONIAL_AND_SINGLE_COMPANY_ROUTINE_LOW`：喪禮、降半旗、紀念活動、例行訪問及一般人事禮儀，若沒有可驗證的權力重組、政策轉向、重大外交或社會後果，預設 D。單一公司上市、一般募資、例行財報或產品發布，若沒有系統性市場影響、產業控制、重大監管、國安、關鍵供應鏈或使用者指定加重關聯，也預設 D；公司知名度本身不能升到 C。
- `SYMBOLIC_CULTURAL_DISPUTE_LOW`：展覽名稱、館名、標示或稱謂爭議，以及主管機關口頭抗議，若沒有撤展或參展權受限、正式外交措施、制度改變、制裁、重大兩岸／跨境影響或可量化損失，預設 D；象徵性冒犯與媒體聲量本身不能升到 C。例如光州雙年展抹去台灣館名稱但僅有文化部抗議時，不進讀者版。
- `ROUTINE_DIPLOMATIC_VISIT_LOW`：只有宣布訪問行程、會面安排或一般禮節性出訪，若尚未簽署協議、改變制裁／安全安排、處理危機、形成政策轉向或造成可驗證的雙邊／區域後果，預設 D；官員層級與媒體關注本身不能升到 C。例如只有宣布王毅訪韓而沒有實質成果時，不進讀者版。
5. 維護此排程對話內的十四天滾動海選清單。新增本輪候選、合併同事件更新，並移除超過十四天的項目；每筆仍須保留六項大評分、總分、等級、決定與理由。
   - `FIRST_RUN_14_DAY_AUDIT_BOOTSTRAP`：若 `run-logs/logs/latest-candidate-audit.json` 尚不存在，這是持久化格式第一次啟用，不得要求復原從未保存的前輪淘汰候選，也不得因此直接失敗。只在這一次，使用既有來源路由做一輪純文字十四天回填：按日期取得候選、同事件去重、完成六項評分，並把完整結果建立為第一份 `latest-candidate-audit.json`。圖片仍只在 C 級以上選稿完成後處理；瀏覽器仍是最後備援。
   - 首次回填若有必要來源確實無法覆蓋，才以具體來源與日期範圍失敗；完成第一份 audit 後，後續每日只合併新 24 小時候選並移除超過十四天項目，不得每天重跑十四天。
   - `DISCOVERY_COVERAGE_RECORD`：首次回填與每日增量只需如實記錄 GDELT、中央社與中新社三個 discovery route 的成功或失敗；不再要求所有驗證來源逐站完成才開始評分。候選仍必須保留實際文章網址與發現來源。
   - `TYPE_CONSISTENT_COVERAGE_SANITY`：不得拿前輪來源掃描的 `raw_item_count` 與本輪去重評分後的 `deduplicated_candidate_count` 互相比較；只有同欄位、同口徑、同時間窗的數量才可作完整性警示，數量本身不得取代逐站證據。
   - `RECOVERABLE_14_DAY_BASELINE_WITHOUT_READER_BLOCK`：若舊資料沒有完整十四天 provenance，不得宣稱來源絕對窮盡，但也不得因此阻止本日讀者版。保留仍在十四天內、可核對來源且已有六項評分的候選，合併本輪 24 小時 discovery 候選、去重與評分，並移除逾期項目；所有可恢復的 C 級以上仍須進讀者版。
   - `MOBILE_NATIVE_AUDIT_ROLLING_MERGE`：`latest-candidate-audit.json` 已存在時，mobile-native 直接以該檔為滾動基底。若六項欄位、各欄範圍與總分算法未變，舊候選不得只因 main SHA、來源發現方式或驗證政策更新就被視為評分格式失效，也不得重算未發生實質更新的歷史候選。只重評本輪新增或發生實質更新的候選；移除超過十四天項目、按 `dedup_key`／`continuity_key` 合併本輪增量，並保留其餘歷史物件的既有分數、理由與來源。需要更新 durable audit 時，允許使用 GitHub contents API 整檔 replacement 寫回語意等同的合併結果，不要求本機程式；C 級以上事件仍須依本輪證據政策獨立驗證。這項 mobile-native 合併不得冒充 script validation，但也不得因此阻止本日讀者版。
   - `MOBILE_NATIVE_COMPACT_DURABLE_AUDIT`：mobile-native 的 durable 十四天清單只保存每日合併必需欄位：`candidate_id`、`dedup_key`、可用時的 `continuity_key`、`event_date`、`section`、`title`、`importance_breakdown`、`importance_score`、逐項 `dimension_evidence`、`provisional_grade`、`decision`、`reason`、`source_ids`、`selected_event_id`，以及精簡的 `continuity` 狀態與本輪影響變化。`MUST_OMIT_VERBOSE_GRADING_EVIDENCE`：此 mobile artifact 不得重複保存 verbose `grading_evidence`、逐頁 `source_audit`、文章全文或重複的驗證敘述；這些證據仍用於本輪 C 級以上獨立驗證，full-runtime 的詳細驗證與稽核規則保持不變。壓縮既有檔案時不得改變候選集合、六項分數、總分或 C 級以上 `selected_event_id` 映射。
   - `DAILY_COVERAGE_IS_NOT_HISTORICAL_PROOF`：本日 24 小時 source coverage 只能證明本日掃描，不得冒充過去十四天逐站掃描；內部 audit 必須如實保留 `bootstrap_mode` 與各 run 的時間窗。這項限制只禁止誇大證據，不得把可用、來源可核對且符合模板的每日讀者版改判失敗。
6. 本輪及十四天清單內所有 C 級以上新聞都必須出現在更新後的讀者版；同事件可合併成一則，但不得漏掉其重要更新與來源。
7. 圖片內容沿用原先為該則新聞選定的圖片，不得為了縮小檔案改換另一張圖。`IMAGE_DEFAULT_ONE_ASSET`：每則預設一張內嵌圖片；`IMAGE_SECOND_ASSET_REQUIRES_INCREMENTAL_INFORMATION`：只有第二張能補充第一張未呈現的範圍、數字、現場或時間變化時才追加，並記錄新增資訊理由，每則最多兩張：
   - `IMAGE_ONE_ASSET_MAY_SATISFY_BOTH_SOURCE_AND_PROFESSIONAL`：同一張官方或專業圖若同時來自已引用來源、內容合格且能滿足專業圖資要求，可同時通過兩組檢查，不必為了形式再附一張重複新聞照；兩組檢查紀錄仍須保留。
   - `IMAGE_SHA256_REUSE`：取得圖片後先計算 SHA-256；同一輪遇到相同內容時，直接沿用已下載檔、縮圖與驗收結果，不重複下載或轉檔。
   - `IMAGE_VISUAL_CHECK_ONCE_PER_HASH`：先以 MIME、解碼、尺寸與 SHA-256 做程式檢查；每個唯一 SHA-256 只開啟並視覺驗收一次，只有相關性、日期或內容仍不確定時才再次判讀。
   - 優先使用發布者在 `srcset`、縮圖欄位或官方 CDN 明確提供的同一張圖小尺寸版本。
   - 若本輪可確實轉檔，將同一張圖縮至最長邊 `640px`，使用 JPEG 或 WebP、品質約 `75–82`，目標 `200KB` 以下；不得只改網址參數就宣稱已完成壓縮。
   - 若沒有小尺寸版本且本輪無法實際轉檔，但原始圖片是可公開讀取且不會短期失效的 HTTPS 網址，允許改放同一張原圖；「有圖可看」優先於檔案大小，不得因此中止整份新聞。
   - 圖片只以對話中可直接觀看的內嵌圖片或圖片卡呈現，並附描述畫面的替代文字；不得用圖片網址或圖片來源頁連結代替圖片。新聞事實的來源連結仍照常保留。標題、摘要與來源不得依賴圖片才能理解。
   - 不使用需要登入、限制外站引用、防盜連、含短效簽名或到期 token 的圖片網址，也不使用 `data:` 或 `blob:` 網址。
   - `MOBILE_PER_STORY_VISIBLE_IMAGE_GATE`（取代整份層級的 `MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE`）：每一則本輪入選新聞都必須逐則執行圖片搜尋與顯示驗收，一則新聞的圖片不得替其他新聞通過。逐則先檢查已引用來源頁的內文圖片、`og:image`／`srcset`、縮圖欄位與官方圖資；仍無結果時，再檢查一個已加入來源欄且可靠的同事件來源。圖片必須在本對話實際可見、可確認與該事件相關，且不得用無關示意圖、人物舊照或來源標誌湊數。舊規則「C 級新聞可使用圖片說明」不代表可跳過逐則找圖；若讀者版含 B 以上事件，仍不得整份零張可見圖片。找到可用圖片卻無法顯示時，只重做圖片階段且限於該則，不重跑 discovery、評分、驗證或 reader 文字。
   - 只有同一張原圖也不適合公開內嵌時，才不換圖、不留下破圖，也不輸出圖片網址；直接以 `**圖片說明：**` 說明該圖內容與未內嵌原因。完全沒有可確認圖片時，也只列 `**圖片說明：**`，用一句非技術性文字說明未找到可確認且適合刊載的圖片。
   - `IMAGE_READER_VISIBLE_DELIVERY_GATE`：圖片只有在本輪排程對話的最終訊息中實際顯示為可見圖片或圖片卡，才算交付成功。Markdown 圖片語法、本機絕對路徑、`sandbox:` 路徑、外部圖片網址、空白方框或破圖圖示都不算可見圖片。
   - `NATIVE_MEDIA_BLOCK_DELIVERY_GATE`：最終交付必須是 ChatGPT 原生 `image/media content block` 或原生圖片卡，不得把外部 HTTPS 圖片寫進 `agentMessage text` 後期待 Markdown 自動渲染。圖片先保存為實體 JPEG／WebP 位元組，完成 MIME、解碼、尺寸與內容驗收後，再以上傳附件或原生媒體工具送入本對話；穩定網址、HTTP 200 與 Markdown 語法都不能取代上傳。
   - `NATIVE_IMAGE_SEARCH_CARD_ROUTE`：mobile-native 對每則既有選圖使用 ChatGPT 原生圖片搜尋／媒體工具，查詢必須同時包含事件、發布者與日期，交付原生圖片卡；不得在 reader 內產生 `![alt](https://...)`。`read_thread` 可把這類原生卡表示為 `async_image_group`，但該標記本身仍不是像素驗收。
   - 外部驗收器必須用結構化 `read_thread` 讀取本輪最終回覆，確認存在非文字的 `image/media content block` 或原生 `async_image_group`，再以唯讀畫面擷取確認實際 `rendered pixel` 圖片區域寬高非零。若只有一般 `agentMessage text`、圖片網址、Markdown、圖說，或畫面仍空白，立即判定圖片交付失敗，不得要求使用者目視補驗。
   - mobile-native 若沒有可產生原生媒體區塊的工具，必須回報 `NATIVE_MEDIA_UNAVAILABLE`，保留本輪 discovery、評分、驗證與 reader checkpoint，只把圖片交付切換到既有 full-runtime：由 full-runtime 執行 `<bundled-python> scripts/materialize_news_images.py --input <image-candidates.json> --output-dir <materialized-image-dir> --manifest <materialized-images.json>`，使用 manifest 中 `status=ready` 的本機 JPEG 實體檔以上傳附件方式交付；不得建立新 run、重跑新聞流程或只改成另一個外部圖片網址。
   - 若無法在送出前確認圖片可見，必須移除該圖片標記，改成一句非技術性的 `**圖片說明：**`；不得寫「沿用前輪選圖」、「前輪同圖」、「不重新驗收」或「圖片待補」。
8. `## 後續觀察` 每一項必須是可驗證的具體條件，包含事件編號與數值門檻、日期、決策節點或明確官方動作；不得使用「追蹤官方後續更新與實際影響」等通用占位句。

## 基礎讀者版

依序輸出：

1. `YYYY/MM/DD 每日新聞`
2. 本期總數與各區域數量
3. 今日重點表：時間、區域、標題、等級
4. 每則新聞：標題、時間、摘要、為何重要、已確認事實、不確定處、新聞來源連結，以及「同圖低解析內嵌」、「同一張原圖」或「圖片說明」；圖片區不顯示圖片網址或圖片來源頁
5. 十四天海選清單：每筆列出日期、區域、標題、六項大評分、總分、等級、決定、理由與來源

只提供有來源支持的內容。GitHub 規則、搜尋或來源無法讀取時，回報實際缺口，不得假裝完成。
