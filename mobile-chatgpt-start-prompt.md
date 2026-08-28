# 手機 ChatGPT 相容啟動指令

本檔只提供舊書籤／舊連結的相容導引，**不是另一個安裝入口，也不是 Scheduled Task 規則來源**。目前唯一安裝入口與排程 prompt 權威是 repository 當下最新 `INSTALL.md`。

若從手機一般 ChatGPT 開始，直接貼：

```text
請使用以下 GitHub 專案建立我的每日新聞簡報：
https://github.com/robert820728-star/global-news-brief

請先完整閱讀當下最新 main 的 INSTALL.md，並以 INSTALL.md 作為唯一安裝與執行入口；依其中的 Scheduled Task 排程指令唯一契約建立排程。不要把本檔、mobile-chatgpt-daily-prompt.md 或任何圖片／驗證細節複製成第二份 task prompt。每次觸發都 fresh resolve 最新 main，執行進度、成功結果或最早不可恢復 blocker 只回覆到建立此排程的目前對話，不得另開新對話。
```

排程時間、時區、區域與監控類型若已由使用者指定就直接沿用；未指定時由 `INSTALL.md` 的現行規則處理。mobile-native 的 discovery、評分、驗證、圖片、release gate assertions、Reader、恢復與持久化契約均由每次觸發時的最新 `INSTALL.md` 及其權責文件取得，本檔不複製那些規則，避免版本漂移。
