---
name: audit-news-candidates
description: Maintain a rolling fourteen-day audit of all news candidates, including selection or exclusion reasons, source coverage, duplicate relationships, internal D/E grades, and continuing-event changes. Use after selection and before verification so important candidates cannot disappear without an explicit reason.
---

# 候選事件稽核

只管理候選稽核及本階段狀態，不修改最終事件、來源、地圖、圖片或讀者版。

## 流程

## 成本與模型邊界

候選歷史讀寫、十四天裁切、`dedup_key`／`continuity_key` 比對、理由完整性、來源數計數及 D／E 保存均以程式完成，不使用大型模型重算整份稽核。

只有下列工作需要模型：判斷持續事件是否有實質轉折、檢查暫定 B 以上事件是否被錯誤排除、辨認不同標題是否其實是同一底層事件。可選小模型只能提出標籤或合併建議；最終排除、降為 D／E 或重大事件合併須由高階模型確認。


1. 讀取本輪全部聚類候選、`news-source-pool.json`、每站來源掃描證據與最近十四天 `state/candidate-audit.json`。先由 `scripts/validate_source_scan_evidence.py` 驗證快照雜湊、翻頁鏈與停止證據並重算時間窗清單；不得採信自行填寫的來源筆數。`FULL_DISCOVERY_POOL_NO_FIXED_LIMIT` 要求每個成功來源的 `selected_item_urls` 精確等於完整 `ranked_items`，不得截斷或使用溢位例外。每筆 `ranked_items` 必須保存 `public_value_v1` 六項 `importance_breakdown`、總分與理由；每項不超過權重且六項總和等於 `importance_score`。
   - `PIPELINE_COUNT_RECEIPT_V1`：最新一輪保存 `merged_article_row_count`、`in_window_article_row_count`、`canonical_url_count`、`provisional_title_cluster_count`、`semantic_event_count`、`scored_event_count`、`c_or_higher_scored_event_count`、`selected_event_count`，以及 `event_evidence_article_row_count`、`non_news_article_row_count`、`unresolved_article_row_count`。全部由當輪 artifact 重算，且前四層至語意事件數不得增加。文章列數不得稱為語意事件數；網址正規化或標題分群不得稱為語意去重。小計不守恆時必須回報差額並撤回未證實的數量宣稱，但不得因此停止發布仍可核實的新聞。
   - `SEMANTIC_EVENT_LEDGER_GATE`：只有語意事件才算新聞、才可進入六項評分。每個真正事件必須有唯一 `semantic_event_id` 與完整 `event_identity`；每個窗內文章列都必須記入 `article_dispositions`，且只能是 `event_evidence`、`non_news` 或 `unresolved`。`event_evidence` 必須指向事件，`non_news` 必須保存具體理由，任何 `unresolved` 都阻擋 audit 完成。文章列數、網址數與標題群組數不得稱為新聞數或完成評分數。
   - `EVENT_REGION_AND_TIME_IDENTITY_GATE`：最新一輪每個語意事件都必須保存 `event_identity.country_codes`、`primary_country_code`、`location_evidence`、`event_occurred_at`、`material_update_at`、`material_update_type`、`material_update_evidence`。來源分桶與媒體國別不得當成事件地區，文章 `published_at` 不得冒充事件或更新時間。舊事件若只是重新整理、回顧、週年、換標題或重刊，文章處置只能是 `non_news`；只有精確時間窗內可驗證的實質更新才可保留為延續事件。任何缺漏或矛盾必須是 `unresolved` 且阻止 audit 完成。
2. 以 `dedup_key` 去重，以 `continuity_key` 連接跨日事件。
3. 每筆記錄 `selected`、`excluded`、`merged` 或 `deferred`，並附理由代碼與繁體中文說明。
4. 記錄可靠來源數、獨立群組、官方／原始來源及來源限制。
5. 記錄持續事件的新增、未變、狀態轉折與本輪決定。
   - 最新一輪每個候選都必須保存最終 `importance_breakdown`、`importance_score` 與六項非空白 `dimension_evidence`；六項總分直接依 `SCORE_TO_GRADE_BANDS_V1` 換算等級，任何單項都不得成為地域硬上限或例外補丁。
   - 來源清單的站內分數只用於 discovery 排序，不得複製成最終候選分數；最終六項必須在去重後按事件本身後果重新評估。
   - 同步驗證 `grading_evidence`：影響範圍、直接後果、本期實質增量、上下級比較、邊境衝突與長期戰爭連續性判定不得缺漏。
   - 最新一輪每個候選都要有 `local_disaster_review`；普通地方災害記錄保守確認死亡數、特殊意義觸發與調整理由作為六項證據索引，軍事／衝突事件則標記 `applies: false` 並沿用既有衝突判定。
6. 附加本輪並刪除十四天前紀錄。
7. 暫定 B 以上未入選卻沒有理由時，回到海選補查。

### Mobile-native rolling merge

`MOBILE_NATIVE_AUDIT_ROLLING_MERGE`

下方 `manage_candidate_audit.py` 命令是 full-runtime 的首選路徑；它不是 mobile-native 的必要前提。當排程宿主沒有可執行 runtime、但 GitHub 已存在 durable audit 時，可直接讀取該 JSON 做受限的結構化合併：若六項欄位、各欄範圍與總分算法未變，保留仍在十四天內的既有候選，不得重算未發生實質更新的歷史候選；只評分本輪新增或有實質更新的候選，移除逾期項目並依既有 key 去重。可用 GitHub contents API 整檔 replacement 保存合併結果，同時如實記錄 `execution_mode=mobile-native`，不得宣稱已執行 script validation。C 級以上仍依當輪規則另做來源驗證；缺少本機 runtime 不得因此阻止本日讀者版。

`MOBILE_NATIVE_COMPACT_DURABLE_AUDIT`

mobile-native durable audit 僅保存滾動合併與讀者驗收必要欄位：`candidate_id`、`dedup_key`、可用時的 `continuity_key`、`event_date`、`section`、`title`、`importance_breakdown`、`importance_score`、逐項 `dimension_evidence`、`provisional_grade`、`decision`、`reason`、`source_ids`、`selected_event_id`，以及精簡的 `continuity` 狀態與影響變化。`MUST_OMIT_VERBOSE_GRADING_EVIDENCE`：mobile artifact 不得重複保存 verbose `grading_evidence`、逐頁 `source_audit`、文章全文或重複驗證敘述；本輪 C 級以上仍須完成類別相稱的獨立驗證，full-runtime 的詳細證據驗證與稽核規則不變。壓縮既有檔案不得改變候選 ID、六項分數、總分或 C 級以上 `selected_event_id` 映射。

任何 `SS` 至 `C` 候選只能是 `selected` 或同事件的 `merged`，且兩者都必須保存指向本輪 manifest／讀者版事件的 `selected_event_id`。`C-` 預設為 `deferred`／`c_minus_reserve`，取用時必須使用 `c_minus_selected_need` 並保存具體理由。若核心內容查證失敗或未達公共價值，評為 `D`／`E`；不得保留達標評級再以相對重要性、篇數、版面或來源數排除／延後。

## 內部等級

- `D`：有具體資訊，但未達每日簡報門檻。
- `E`：低價值、舊聞、宣傳、未查證或不適合。
- D／E 不配置事件編號、不進入最終事件資料、不出現在讀者版；後續有重大轉折可重新評為 C 以上。

## 理由代碼

`selected_threshold_met`、`outside_time_window`、`duplicate_merged`、`continuation_no_material_change`、`below_public_value_threshold`、`unreliable_or_unverified`、`superseded_by_later_update`、`wrong_scope`、`processing_failure`、`search_recall_failure`。

禁止使用版面不足、同級太多、固定篇數或只有一個可靠來源。完全沒有可靠證據時才可用 `unreliable_or_unverified`。

## 持續事件

`IMPACT_DELTA_CONTINUITY_SCORING`：以 `continuity_key` 對照十四天歷史，本輪只按本日可驗證的影響力變化評級。無新增公共影響的名人死亡、喪禮或重複報導下調並只留稽核；颱風、地震、疾病或戰爭若有死傷增加、影響範圍擴大、傳播／戰線擴張、系統中斷或制度後果則可上調。受控、停火、消退或官方下修可下降。不得因事件較舊而自動降級，也不得因重複報導而維持歷史最高級；在 `continuity` 中記錄相對十四天基準為上升、持平或下降及其證據。

`PASSIVE_ONE_OFF_FIVE_DAY_DECAY`：五日衰減只適用於事件本身已結束、沒有持續公共／制度／安全影響的一次性個人或禮儀事件，例如自然死亡、喪禮、追悼與回顧；它是評級上限，不是強迫升到該級。自首次可驗證事件日起：當日依事件本身獨立評級、次日最高 B、第三日最高 C、第四日 D、第五日 E，五個日曆日後移出活躍滾動稽核。颱風、地震、疾病、戰爭及任何仍在發展的事件不得套用機械式日數衰減；死傷、範圍、傳播、戰線、系統中斷、權力重組、暗殺證據或制度後果一有實質變化，就退出本規則，依 `IMPACT_DELTA_CONTINUITY_SCORING` 當成新實質更新重新評級，可升級。朱鎔基自然死亡若沒有權力或制度後果，依本規則退場；日後若另有實質影響，仍會以新原因重新入池。

政策決定、傷亡或病例顯著跳升、跨境擴散、軍事外交轉折、重大市場反應、災害階段改變、正式調查結論或企業正式決策屬實質更新。重述背景、輕微波動或相同轉載不算。

長期戰爭中的一般砲擊、空襲、無人機攻擊、小規模陣地變化、少量日常死傷、重複戰果宣稱與例行軍援，不因母事件嚴重而取得高等級；沒有戰局反轉／升級、停火或和平進程改變、新國家／新戰線、或可驗證的外部系統影響時，必須評為 `D`。國際邊境小衝突若未達正式／事實戰爭、不是監控板塊且未提高相關權重，也必須評為 `D`。

## 保存與降級

十四天歷史是增強功能，不是每日簡報的執行門檻。先讀取目前可取得的 `state/candidate-audit.json` 作為歷史基準，再依可用能力保存：

1. 有可持久保存的使用者工作區：更新工作區的 `state/candidate-audit.json`。
2. 工作區無法跨次保存，但有 repository 寫入權限：更新 repository 同一路徑。
3. 沒有寫入權限但可輸出附件：輸出本輪候選稽核 JSON，供後續執行匯入。
4. 以上皆不可用：只在本次執行中完成候選決策與比較，將歷史模式標記為 `current_run_only`。

沒有 GitHub 帳號、repository 寫入權限或持久工作區時，仍必須完成本輪稽核並繼續驗證、圖片、地圖與讀者版。不得因歷史無法保存而排除事件、降低評級、把最終狀態設為失敗或停止輸出。

只有實際載入歷史資料時才可聲稱完成十四天比較；否則在內部紀錄標記 `no_persisted_history` 或 `current_run_only`，不得把後台限制寫進讀者版。

```bash
python3 scripts/manage_candidate_audit.py append --history state/candidate-audit.json --run /path/to/run.json --output state/candidate-audit.json --source-pool news-source-pool.json --retention-days 14
python3 scripts/manage_candidate_audit.py validate --input state/candidate-audit.json --source-pool news-source-pool.json
```
