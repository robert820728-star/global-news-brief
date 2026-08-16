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


1. 讀取本輪全部聚類候選、`news-source-pool.json`、每站來源掃描證據與最近十四天 `state/candidate-audit.json`。先由 `scripts/validate_source_scan_evidence.py` 驗證快照雜湊、翻頁鏈與停止證據並重算時間窗清單；不得採信自行填寫的來源筆數。確認核心來源逐站完成掃描後，每站有 30 則以上必須取前 30 則，不足 30 則取全部，並核對排名外強制例外。每筆 `ranked_items` 必須保存 `public_value_v1` 六項 `importance_breakdown`、總分與理由；每項不超過權重且六項總和等於 `importance_score`。
2. 以 `dedup_key` 去重，以 `continuity_key` 連接跨日事件。
3. 每筆記錄 `selected`、`excluded`、`merged` 或 `deferred`，並附理由代碼與繁體中文說明。
4. 記錄可靠來源數、獨立群組、官方／原始來源及來源限制。
5. 記錄持續事件的新增、未變、狀態轉折與本輪決定。
   - 同步驗證 `grading_evidence`：影響範圍、直接後果、本期實質增量、上下級比較、邊境衝突預設 D 與長期戰爭常態事件折扣不得缺漏。
6. 附加本輪並刪除十四天前紀錄。
7. 暫定 B 以上未入選卻沒有理由時，回到海選補查。

任何 `SS` 至 `C` 候選只能是 `selected` 或同事件的 `merged`，且兩者都必須保存指向本輪 manifest／讀者版事件的 `selected_event_id`。`C-` 預設為 `deferred`／`c_minus_reserve`，取用時必須使用 `c_minus_selected_need` 並保存具體理由。若核心內容查證失敗或未達公共價值，評為 `D`／`E`；不得保留達標評級再以相對重要性、篇數、版面或來源數排除／延後。

## 內部等級

- `D`：有具體資訊，但未達每日簡報門檻。
- `E`：低價值、舊聞、宣傳、未查證或不適合。
- D／E 不配置事件編號、不進入最終事件資料、不出現在讀者版；後續有重大轉折可重新評為 C 以上。

## 理由代碼

`selected_threshold_met`、`outside_time_window`、`duplicate_merged`、`continuation_no_material_change`、`below_public_value_threshold`、`unreliable_or_unverified`、`superseded_by_later_update`、`wrong_scope`、`processing_failure`、`search_recall_failure`。

禁止使用版面不足、同級太多、固定篇數或只有一個可靠來源。完全沒有可靠證據時才可用 `unreliable_or_unverified`。

## 持續事件

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
