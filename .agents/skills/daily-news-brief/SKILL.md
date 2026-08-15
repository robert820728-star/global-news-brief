---
name: daily-news-brief
description: Orchestrate a complete daily news brief from a precise rolling time window. Use when selection, verification, self-made maps, optional data charts, official or media images, formatting, recovery, and final validation must execute in a fixed order without one visual type replacing another.
---

# 每日新聞主控

以事件資料為唯一交接物，不直接用一段提示詞完成搜尋到成稿的全部工作。

## 必讀

1. 讀取 repo 根目錄的 `news-brief-settings.md`。
2. 讀取排程或使用者保存的偏好；沒有時使用 `user-preferences.example.yaml`。
3. 讀取 `references/manifest-contract.md`。
4. 讀取 `schemas/news-event-manifest.schema.json`。
5. 在輸出前讀取 `news-brief-template.md`。
6. 只有驗證失敗或需要判斷正反例時，才讀取 `news-brief-examples.md` 相關段落。

## 固定流程

## 分層執行原則

- 先以 `scripts/preprocess_news_candidates.py` 處理時間窗、網址正規化及初步重複聚類，避免把確定性工作反覆交給模型。
- 小模型是可選加速層，不是必要依賴。沒有 Ollama、本地服務或低成本模型時，流程仍必須使用規則加高階模型完成。
- 小模型只做分類、標籤與合併建議；不得單獨排除候選、決定最終等級、拆解最小主張或完成事實查核。
- 高階模型保留給重大候選複核、語意聚類、評級、主張拆解、多來源矛盾、官方說法定位、分析及最終編纂。
- 每個事件獨立處理與保存階段結果；不得把全部候選與全部來源重複塞入每一次模型請求。
- 任何成本或速率限制最佳化都不得降低海選召回率，也不得讓政治、軍事、外交、金融市場、重大科技、災害、疫情及公共安全事件無聲消失。

### 一、建立執行資料

- 以實際執行時間與使用者時區計算精確 24 小時窗口。
- 建立空白事件資料，記錄版本、語言、時區、窗口起訖、板塊順序與模組狀態。
- 不得先寫讀者版。

### 二、選題

使用 `select-news-events`：

- 海選候選。
- 依底層事件聚類去重。
- 套用使用者偏好及收納門檻。
- 配置板塊、事件編號、標題與等級。
- 保存選題快照，作為後續欄位所有權比較基準。

不得讓後續技能自行新增、刪除、重新編號或改評級。若查證發現實質錯誤，回到此階段由主控明確處理。

### 三、驗證

逐事件使用 `verify-news-events`：

- 搜尋獨立來源。
- 回查官方、原始或最接近原始的資料。
- 拆分關鍵主張並記錄支持、矛盾與不確定性。
- 產生讀者版來源、各方說法與語氣建議。
- 單一可靠來源可以保留，且不得因此自動降級或移除。

驗證技能只能修改 `verification`。完成後比較前後事件資料；若其他欄位變動，撤銷越權變更並重做該事件。

### 四、地圖

對具空間意義的事件使用 `build-news-maps`：

- 判斷是否需要自製定位圖。
- 以合適尺度的全域底圖標點、高亮、範圍或路線。
- 驗收地圖後寫入 `map`。
- 不需要地圖時明確記錄判斷，但讀者版省略地圖欄。

地圖技能只能修改 `map`，且不得把專業資訊圖移入地圖欄。

### 五、自製資料圖表

數值比較、趨勢、比例或分布確實有助理解時使用 `build-news-charts`。純文字摘要或立場卡禁止製作。圖表只寫入 `charts`，不得取代來源圖片。

### 六、圖片

使用 `collect-news-images`：

- B 以上事件若引用來源有圖，必須嘗試取得；C 級依資訊價值決定。
- 優先取得官方或專業資訊圖，再保留互補的新聞現場照或來源配圖。
- 下載或截圖為可直接顯示的本地附件，完成視覺、時間與內容驗收。
- 將合格附件寫入 `images`。

圖片技能只能修改 `images`。不得重建事件物件、刪除地圖或圖表，或變更來源、標題與等級。已有自製圖表不影響來源圖片硬閘門。

### 七、自主恢復

使用 `recover-news-run`：

- 每個階段完成後及最終輸出前，執行 `python3 scripts/recover_news_run.py plan --input /path/to/news-event-manifest.json --brief /path/to/news-brief.md`。
- 驗證失敗、讀者版不存在或發布檔未產生時，不得結束；恢復計畫必須定位到原欄位擁有模組，修復後自動回到渲染、驗證與發布。
- 只重跑恢復計畫指定的事件與失敗模組；已完成的事件、地圖、圖片與驗證資料不得重做或清空。
- 每種恢復策略最多嘗試 `recovery.max_attempts_per_target` 次；同一策略耗盡後切換下一策略，不得把單一路徑失敗當成整輪終止條件。
- 圖片依序切換原圖下載、官方產品頁截圖、官方存檔或地方主管機關、主要媒體引用的同一官方圖、替代可靠來源；不得用地圖、圖廊或文字佔位替代。
- 格式錯誤依序重新依 manifest 渲染、局部修復 Markdown、重建發布檔；每次修復後重新執行完整驗證。
- 只有權限明確拒絕、執行環境禁止建立附件或外部服務持續不可用等不可由本流程排除的硬阻擋，才可留下 `exhausted`／`failed`；一般取得、渲染、格式與驗證錯誤必須保持 `recovering` 並繼續。

恢復技能負責判斷與調度，不得直接修改 `verification`、`map` 或 `images`；實際修復仍由原欄位擁有技能完成。

### 八、完整性檢查

在寫稿前確認：

- 每個事件仍保有選題、驗證、地圖與圖片階段已完成的欄位。
- `map.assets`、`charts.assets` 與 `images.assets` 分開保存。
- 自製圖表不得包含純文字摘要卡，也不得讓圖片階段跳過來源頁檢查。
- 單一可靠來源事件有來源限制文字，但等級未被自動改變。
- 所有附件都有路徑、圖說、來源、驗收狀態；地圖不計入圖片數量。
- B 以上事件必須完成所有引用來源頁的圖片檢查。任何來源已找到可用圖片時，至少一張合格附件必須存在；否則不得把最終狀態設為 `ready`。
- 圖片模組若因工具或下載錯誤中斷，保持未完成並只重跑圖片模組；不得以地圖成功、文字完成或省略圖片作為替代。
- 任一模組失敗時，只重試該模組或該事件，不得從頭生成全部事件。
- `recovery.status` 必須為 `completed`，且不得有未解決目標，才能進入讀者版輸出。

環境可執行程式時，先執行：

```bash
python3 scripts/validate_news_brief.py manifest --input /path/to/news-event-manifest.json
```

### 九、輸出讀者版

- 從事件資料渲染，不重新搜尋或重新判斷。
- 套用 `news-brief-template.md`。
- 事件資料內所有已驗收的地圖、資料圖表與圖片都必須出現在對應詳報。
- 圖片與圖說成對；不得留下文字佔位。
- 只輸出日期行與今日總覽、逐條詳報、後續觀察三個二級標題。

### 十、最終驗證

執行：

```bash
python3 scripts/validate_news_brief.py brief \
  --manifest /path/to/news-event-manifest.json \
  --input /path/to/news-brief.md
```

若失敗，交由 `recover-news-run` 建立局部恢復計畫，只修正驗證訊息指出的欄位；修復後必須重新渲染並重新驗證，不得中止。驗證通過後仍須執行 `scripts/publish_news_brief.py`，只有發布器產生的 `release/news-brief.md` 可以送出。

## 失敗處理

- 搜尋不足：回到驗證技能補查，不影響原評級。
- 地圖失敗：重試地圖技能；不能拿官方資訊圖冒充定位圖。
- 圖片失敗：重試原圖下載、來源頁截圖或替代來源圖；已確認來源有圖時，附件通過驗收前禁止輸出整份簡報。
- 格式失敗：修正模板渲染；不能重新生成新聞內容。
- 來源互相矛盾：保留差異並調整確定語氣；只有事件核心被證偽時，才回到選題階段重新處理。
- 執行中斷或工具暫時故障：由 `recover-news-run` 偵測未完成狀態並局部重跑；不得等待人工發現才恢復。

## 候選稽核階段

選題後、驗證前使用 `audit-news-candidates`：保存全部候選的十四天紀錄，比較持續事件，並檢查暫定 B 以上未入選候選都有理由。D／E 只供內部追蹤。稽核內容或理由驗證失敗時，只重跑 `select-news-events` 與 `audit-news-candidates`，不得清空其他模組。無法跨次保存歷史不屬於稽核失敗；改用目前可讀歷史或本輪資料並繼續後續流程。
