# 每日新聞排程起始指令

可存取 repository 執行面時，先用 `scripts/build_scheduled_task_install_payload.py` 產生 `saved-prompt.txt` 與收據；安裝 smoke／診斷只放在獨立的 `install-extension.json`，**不得寫入 saved-prompt.txt**。若目前 ChatGPT 宿主不能執行 script，仍須以 fresh main 模板全文與控制面 readback 完成同一 canonical identity，不得以短 launcher 代替。

`CHAT_CONTINUATION_IS_NOT_SCHEDULED_OCCURRENCE_GATE`：只有 Scheduled Task 控制面真正觸發並提供可核對的 `scheduled_for`，才可建立或恢復 occurrence／run。一般對話中的「重新執行」、「再跑一次」或貼上舊結果不是 task trigger；manual、single-run、test 與 resume 只指帶有 `scheduled_for` 的實際 task occurrence。缺少 authority 時不得 fresh resolve main、不得建立或恢復 run、不得執行新聞 discovery，也不得輸出 Reader；只能回覆精簡 `lifecycle blocker receipt`。

`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE`／`EVERY_DAILY_NEWS_EXECUTION_GATE`：manual, single-run, test, first-run, recurring, or resume 使用相同新聞與逐則可見圖片門檻。建立或修正排程時先更新最新版完整 task prompt，再於目前對話依獨立 capability probe 完成至少一條端到端可見媒體路徑：可驗證的來源 bytes→解碼／雜湊→本機媒體交付、原生圖片卡，或已實測可用的公開頁面圖片區域截圖。這不是 Scheduled Task occurrence，不要求立即觸發指定 task ID，也不得等待 occurrence 執行介面；不得由 `page_open` 推導 `webpage_region_screenshot`。不得要求先取得 verified workspace、台灣底圖、原始檔或原畫質。

`SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE`／`SCHEDULE_PROMPT_CAPABILITY_AWARE_VERIFICATION_GATE`／`SCHEDULE_PROMPT_EXACT_ID_READBACK_ONLY_GATE`／`SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE`：先核對並提交完整 prompt；同一控制面支援 exact task ID readback 時讀回逐字核對，沒有 exact-ID view 時以提交前核對證明完整 outbound payload，再核對正式 create／update 結果中的 task ID、成功狀態、每天 06:00、時區與目前對話。scope 不明的一般 list 空結果不得推翻 create 成功，且不得盲建重複排程；再做同宿主可見圖片 smoke。smoke 失敗時保留最新版 prompt 並暫停 task，禁止回復或繼續啟用舊 prompt。

`INSTALL_CONTROL_PLANE_FAST_PATH`／`EXPLICIT_SCHEDULE_INSTALL_INTENT_GATE`：新對話明確要求建立時固定為 `create_new`，第一次 create／update 前只讀安裝必要檔案，不先展開新聞 runtime 文件；create 不以同名 list／search 為前置且只呼叫一次。更新同名既有排程屬 `update_existing`，必須先有 exact task ID。結果不明時不得重送 create，必須保存實際控制面錯誤並查明第一次結果。取得 ID 後，以目前對話內的正式 task 回傳或 task 卡核對同一身分，不要求不存在的 destination 欄位。canonical saved prompt 不得摘要、刪節。圖片 smoke 必須在建立或更新排程的目前對話直接執行，並以直接截圖或原生圖片卡證明實際可見；它不是 Scheduled Task occurrence，也不要求立即觸發指定 task ID。

`NON_TEXT_SMOKE_OUTPUT_GATE`：smoke 回覆本身必須含真正可見的非文字 image/media content block 或附件。只有字面 `!:chatgpt-content-reference{...}`、`image_ref`、Markdown、URL、圖說或路徑時，不得宣稱 smoke 通過。`attachments=[]` 僅是 metadata，不能單獨否定 UI 已由 exact-thread PrintWindow 證明的真正圖片像素；若 metadata 為空且也沒有可見像素證據，才保持同一 task 暫停並改走另一條已驗證媒體路徑。

`NATIVE_IMAGE_QUERY_RESULT_IS_NOT_CAPABILITY_GATE`：smoke 與 occurrence 判斷的是原生圖片／截圖工具本身是否可呼叫；某次查詢沒有回傳合格 `image_ref` 不代表宿主缺少圖片交付能力，也不得在 discovery 前據此停止。`WIRE_PROVIDER_SUBSTITUTION_GATE`：Reuters 等第一通訊社沒有合格 ref 時，必須切換 AP、官方／當事組織、當地可靠媒體與當地語言查詢，不得反覆撞同一來源。

在建立排程的目前對話貼上下方整段。ChatGPT 必須讀取最新版 `INSTALL.md`，先把最新版 `scheduled-task-prompt-template.md` 全文原樣設為 Scheduled Task instruction，並依控制面是否提供 saved-prompt readback 執行對應驗證，再完成同宿主原生圖片／直接截圖實測；不得濃縮成只有「依 INSTALL 執行」的短 launcher：

```text
每日新聞排程

IMMUTABLE_INSTALL_MAIN_RESOLUTION_GATE：先各產生一個 fresh UTC nonce，分別讀取 https://api.github.com/repos/robert820728-star/global-news-brief/branches/main?cache_bust=<nonce-a> 與 https://api.github.com/repos/robert820728-star/global-news-brief/commits/main?cache_bust=<nonce-b>。兩者必須回傳相同的 40 字元 SHA；若不同，用兩個新 nonce 重試整組一次，仍不同就回報兩個值並停止，不得猜測。之後只從 https://raw.githubusercontent.com/robert820728-star/global-news-brief/<resolved-main-sha>/INSTALL.md 讀取安裝契約，並從同一 <resolved-main-sha> 讀取 template 與安裝檔；mutable /main 不得作為本次安裝權威。

本次安裝意圖：create_new。區域：台灣、中國、世界。監控類型：預設。依該 immutable INSTALL.md 的 INSTALL_CONTROL_PLANE_FAST_PATH，把同一 SHA 的 scheduled-task-prompt-template.md 全文只替換允許的兩個 placeholder，驗證後作為唯一一次 create payload。第一次 create 前不得呼叫 list／search／inventory，也不得先讀新聞 runtime 文件；anti-duplicate 只禁止第二次 create。請在目前這個對話建立每天 06:00、使用目前帳號／對話時區、結果回覆目前對話的循環 Scheduled Task。正式 create／update 回傳 task ID 後，所有 readback、可見圖片 smoke、啟用與 next-run 核對只綁定同一控制面的 exact task ID；一般 list／search 空結果不得推翻正式成功回傳。第一次 create 結果不明時不得重送，須保存 actual control-plane error 並查明原操作。smoke 通過才啟用，最後回覆 exact task ID、saved-prompt 驗證、時區、enabled、next run 與目前對話 delivery 證據。
```


