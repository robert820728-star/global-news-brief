# 每日新聞排程起始指令

`USABLE_FIRST_SCHEDULE_INSTALL_GATE`：canonical create／update 以單一 mutation 提交完整 prompt、每天 06:00、帳號時區、目前對話與 `enabled=true`；控制面成功回傳 exact task ID 即完成可用安裝。

`POST_INSTALL_DIAGNOSTICS_GATE`：額外 readback 與 visible-media smoke 在安裝後執行；缺失標記 `verification_partial`，不得暫停、停用、刪除、重建或另建正式 task。

可存取 repository 執行面時，先用 `scripts/build_scheduled_task_install_payload.py` 產生 `saved-prompt.txt` 與收據；安裝 smoke／診斷只放在獨立的 `install-extension.json`，**不得寫入 saved-prompt.txt**。若目前 ChatGPT 宿主不能執行 script，仍須以 fresh main 模板全文與控制面 readback 完成同一 canonical identity，不得以短 launcher 代替。

排程保存內容必須把 `scheduled-task-prompt-template.md` 全文原樣設為 Scheduled Task instruction，只替換 INSTALL 明列允許的欄位；不得摘要、刪節或把 starter 本身存成 task prompt。

`CHAT_CONTINUATION_IS_NOT_SCHEDULED_OCCURRENCE_GATE`：只有 Scheduled Task 控制面真正觸發並提供可核對的 `scheduled_for`，才可建立或恢復 occurrence／run。一般對話中的「重新執行」、「再跑一次」或貼上舊結果不是 task trigger；manual、single-run、test 與 resume 只指帶有 `scheduled_for` 的實際 task occurrence。缺少 authority 時不得 fresh resolve main、不得建立或恢復 run、不得執行新聞 discovery，也不得輸出 Reader；只能回覆精簡 `lifecycle blocker receipt`。

`EVERY_DAILY_NEWS_EXECUTION_GATE`：每個真正 occurrence 仍使用相同新聞與逐則可見圖片門檻。安裝後可在建立或更新排程的目前對話直接執行獨立 capability probe，診斷來源 bytes→本機媒體交付、原生圖片卡或直接截圖頁面圖片區域；這不是 Scheduled Task occurrence，不要求立即觸發指定 task ID，也不是排程啟用前置條件。

`SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE`／`SCHEDULE_PROMPT_CAPABILITY_AWARE_VERIFICATION_GATE`／`SCHEDULE_PROMPT_EXACT_ID_READBACK_ONLY_GATE`／`SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE`：入口狀態解析後，以第一個 mutation 提交完整 prompt 與 enabled schedule。正式 create／update 成功回傳 exact task ID 後保持啟用；readback 與圖片 smoke 是後續診斷。一般 list 空結果或診斷失敗不得推翻成功回傳、停用 task 或觸發第二次 create。

`INSTALL_CONTROL_PLANE_FAST_PATH`／`SINGLETON_SCHEDULE_INSTALL_GATE`：新對話預設 `ensure_singleton`。`new_without_exact_id` 先用 authoritative inventory；`known_exact_id_resume` 對同一 ID 冪等更新；`create_outcome_unknown` 只查明原 operation。後兩者不得重新 inventory／create。第一次 create／update 前只讀安裝必要檔案，不展開新聞 runtime 文件。取得 ID 後，以目前對話內的正式 task 回傳或 task 卡核對同一身分，不要求不存在的 destination 欄位。

`NON_TEXT_SMOKE_OUTPUT_GATE`：smoke 回覆本身必須含真正實際可見的非文字 image/media content block 或附件，否則不得宣稱 smoke 通過。只有字面 `!:chatgpt-content-reference{...}`、`image_ref`、Markdown、URL、圖說或路徑時，把該路徑記為不可用。`attachments=[]` 僅是 metadata，不能單獨否定 UI 已由 exact-thread PrintWindow 證明的真正圖片像素；診斷結果不得修改正式 task。

`NATIVE_IMAGE_QUERY_RESULT_IS_NOT_CAPABILITY_GATE`：smoke 與 occurrence 判斷的是原生圖片／截圖工具本身是否可呼叫；某次查詢沒有回傳合格 `image_ref` 不代表宿主缺少圖片交付能力，也不得在 discovery 前據此停止。`WIRE_PROVIDER_SUBSTITUTION_GATE`：Reuters 等第一通訊社沒有合格 ref 時，必須切換 AP、官方／當事組織、當地可靠媒體與當地語言查詢，不得反覆撞同一來源。

在建立排程的目前對話貼上下方整段。安裝細節全部以 fresh main 的 `INSTALL.md` 為準；starter 不重複內部 state machine：

下方 starter 的「目前對話」就是目前這個對話；`present` 分支必須更新同名既有排程。

```text
請依 GitHub repository `robert820728-star/global-news-brief` 最新 main 的 `INSTALL.md`，完整安裝並確保只有一個「每日新聞」ChatGPT Scheduled Task。

設定：區域＝台灣、中國、世界；監控類型：預設；每天 06:00；目前帳號時區；結果回覆目前這個對話。

請 fresh resolve 最新 main，完整遵循 INSTALL.md 的 canonical prompt、安裝與驗證流程。不得使用縮短版 prompt；若已有符合排程就更新，不得建立重複排程。完成後回覆 exact task ID、saved prompt 驗證、時區、enabled、next run time 與同對話 delivery 證據；無法取得的安裝後診斷欄位標記 `verification_partial`，不得因此停用已成功建立或更新的排程。
```


