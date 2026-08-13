# global-news-brief

可版本化、可分享、可個人化的每日新聞簡報規格。

## 快速安裝

在新的 ChatGPT 對話貼上本 repo 網址，並輸入：

> 請讀取此 GitHub repo 的 INSTALL.md，依序協助我建立「每日新聞」專案、個人偏好與每日獨立排程。任何建立專案、排程或授權動作都先取得我的確認。

安裝流程會詢問所在地、關注地區、板塊順序、三碼代碼、新聞主題權重、時區及執行時間。完成後，每次排程都會重新讀取 repo 的最新規則。

詳細步驟請見 [INSTALL.md](INSTALL.md)，個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)。

## 核心文件

- `news-brief-settings.md`：篩選、驗證、地圖與圖片規則
- `news-brief-template.md`：讀者版硬模板
- `news-brief-examples.md`：正確與錯誤範例
- `user-preferences.example.yaml`：使用者可覆寫的地區與主題偏好
