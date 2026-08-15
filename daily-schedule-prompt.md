# 每日新聞固定排程提示詞

本文件是排程執行規格，不是讀者版內容。既有選稿、來源、地圖、圖表、圖片與版面細節以 `news-brief-settings.md`、各技能與 schema 為準；本文件定義不可繞過的執行順序、恢復與交付契約。

## 對話與日期

- 排程名稱固定為「每日新聞」，每次執行使用獨立結果對話；可控制名稱時只能叫「每日新聞」。
- 第一行固定為執行地日期 `YYYY/MM/DD 每日新聞`；下一個非空白行由本輪 manifest 計算新膞總數與各板塊數量。
- 讀者版不得加入完成通知、執行說明、安裝狀態、專案歸屬、驗證日誌或後台限制。

## 唯一交付閘門

`DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py`

- 只有 canonical publisher 可以建立可交付 release；任何模型直接��寫、草稿檔、manifest、技能輸出、驗證器 stdout、舊 release、其他 script 或手動複製內容都不是成品。
- manifest 出現以前必須先建立 `news-run-checkpoint.json`，保存本輪 `run-id`、精確 24 小時時間窗、pre-manifest 階段狀態與 artifact SHA-256。沒有 manifest 不是停止或略過恢復的理由。
- publisher 每次嘗試發布前先刪除同一 output directory 內既有 `news-brief.md` 與 `release-receipt.json`，再重新驗證 checkpoint、候選稽核、來源掃描證據、manifest、視覺附件、讀者版與 repository 唯一閘門不變式；失敗不得留下本輪 receipt。
- receipt 綁定 canonical publisher、交付契約、checkpoint、manifest、candidate audit、source pool、輸入 brief 與 release 的 SHA-256。任何一項變更都使交付失效。
- 最終不得「先驗證再自行讀檔」。必須由 canonical publisher 在同一次呼叫內驗證 receipt 與**目前 checkpoint**，再直接輸出已驗證的 release bytes；stdout 才是唯一可送給使用者的內容。
- `scripts/check_unique_delivery_gate.py` 必須確認 repository 的 scripts 內沒有第二支程式使用保留發布檔名，且本文件只宣告一個 canonical gate 與一個 canonical delivery command。

## 每次執行

1. 重新讀取最新 `main`：`.agents/skills/daily-news-brief/SKILL.md`、`news-brief-settings.md`、`news-brief-template.md`、`user-preferences.example.yaml`、兩份 schema、`news-source-pool.json`、`audit-news-candidates`、`build-news-maps`、`recover-news-run` 技能，以及 `scripts/news_run_checkpoint.py`、`scripts/publish_news_brief.py`、`scripts/check_unique_delivery_gate.py`。格式失敗時才讀 `news-brief-examples.md` 相關段落。
2. 主控技能固定依序使用 `select-news-events` → `audit-news-candidates` → `verify-news-events` → `build-news-maps` → `build-news-charts` → `collect-news-images` → `recover-news-run`。偏好只能覆寫板塊、順序、權重、C-候補主題、語言、時區與執行時間，不得改查證、門檻、欄位所有權、地圖、圖片、恢復或交付規則。
3. 以實際執行時間往前精確 24 小時，建立唯一 `<run-id>`；任何來源掃描之前先執行：

```bash
python3 scripts/news_run_checkpoint.py init --output <checkpoint> --run-id <run-id> --window-start <window-start> --window-end <window-end>
```

   本輪只能沿用這一份 `<checkpoint>`；禁止另建 checkpoint 規避失敗狀態。
4. Manifest 前固定依序完成並更新 checkpoint：
   - `source-scan`：逐一掃描 `news-source-pool.json` 核心來源；每站保存原始快照、SHA-256、連續翻頁鏈與停止證據。只有證明已掃到 `window_start` 或來源明確耗盡才可完成；403、登入牆、逾時或解析失敗不是終點。
   - `preprocess-news-candidates`：執行 `scripts/preprocess_news_candidates.py`；只處理時間窗、網址正規化、完全重複與初步聚類，不得決定入選或評級。
   - `select-news-events`：每站對驗證後時間窗全部條目排序，30 則以上取前 30，不足取全部；排名 30 後命中重大災害、疫情、戰爭、軍事外交、選舉、央行金融、重大資安、關鍵基礎設施、重大科研、文化產業／創作者生態／平台制度轉折或官方警報者強制追加，再跨站／跨語言去重並逐筆評 SS–E。
   - 每筆保存事件特有 `grading_evidence`；非監控板塊一般邊境小衝突、長期戰爭例行同類小衝突／傷亡更新依既有規則固定 D，除非有可驗證的戰局、和平、新戰線或外部系統實質轉折。
   - `audit-news-candidates`：完成本輪 candidate audit；完成時以 `--artifact candidate_audit=<candidate-audit>` 綁定 checkpoint。
   - `materialize-manifest`：只能由已通過 audit 的 selected event ids 建立 manifest；完成時以 `--artifact manifest=<manifest>` 綁定 checkpoint。
   - 每階段都使用 `scripts/news_run_checkpoint.py mark` 將同一 checkpoint 標成 `running`、`completed` 或 `failed`；完成與失敗都不得只留在模型記憶。
5. Manifest 前若程序消失、stage 為 `running`／`failed`／`pending`、或任何階段未完成，執行：

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>
```

   只恢復回報的**最早未完成階段**，成功後更新 checkpoint 並從下一階段續行；不得因 manifest 不存在而終止。
6. Manifest 建立後，先固定事件清單，再由各技能只修改自己欄位。禁止後段模組重建事件、刪除其他模組的 map/charts/images/sources/analysis，禁止篇數、板塊或等級配額。每個 `verify-news-events`、`build-news-maps`、`build-news-charts`、`collect-news-images` 完成／失敗後，同步更新 checkpoint。
7. 既有視覺硬閘門全部保留：每事件明確判定 `map.required`；必要地圖使用完整 canonical 板塊畫布與輸出語言地名；map/charts/images 三類附件獨立且不得互相替代。所有入選事件不分評級逐一檢查每個引用來源頁圖片並保存本地 evidence；找到圖卻沒有合格附件時保持 recovering。氣象、災害、疫情、地震、海嘯、野火、戰爭、軍事、航運、漏油／海洋污染等依事件內容另有官方專業圖資硬閘門，不得用評級或事件編號跳過。
8. Manifest 後每階段及輸出前使用既有恢復器：

```bash
python3 scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

   只重跑失敗事件與原欄位擁有模組；一般取得、渲染、格式、地圖、圖片與驗證錯誤不得無聲結束。硬性權限／環境阻擋才可停止，並保留 checkpoint。
9. 從 manifest 渲染 `<brief>`；不得重新搜尋或重新評級。以 `--artifact brief=<brief>` 將 checkpoint 的 `render` 標成 completed，然後執行 `validate_map_decisions.py` 與 `validate_news_brief.py brief`。任一驗證失敗立即回到局部恢復，不得直接在對話輸出草稿。
10. 只有以下命令可以建立 release：

```bash
python3 scripts/publish_news_brief.py --checkpoint <checkpoint> --manifest <manifest> --audit <candidate-audit> --source-pool news-source-pool.json --brief <brief> --output-dir <release-dir>
```

   publisher 必須同時確認 pre-manifest checkpoint、十站原始掃描證據與時間邊界、前 30 入池與強制例外、SS–E 與理由、14 天候選稽核、selected→manifest 一致性、地圖、圖片、附件與讀者版；成功後才建立 release + receipt。
11. **真正交付只允許執行以下一次命令，並將其 stdout 原樣送出；不得在前後補字、摘要、重寫、重新讀檔或拼接：**

```bash
python3 scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>
```

   命令非 0 結束即視為未交付，回到恢復／發布流程；禁止改拿草稿或舊 release 補交。
12. 未設定偏好時使用台灣 `TWN`、中國 `CHN`、世界 `GLB`，繁體中文，`Asia/Taipei`。若時間窗內沒有事件達標，仍需完成 checkpoint、空事件 manifest、驗證、發布與 receipt 交付，不得用舊聞補數量。

## 兩週候選稽核

- 全部候選保存決定、SS–E、理由與持續事件比較；D/E 只留內部，C 以上不得無聲消失，C-取用需明確需求理由。
- `scripts/manage_candidate_audit.py validate` 未通過時不得發布；不得刪候選規避。
- 十四天歷史跨次保存是增強功能；沒有持久工作區／repo 寫權可降級，但**本輪** candidate audit、來源掃描證據、決定與 selected→manifest 對應不可降級。
- 單一可靠來源不得成為排除或自動降級理由。

## 最終輸出格式

日期行與數量摘要之後只能保留 `今日總覽`、`逐條詳報`、`後續觀察` 三個二級標題；詳細版面依 `news-brief-template.md`。此節只定義 release 內容，不授權任何繞過 `--deliver-receipt` 的交付方式。
