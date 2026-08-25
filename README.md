# global-news-brief

可版本化、可分享、可個人化，而且能逐階段驗收的每日新聞簡報工作流。

## 手機 ChatGPT 基礎排程

若要在一般手機 ChatGPT 對話執行，不使用手機 Codex，請先選擇 `Instant` 並貼上 [mobile-chatgpt-start-prompt.md](mobile-chatgpt-start-prompt.md)。此低消耗版本不執行本機程式、地圖或圖表，但仍保存當輪海選、每筆六項大評分、當輪所有 C 級以上新聞的讀者版，以及可用時的十四天 continuity cache。十四天 merge 延後不會阻擋當日讀者版。圖片維持原本選圖，優先使用同圖的 640px 小尺寸版本；無法縮小時允許使用同一張原圖，原圖也無法可靠內嵌時直接提供圖片說明，不用圖片網址或原網站連結代替圖片。執行進度與最新讀者版會保存在 `run-logs` 分支；05:58 的輕量守望工作只初始化紀錄，不搜尋新聞，也不使用模型額度。

完整本機工作流仍使用下方的安裝方式與 `daily-schedule-prompt.md`；兩種模式互不覆蓋。

完整 capsule 工作流的 canonical runtime 與來源擷取已使用跨平台 Python；手機／Linux 排程不需要 PowerShell。宿主提供的 bundled-runtime Python 會先經 Pillow 實際匯入驗證，通過後才執行 checkpoint 與後續 pipeline。

## 快速安裝

在新的 ChatGPT 對話貼上本 repo 網址，並輸入：

> 請讀取此 GitHub repo 的 INSTALL.md，協助我設定個人偏好與每日新聞排程。任何建立或修改排程的動作都先取得我的確認。

安裝時只需確認三件事：

1. 是否自訂監控板塊；可以是單一國家，也可以是區域，例如日本、歐盟、北美、非洲或東南亞。不自訂時使用台灣、中國、世界。
2. 是否調整特別感興趣或降低權重的新聞主題。
3. 每日幾點執行。

輸出語言優先沿用使用者已設定的語言；沒有設定時沿用安裝對話的主要語言。時區優先使用帳號、裝置或目前工作區時區，只有無法判斷時才詢問。

完成後，每次排程都會重新讀取 repo 最新規則，並以獨立結果對話輸出當日新聞。完整版每輪會以兩個帶新 nonce 的 GitHub API 端點交叉確認當下 `main` SHA；同一輪固定使用確認後的 SHA，下一輪再重新解析，不會把安裝時或前一輪的 commit 永久釘住：

- 排程及結果對話名稱固定為「每日新聞」。
- 每份讀者版第一行固定為 `# 每日新聞讀者版`，下一個非空白行是 manifest 衍生的統計期間；總數與各板塊事件完整列在唯一的 `## 今日總覽`。
- 地圖點位直接標示地名；圖說只解釋地點與事件的關係，不以 1、2、3 代碼或重複底圖描述增加閱讀負擔。

詳細步驟請見 [INSTALL.md](INSTALL.md)，個人設定格式請見 [user-preferences.example.yaml](user-preferences.example.yaml)，排程執行提示詞請見 [daily-schedule-prompt.md](daily-schedule-prompt.md)。

## 不需要 GitHub 帳號

公開 repo 的規則、技能、模板、地圖與圖片流程都可直接讀取；沒有 GitHub 帳號或寫入權限仍可產生完整每日新聞。

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

所有技能共用 `schemas/news-event-manifest.schema.json`。欄位所有權與最終讀者版由 `scripts/validate_news_brief.py` 檢查，因此新增地圖不會清空圖片，補圖片也不會覆蓋來源或評級。

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
- `mobile-chatgpt-start-prompt.md`：手機一般 ChatGPT 建立低消耗排程的貼上指令
- `mobile-chatgpt-daily-prompt.md`：手機排程每輪重新讀取的基礎新聞規則

## 本地驗證

手機排程在 news checkpoint 之前，優先一次取得固定 main SHA 的完整 capsule payload 並驗證；只有宿主封鎖此請求時才回退到分段 chunks。它同時使用原子 `bootstrap-progress.json`，並在具備留言權限時將節流後的進度寫到 [Daily News Run Ledger](https://github.com/robert820728-star/global-news-brief/issues/3)。台帳失敗只降低診斷能力，不會阻擋每日新聞。 / Before the news checkpoint, mobile runs first fetch and verify one payload pinned to the resolved main SHA, falling back to segmented chunks only when the host blocks that request. They keep atomic bootstrap progress and optionally publish debounced milestones to the persistent run ledger; ledger failure never blocks delivery.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_news_brief.py manifest --input /path/to/news-event-manifest.json
python3 scripts/validate_news_brief.py brief --manifest /path/to/news-event-manifest.json --input /path/to/news-brief.md
```

上述 brief 命令預設驗證唯一 canonical 分區版型；舊欄位式三大區塊版型不再是發布路徑。驗證器只依標準函式庫執行，不需要另裝 Python 套件。
