# 每日新聞排程起始指令

可存取 repository 執行面時，先用 `scripts/build_scheduled_task_install_payload.py` 產生 `saved-prompt.txt` 與收據；安裝 smoke／診斷只放在獨立的 `install-extension.json`，**不得寫入 saved-prompt.txt**。若目前 ChatGPT 宿主不能執行 script，仍須以 fresh main 模板全文與控制面 readback 完成同一 canonical identity，不得以短 launcher 代替。

`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE`／`EVERY_DAILY_NEWS_EXECUTION_GATE`：manual, single-run, test, first-run, recurring, or resume 使用相同新聞與逐則可見圖片門檻。建立或修正排程時先更新最新版完整 task prompt，再於目前對話依獨立 capability probe 完成至少一條端到端可見媒體路徑：可驗證的來源 bytes→解碼／雜湊→本機媒體交付、原生圖片卡，或已實測可用的公開頁面圖片區域截圖。這不是 Scheduled Task occurrence，不要求立即觸發指定 task ID，也不得等待 occurrence 執行介面；不得由 `page_open` 推導 `webpage_region_screenshot`。不得要求先取得 verified workspace、台灣底圖、原始檔或原畫質。

`SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE`／`SCHEDULE_PROMPT_CAPABILITY_AWARE_VERIFICATION_GATE`／`SCHEDULE_PROMPT_EXACT_ID_READBACK_ONLY_GATE`／`SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE`：先核對並提交完整 prompt；同一控制面支援 exact task ID readback 時讀回逐字核對，沒有 exact-ID view 時以提交前核對證明完整 outbound payload，再核對正式 create／update 結果中的 task ID、成功狀態、每天 06:00、時區與目前對話。scope 不明的一般 list 空結果不得推翻 create 成功，且不得盲建重複排程；再做同宿主可見圖片 smoke。smoke 失敗時保留最新版 prompt 並暫停 task，禁止回復或繼續啟用舊 prompt。

`NON_TEXT_SMOKE_OUTPUT_GATE`：smoke 回覆本身必須含真正可見的非文字 image/media content block 或附件。只有字面 `!:chatgpt-content-reference{...}`、`image_ref`、Markdown、URL、圖說或路徑時，不得宣稱 smoke 通過。`attachments=[]` 僅是 metadata，不能單獨否定 UI 已由 exact-thread PrintWindow 證明的真正圖片像素；若 metadata 為空且也沒有可見像素證據，才保持同一 task 暫停並改走另一條已驗證媒體路徑。

`NATIVE_IMAGE_QUERY_RESULT_IS_NOT_CAPABILITY_GATE`：smoke 與 occurrence 判斷的是原生圖片／截圖工具本身是否可呼叫；某次查詢沒有回傳合格 `image_ref` 不代表宿主缺少圖片交付能力，也不得在 discovery 前據此停止。`WIRE_PROVIDER_SUBSTITUTION_GATE`：Reuters 等第一通訊社沒有合格 ref 時，必須切換 AP、官方／當事組織、當地可靠媒體與當地語言查詢，不得反覆撞同一來源。

在建立排程的目前對話貼上下方整段。ChatGPT 必須讀取最新版 `INSTALL.md`，先把最新版 `scheduled-task-prompt-template.md` 全文原樣設為 Scheduled Task instruction，並依控制面是否提供 saved-prompt readback 執行對應驗證，再完成同宿主原生圖片／直接截圖實測；不得濃縮成只有「依 INSTALL 執行」的短 launcher：

```text
每日新聞排程

請 fresh resolve https://github.com/robert820728-star/global-news-brief 當下最新 main，完整閱讀最新版 INSTALL.md，依「Scheduled Task 排程指令唯一契約」取得 scheduled-task-prompt-template.md 全文。只替換「區域：台灣、中國、世界」及「監控類型：預設」兩個 placeholder，將完整全文原樣設為 saved prompt；不得摘要、刪節或只保存連結。

在目前這個對話建立每天 06:00、使用目前對話／帳號時區、結果只回覆目前對話的「每日新聞」循環排程；優先更新同名既有排程，不得重複建立。

提交前先全文核對 create／update payload。若同一控制面的 exact task ID view 可用，建立或更新後以回傳的 task ID 讀回並比較完整 prompt（只容許 CRLF／LF 與檔尾換行差異）；只有該 exact-ID view 明確回傳不存在或內容不一致，才更新同一排程後重試並在再次失敗時判定未完成。若沒有 exact-ID view，依 INSTALL.md 核對正式 create／update 回傳中的 task ID、成功狀態、每天 06:00 與時區；在目前對話發出 create／update，且目前對話內的正式 task 回傳或 task 卡顯示相同 exact task ID，即證明 destination 是目前對話，不要求不存在的 destination 欄位。一般 list／search 空結果不得推翻成功回傳、不得觸發重複建立，也不得自行發明另一套讀回機制。

prompt 驗證後，依 INSTALL.md 在建立或更新排程的目前對話直接執行可見圖片 smoke，依獨立 capability probe 使用完整來源 bytes→本機媒體交付、原生圖片卡或已實測可用的公開頁面圖片區域截圖，確認目前對話實際可見。這不是 Scheduled Task occurrence，不要求立即觸發指定 task ID，也不得因沒有 occurrence 立即執行介面而停止；通過才啟用循環並回覆排程已完成，失敗則保留最新版 prompt、暫停同一 task 並回報實際失敗步驟。

smoke 的同一則回覆必須真正含非文字圖片／附件；字面 `!:chatgpt-content-reference{...}`、`image_ref`、Markdown、URL、圖說或路徑都是 FAIL。`attachments=[]` 不能單獨推翻 exact-thread PrintWindow 中可辨識的真正圖片像素；若兩者都沒有，禁止回覆 smoke 已通過。
```


