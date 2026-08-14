# 每日新聞固定排程提示詞

本文件是排程執行規格，不是讀者版內容。

## 對話與日期

- 排程名稱固定為「每日新聞」。
- 每次執行使用獨立結果對話；可控制名稱時，名稱只能是「每日新聞」。
- 讀者版第一行固定為執行地日期 `YYYY/MM/DD 每日新聞`，每次重新計算。
- 不得在讀者版加入完成通知、執行說明、安裝狀態、專案歸屬或後台限制。

## 每次執行

1. 重新讀取 repo `robert820728-star/global-news-brief` 最新版：
   - `.agents/skills/daily-news-brief/SKILL.md`
   - `news-brief-settings.md`
   - `news-brief-template.md`
   - `user-preferences.example.yaml`
   - `schemas/news-event-manifest.schema.json`
   - `schemas/news-candidate-audit.schema.json`
   - `.agents/skills/audit-news-candidates/SKILL.md`
2. 明確依 `daily-news-brief` 主控技能執行。主控技能必須依序使用：
   - `select-news-events`
   - `audit-news-candidates`
   - `verify-news-events`
   - `build-news-maps`
   - `build-news-charts`
   - `collect-news-images`
   - `recover-news-run`
3. 讀取排程保存的個人偏好。個人偏好只覆寫板塊、順序、權重、篇數、最低等級、主題、語言、時區與執行時間，不得覆寫查證、欄位所有權、地圖、圖片及驗收規則。
4. 以實際執行時間往前精確 24 小時搜尋新聞。
5. 先執行 `scripts/preprocess_news_candidates.py`，以程式處理時間窗、網址正規化、完全重複及初步聚類；此步驟不得決定入選或評級。
6. 先建立事件資料，再按固定模組逐步補充。任何模組不得重新生成整份事件清單或刪除其他模組已完成的地圖、資料圖表、圖片、來源與分析。
7. 完成後套用 `news-brief-template.md`。若環境可執行程式，使用 `scripts/validate_news_brief.py` 驗證事件資料與讀者版；若格式驗證失敗，才讀取 `news-brief-examples.md` 的相關正反例並局部修正。
   - B 以上事件必須逐一記錄引用來源頁的圖片檢查結果。
   - 任一來源已找到可用圖片時，至少一張本地附件完成視覺驗收前，最終狀態不得為 `ready`，也不得輸出讀者版。
   - 圖片取得中斷只重跑 `collect-news-images`；不得以自製地圖或 `omitted` 取代已存在的來源圖片。
   - 自製資料圖表只在數值比較、趨勢、比例或分布有實質價值時建立；禁止製作純文字摘要卡或立場卡。
   - 地圖、自製資料圖表、官方或媒體來源圖片三者獨立；自製資料圖表不得取代來源圖片，也不得讓圖片硬閘門提前完成。
   - 每階段完成後及輸出前使用 `recover-news-run` 檢查未完成、失敗與驗證錯誤；只重跑失敗事件與原欄位擁有技能。
   - 同一事件同一模組最多重試三次。成功後重新驗證；耗盡時明確輸出故障回報，不得無聲結束或假稱完成。
8. 未設定偏好時使用台灣 `TWN`、中國 `CHN`、世界 `GLB`，語言為繁體中文，時區為 `Asia/Taipei`。
9. 若時間窗內沒有事件通過門檻，仍輸出當日日期與三個固定區塊，簡短說明沒有事件通過門檻；不得以舊聞補數量。

## 兩週候選稽核

- 海選後、驗證前完整執行 `audit-news-candidates`；十四天歷史是增強功能，不是每日簡報的執行門檻。
- 全部候選都要記錄決定與理由；D／E 只留內部，不得輸出讀者版。
- 暫定 B 以上候選不得無聲消失；理由缺漏時只重跑 `select-news-events` 與 `audit-news-candidates`。
- 持續事件比較十四天內新增、未變與狀態轉折；無實質更新可不重複入選，但必須留下比較說明。
- 單一可靠來源不得成為排除理由。
- 歷史讀取與保存依序採用：可讀的既有 `state/candidate-audit.json`、使用者可持久保存的工作區、具有寫入權限的 repository。可同時使用時，以可持久保存且不會影響公共範本的使用者工作區為優先。
- 沒有 GitHub 帳號、repository 寫入權限或持久工作區時，仍完成本輪候選決策、D／E 分類與讀者版；十四天比較降級為本輪或目前可讀歷史，不得中止簡報。
- 無法跨次保存時，可輸出本輪稽核附件供下次匯入；若附件也無法保存，只在本次執行中使用並如實標記「未延續歷史」，不得假稱十四天歷史已更新。
- 稽核保存失敗不得改變事件評級、入選結果、圖片、地圖、資料圖表或最終輸出狀態。

## 最終輸出

日期行之後只能保留：

- `今日總覽`
- `逐條詳報`
- `後續觀察`

不得輸出事件資料、技能執行紀錄、驗證報告或任何前言。
