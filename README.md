# global-news-brief

可版本化、可分享、可個人化的每日新聞簡報規格。

## 快速安裝

在新的 ChatGPT 對話貼上本 repo 網址，並輸入：

> 請讀取此 GitHub repo 的 INSTALL.md，依序協助我建立「每日新聞」專案、個人偏好與每日獨立排程。任何建立專案、排程或授權動作都先取得我的確認。

ChatGPT 不會自動建立專案。開始安裝後，會先在原對話引導你於側邊欄建立「每日新聞」專案；你回覆「已建立」或「沿用既有專案」後，才會繼續設定偏好與排程。專案確認前不會建立任何測試或正式排程。

安裝時再確認三件事：

1. 是否自訂監控板塊；可以是單一國家，也可以是區域，例如日本、歐盟、北美、非洲或東南亞。不自訂時使用台灣、中國、世界。
2. 是否調整特別感興趣或降低權重的新聞主題。
3. 每日幾點執行。

輸出語言優先沿用使用者已設定的語言；沒有設定時沿用安裝對話的主要語言。時區優先使用帳號、裝置或目前工作區時區，只有無法判斷時才詢問。

完成後，每次排程都會重新讀取 repo 最新規則，並以獨立結果對話輸出當日新聞，建議標題為 `YYYY/MM/DD 每日新聞`。

詳細步驟請見 [INSTALL.md](INSTALL.md)，個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)，排程執行提示詞請見 [daily-schedule-prompt.md](daily-schedule-prompt.md)。

## 核心文件

- `news-brief-settings.md`：篩選、驗證、地圖與圖片規則
- `news-brief-template.md`：讀者版硬模板
- `news-brief-examples.md`：正確與錯誤範例
- `user-preferences.example.yaml`：使用者可覆寫的地區與主題偏好
- `daily-schedule-prompt.md`：每日獨立排程的固定執行提示詞
