# 手機 ChatGPT 起始指令

先在手機 ChatGPT 的模型選單選擇 **Instant**。若可設定，關閉自動切換到 Thinking。不要使用 Thinking 或 Pro。

接著把下方整段貼到一般 ChatGPT 對話。ChatGPT 必須讀取最新版 `INSTALL.md`，再把最新版 `scheduled-task-prompt-template.md` 全文原樣設為 Scheduled Task instruction；不得濃縮成只有「依 INSTALL 執行」的短 launcher：

```text
每日新聞排程
請確認 https://github.com/robert820728-star/global-news-brief 的最新 main commit，完整閱讀最新版 INSTALL.md，依其「Scheduled Task 排程指令唯一契約」取得 scheduled-task-prompt-template.md 全文，替換我指定的區域與監控類型後，原樣設為 Scheduled Task instruction，不得摘要、縮短或只留下檔案連結。

1. 請在目前這個對話內建立每天 6 點循環排程；使用目前對話／帳號的時區，名稱為「每日新聞」。
2. 區域：台灣、中國、世界。監控類型：預設。
3. 每次結果只回覆在目前這個對話，不要另開新對話。
4. 建立完成後，回報實際保存的完整 task instruction 與 schedule；不得只回覆一段摘要。
```
