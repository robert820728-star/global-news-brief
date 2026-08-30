# 每日新聞排程起始指令

正式循環排程必須從 ChatGPT desktop／Codex 的 desktop/local project 對話建立，不能從只有 web／mobile `mobile-native` 能力的一般對話建立。`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE` 與 `VISIBLE_LOCAL_ATTACHMENT_INSTALL_SMOKE_GATE` 要求先把 verified workspace 的 `maps/generated/taiwan-counties-yellow-v2.png` 當作本機實體附件送到目前對話，並確認目前對話中實際可見；失敗時不得啟用排程或改建 production mobile-native 排程。

在已開啟 repository 的 desktop/local project 對話貼上下方整段。ChatGPT 必須讀取最新版 `INSTALL.md`，先完成真實本機附件實測，再把最新版 `scheduled-task-prompt-template.md` 全文原樣設為 Scheduled Task instruction；不得濃縮成只有「依 INSTALL 執行」的短 launcher：

```text
每日新聞排程
請確認 https://github.com/robert820728-star/global-news-brief 的最新 main commit，完整閱讀最新版 INSTALL.md。先依 VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE 與 VISIBLE_LOCAL_ATTACHMENT_INSTALL_SMOKE_GATE，在目前 desktop/local project 取得 verified workspace，將 maps/generated/taiwan-counties-yellow-v2.png 以本機實體附件送到目前對話並確認實際可見；未通過時不得建立或啟用排程。通過後依「Scheduled Task 排程指令唯一契約」取得 scheduled-task-prompt-template.md 全文，替換我指定的區域與監控類型後，原樣設為 Scheduled Task instruction，不得摘要、縮短或只留下檔案連結。

1. 請在目前這個對話內建立每天 6 點循環排程；使用目前對話／帳號的時區，名稱為「每日新聞」。
2. 區域：台灣、中國、世界。監控類型：預設。
3. 每次結果只回覆在目前這個對話，不要另開新對話。
4. 排程必須綁定目前 desktop/local project 並使用 full-runtime；不得建立成 production mobile-native。建立完成後，回報實際可見的安裝測試圖片、實際保存的完整 task instruction 與 schedule；不得只回覆一段摘要。
```
