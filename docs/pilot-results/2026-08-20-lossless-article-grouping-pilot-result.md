# 無損文章分組第一輪測試 / Lossless Article Grouping Pilot — Round 1

## 結論 / Conclusion

本輪不具備升為正式規則的條件。20,450 筆輸入列全部保留，第一步可安全合併 534 筆重複證據，將後續暫定處理單位降至 19,916，縮減 2.61%。自動刪除為 0，重要性評分為 0。

This round is not eligible for production promotion. All 20,450 input rows were preserved. The first stage safely consolidated 534 duplicate evidence rows, reducing provisional downstream units to 19,916, a 2.61% reduction. Automatic deletions: 0. Importance decisions: 0.

## 最終計數 / Final Counts

| 指標 / Metric | 數量 / Count |
|---|---:|
| 輸入文章列 / Input article rows | 20,450 |
| 暫定證據組 / Provisional evidence groups | 19,916 |
| 合併的重複證據列 / Consolidated duplicate evidence rows | 534 |
| 同網址多列組 / Canonical-URL multi-row groups | 6 |
| 同標題多列組 / Exact-title multi-row groups | 416 |
| 需補標題列 / Title-recovery rows | 4,203 |
| 自動刪除列 / Automatically deleted rows | 0 |
| 重要性或發布決定 / Importance or publication decisions | 0 |

## 模型介入結果 / Model Review Results

第一版為 20,450 → 19,899，合併 551 列。模型逐一檢查 432 個同標題組及 6 個同網址組後，發現 16 個結構性誤合併組，共涉及 270 列、17 個不應合併的列差額：11 組純識別碼標題，以及 `comment page 1`、`business economy`、`peoplemovesarticle`、`Press TV's news headlines`、`t20260820 800444472` 等頁面容器或識別碼格式。這些列沒有刪除；全部改送標題復原。

The first pass produced 20,450 → 19,899 and consolidated 551 rows. Model review of all 432 exact-title groups and all 6 canonical-URL groups found 16 structural false-merge groups, covering 270 rows and 17 rows of improper consolidation. They consisted of 11 opaque identifier-title groups plus page-container or identifier formats such as `comment page 1`, `business economy`, `peoplemovesarticle`, `Press TV's news headlines`, and `t20260820 800444472`. No rows were deleted; all were rerouted to title recovery.

修正後，模型再檢查全部 416 個同標題組及 6 個同網址組，未發現剩餘的結構性誤合併。抽查的 200 個補標題列中，200/200 的網址或網址路徑都指向可復原的內容頁，包括新聞、評論、訃聞、娛樂或新聞稿；因此「標題不可用」絕不能等同「不是新聞」或「可刪除」。

After correction, model review of all 416 exact-title groups and all 6 canonical-URL groups found no remaining structural false merge. In the deterministic sample of 200 recovery rows, 200/200 URLs or URL paths pointed to recoverable content pages, including news, opinion, obituary, entertainment, or press-release material. Therefore, an unusable title must never be treated as non-news or deletable.

在 200 組疑似漏合併對中，模型判定 184 組可明確視為同事件或同內容的不同標題，11 組需要正文或來源時間線才能確認，5 組明確不應合併或本身是頁面容器。這證明近似標題適合送模型審核，但目前不適合自動合併。

Among 200 suspected missed-merge pairs, the model judged 184 as clearly the same event or content with title variation, 11 as requiring body text or source chronology, and 5 as definite non-merges or page containers. This supports model routing for near-title pairs, but not automatic fuzzy merging.

## 版本紀錄 / Version Record

| 版本 / Version | 建立原因 / Reason | 實作方式 / Approach | 驗證 / Validation | 結果與下一步 / Result and Next Decision |
|---|---|---|---|---|
| Pilot v0 | 測量無損第一步縮減量 / Measure lossless first-stage reduction | URL 正規化、同區同標題合併、壞標題復原 / URL normalization, same-section exact-title grouping, bad-title recovery | 10 項 TDD、20,450 列守恆、模型全組審查 / 10 TDD tests, 20,450-row conservation, full-group model review | 失敗：16 個結構性誤合併 / Failed: 16 structural false-merge groups |
| Pilot v1 | 修正模型發現的格式誤判 / Correct model-detected format errors | 將純識別碼與頁面容器格式送復原，不刪除 / Route opaque IDs and page containers to recovery without deletion | 10/10 測試、完整重跑、獨立 `CONSERVATION_OK` / 10/10 tests, full rerun, independent `CONSERVATION_OK` | 通過單日實驗；不得升正式 / Passed one-day pilot; no production promotion |

## 升級條件 / Promotion Gate

至少還需兩個獨立 24 小時資料集，使總數達三天；每一天都必須符合列數守恆、決定性輸出雜湊一致、全量同標題組零確認誤合併，並由模型審核復原樣本與近似對。即使三天通過，也需另行核准才可修改正式排程。

At least two additional independent 24-hour datasets are required for a three-day total. Each day must pass row conservation, deterministic output hashing, zero confirmed false merges across all exact-title groups, and model review of recovery samples and near pairs. Passing three days still requires a separate approval before the production schedule is changed.

