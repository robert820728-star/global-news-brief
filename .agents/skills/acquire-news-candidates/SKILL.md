---
name: acquire-news-candidates
description: Acquire complete rolling-window article lists from the configured daily-news sources, switch from direct retrieval to a rendered browser when direct routes fail, and materialize auditable source candidate lists before news selection, grading, deduplication, or verification.
---

# 取得新聞候選清單

只負責逐站取得文章清單與原始證據，不評級、不排除、不撰寫簡報。

## 固定輸入

- `news-source-pool.json`
- 精確 `window_start`、`window_end` 與時區
- `.agents/skills/select-news-events/references/source-scan-evidence.md`
- `schemas/news-source-candidate-list.schema.json`

## 路由順序

每個主要來源依序嘗試：

1. 官方 API、JSON、RSS 或其他結構化直接介面。
2. 普通 HTML 列表、分類頁、站內搜尋或 sitemap。
3. 直接方式遇到 robots、403、不支援 MIME、動態內容未載入、逾時或解析失敗，立即改用完整瀏覽器渲染；不得把第一種工具失敗寫成來源不可讀。
4. 瀏覽器仍失敗時，改用同一網站的另一個合法列表、搜尋、分類或存檔入口。
5. 同一來源所有合法路徑均失敗才交給 `recover-news-run`。不得拿別站文章冒充該站掃描完成。

瀏覽器必須保存完整 DOM 快照；若能取得網路回應狀態一併保存。快照視同 HTML 原始證據，必須計算 SHA-256，並讓驗證器能在快照中找到網址、時間與摘要原文。

## 逐站完成條件

- `section_sources` 每個板塊恰有5個主要來源；預設 TWN、CHN、GLB 合計15站，全部獨立掃描。
- 連續翻頁直到跨過精確24小時起點或來源明確耗盡。
- 每站先保存時間窗內完整文章，再按公共價值取前30；強制例外可突破30。
- specialist supplements 只在相應主題出現時補漏，不計入15站完成數，也不能代替失敗的主要來源。

## 每篇最少欄位

- `source_id`、`source_name`、`section`
- `title`、`summary`
- `published_at`、`url`
- `categories`
- `importance_hint`：只寫可能重要的具體原因，不做最終評級
- `acquisition_route`：實際成功的 `structured_direct`、`html_direct`、`browser_rendered` 或 `same_source_alternate`
- `snapshot_path`、`page_index`

標題或摘要缺失時，必須進入同站文章頁或瀏覽器補齊；不得留下只有首頁網址的候選。

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

接著執行 `scripts/validate_source_scan_evidence.py` 驗證每站證據，並用 JSON Schema 驗證候選清單。只有15站全部通過才交給 `select-news-events`；中斷則定位到單一來源與路由後局部恢復。
