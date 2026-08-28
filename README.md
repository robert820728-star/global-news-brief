# global-news-brief

可版本化、可分享、可個人化，而且能逐階段驗收的每日新聞簡報工作流。

## 手機 ChatGPT 基礎排程

`INSTALL.md` 是唯一安裝入口。一般手機 ChatGPT／Scheduled Task 也先從 `INSTALL.md` 開始，由它在每次實際觸發時依 capability routing 選擇 `mobile-native` 或 `full-runtime`，再讀取對應權責文件；不得把 `mobile-chatgpt-daily-prompt.md`、圖片規則或其他執行細節複製成第二份 Scheduled Task prompt。`mobile-chatgpt-start-prompt.md` 只保留給舊書籤作相容導引。

mobile-native 仍必須完成 discovery、語意事件、Public Value V2 評分、驗證、逐則圖片 evidence 與 canonical reader；正式保存 Reader 前另以 `MANDATORY_GATE_EXECUTION_ASSERTION` 保存 run-scoped release coverage receipt。來源確實沒有合格圖片時才可依權責規則省略；已確認合格圖片但交付失敗時仍停在同一 run 的視覺恢復。執行進度與成功結果只回覆到建立該排程的原 ChatGPT 對話，不另開結果對話。

## 快速安裝

在新的 ChatGPT 對話貼上本 repo 網址，並輸入：

> 請讀取此 GitHub repo 的 INSTALL.md，協助我設定個人偏好與每日新聞排程。任何建立或修改排程的動作都先取得我的確認。

安裝時確認兩項內容偏好與 Scheduled Task 自身的時間／時區：

1. 是否自訂監控板塊；可以是單一國家，也可以是區域，例如日本、歐盟、北美、非洲或東南亞。不自訂時使用台灣、中國、世界。
2. 是否調整特別感興趣或降低權重的新聞主題。
3. 單次或循環排程時間／時區由 Scheduled Task 自身決定；使用者指定 04:00、06:00 或其他時間都不需要修改 repository。未指定時才預設每日 06:00 並優先使用帳號／裝置時區。每次實際觸發後先 probe capability，再以該輪選定的 full-runtime 或 mobile-native 建立 occurrence。

完成後，每次排程都會重新讀取 repo 最新規則，並把當輪進度、成功結果或最早不可恢復 blocker 回覆到建立該排程的原對話。完整版每輪會以兩個帶新 nonce 的 GitHub API 端點交叉確認當下 `main` SHA；同一輪固定使用確認後的 SHA，下一輪再重新解析，不會把安裝時或前一輪的 commit 永久釘住：

- 排程及結果對話名稱固定為「每日新聞」。
- 每份讀者版第一行固定為 `# 每日新聞讀者版`，下一個非空白行是 manifest 衍生的統計期間；其後依序使用 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察`。總覽按板塊列事件，逐條詳報保留時間、來源、事件細節與分析欄位。
- 地圖點位直接標示地名；圖說只解釋地點與事件的關係，不以 1、2、3 代碼或重複底圖描述增加閱讀負擔。

詳細步驟請見 [INSTALL.md](INSTALL.md)，個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)，排程執行提示詞請見 [daily-schedule-prompt.md](daily-schedule-prompt.md)。

## 不需要 GitHub 帳號

公開 repo 的規則、技能、模板、地圖與圖片流程可在沒有 GitHub 帳號時直接讀取；但可恢復的 durable mobile-native Scheduled Task 必須使用具此 repository `run-logs` 寫入權限的 GitHub app。沒有寫入權限時最多只能在當前執行做一次性 reader，不得宣稱具備跨執行 resume、durable run identity 或 continuity。

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
- `mobile-chatgpt-start-prompt.md`：舊手機入口的相容導引；重新導向唯一安裝入口 `INSTALL.md`
- `mobile-chatgpt-daily-prompt.md`：由 `INSTALL.md` 導向的 mobile-native 詳細每日執行契約

## 本地驗證

只有 full-runtime 取得並驗證 capsule、建立本機 checkpoint 與必要時回退到分段 chunks；mobile-native 固定 fresh main 後直接沿用同一 `scheduled_for` 的 run ledger 與 run-scoped artifacts，不捏造 capsule、workspace 或 checkpoint。full-runtime 的 external diagnostic ledger 失敗只降低診斷能力；可恢復的 durable mobile-native 則必須具備 `run-logs` 寫入權限，不能套用這個降級。 / Only full-runtime fetches and verifies the capsule, creates a local checkpoint, and may degrade its external diagnostic ledger. Durable mobile-native pins fresh main and resumes through the writable `run-logs` ledger and run-scoped artifacts without claiming a capsule, workspace, or local checkpoint.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_news_brief.py manifest --input /path/to/news-event-manifest.json
python3 scripts/validate_news_brief.py brief --manifest /path/to/news-event-manifest.json --input /path/to/news-brief.md
```

上述 brief 命令驗證唯一 canonical 三段式版型；簡化的分區單項新聞版型不再是發布路徑。驗證器只依標準函式庫執行，不需要另裝 Python 套件。
