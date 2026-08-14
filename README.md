# global-news-brief

可版本化、可分享、可個人化，而且能逐階段驗收的每日新聞簡報工作流。

## 快速安裝

在新的 ChatGPT 對話貼上本 repo 網址，並輸入：

> 請讀取此 GitHub repo 的 INSTALL.md，協助我設定個人偏好與每日新聞排程。任何建立或修改排程的動作都先取得我的確認。

安裝時只需確認三件事：

1. 是否自訂監控板塊；可以是單一國家，也可以是區域，例如日本、歐盟、北美、非洲或東南亞。不自訂時使用台灣、中國、世界。
2. 是否調整特別感興趣或降低權重的新聞主題。
3. 每日幾點執行。

輸出語言優先沿用使用者已設定的語言；沒有設定時沿用安裝對話的主要語言。時區優先使用帳號、裝置或目前工作區時區，只有無法判斷時才詢問。

完成後，每次排程都會重新讀取 repo 最新規則，並以獨立結果對話輸出當日新聞：

- 排程及結果對話名稱固定為「每日新聞」。
- 每份讀者版第一行固定為執行地日期的 `YYYY/MM/DD 每日新聞`。

詳細步驟請見 [INSTALL.md](INSTALL.md)，個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)，排程執行提示詞請見 [daily-schedule-prompt.md](daily-schedule-prompt.md)。

## 不需要 GitHub 帳號

公開 repo 的規則、技能、模板、地圖與圖片流程都可直接讀取；沒有 GitHub 帳號或寫入權限仍可產生完整每日新聞。

十四天候選回查採漸進式保存：優先使用可持久工作區，其次使用具寫入權限的 repository。若兩者皆不可用，系統仍完成本輪海選、D／E 內部分級、來源複查與讀者版，只是不保證跨日保存十四天歷史。此降級不得影響事件評級、入選、圖片、地圖或最終輸出。

## 模組化架構

工作流固定使用七個 repo 技能，透過同一份事件清單交接；後段技能不能重建事件或刪除前段成果。

| 階段 | 技能 | 唯一負責內容 |
|---|---|---|
| 主控 | `daily-news-brief` | 精確時間窗、模組順序、詳報組裝、最終輸出與驗收 |
| 海選 | `select-news-events` | 候選、事件去重、板塊、編號、入選與評級 |
| 稽核 | `audit-news-candidates` | 十四天候選紀錄、排除理由、D／E 內部分級與持續事件比較 |
| 複查 | `verify-news-events` | 多來源、原始／官方回查、主張台帳、差異與不確定性 |
| 地圖 | `build-news-maps` | 自製定位地圖及其驗收 |
| 圖片 | `collect-news-images` | 官方資訊圖、新聞配圖、下載／截圖與視覺驗收 |
| 恢復 | `recover-news-run` | 失敗偵測、局部重跑、重試上限與重新驗證 |

所有技能共用 `schemas/news-event-manifest.schema.json`。欄位所有權與最終讀者版由 `scripts/validate_news_brief.py` 檢查，因此新增地圖不會清空圖片，補圖片也不會覆蓋來源或評級。

## 核心文件

- `.agents/skills/`：七個可獨立維護的工作流技能
- `schemas/news-event-manifest.schema.json`：跨技能事件資料契約
- `schemas/news-candidate-audit.schema.json`：候選稽核與十四天歷史資料契約
- `scripts/manage_candidate_audit.py`：候選歷史裁切、附加與驗證工具
- `scripts/validate_news_brief.py`：事件資料、欄位所有權與讀者版驗證器
- `scripts/recover_news_run.py`：產生局部恢復計畫並記錄重試結果
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
