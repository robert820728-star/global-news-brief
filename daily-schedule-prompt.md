# 每日新聞排程執行契約

本文件是排程執行時的主控契約。所有新聞內容、選稿、驗證、地圖、圖表、圖片、恢復與發布規則，以 repository 內最新版設定、skills、schemas 與 scripts 為準；不得由模型自行另造平行流程。

## 固定輸出設定

- 區域：`TWN`、`CHN`、`GLB`。
- 語言：繁體中文。
- 時區語意：`Asia/Taipei`。
- 新聞時間窗：以本輪**實際執行時間**為 `window_end`，精確向前 24 小時為 `window_start`。不得用「今天 00:00 起」或排程原定時間替代。
- 不設定任意篇數上限；依 `news-brief-settings.md` 的評級、門檻與 continuity 規則決定事件數量。
- 讀者版標題固定為「每日新聞」；若宿主可控制對話標題則使用此名稱。

## Stage -1：先取得可執行 workspace

任何 `scripts/*.py` 執行前，先完整遵守 `bootstrap-workspace.md`。

GitHub connector 可見 repository 不代表 shell 已有 repository。必須使用最新版 `main` 的 verified runtime capsule：

1. connector 解析最新 `main` commit 與 recursive tree；
2. 取得同一 commit 的 `bootstrap/capsule-manifest.json`、`bootstrap/bootstrap_loader.py` 與 manifest 指定 chunks；
3. 依 `bootstrap-workspace.md` 驗證 capsule freshness、runtime Git blob SHA、loader SHA 與 chunks；
4. 將 manifest／loader／chunks 精確寫入 writable staging directory；
5. 由 loader 在 shell 本地解碼、驗 SHA、解壓並建立 executable workspace；
6. loader 成功產生 `bootstrap-workspace.json` 後，才可建立 news checkpoint。

禁止 Stage -1 使用 shell `git clone`、`curl`、`wget`、raw GitHub HTTP，禁止逐 blob 搬完整 repository，也禁止 workspace 失敗後人工直接寫新聞。

若 Stage -1 無法完成，最早 blocker 固定回報為：

`repository materialization / executable workspace acquisition`

此時不得產生 checkpoint、manifest、release receipt 或假讀者版。

## 必讀 runtime 契約

Stage -1 完成後，至少讀取並遵守：

- `.agents/skills/daily-news-brief/SKILL.md`
- `news-brief-settings.md`
- `news-brief-template.md`
- `user-preferences.example.yaml` 或本輪明確偏好
- `news-source-pool.json`
- `schemas/news-event-manifest.schema.json`
- `schemas/news-candidate-audit.schema.json`
- `scripts/news_run_checkpoint.py`
- `scripts/preprocess_news_candidates.py`
- `scripts/manage_candidate_audit.py`
- `scripts/recover_news_run.py`
- `scripts/validate_map_decisions.py`
- `scripts/validate_news_brief.py`
- `scripts/check_unique_delivery_gate.py`
- `scripts/publish_news_brief.py`
- select / audit / verify / maps / charts / images / recovery skills 與其 references。

只有格式或示例需求時才讀 `news-brief-examples.md`，不得用 examples 取代正式 schema/settings。

## 本輪唯一 checkpoint

以實際執行時間計算精確 24 小時窗後，建立唯一 `<run-id>`，並初始化唯一 checkpoint：

```bash
python3 scripts/news_run_checkpoint.py init \
  --output <checkpoint> \
  --run-id <run-id> \
  --window-start <window-start> \
  --window-end <window-end> \
  --bootstrap-receipt <workspace>/bootstrap-workspace.json
```

所有 pre-manifest 狀態都必須沿用同一份 checkpoint；不得失敗後另開 checkpoint 來抹掉前一輪證據。

## 固定 pipeline

依序執行，不得跳關：

1. `source-scan`
   - 必須先調用 `acquire-news-candidates`，依 `news-source-pool.json` 掃描每板塊5站、合計15個主要來源並產生 `work/source-candidates.json`。
   - 直接 API／RSS／HTML 失敗時立即切換完整瀏覽器渲染並保存 DOM；瀏覽器仍失敗才改同站替代入口，不得直接停止整輪或用別站補足。
2. `preprocess-news-candidates`
3. `select-news-events`
4. `audit-news-candidates`
5. `materialize-manifest`
6. `verify-news-events`
7. `build-news-maps`
8. `build-news-charts`
9. `collect-news-images`
10. `render`
11. validators / unique delivery gate
12. canonical publisher release
13. canonical receipt delivery

來源掃描必須保存站點、快照／證據、SHA-256、時間邊界、翻頁與停止理由。403、登入牆、timeout、解析失敗或單一來源異常不得假裝成功，也不得因此直接整輪放棄；按 skills/settings 做局部恢復與替代來源處理。

Manifest 建立以前，候選與選稿必須有 candidate audit；manifest 建立後，事件內容只能由 manifest 驅動，不得直接從搜尋結果或模型記憶補事件。

每個已選事件都必須經 verify、map decision、chart decision、image decision。地圖、圖表與圖片互相獨立，不能互相替代。capsule 不搬運可重建的 generated basemap PNG/SVG；需要時由 workspace 內 canonical map source/style 與 renderer 重建。

## 恢復

Manifest 前發生中斷或 stage failure：

```bash
python3 scripts/news_run_checkpoint.py plan --input <checkpoint>
```

只從最早未完成 pre-manifest stage 繼續，不清除已完成且 artifact binding 仍有效的 stage。

Manifest 後發生事件級失敗：

```bash
python3 scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

只重跑失敗事件／stage 與必要後續依賴。不得對 `recover_news_run.py` 虛構不存在的 `--checkpoint` 參數。

一般來源、圖片、地圖、圖表、格式與 validator failure 都應先局部恢復；只有無法排除的硬性 execution blocker 才可停止整輪。

## 唯一發布閘門

DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py

Repository 內只有 canonical publisher 可以建立 reader-facing release。其他 script、模型回答、草稿、舊 release、manifest 或中間 renderer stdout 都不是正式交付。

發布前必須：

- 所有 checkpoint required stages = completed；
- candidate audit 與 source-scan 證據有效；
- manifest/schema 有效；
- map decisions、reader brief 與附件 validators 通過；
- unique delivery gate 通過；
- publisher 建立 `release-receipt.json`；
- 交付當下 publisher 再次 revalidate bootstrap binding、checkpoint、manifest、audit、source pool、brief、attachments 與 map decisions。

最後正式輸出只能由以下命令的 stdout 直接交付，不得在 stdout 前後自行添加文字，也不得重新讀取 release 後轉貼：

```bash
python3 scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>
```

若此命令失敗或 stdout 為空，回到對應 recovery stage；不得改用手工摘要或舊 release 冒充成功。

## 成功與失敗的判定

只有 canonical delivery command 成功輸出 reader bytes，才算本輪每日新聞成功。

下列都不算成功：

- 只完成搜尋或整理；
- 只建立 manifest；
- 只完成 render；
- 只建立 release receipt；
- pipeline 未跑但模型直接寫出看似完整的新聞簡報。

若停止，必須回報**最早不可恢復 blocker**及已完成到哪個 stage，不得把後續未執行階段誤報成故障來源。
