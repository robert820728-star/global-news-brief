# 每日新聞排程起始指令

`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE`／`EVERY_DAILY_NEWS_EXECUTION_GATE`：manual, single-run, test, first-run, recurring, or resume 使用相同新聞與逐則可見圖片門檻。建立或修正排程時先更新最新版完整 task prompt，再以同一 Scheduled Task／ChatGPT 工具執行面直接截圖公開頁面的圖片區域或交付原生圖片卡；不得要求先取得 verified workspace、台灣底圖、原始檔或原畫質。

`SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE`／`SCHEDULE_PROMPT_CAPABILITY_AWARE_VERIFICATION_GATE`／`SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE`：先核對並提交完整 prompt；支援 saved-prompt readback 時讀回逐字核對，明確不提供時以提交前核對證明完整 outbound payload，再核對正式 create／update 結果中的 task ID、成功狀態、每天 06:00、時區與目前對話，且不得盲建重複排程；再做同宿主可見圖片 smoke。smoke 失敗時保留最新版 prompt 並暫停 task，禁止回復或繼續啟用舊 prompt。

`NATIVE_IMAGE_QUERY_RESULT_IS_NOT_CAPABILITY_GATE`：smoke 與 occurrence 判斷的是原生圖片／截圖工具本身是否可呼叫；某次查詢沒有回傳合格 `image_ref` 不代表宿主缺少圖片交付能力，也不得在 discovery 前據此停止。`WIRE_PROVIDER_SUBSTITUTION_GATE`：Reuters 等第一通訊社沒有合格 ref 時，必須切換 AP、官方／當事組織、當地可靠媒體與當地語言查詢，不得反覆撞同一來源。

在建立排程的目前對話貼上下方整段。ChatGPT 必須讀取最新版 `INSTALL.md`，先把最新版 `scheduled-task-prompt-template.md` 全文原樣設為 Scheduled Task instruction，並依控制面是否提供 saved-prompt readback 執行對應驗證，再完成同宿主原生圖片／直接截圖實測；不得濃縮成只有「依 INSTALL 執行」的短 launcher：

```text
每日新聞排程
請確認 https://github.com/robert820728-star/global-news-brief 的最新 main commit，完整閱讀最新版 INSTALL.md。依「Scheduled Task 排程指令唯一契約」取得 scheduled-task-prompt-template.md 全文，替換我指定的區域與監控類型後，先原樣設為 Scheduled Task instruction，不得摘要、縮短或只留下檔案連結。控制面支援 saved-prompt readback 時，讀回並逐字核對；若明確不提供 readback，依 INSTALL.md 的 capability-aware 規則核對正式 create／update 結果，不得因缺少 readback 就宣告未建立，也不得盲建重複排程。完成 prompt 更新驗證後，以同一 Scheduled Task／ChatGPT 工具執行面直接截圖一個公開頁面的圖片區域或交付原生圖片卡，確認目前對話實際可見後才啟用循環；不要求 verified workspace、原始檔或原畫質。若 smoke 失敗，保留最新版 prompt 並暫停 task，不得讓舊 prompt 繼續啟用。

1. 請在目前這個對話內建立每天 6 點循環排程；使用目前對話／帳號的時區，名稱為「每日新聞」。
2. 區域：台灣、中國、世界。監控類型：預設。
3. 每次結果只回覆在目前這個對話，不要另開新對話。
4. 建立完成後，回報實際可見的同宿主測試截圖／原生圖片、實際保存的完整 task instruction 與 schedule；不得只回覆一段摘要。
```


