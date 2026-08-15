---
name: daily-news-brief
description: Orchestrate a complete daily news brief from a precise rolling time window with pre-manifest checkpoint recovery, audited selection, independent visual stages, and one fail-closed delivery gate.
---

# 每日新聞主控

本技能負責固定順序與欄位所有權。事件資料是 manifest 建立後的唯一事件交接物；manifest 建立以前則以 `news-run-checkpoint.json` 作為唯一執行 checkpoint。不得直接用一段提示詞從搜尋跳到讀者版。

## 必讀

1. `news-brief-settings.md`、排程保存偏好或 `user-preferences.example.yaml`。
2. `news-source-pool.json` 與 `select-news-events/references/source-scan-evidence.md`。
3. `references/manifest-contract.md`、兩份 schema。
4. `scripts/news_run_checkpoint.py`、`scripts/recover_news_run.py`、`scripts/check_unique_delivery_gate.py`、`scripts/publish_news_brief.py`。
5. 輸出前讀取 `news-brief-template.md`；只有格式驗證失敗才讀 `news-brief-examples.md` 相關段落。

## 固定流程

### 一、先建立 pre-manifest checkpoint

- 以實際執行時間與使用者時區計算精確 24 小時窗口，建立唯一 `run-id`。
- 在任何來源掃描之前執行 `news_run_checkpoint.py init`。
- checkpoint 依序追蹤：`source-scan` → `preprocess-news-candidates` → `select-news-events` → `audit-news-candidates` → `materialize-manifest` → `verify-news-events` → `build-news-maps` → `build-news-charts` → `collect-news-images` → `render`。
- 每階段完成或失敗都更新同一 checkpoint；audit、manifest、brief 分別綁定 `candidate_audit`、`manifest`、`brief` artifact SHA-256。
- manifest 前中斷時，直接用 `news_run_checkpoint.py plan --input <checkpoint>` 從最早未完成階段續行；不得因無 manifest 中止。

### 二、來源掃描與預處理

- 固定十站逐站掃描，保存原始快照、SHA-256、連續翻頁與抵達 `window_start`／來源耗盡證據。
- 403、登入牆、逾時、解析失敗不是掃描終點，必須恢復或切換合法來源介面。
- `preprocess_news_candidates.py` 只做時間窗、URL 正規化、完全重複與初步聚類；不得排除或評級。
- 每站對時間窗全部條目排序，前 30 加重大強制例外後才跨站去重。

### 三、選題與候選稽核

使用 `select-news-events` 與 `audit-news-candidates`：

- 逐候選評為 SS–E；每筆保存事件特有 `grading_evidence`。
- C 以上達標者必須 selected 或合併到同一 selected event；C- 只有需求理由才能取用；D/E 只留內部。
- 邊境小衝突與長期戰爭例行更新按既有 D 級折扣規則處理，不繼承母事件等級。
- 十四天歷史保存是增強功能，但本輪 candidate audit、十站掃描證據、候選決定與理由不是可選項。
- audit 完成後綁定 checkpoint；只有 audit 通過才物化 manifest，並把 selected event ids 精確映射到 manifest。

### 四、逐事件驗證

`verify-news-events` 只能修改 `verification`。搜尋獨立來源、回查官方／原始資料、拆解主張與不確定性；單一可靠來源不自動降級或排除。其他欄位若被改動，撤銷越權變更並重做該事件。

### 五、地圖

`build-news-maps` 只能修改 `map`。每事件明確判斷 required；需要時使用完整板塊 canonical yellow-admin-v2 底圖，不得裁切或局部放大。點位直接標示輸出語言地名並保存 `place_labels`；繁中輸出不得只留英文。專業資訊圖不得塞入 map。

### 六、自製資料圖表

`build-news-charts` 只能修改 `charts`。只有數值比較、趨勢、比例或分布有實質價值時製作；禁止純文字摘要卡或立場卡。圖表不得取代來源圖片或官方專業圖。

### 七、圖片與專業圖資

`collect-news-images` 只能修改 `images`：

- 所有入選事件不分評級逐一檢查每個引用來源頁，保存 `checked_at`、方法、本地 evidence、檢出圖片網址與結果。
- 找到可用圖片就必須取得至少一張對應本地附件並視覺驗收；取得失敗保持 pending/recovering，不得改 `omitted` 結案。
- 氣象、災害、疫情、地震、海嘯、野火、戰爭、軍事、航運、漏油／海洋污染等依事件內容另設官方專業圖資硬閘門，不得用評級或事件編號規避。
- `map.assets`、`charts.assets`、`images.assets` 完全獨立、路徑不得互借。

### 八、自主恢復與完整性檢查

- manifest 建立後，每階段及輸出前執行 `recover_news_run.py plan --checkpoint <checkpoint> --input <manifest> --brief <brief>`。
- 只重跑計畫指定的事件與原欄位擁有模組；已通過工作不得清空。
- 地圖語言／畫布、圖片 evidence、官方專業圖、附件不存在、render/validate 等失敗都必須局部恢復。
- checkpoint required stages 必須全部 completed 且 artifact binding 未變；manifest `stage_status` 與 recovery 也必須通過既有驗證。

### 九、渲染與驗證

- 從 manifest 渲染，不重新搜尋或重新評級。
- 讀者版只含日期行、由 manifest 計算的數量摘要、`今日總覽`、`逐條詳報`、`後續觀察`。
- 已驗收的 map/charts/images 必須出現在對應事件且圖說成對。
- 建立草稿後把 `render` 與 `brief` SHA-256 綁定 checkpoint。
- 執行 `validate_map_decisions.py` 與 `validate_news_brief.py brief`；失敗即回恢復，不得直接輸出草稿。

### 十、唯一發布與交付

只有 `scripts/publish_news_brief.py` 可以建立保留 release 檔。發布必須同時提供 checkpoint、manifest、candidate audit、source pool、brief 與 output directory。publisher 會清除同目錄舊 release、重新跑所有 gate、驗證 repository 沒有第二發布 script，並以 SHA-256 receipt 綁定 canonical gate、交付契約與所有輸入。

**發布成功仍不等於已交付。** 最終 reader bytes 只能由同一支 canonical script 執行 `--deliver-receipt <release-receipt> --checkpoint <current-checkpoint>` 的 stdout 取得；此呼叫會在記憶體中驗證 receipt 與目前 run checkpoint 後直接吐出同一份已驗證 bytes。不得在此呼叫後重新讀 release、不得自行補字、摘要或重寫。

任何其他輸出路徑都視為驗收失敗，即使內容看起來正確。
