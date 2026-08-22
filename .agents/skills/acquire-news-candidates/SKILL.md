---
name: acquire-news-candidates
description: Use when a daily-news run needs a fresh, auditable rolling-window candidate pool before selection or grading, especially when one or more discovery routes may be unavailable.
---

# 取得新聞候選清單

## Discovery first

`DISCOVERY_THEN_VERIFY`

Use `news-source-pool.json.discovery_sources` for the initial list: GDELT plus CNA and China News Service. A failed discovery feed is recorded as degraded and does not block the brief when another feed or the final web-search fallback yields current verifiable candidates. Deduplicate and score before any C-or-higher event is independently verified; collect images only after verification.

+## Same-source recovery order

`SAME_SOURCE_RECOVERY_ORDER`

The required order for every configured source is: `canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot`.

- Run `scripts/recover_same_source_leads.py` for a verified coverage lead; never inject a search result directly into selection.
- `browser is the final fallback only`. It is permitted only after the direct article fetch and all configured same-site non-browser alternatives have failed and those failures were logged.
- A browser DOM snapshot must pass the same same-source host, SHA-256, publication-window, evidence, coverage, and candidate validators as direct evidence.
- Recovery applies to all configured sources. It updates only the affected source scan and coverage record; it must not restart already verified sources.


只負責逐站取得文章清單與原始證據，不評級、不排除、不撰寫簡報。

## 固定輸入

- `news-source-pool.json`
- 精確 `window_start`、`window_end` 與時區
- `.agents/skills/select-news-events/references/source-scan-evidence.md`
- `schemas/news-source-candidate-list.schema.json`

## 路由順序

GDELT 固定先讀官方 15 分鐘 export archives，依精確時間窗下載完整分片並在本地過濾。只有 archive 不可用時才可送出一次 DOC API 補充請求；不得因 429 等待或重試，DOC API 結果必須標示為非完整補充。兩者皆不可用才使用有時效標記的最近有效快取。

每個主要來源依序嘗試：

1. 官方 API、JSON、RSS 或其他結構化直接介面。
2. 普通 HTML 列表、分類頁、站內搜尋或 sitemap。
3. 改用同一網站的另一個合法列表、搜尋、分類、存檔或結構化入口。
4. 只有目前工具契約明確允許時，才可用完整瀏覽器渲染補足動態內容；瀏覽器不得是排程完成的必要依賴。
5. 同一來源的非瀏覽器合法路徑均失敗即交給 `recover-news-run`。若主來源長期不相容，必須在排程外完成同標準替代來源健康檢查並更新來源池；不得在本輪拿別站文章冒充該站掃描完成。

若實際使用瀏覽器，必須保存完整 DOM 快照；若能取得網路回應狀態一併保存。快照視同 HTML 原始證據，必須計算 SHA-256，並讓驗證器能在快照中找到網址、時間與摘要原文。

## 逐站完成條件

- `discovery_sources` 固定為 GDELT、中央社與中新社；GDELT 覆蓋三個板塊，兩個區域來源補台灣與中國盲區。其餘 `sources` 是評分後驗證池，不是前期完成門檻。
- 連續翻頁直到跨過精確24小時起點或來源明確耗盡。
- `GDELT_RESILIENT_ACQUISITION`：DOC API 失敗時總請求數最多 5 次；429 後每次至少等待 120 秒，若 `Retry-After` 更久則依其指定。第 5 次仍失敗不得發第 6 次，立即改讀 GDELT 官方 15 分鐘 export archives，最後才使用明確標記時效的有效快取；不得因單一介面 429 停止發佈。
- `FULL_DISCOVERY_POOL_NO_FIXED_LIMIT`：每個成功來源在精確 24 小時窗內的已驗證條目全部入池，不得設前 30 或其他固定名額。
- specialist supplements 只在相應主題完成評分後用於驗證，不計入 discovery readiness。
- `TAIWAN_DOMESTIC_COVERAGE_GUARD` 以中央社補查三個限定領域，每個領域最多 `5 results`；中央社不可用或明顯過舊時才使用最後的網頁搜尋備援。所有線索都先查重與評分，不得在評級前啟動圖片。

## 每篇最少欄位

- `source_id`、`source_name`、`section`
- `title`、`summary`
- `published_at`、`url`
- `categories`
- `importance_hint`：只寫可能重要的具體原因，不做最終評級
- `acquisition_route`：實際成功的 `structured_direct`、`html_direct`、`same_source_alternate` 或在允許時使用的 `browser_rendered`
- `snapshot_path`、`page_index`

標題或摘要缺失時，必須進入同站文章頁或可用的同站替代入口補齊；只有工具契約允許時才用瀏覽器。不得留下只有首頁網址的候選。

## 產物

逐站證據寫入 `work/source-scans/<source_id>.json`，再執行：

```bash
python3 scripts/build_source_candidate_list.py \
  --source-pool news-source-pool.json \
  --scan-dir work/source-scans \
  --output work/source-candidates.json \
  --window-start <window-start> \
  --window-end <window-end>
```

接著以 `scripts/validate_source_scan_evidence.py` 驗證實際成功的 discovery scans，並用 JSON Schema 驗證候選清單。至少一個 discovery source 或最後搜尋備援取得可核實候選即可交給 `select-news-events`；只有完全沒有可核實候選才停止。
