# 手機 ChatGPT 基礎每日新聞規則

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

1. 第一個 GitHub 動作先讀取 `run-logs/logs/current.json`。05:58 守望工作已建立當天 `status=awaiting_executor` 時，沿用其中的 `run_id`，立即把目前階段更新成 `executor-started`、`status=running`。
   - `run_id` 固定為 `gnb-YYYYMMDDThhmmssZ-xxxxxxxx`：UTC 精確到秒，加 8 碼小寫十六進位隨機值。格式不符、與 manifest／讀者版不一致或沿用前輪編號時立即失敗。
2. 若當天紀錄不存在，才由本任務執行相同輪替：舊 `current.json` 若仍是 `awaiting_executor` 或 `running`，先標為 `interrupted_by_next_run` 並覆寫 `previous.json`；接著建立本輪 `current.json`。更舊的 `previous.json` 直接覆寫，不增加第三份歷史紀錄。
3. 每次用 GitHub contents API 更新同一個 `current.json`，必須先取得目前 blob SHA；檔案更新失敗時只重試一次，仍失敗就改在 Issue #3 建立或更新本輪單一留言，不得因紀錄失敗重跑已完成的新聞搜尋。
4. 每到下一個高階階段時更新一次，因此同一筆紀錄會保留「最後完成階段」和「目前執行階段」。固定順序不得倒退：`schedule-prepared`、`executor-started`、`main-pinned`、`workspace-ready`、`source-scan`、`candidate-audit`、`selection-verified`、`visuals-completed`、`reader-rendered`、`github-result-saved`、`delivery-handoff`。
5. 任一步驟失敗時，立即將 `status=failed`，並在 `last_error.code` 與 `last_error.message` 寫入精簡、可排查且不含憑證的原因。突然中斷時，GitHub 保留最後一次成功更新；下一輪會把它標成 `interrupted_by_next_run`。
6. 完成評分後，先以 UTF-8 JSON 覆寫 `run-logs/logs/latest-candidate-audit.json`，內容必須是本輪完整十四天海選清單、每筆六項分數、總分、等級、決定、理由、來源與 `selected_event_id`；將其 blob SHA 記入 `current.json.candidate_audit_artifact`。完整讀者版產生後，再以 UTF-8 Markdown 覆寫 `run-logs/logs/latest-reader.md`，並把其 blob SHA 記入 `current.json.reader_artifact`，階段才可進入 `github-result-saved`。完成這一步後才嘗試把同一份內容輸出至排程對話。
   - 讀者版日期後必須依序顯示 `執行編號：<run_id>`、`程式版本：<main_sha>`、`正式發布：是`。任何十四天清單與新聞內容都屬於這三行所識別的同一輪；不得混用舊清單。
   - `READER_TEMPLATE_STRUCTURE_GATE`：產生讀者版前必須讀取同一 pinned main 的 `news-brief-template.md`，並依該檔固定骨架輸出。非空白行順序須為日期、執行編號、程式版本、正式發布、數量摘要；讀者版只能有 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察` 三個二級標題且順序一致，不得加入 `今日重點表`、板塊二級標題、`十四天海選清單`、`驗收註記`、執行模式或其他測試／後台內容。結構不符時不得寫入 `latest-reader.md`，也不得進入 `github-result-saved`。
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
   - `TAIWAN_DOMESTIC_COVERAGE_GUARD`：台灣新聞另補查經濟產業、食藥消費安全、中央政策制度三個領域，每個領域最多 `5 results`，並只採用目前設定的台灣主要來源。找到首頁漏項時，必須用 `same-source recovery` 補齊同站文章證據後才加入 `canonical candidate audit`；不能略過查重、評分或因搜尋命中就直接抓圖片。
2. 將找到的新聞按底層事件合併，保留本輪完整海選清單。不同來源報導同一事件可合併，但每個來源網址都要保留。
3. 海選清單每一筆都要列出六項大評分、總分及一句具體理由：
   - 公共影響：0–30
   - 時效與變化：0–20
   - 影響範圍：0–15
   - 後續重要性：0–15
   - 可靠與可查證：0–10
   - 使用者關聯：0–10
   六項總和必須等於 0–100 的總分。
4. 依總分分級：`SS` 90–100、`S` 85–89、`A` 75–84、`B` 65–74、`C` 55–64、`C-` 50–54、`D` 35–49、`E` 0–34。`+`／`-` 只用於同一級距內排序，不得改變 C 級門檻。
   - 災害／事故另有絕對基準，優先於總分換算：普通地方事件未滿 50 人且無特殊意義時低於 C；50–99 人為 C；100–249 人為 B；250–2,499 人為 A-；2,500 人以上可因死亡數到 A，但僅憑死亡數不得高於 A。`DISASTER_2500_DEATHS_A_CEILING`
   - A+ 必須另有快速傳播、跨國系統衝擊、國家級失能或其他重大場外因素。`A_PLUS_REQUIRES_SEPARATE_ESCALATION_EVIDENCE`
   - Risk Group 4／四級病毒不能自動升 A+，須同時評估傳播途徑、實際擴散與系統後果。`RISK_GROUP_4_NOT_AUTOMATIC_A_PLUS`
   - 數萬至數十萬人死傷時，必須進入 S 級評估並列出伴隨的醫療崩潰、治理失能、巨量流離失所、跨境衝擊或長期結構改變。`MASS_CASUALTY_S_SYSTEMIC_IMPACT_PRESUMPTION`
   - 疫情進入 S- 或以上須為全球大流行，且具改變世界、全球轉捩點、全球制度劇變或文明／存續風險。`PANDEMIC_S_MINUS_WORLD_CHANGE_GATE`
   - COVID-19 的全球封控、旅行與供應鏈中斷及長期制度改變，是 S- 最低校正案例。`COVID_GLOBAL_LOCKDOWN_S_MINUS_REFERENCE`
   - 特殊意義包含但不限於：極大量異常失蹤、重傷或撤離；醫療、電力、交通等大規模公共系統中斷；災情仍迅速擴大且有官方時間序列證據；跨國影響或罕見災害機制；明顯監管／救援失靈或制度性風險；可能引發監控／指定區域內的軍事或其他衝突。上調必須說明具體觸發與證據。
   - 軍事／衝突事件不套用上述 50 人門檻：非監控板塊且未加權的邊境小衝突預設 D；長期戰爭的同戰線、同型態、例行傷亡更新預設 D。只有戰局反轉或實質升級、停火／和平進程改變、新國家／新戰線，或可驗證的外部系統影響，才重新評級。
5. 維護此排程對話內的十四天滾動海選清單。新增本輪候選、合併同事件更新，並移除超過十四天的項目；每筆仍須保留六項大評分、總分、等級、決定與理由。
   - `FIRST_RUN_14_DAY_AUDIT_BOOTSTRAP`：若 `run-logs/logs/latest-candidate-audit.json` 尚不存在，這是持久化格式第一次啟用，不得要求復原從未保存的前輪淘汰候選，也不得因此直接失敗。只在這一次，使用既有來源路由做一輪純文字十四天回填：按日期取得候選、同事件去重、完成六項評分，並把完整結果建立為第一份 `latest-candidate-audit.json`。圖片仍只在 C 級以上選稿完成後處理；瀏覽器仍是最後備援。
   - 首次回填若有必要來源確實無法覆蓋，才以具體來源與日期範圍失敗；完成第一份 audit 後，後續每日只合併新 24 小時候選並移除超過十四天項目，不得每天重跑十四天。
   - `FIRST_RUN_SOURCE_COVERAGE_COMPLETENESS_GATE`：首次回填必須為設定中的每一個來源各保留一筆獨立 coverage record（目前 15/15），不可只用 TWN／CHN／GLB 三筆彙總代替。任何來源 `within_window_count>0` 時，`ranked_items` 或可核對的候選網址／文章識別不得同時為空；候選必須能回指逐站來源紀錄。
   - `TYPE_CONSISTENT_COVERAGE_SANITY`：不得拿前輪來源掃描的 `raw_item_count` 與本輪去重評分後的 `deduplicated_candidate_count` 互相比較；只有同欄位、同口徑、同時間窗的數量才可作完整性警示，數量本身不得取代逐站證據。
   - `RECOVERABLE_14_DAY_BASELINE_WITHOUT_READER_BLOCK`：若舊資料沒有逐站十四天 provenance，不得把它宣稱為來源絕對窮盡，但也不得因此阻止本日讀者版。保留仍在十四天內、可核對來源且已有六項評分的候選，合併本輪完整 24 小時的 15/15 逐站掃描、去重與評分，並移除逾期項目；所有可恢復的 C 級以上仍須進讀者版。後續每日同樣滾動，十四天後舊的不可證明部分自然退出。
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
   - 只有同一張原圖也不適合公開內嵌時，才不換圖、不留下破圖，也不輸出圖片網址；直接以 `**圖片說明：**` 說明該圖內容與未內嵌原因。完全沒有可確認圖片時，也只列 `**圖片說明：**`，用一句非技術性文字說明未找到可確認且適合刊載的圖片。
   - `IMAGE_READER_VISIBLE_DELIVERY_GATE`：圖片只有在本輪排程對話的最終訊息中實際顯示為可見圖片或圖片卡，才算交付成功。Markdown 圖片語法、本機絕對路徑、`sandbox:` 路徑、外部圖片網址、空白方框或破圖圖示都不算可見圖片。
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
