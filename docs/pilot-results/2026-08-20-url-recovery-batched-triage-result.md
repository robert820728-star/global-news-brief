# 網址標題復原與批次模型初審 / URL Recovery and Batched Model Triage

## 結論 / Conclusion

第二層可將 4,203 個不可用標題中的 2,906 個復原為描述性標題，復原率為 69.1%。20,450 個輸入列全部保留，安全合併的重複證據由第一層的 534 列增加到 751 列；暫定處理單位為 19,699。這代表純本機無損處理目前只可減少 3.67% 的單位，不能合理地直接裁成 300 或 500 則。

The second stage recovered descriptive titles for 2,906 of 4,203 unusable-title rows, a 69.1% recovery rate. All 20,450 input rows remain preserved. Safely consolidated duplicate evidence increased from 534 rows in stage one to 751 rows, leaving 19,699 provisional units. Lossless local processing therefore reduces only 3.67% of units and cannot justify cutting the list directly to 300 or 500 items.

## 最終計數 / Final Counts

| 指標 / Metric | 數量 / Count |
|---|---:|
| 輸入文章列 / Input article rows | 20,450 |
| 復原標題列 / Recovered-title rows | 2,906 |
| 尚未復原標題列 / Unresolved-title rows | 1,297 |
| 暫定證據組 / Provisional evidence groups | 19,699 |
| 合併的證據列 / Consolidated evidence rows | 751 |
| 新增的復原標題多列組 / Recovered-title multi-row groups | 132 |
| 每批最多組數 / Maximum groups per batch | 100 |
| 模型初審批次 / Model triage batches | 197 |
| 自動刪除／重要性決定 / Automatic deletion / importance decisions | 0 / 0 |

## 模型介入修正 / Model-Guided Corrections

第一版復原 2,959 列並形成 19,690 組。模型審核發現 UUID 被拆成假標題、跨日期共用的新聞標題頁、短通用 feed 名稱及分類頁被誤當內容標題。修正後，英文復原標題至少需要四個描述詞，候選本身也必須通過描述性標題檢查；UUID、新聞標題頁及分類名稱返回 unresolved，仍然不刪除。

The first pass recovered 2,959 rows and produced 19,690 groups. Model review found UUID fragments, cross-date headline pages, short generic feed names, and category pages incorrectly treated as content titles. The corrected rule requires at least four descriptive English tokens and revalidates every recovered candidate as a descriptive title. UUIDs, headline pages, and category names return to unresolved status without deletion.

修正後，模型檢查全部 132 個復原標題多列組，未再發現結構性誤合併。200 個 unresolved 樣本中，198 個仍是可識別的文章端點，2 個是日期或分類列表頁；因此 unresolved 必須進正文或中繼資料補取，不能當成低價值新聞淘汰。

After correction, model review of all 132 recovered-title multi-row groups found no remaining structural false merge. Of 200 unresolved samples, 198 remained identifiable article endpoints and 2 were date or category listing pages. Unresolved rows therefore require body or metadata recovery and cannot be discarded as low-value news.

## 額度與執行方式 / Quota and Execution Shape

逐組呼叫需要 19,699 次模型請求。固定每批 100 組後只需 197 次初審請求。初審只傳 `group_id`、區域、標題、證據數及最早時間；完整網址與來源證據留在本機，只有標記為深查的組才載入。完整初審清單估計約 1,007,773 input tokens，最大單批約 5,423 tokens。這降低的是請求與提示重複開銷，不是假裝模型不必看每一組。

One-request-per-group would require 19,699 model calls. Fixed batches of 100 require 197 triage calls. Triage sends only `group_id`, section, title, evidence count, and earliest time; full URLs and source evidence remain local until deep review. The complete compact triage payload is approximately 1,007,773 input tokens, with a maximum batch of about 5,423 tokens. This reduces request and prompt overhead without pretending the model can ignore any group.

## 相容性壓測 / Compatibility Checks

| 資料 / Artifact | 輸入 / Input | 組 / Groups | 批次 / Batches | 驗證 / Verification |
|---|---:|---:|---:|---|
| 2026-08-17 舊來源邏輯 / legacy acquisition | 672 | 664 | 7 | `RECOVERY_OK` |
| 2026-08-16 舊來源邏輯 / legacy acquisition | 441 | 438 | 5 | `RECOVERY_OK` |

兩份舊資料只證明守恆與批次契約相容，不能算目前 GDELT archive 邏輯的第二、第三天正式樣本。

The two legacy artifacts prove conservation and batch-contract compatibility only. They do not count as days two and three for the current GDELT archive acquisition design.

## 下一步 / Next Step

依197個固定批次執行模型初審；每批必須回傳完全相同的 batch hash 與一對一 `group_id` 結果。缺少、重複或失敗批次只能重跑該批，不能跳過。模型建立事件指紋後，再合併同事件並只對可能達 C、證據衝突或資料不足的事件載入正文及執行六項深評。

Execute the 197 immutable model batches. Every result must echo the exact batch hash and return one result per `group_id`. Missing, duplicate, or failed batches may only rerun that batch and may never be skipped. After the model assigns neutral event fingerprints, same-event groups can be consolidated, while only possible-C, conflicting-evidence, or insufficient-evidence events load full content for six-dimension deep review.

