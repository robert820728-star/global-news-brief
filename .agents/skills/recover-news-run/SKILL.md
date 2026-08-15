---
name: recover-news-run
description: Detect, isolate, retry, and revalidate failed stages in the daily news workflow without restarting successful work. Use whenever a news run has pending or failed verification, maps, images, rendering, or validation; when an attachment or source operation fails transiently; or before declaring a scheduled run failed or silent.
---

# 每日新聞自主恢復

把失敗視為可定位的工作項目，不把整份簡報視為只能重做的單一任務。

## 核心規則

1. 讀取事件資料、`stage_status`、`recovery` 與驗證器錯誤。
2. 先執行 `scripts/recover_news_run.py plan` 取得待恢復目標。
3. 每次只重跑一個「模組＋事件」；根層渲染與驗證失敗則只重跑該階段。
4. 重跑前保存快照，重跑後執行欄位所有權驗證及完整事件資料驗證。
5. 通過才記錄成功；仍失敗則記錄錯誤類型並依替代路徑重試。
6. 每種恢復策略最多三次；成功即停止該策略並繼續後續階段。單一策略耗盡時切換下一策略，不得結束整輪。
7. 沒有讀者版草稿或沒有可交付檔案時，必須把 `render`、`validate` 或其上游失敗模組加入恢復計畫，修復後繼續到發布成功。
8. 不得清空或重建已通過的事件、來源、地圖、圖片及分析。

## 目標路由

| 失敗位置 | 只重跑 |
|---|---|
| `verification` | `verify-news-events` 的該事件 |
| `map` | `build-news-maps` 的該事件 |
| `images` | `collect-news-images` 的該事件 |
| 讀者版缺欄、順序或附件 | `render` |
| 讀者版草稿或發布檔不存在 | `render`，完成後接續 `validate` 與發布閘門 |
| 資料或版面驗證失敗 | 依錯誤欄位路由；無法定位時重跑 `validate` |

圖片失敗時，每一輪依序採用：原圖下載、重新載入來源頁後下載或截圖、同一事件的另一個可靠來源。每輪都重新開啟並視覺驗收，不沿用失敗頁面狀態。地圖不得替代圖片。

## 狀態紀錄

每次嘗試寫入 `recovery.attempts`：

- `target_stage`
- `event_id`；根層工作使用 `null`
- `attempt`
- `started_at`、`ended_at`
- `outcome`
- `error_code`、`message`

使用：

```bash
python3 scripts/recover_news_run.py plan \
  --input /path/to/news-event-manifest.json \
  --brief /path/to/news-brief.md

python3 scripts/recover_news_run.py record \
  --input /path/to/news-event-manifest.json \
  --output /path/to/news-event-manifest.json \
  --stage collect-news-images \
  --event-id GLB-02 \
  --outcome failed \
  --error-code image-download-timeout \
  --message "來源頁圖片下載逾時"
```

## 結束條件

- 所有目標通過：`recovery.status = completed`，`unresolved_targets` 必須為空，再執行完整 manifest、brief 與發布閘門驗證。
- 單一策略達三次仍失敗：保持 `recovery.status = recovering`，切換下一取得、渲染或驗證策略並繼續；不得因此把 `final_status` 設為 `failed`。
- 所有已知策略均失敗：重新解析最新驗證錯誤並改派原欄位擁有模組；只要仍屬可修復錯誤，就不得中止。
- 只有權限明確拒絕、執行環境禁止建立附件或外部服務持續不可用等硬阻擋，才能設為 `exhausted`／`failed`，並保存 checkpoint 供下次從原階段恢復。
- 沒有失敗目標且可交付檔案已存在：記錄 `completed`，不得為形式重跑任何模組。

只有完整驗證及 `scripts/publish_news_brief.py` 通過，才可把 `recover-news-run`、`validate` 與 `final_status` 分別設為 `completed`、`completed` 與 `ready`。缺少可交付檔案時，即使其他狀態已 completed，也必須重新開啟 `render`／`validate` 恢復目標。


## 候選稽核恢復

| 失敗位置 | 只重跑 |
|---|---|
| 候選缺少決定或理由 | `audit-news-candidates` |
| 暫定 B 以上候選無故消失 | `select-news-events`，再執行 `audit-news-candidates` |
| 十四天裁切或持續事件比較失敗 | `audit-news-candidates` |
| 無 GitHub 寫入權限或無持久工作區 | 不重跑；標記稽核歷史降級並繼續 |

D／E 只修復稽核資料；單一可靠來源不得改寫成排除理由。歷史無法跨次保存不是執行故障，不得觸發整輪重跑或阻止讀者版輸出。
