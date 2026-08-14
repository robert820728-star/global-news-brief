# global-news-brief

可版本化、可分享、可個人化，而且能逐階段驗收的每日新聞簡報工作流。

## 快速安裝

在新的 ChatGPT 或 Codex 對話貼上本 repo 網址，並完整輸入：

> 請讀取此 GitHub repo 的 INSTALL.md。先從 `.agents/skills/` 下載並安裝完整的五個新聞技能及其必要檔案，逐一驗證後，再協助我設定個人偏好與每日新聞排程。不得只讀取 `SKILL.md` 就宣稱安裝成功；任何建立或修改技能與排程的動作都先取得我的確認。

GPT 應先處理技能，再詢問偏好與排程：

1. 能安裝技能時，下載五個完整技能資料夾並逐一驗證。
2. 在本 repo 工作目錄內執行時，使用 `.agents/skills/` 的 repo 級技能。
3. 只有讀取 GitHub 的能力、無法安裝技能時，必須明確說明並改成每次重新讀取，不得假稱已安裝。

詳細的下載、驗證與降級流程以 [INSTALL.md](INSTALL.md) 為準。

安裝時只需確認三件事：

1. 是否自訂監控板塊；可以是單一國家，也可以是區域，例如日本、歐盟、北美、非洲或東南亞。不自訂時使用台灣、中國、世界。
2. 是否調整特別感興趣或降低權重的新聞主題。
3. 每日幾點執行。

輸出語言優先沿用使用者已設定的語言；沒有設定時沿用安裝對話的主要語言。時區優先使用帳號、裝置或目前工作區時區，只有無法判斷時才詢問。

完成後，每次排程都會重新讀取 repo 最新規則，並以獨立結果對話輸出當日新聞：

- 排程及結果對話名稱固定為「每日新聞」。
- 每份讀者版第一行固定為執行地日期的 `YYYY/MM/DD 每日新聞`。

個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)，排程執行提示詞請見 [daily-schedule-prompt.md](daily-schedule-prompt.md)。

## 模組化架構

工作流固定使用五個 repo 技能，透過同一份事件清單交接；後段技能不能重建事件或刪除前段成果。

| 階段 | 技能 | 唯一負責內容 |
|---|---|---|
| 主控 | `daily-news-brief` | 精確時間窗、模組順序、詳報組裝、最終輸出與驗收 |
| 海選 | `select-news-events` | 候選、事件去重、板塊、編號、入選與評級 |
| 複查 | `verify-news-events` | 多來源、原始／官方回查、主張台帳、差異與不確定性 |
| 地圖 | `build-news-maps` | 自製定位地圖及其驗收 |
| 圖片 | `collect-news-images` | 官方資訊圖、新聞配圖、下載／截圖與視覺驗收 |

所有技能共用 `schemas/news-event-manifest.schema.json`。欄位所有權與最終讀者版由 `scripts/validate_news_brief.py` 檢查，因此新增地圖不會清空圖片，補圖片也不會覆蓋來源或評級。

## 核心文件

- `.agents/skills/`：五個可獨立維護的工作流技能
- `schemas/news-event-manifest.schema.json`：跨技能事件資料契約
- `scripts/validate_news_brief.py`：事件資料、欄位所有權與讀者版驗證器
- `news-brief-settings.md`：編輯偏好、收納、分級與共通規則
- `news-brief-template.md`：讀者版硬模板
- `news-brief-examples.md`：正確與錯誤範例
- `user-preferences.example.yaml`：使用者可覆寫的地區與主題偏好
- `daily-schedule-prompt.md`：每日獨立排程的固定執行提示詞

## 本地驗證

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_news_brief.py manifest --input /path/to/news-event-manifest.json
python3 scripts/validate_news_brief.py brief --manifest /path/to/news-event-manifest.json --input /path/to/news-brief.md
```

驗證器只依標準函式庫執行，不需要另裝 Python 套件。
