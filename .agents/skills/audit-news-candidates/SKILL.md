---
name: audit-news-candidates
description: Maintain a rolling fourteen-day audit of all news candidates, including selection or exclusion reasons, source coverage, duplicate relationships, internal D/E grades, and continuing-event changes. Use after selection and before verification so important candidates cannot disappear without an explicit reason.
---

# 候選事件稽核

只管理候選稽核及本階段狀態，不修改最終事件、來源、地圖、圖片或讀者版。

## 流程

1. 讀取本輪全部聚類候選與最近十四天 `state/candidate-audit.json`。
2. 以 `dedup_key` 去重，以 `continuity_key` 連接跨日事件。
3. 每筆記錄 `selected`、`excluded`、`merged` 或 `deferred`，並附理由代碼與繁體中文說明。
4. 記錄可靠來源數、獨立群組、官方／原始來源及來源限制。
5. 記錄持續事件的新增、未變、狀態轉折與本輪決定。
6. 附加本輪並刪除十四天前紀錄。
7. 暫定 B 以上未入選卻沒有理由時，回到海選補查。

## 內部等級

- `D`：有具體資訊，但未達每日簡報門檻。
- `E`：低價值、舊聞、宣傳、未查證或不適合。
- D／E 不配置事件編號、不進入最終事件資料、不出現在讀者版；後續有重大轉折可重新評為 C 以上。

## 理由代碼

`selected_threshold_met`、`outside_time_window`、`duplicate_merged`、`continuation_no_material_change`、`below_public_value_threshold`、`unreliable_or_unverified`、`superseded_by_later_update`、`wrong_scope`、`processing_failure`、`search_recall_failure`。

禁止使用版面不足、同級太多、固定篇數或只有一個可靠來源。完全沒有可靠證據時才可用 `unreliable_or_unverified`。

## 持續事件

政策決定、傷亡或病例顯著跳升、跨境擴散、軍事外交轉折、重大市場反應、災害階段改變、正式調查結論或企業正式決策屬實質更新。重述背景、輕微波動或相同轉載不算。

## 保存與降級

十四天歷史是增強功能，不是每日簡報的執行門檻。先讀取目前可取得的 `state/candidate-audit.json` 作為歷史基準，再依可用能力保存：

1. 有可持久保存的使用者工作區：更新工作區的 `state/candidate-audit.json`。
2. 工作區無法跨次保存，但有 repository 寫入權限：更新 repository 同一路徑。
3. 沒有寫入權限但可輸出附件：輸出本輪候選稽核 JSON，供後續執行匯入。
4. 以上皆不可用：只在本次執行中完成候選決策與比較，將歷史模式標記為 `current_run_only`。

沒有 GitHub 帳號、repository 寫入權限或持久工作區時，仍必須完成本輪稽核並繼續驗證、圖片、地圖與讀者版。不得因歷史無法保存而排除事件、降低評級、把最終狀態設為失敗或停止輸出。

只有實際載入歷史資料時才可聲稱完成十四天比較；否則在內部紀錄標記 `no_persisted_history` 或 `current_run_only`，不得把後台限制寫進讀者版。

```bash
python3 scripts/manage_candidate_audit.py append --history state/candidate-audit.json --run /path/to/run.json --output state/candidate-audit.json --retention-days 14
python3 scripts/manage_candidate_audit.py validate --input state/candidate-audit.json
```
