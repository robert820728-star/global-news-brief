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
2. 明確依 `daily-news-brief` 主控技能執行。主控技能必須依序使用：
   - `select-news-events`
   - `verify-news-events`
   - `build-news-maps`
   - `collect-news-images`
3. 讀取排程保存的個人偏好。個人偏好只覆寫板塊、順序、權重、篇數、最低等級、主題、語言、時區與執行時間，不得覆寫查證、欄位所有權、地圖、圖片及驗收規則。
4. 以實際執行時間往前精確 24 小時搜尋新聞。
5. 先建立事件資料，再按固定模組逐步補充。任何模組不得重新生成整份事件清單或刪除其他模組已完成的地圖、圖片、來源與分析。
6. 完成後套用 `news-brief-template.md`。若環境可執行程式，使用 `scripts/validate_news_brief.py` 驗證事件資料與讀者版；若格式驗證失敗，才讀取 `news-brief-examples.md` 的相關正反例並局部修正。
7. 未設定偏好時使用台灣 `TWN`、中國 `CHN`、世界 `GLB`，語言為繁體中文，時區為 `Asia/Taipei`。
8. 若時間窗內沒有事件通過門檻，仍輸出當日日期與三個固定區塊，簡短說明沒有事件通過門檻；不得以舊聞補數量。

## 最終輸出

日期行之後只能保留：

- `今日總覽`
- `逐條詳報`
- `後續觀察`

不得輸出事件資料、技能執行紀錄、驗證報告或任何前言。

