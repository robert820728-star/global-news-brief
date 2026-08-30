---
name: select-news-events
description: Discover, cluster, deduplicate, select, section, and grade news events for a rolling daily brief. Use after the time window and user preferences are known, before source verification, maps, images, or reader-facing writing.
---

# 新聞海選與評級

只建立或更新事件資料中的選題欄位，不撰寫最終簡報。

## 輸入

- 精確時間窗與時區。
- 使用者板塊、順序、主題權重與最低等級；篇數上限不是有效設定。
- repo 根目錄 `news-brief-settings.md`。
- 候選來源網址與基本中繼資料。
- `news-source-pool.json` 的 GDELT、中央社與中新社三條 discovery routes；驗證來源不使用固定數量或預設清單，而由後續技能依事件與主張角色選取。
- `work/model-source-candidates.json`，必須由 `acquire-news-candidates` 先建立完整 `work/source-candidates.json`，再經 `scripts/build_news_relevance_gate.py` 逐列守恆路由並通過兩份 schema 與逐站證據驗證。

## 流程

## 執行層級

先以 `work/model-source-candidates.json` 執行 `python3 scripts/preprocess_news_candidates.py`，以程式完成時間窗檢查、網址正規化、完全重複及高相似標題聚類。程式輸出只作為候選索引，不得直接決定入選、排除或評級。完整 discovery rows 仍保存在 `work/source-candidates.json` 與逐列 `work/news-relevance-gate.json`；relevance gate 不可使用固定 top-N、相對名次或模型評級，且不得省略中央社／中新社任何窗內列。

`REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE`：`news-source-pool.json` 中角色為 `regional_supplement` 的來源（目前中央社與中新社），其全部精確窗內 provisional groups 與文章列都必須出現在模型 `candidate_groups`。不得因缺少 GDELT heat、Google Trends、Google News coverage 或關鍵字命中而省略；熱度只可增加召回或排序，不能判斷重要性。模型輸入建立後、語意合併與六項評分前，執行 `python3 scripts/validate_local_source_admission.py --preprocessed <preprocessed-candidates.json> --selection <selection-results.json> --source-pool news-source-pool.json`。驗證失敗不得進入後續階段。

`SEMANTIC_EVENT_LEDGER_GATE`：只有語意事件才算新聞、才可進入六項評分。前處理輸出的 `provisional_article_groups` 只是文章索引，不是事件。必須讀取文章內容或來源支援摘要，為每個真正事件建立唯一 `semantic_event_id` 與完整 `event_identity`，並逐列寫入 `article_dispositions`。每列只能是 `event_evidence`、`non_news`、`unresolved` 或 `unresolved_exhausted`；`event_evidence` 指向事件，`non_news` 保存具體理由，仍在恢復的 `unresolved` 必須歸零。只有原網址、同站直接／替代路徑與最後瀏覽器證據皆已明確失敗者可標 `unresolved_exhausted`，保留原因並使內容覆蓋降級，但不得阻止其他已驗證事件完成。文章列數、網址數與標題群組數不得稱為新聞數或完成評分數。

`CONTENT_HYDRATION_BATCH_RECEIPT_GATE`：對 admitted rows 中 `summary_quality=title_only`，或 `summary_quality=structured_event_context` 但 event identity 仍有歧義，或其他內容仍不足者，不得再用單一 shell/exec_command 多網域大量抓取。`structured_event_context` 是來源支持的事件脈絡，不是正文摘要；若其 event identity 已可稽核，不得僅因 summary 與 title 相同就強制補抓文章正文。以目的型網頁／瀏覽器 connector 逐批補齊，每批最多 20 個 article rows；批次大小是恢復邊界，不是 top-N，必須持續至所有需要 hydration 的 admitted rows 都有內容證據、仍在恢復，或留下已窮盡證據。每批在同一 run 下先寫 running receipt，再以 append-only `work/content-evidence/batch-<sequence>.jsonl` 保存 candidate_id、實際 URL、工具／端點、HTTP 或 connector 狀態、來源摘要或正文雜湊、替代來源、elapsed、retry 與 sanitized error，最後寫 passed/failed receipt 並讀回 hash。中斷時只從第一個未完成 batch 繼續，不重跑已完成 batch。只有尚未跑完既定恢復鏈的列保持 `unresolved` 並阻擋 stage；恢復鏈確實窮盡者標 `unresolved_exhausted`，不得批量標為 `non_news`，也不得拖死其他可驗證事件。

`EVENT_REGION_AND_TIME_IDENTITY_GATE`：在任何六項評分之前，必須讀取內容並獨立建立事件的 `country_codes`、`primary_country_code`、`location_evidence`、`event_occurred_at`、`material_update_at`、`material_update_type`、`material_update_evidence` 與 `temporal_review`。來源分桶與媒體國別只是 discovery 提示，絕不能當事件地區。高階模型必須逐事件比較文章內容、十四天時間線、舊數據與本輪事實，將時間資格判為 `new_event`、`ongoing_current_impact`、`material_update` 或 `old_restatement`，並分列新增／變更事實、重複舊事實與窗內當下影響；程式只檢查結構與一致性。已結束的舊事件只重複舊傷亡、重新整理、回顧、週年、換標題或重刊時為 `non_news`。開始較早但有內容證明事件仍持續跨越精確時間窗、並在窗內造成當下影響時可列 `ongoing_current_impact`，不得因開始日久遠排除，也不得強迫必須新增傷亡。地區或時間缺漏／矛盾時保持 `unresolved`，不得評分；地區修正後必須重算 `core_section_relevance` 與總分。

`POLICY_GOVERNANCE_EVIDENCE_GATE`：事件身分與時間資格確認後、六項評分前，先證明政策、法規、主管機關處置、平台治理或文化產業制度事件真正是什麼。最新一輪每個候選必須填 `policy_governance_review`；適用時分列法律依據、官方行動、業者／平台實際效果、受影響行為者、跨機關影響、先例／外溢範圍、窗內效果與證據網址。未經證實的歷史指控必須置於 `unverified_allegations`，與事件身分、直接後果及六項分數分離。六項草評後逐項比對制度證據；任何 `contradiction`、`unresolved` 或非 `consistent` 結果都必須退回重審，修正事件身分或重新評分。若官方行動、業者實際效果及跨機關／外溢證據同時成立但總分低於 B，必須填寫證據支持的 `why_not_b`；這是反向挑戰，不是自動 B 級下限。

模型路由依序為：

1. 規則與程式：處理時間、網址、重複、既有十四天紀錄比對及固定欄位。
2. 可選小模型：只做主題、板塊、實體、語言與低風險候選標籤；沒有可用小模型時直接跳過，不得阻止流程。
3. 高階模型：處理語意聚類、公共價值、暫定評級、疑似漏選與所有重大或不確定事件。

小模型不得單獨排除候選。符合任一條件時必須送高階模型：暫定 B 以上、政治／選舉／軍事／外交／金融市場／重大企業／災害／疫情／公共安全、跨境或跨產業影響、來源互相矛盾、信心不足、十四天紀錄顯示狀態轉折，或規則命中「不可漏選」主題。

採高召回原則：寧可把邊界候選送入下一階段，也不得為節省 Token 提前刪除。模型前只可排除超出時間窗或完全重複的 discovery rows；`lightweight_semantic_review` 仍必須完整進入 model input，其 route 只控制內容補齊深度與處理順序，不得當成 `non_news` 或省略語意審查。所有 gate decisions 必須保留原因與結構化訊號，且 discovery total 必須守恆。


### 一、廣泛海選

不得在本技能臨時重新抓新聞。先調用 `acquire-news-candidates` 執行三條 discovery routes，保存原始快照、SHA-256、連續翻頁鏈及時間邊界或來源耗盡證據，再讀取候選清單。驗證器必須從快照重算清單，禁止模型自行宣告筆數。直接連結遇到403、robots、不支援 MIME、逾時、解析失敗或動態內容未載入時，依 `canonical route → same-site direct fetch → same-site alternate non-browser route → browser-rendered snapshot` 恢復；瀏覽器只可作最後備援。不得以總候選數或任何等級數量作為成功門檻。

每條成功 route 確認完整抵達精確 24 小時邊界後，再按 `discovery_priority_score` 排序；每筆保存 `discovery_signals` 與事件特有的 `discovery_priority_reason`。這些欄位只是 hydration 次序，不是 `public_value_v2`、`importance_score` 或正式等級。`FULL_DISCOVERY_POOL_UNCAPPED` 要求成功 route 的全部已驗證窗內條目入池，不設前 30 或其他預設名額。不得把其他來源冒充為某 route 覆蓋；保存 route 確認紀錄後才可跨來源去重。

搜尋各設定板塊及公共政策、經濟、科技、資安、國際關係、災害、公衛、公共安全、科學、自然史、文化與產業。

每個候選只記錄：

- 暫定標題。
- 新聞時間與事件時間。
- 來源網址。
- 地區及影響範圍。
- 主題。
- 一句可能重要的原因。

此階段不要產生詳報、地圖或圖片。

### 二、事件聚類

以底層事件而非標題去重：

- 合併不同語言、不同標題、不同媒體轉載及同一事件更新稿。
- 建立穩定 `dedup_key`。
- 保存候選網址，不把報導篇數當成重要性。
- 跨日事件若只是數字或狀態更新，併入原事件時間線；出現重大新轉折才建立新事件。

### 三、套用偏好

- 依使用者設定提高或降低排序，不得把偏好誤當事實重要性。
- 地區板塊可為國家或區域；同一事件只配置一個主要板塊。
- 世界板塊只收跨國系統性事件或其他板塊未涵蓋的重要事件。
- 不為填滿板塊加入弱事件。

### 四、判斷入選

依公共影響、政策、經濟、科技、安全、災害、公衛、產業與文化制度意義判斷。排除：

- 純聲量、普通八卦、宣傳稿及無公共價值熱搜。
- 未經查證社群爆料或內容農場。
- 與時間窗無關的舊聞，除非時間窗內有新的實質發展。
- 同一事件的重複條目。

來源數量不是入選硬門檻。只有一個看似可靠來源的重大候選仍可入選，交由驗證技能繼續搜尋；不得在此自動降級。

逐事件套用絕對門檻，不做候選間相對淘汰。`SS` 至 `C` 必須全部入選；`C-` 固定進候補池，不得進入 manifest 或讀者版；`D`／`E` 只留稽核。不得限制板塊篇數、總篇數或特定等級數量。30 則達標就輸出 30 則，只有 3 則達標就只輸出 3 則。

### 五、評級

評定災害、疫情、事故、公共安全與人道事件前，必須完整讀取 `references/severity-rubric.md`。依 `news-brief-settings.md` 的嚴重度標準對全部去重候選評定 `SS` 至 `E`：

- 評級只看影響範圍、強度、持續性、轉折性與結構意義。
- 不依來源篇數、圖片震撼度、媒體聲量或使用者個人興趣抬高等級。
- 單一產業的大型評選活動第一次停辦，可作為制度轉折與本期增量的候選證據，但仍須以已發生的後果逐項完成六項評分。同一活動後續停辦若沒有新增原因、制度變化或擴散影響，應依十四天 continuity 降低 `material_new_development`；若有實質新變化則重建 facts 並重新評分。產業型平台、網文、創作者經濟、遊戲或電競的監管或商業模式轉折，也不得以事件類型直接指定最終等級。
- C 級只代表影響較低，不代表查證或格式可以縮水。
- 災害、疫情與公共安全事件列為 `A-` 以上時，`selection.reason` 必須明列死亡／重傷、直接受影響人口、地理範圍與關鍵系統中實際觸發的項目。
- 不得把一般受傷等同重傷，不得把警報覆蓋人口等同直接受影響人口，也不得由單張震撼圖片推高評級。
- 所有事件都以六項證據綜合評分；死亡數、地域數、國家大小或任何單一項都不得直接指定最終等級，也不得建立地域硬上限或例外補丁。重要性／嚴重程度放入 `public_impact`，直接人口／行政區／國家／公共系統範圍放入 `geographic_or_population_scope`，其餘四項各自獨立給分，最後依固定總分級距換算 `SS` 至 `E`。
- 每個候選先填唯一 `evidence_facts`，以 `consequence_evidence` 分開 realized／ongoing／potential／speculative，再由逐項 `dimension_evidence` 引用 fact ID；之後才填 0–100 `importance_breakdown`、加權 `importance_score` 與 `grading_evidence`。5 分中點需 `midpoint_rationales`；三項以上重用同一 fact 需 `cross_dimension_rationales`；單項或總分達 70 需完成 `high_score_challenges`。政策事件填 `policy_stage`，證據成熟度另填 `evidence_confidence`／`confidence_band`。只有所有 gate 通過才能標 `grade_status=validated`；只有 `grade_reason`、模板句、關鍵字或未來可能性不得完成評級。
- 來源清單的 `discovery_priority_score` 只供 discovery 排序；去重後的最終候選必須從零依事件證據評分，禁止把 discovery signals 轉抄成 importance，或把「政府／全國／重大」等字詞本身當成公共後果。
- 邊境或長期衝突事件不得依類型固定等級，也不得繼承母事件等級。每次只以本輪已實現／持續後果、直接範圍、急迫性、制度意義與十四天增量計算六項；例行事件通常自然得到低分，重大實際後果則依證據提高。
- 油價或其他市場反應必須記錄幅度、期間、是否超出正常波動及與衝突的直接因果證據；只有方向性上漲不得自動升級。

### 六、編號

依板塊順序及重要性排序，配置唯一的三碼加兩位流水號，例如 `TWN-01`。事件進入驗證階段後，不任意重新編號。

## 輸出

只寫入：

- `event_id`
- `primary_section`
- `title`
- `grade`
- `selection.dedup_key`
- `selection.category`
- `selection.impact_scope`
- `selection.reason`
- `selection.candidate_urls`
- `selection.news_time`
- `selection.event_time`

不得寫入或清空 `verification`、`map`、`images` 及讀者版詳報。



## 全候選決策

將每個聚類候選交給 `audit-news-candidates`，包含暫定等級、決定、理由、候選網址、`dedup_key` 與 `continuity_key`。

所有 `SS` 至 `C` 候選（包含 `merged`）都必須填入對應本輪讀者事件的 `selected_event_id`；合併項可以共用主事件編號，但不得留空。

- `D`：有資訊但未達每日簡報門檻。
- `E`：低價值、舊聞、宣傳、未查證或不適合。
- D／E 不配置事件編號、不進入最終事件資料、不出現在讀者版。
- 不得以篇數、同級過多或版面長度排除候選。
- 暫定 B 以上未入選而沒有理由時，本階段不得標示完成。
