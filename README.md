# global-news-brief

可版本化、可分享、可個人化，而且能逐階段驗收的每日新聞簡報工作流。

## 執行環境

`SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE`：名稱保留作相容識別；實際門檻是同一 Scheduled Task 宿主完成任一條已獨立驗證的端到端可見媒體路徑，並非強制使用 screenshot。

`CHAT_CONTINUATION_IS_NOT_SCHEDULED_OCCURRENCE_GATE`：只有 Scheduled Task 控制面真正觸發並提供可核對的 `scheduled_for`，才可建立或恢復 occurrence／run。一般對話中的「重新執行」、「再跑一次」或貼上舊結果不是 task trigger；manual、single-run、test 與 resume 只指帶有 `scheduled_for` 的實際 task occurrence。缺少 authority 時不得 fresh resolve main、不得建立或恢復 run、不得執行新聞 discovery，也不得輸出 Reader；只能回覆精簡 `lifecycle blocker receipt`。

`EVERY_DAILY_NEWS_EXECUTION_GATE`／`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE`：manual, single-run, test, first-run, recurring, or resume 使用相同新聞與逐則可見圖片門檻。依獨立 capability probe，完整本機媒體鏈可交付本機附件；ChatGPT Scheduled Task 也可使用原生圖片卡或已實測可用的頁面圖片區域截圖。不要求原始檔或原畫質，且不得由能開頁面推導能截圖。

`SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE`／`SCHEDULE_PROMPT_CAPABILITY_AWARE_VERIFICATION_GATE`／`SCHEDULE_PROMPT_EXACT_ID_READBACK_ONLY_GATE`：建立或修正排程時先以最新版完整範本取代 saved prompt。控制面支援同一 namespace 的 exact task ID readback 時必須讀回逐字核對；沒有 exact-ID view 時，由提交前核對證明完整 prompt payload，正式 create／update 結果核對 task ID、成功狀態、排程時間、時區及目前對話。scope 不明的一般 list 空結果不得推翻 create 成功，也不得盲建重複排程。其後以同一 Scheduled Task 工具執行面獨立探測並完成至少一條端到端可見媒體路徑：可驗證的來源 bytes→解碼／雜湊→本機媒體交付、原生圖片卡，或已實測可用的頁面圖片區域截圖；不需要 repository bootstrap 或台灣底圖。失敗時保留最新版 prompt 並暫停 task。

`INSTALL_CONTROL_PLANE_FAST_PATH`／`EXPLICIT_SCHEDULE_INSTALL_INTENT_GATE`：新建與更新必須先固定為 `create_new` 或 `update_existing`。`create_new` 在 canonical payload 核對後立即執行唯一一次 create，不以同名搜尋為前置；`update_existing` 必須先有 exact task ID。第一次 create 結果不明時不得重送，必須保留實際控制面錯誤並查明該次結果。

`IMMUTABLE_INSTALL_MAIN_RESOLUTION_GATE`：可貼入新對話的安裝入口必須先用兩個 fresh nonce 交叉解析 main，再只從兩端點同意的 immutable 40 字元 SHA 讀取 `INSTALL.md` 與 template。mutable `/main/` 不得作為安裝權威，避免 GitHub raw cache 讓已修正的 create-new 規則被舊版 anti-duplicate 文字覆蓋。

完整本機工作流仍使用下方的安裝方式與 `daily-schedule-prompt.md`；兩種模式互不覆蓋。

完整 capsule 工作流的 canonical runtime 與來源擷取已使用跨平台 Python；full-runtime 不需要 PowerShell。宿主提供的 bundled-runtime Python 會先經 Pillow 實際匯入驗證，通過後才執行 checkpoint 與後續 pipeline；mobile-native 不冒充具備這條本機 runtime 路徑。

目前評分契約為 `public_value_v2`：六項各以 0–100 表示，再按 30%／20%／15%／15%／10%／10% 加權。模型必須先列 fact 並區分 Actual／Potential，程式才接受分數；高分需要反向審查，本期增量 70 以上需要十四天 delta。證據信心與事件重要性分開，只有 `grade_status=validated` 可進 manifest 與讀者版。完整欄位、填寫順序與故障處理以 [INSTALL.md](INSTALL.md) 為準。

## 快速安裝

若執行面可以存取 repository，使用 `scripts/build_scheduled_task_install_payload.py` 產生可驗證的 `saved-prompt.txt`，再把該檔全文作為 Scheduled Task instruction。測試 fixture 只可透過 `scheduled-task-test-extension.example.json` 輸出為獨立 `install-extension.json`，**不得寫入 saved-prompt.txt**。這可避免縮短 launcher 或診斷文字污染 canonical task prompt；無本機執行面時仍依 `INSTALL.md` 的 capability-aware 控制面核對流程完成同一要求。

在新的 ChatGPT 對話貼上以下內容即可。ChatGPT 讀取 `INSTALL.md` 後，必須使用 [scheduled-task-prompt-template.md](scheduled-task-prompt-template.md) 全文建立排程，不得自行濃縮成短指令：

> 每日新聞排程
>
> `IMMUTABLE_INSTALL_MAIN_RESOLUTION_GATE`：先各產生一個 fresh UTC nonce，分別讀取 `https://api.github.com/repos/robert820728-star/global-news-brief/branches/main?cache_bust=<nonce-a>` 與 `https://api.github.com/repos/robert820728-star/global-news-brief/commits/main?cache_bust=<nonce-b>`。兩者必須回傳相同的 40 字元 SHA；若不同，用兩個新 nonce 重試整組一次，仍不同就回報兩個值並停止，不得猜測。之後只從 `https://raw.githubusercontent.com/robert820728-star/global-news-brief/<resolved-main-sha>/INSTALL.md` 讀取安裝契約，並從同一 `<resolved-main-sha>` 讀取 template 與安裝檔；mutable /main 不得作為本次安裝權威。
>
> 本次安裝意圖：create_new。區域：台灣、中國、世界。監控類型：預設。依該 immutable `INSTALL.md` 的 `INSTALL_CONTROL_PLANE_FAST_PATH`，把同一 SHA 的 `scheduled-task-prompt-template.md` 全文只替換允許的兩個 placeholder，驗證後作為唯一一次 create payload。第一次 create 前不得呼叫 list／search／inventory，也不得先讀新聞 runtime 文件；anti-duplicate 只禁止第二次 create。請在目前這個對話建立每天 06:00、使用目前帳號／對話時區、結果回覆目前對話的循環 Scheduled Task。取得 task ID 後，所有 readback、可見圖片 smoke、啟用與 next-run 核對只綁定該 exact ID；第一次 create 結果不明時不得重送，須保存 actual control-plane error 並查明原操作。smoke 通過才啟用，最後回覆 exact task ID、saved-prompt 驗證、時區、enabled、next run 與目前對話 delivery 證據。

安裝時確認兩項內容偏好與 Scheduled Task 自身的時間／時區：

1. 是否自訂監控板塊；可以是單一國家，也可以是區域，例如日本、歐盟、北美、非洲或東南亞。不自訂時使用台灣、中國、世界。
2. 是否調整特別感興趣或降低權重的新聞主題。
3. 單次或循環排程時間／時區由 Scheduled Task 自身決定；使用者指定 04:00、06:00 或其他時間都不需要修改 repository。未指定時才預設每日 06:00 並優先使用帳號／裝置時區。每次實際觸發後先 probe capability，再以該輪選定的 full-runtime 或 mobile-native 建立 occurrence。

完成後，每次排程都會重新讀取 repo 最新規則，並以獨立結果對話輸出當日新聞。完整版每輪會以兩個帶新 nonce 的 GitHub API 端點交叉確認當下 `main` SHA；同一輪固定使用確認後的 SHA，下一輪再重新解析，不會把安裝時或前一輪的 commit 永久釘住：

- 排程及結果對話名稱固定為「每日新聞」。
- 每份讀者版第一行固定為 `# 每日新聞讀者版`，下一個非空白行是 manifest 衍生的統計期間；其後依序使用 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察`。總覽按板塊列事件，逐條詳報保留時間、來源、事件細節與分析欄位。
- 地圖點位直接標示地名；圖說只解釋地點與事件的關係，不以 1、2、3 代碼或重複底圖描述增加閱讀負擔。

詳細步驟請見 [INSTALL.md](INSTALL.md)，可直接交給 Scheduled Task 的完整指令見 [scheduled-task-prompt-template.md](scheduled-task-prompt-template.md)，full-runtime 詳細執行契約見 [daily-schedule-prompt.md](daily-schedule-prompt.md)，個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)。

## 不需要 GitHub 帳號

公開 repo 的規則、技能、模板、地圖與圖片流程可在沒有 GitHub 帳號時直接讀取。full-runtime 使用本機附件流程；無本機 Python 的 ChatGPT Scheduled Task 可使用宿主原生圖片卡或頁面圖片區域直接截圖，但仍必須完成相同的新聞、驗證與逐則可見圖片門檻。

十四天候選回查採漸進式保存：優先使用可持久工作區，其次使用具寫入權限的 repository。若兩者皆不可用，系統仍完成本輪海選、D／E 內部分級、來源複查與讀者版，只是不保證跨日保存十四天歷史。此降級不得影響事件評級、入選、圖片、地圖或最終輸出。

## 模組化架構

工作流固定使用九個 repo 技能，透過同一份事件清單交接；後段技能不能重建事件或刪除前段成果。

| 階段 | 技能 | 唯一負責內容 |
|---|---|---|
| 主控 | `daily-news-brief` | 精確時間窗、模組順序、詳報組裝、最終輸出與驗收 |
| 取得 | `acquire-news-candidates` | 三條 discovery routes、快照、時間邊界與候選清單 |
| 海選 | `select-news-events` | 候選、事件去重、板塊、編號、入選與評級 |
| 稽核 | `audit-news-candidates` | 十四天候選紀錄、排除理由、D／E 內部分級與持續事件比較 |
| 複查 | `verify-news-events` | 多來源、原始／官方回查、主張台帳、差異與不確定性 |
| 地圖 | `build-news-maps` | 自製定位地圖及其驗收 |
| 圖表 | `build-news-charts` | 有助理解的數值比較、趨勢、比例或分布圖表 |
| 圖片 | `collect-news-images` | 官方資訊圖、新聞配圖、下載／截圖與視覺驗收 |
| 恢復 | `recover-news-run` | 失敗偵測、局部重跑、重試上限與重新驗證 |

full-runtime 各 stage 共用 `schemas/news-event-manifest.schema.json`，欄位所有權與最終讀者版由 `scripts/validate_news_brief.py` 檢查，因此新增地圖不會清空圖片，補圖片也不會覆蓋來源或評級。mobile-native 以既有 run-scoped audit、結構等價 Reader 檢查與 ledger 守恆，不宣稱通過 unavailable manifest validator。

## 核心文件

- `.agents/skills/`：九個可獨立維護的工作流技能
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
- `scheduled-task-prompt-template.md`：建立 Scheduled Task 時必須原樣使用的完整外層指令
- `mobile-chatgpt-start-prompt.md`：手機一般 ChatGPT 建立低消耗排程的貼上指令
- `mobile-chatgpt-daily-prompt.md`：手機排程每輪重新讀取的基礎新聞規則

## 本地驗證

只有 full-runtime 取得並驗證 capsule、建立本機 checkpoint 與必要時回退到分段 chunks；mobile-native 固定 fresh main 後直接沿用同一 `scheduled_for` 的 run ledger 與 run-scoped artifacts，不捏造 capsule、workspace 或 checkpoint。full-runtime 的 external diagnostic ledger 失敗只降低診斷能力；可恢復的 durable mobile-native 則必須具備 `run-logs` 寫入權限，不能套用這個降級。 / Only full-runtime fetches and verifies the capsule, creates a local checkpoint, and may degrade its external diagnostic ledger. Durable mobile-native pins fresh main and resumes through the writable `run-logs` ledger and run-scoped artifacts without claiming a capsule, workspace, or local checkpoint.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_news_brief.py manifest --input /path/to/news-event-manifest.json
python3 scripts/validate_news_brief.py brief --manifest /path/to/news-event-manifest.json --input /path/to/news-brief.md
```

上述 brief 命令驗證唯一 canonical 三段式版型；簡化的分區單項新聞版型不再是發布路徑。驗證器只依標準函式庫執行，不需要另裝 Python 套件。

