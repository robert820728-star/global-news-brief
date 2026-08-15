---
name: collect-news-images
description: Collect, download or screenshot, prioritize, visually inspect, and attach official or media-published news images for selected events. Use after verification regardless of whether self-made maps or charts already exist; source images must remain an independent output and cannot be replaced by generated graphics.
---

# 新聞圖片取得與驗收

只修改事件資料的 `images`。不得修改事件編號、板塊、標題、等級、驗證內容、自製定位地圖或自製資料圖表。

## 必讀

依事件類型讀取 `references/image-policy.md`，並使用驗證階段已確認的來源清單。

## 適用門檻

- 所有入選事件（SS 至 C-）：`images.required` 固定為 `true`，逐一開啟 `verification.sources` 的來源頁檢查圖片；評級不得作為跳過圖片流程的條件。
- 每個引用來源都必須寫入 `images.source_checks`；除是否找到可用圖片、嘗試次數與結果外，必須保存 `checked_at`、`inspection_method`、本地 `evidence_path`、`detected_image_urls` 與 `failure_detail`。
- `evidence_path` 必須是頁面截圖、保存頁面或可重現檢查結果的本地證據；發布器會確認檔案實際存在。宣告 `no_usable_image` 時不得只填布林值，必須有頁面證據與具體理由。
- 偵測到官方或媒體圖片時，必須下載原圖或截取來源頁中的實際圖片，並以相同 `source_url` 寫入 `images.assets`；找到圖片卻沒有對應附件時維持 `pending` 並恢復。
- 任一來源找到可信且相關圖片後，`images.status` 只能在至少一張附件通過驗收後改為 `ready`。
- 已找到可用圖片但下載或截圖失敗時，`images.status` 維持 `pending`，並把圖片階段標成失敗後回到本技能重試；不得改成 `omitted` 後交付。
- 只有全部引用來源都已檢查且均無可用圖片，才可使用 `omitted`，並保存具體後台原因。
- 圖片取得失敗不改變事件等級。
- 自製定位地圖由 `build-news-maps` 處理，不得放進 `images`。
- 自製資料圖表由 `build-news-charts` 處理，不得放進 `images`。
- `map.assets`、`charts.assets`、`images.assets` 三組附件路徑必須兩兩不重複；任何一種視覺完成都不能改變另外兩種的需求、狀態、檢查紀錄或附件。
- `map.status` 或 `charts.status` 已是 `ready`，不代表圖片階段完成；仍須逐一檢查來源頁並取得官方或媒體實際發布的合格圖片。

## 官方專業圖資硬閘門

- 任何入選事件若屬氣象、災害、疫情、公共衛生、地震、海嘯、火山、野火、洪水、乾旱、熱浪、戰爭、軍事、航運、海峽／航道、漏油、油污、海洋污染、化學或核事故，`images.professional_visual_required` 固定為 `true`；此判定必須依事件內容完成，禁止使用評級門檻或事件編號白名單。
- 先依事件類型與主要影響地區，主動搜尋主管機關、監測機構、地方政府或專業組織的圖資；不得只檢查新聞來源頁後就宣告沒有專業圖。
- 每個查過的官方或專業頁面都寫入 `images.professional_source_checks`。至少涵蓋中央主管機關與主要受影響地區主管單位；跨國事件再查國際組織或受影響國官方來源。
- 官方專業圖資檢查同樣必須保存檢查時間、方法、本地頁面證據、檢出的圖片網址與判定理由；取得失敗必須進入恢復流程，不能改寫成 `not_available`。
- 找到與事件時間、地區及主張相符的專業圖時，至少一張 `kind` 為 `official_information` 或 `professional_information` 的本地附件通過視覺與時間驗收前，`images.professional_visual_status` 不得設為 `ready`，整則事件也不得交付。
- 專業圖下載或截圖失敗時，依「原始下載資產 → 官方產品頁截圖 → 官方歷史／存檔頁 → 地方主管機關 → 主要媒體引用的同一官方圖」重試；不得因第一次取得失敗就改用現場照結案。
- 只有完成上述搜尋且確實沒有符合事件階段的專業圖，才可把 `images.professional_visual_status` 設為 `not_available`，並在 `images.professional_omission_reason` 保存具體後台原因。
- 自製定位地圖、自製資料圖表、新聞照片與頁首圖均不能滿足專業圖資硬閘門；反之，專業圖資也不能取代來源頁新聞配圖硬閘門。兩者必須各自完成。

## 雙軌選圖

### 資訊圖

優先回答範圍、數字、路徑、風險與時間變化：

- 官方路徑、雨量、警戒、雷達及衛星圖。
- 官方震央、震度、烈度、海嘯警戒圖。
- 疫情統計、曲線、分布與病例圖。
- 戰況、航線、災害影響、財務或政策圖表。

事件類型有慣用監測產品時，必須優先找對應產品，而不是只找任何一張「看起來專業」的圖：

- 豪雨／淹水：解析雨量、累積雨量、雷達、淹水風險、土砂災害風險或警戒區域圖。
- 颱風：官方路徑、警戒區、雨量、雷達或衛星圖。
- 地震／海嘯：震央、震度／烈度、海嘯警戒或預估影響圖。
- 疫情：官方病例趨勢、地理分布、死亡或醫療負荷圖。
- 野火／熱浪：火場範圍、衛星熱點、疏散區、溫度異常或健康風險圖。
- 航運／軍事：官方航行警告、限制區、航線、設施或經驗證的影響圖。

### 新聞配圖

補充現場狀態、人物、設施與事件辨識：

- 災害、戰爭、救援與公共安全現場。
- 關鍵人物、機構、設備、工廠、港口或受影響對象。
- 本則引用媒體的新聞頁首圖或具實質資訊的照片。

官方資訊圖成功不代表刪除新聞配圖；兩者互補時都保留。

## 禁止以自製內容冒充來源圖片

- 不得自行把新聞文字、各方立場、摘要、結論或三個數字排成卡片後寫入 `images.assets`。
- 不得把「俄羅斯／烏克蘭及盟友」、「安全評估／全面否認」等純文字對照卡當成新聞圖片。
- 自製圖表只限至少兩個可比較的數值、時間序列、比例或分布；必須寫入獨立 `charts` 欄位。
- 自製圖表的圖說須標示「本簡報依○○資料製作」，不得宣稱為該媒體或官方發布的圖片。
- 即使已有合格自製圖表，所有入選事件的來源圖片硬閘門仍照常生效；自製圖表不得計入圖片 1 至 5 張，也不得滿足「至少一張來源圖片附件」要求。

## 數量與順序

每則事件原則上 1 至 5 張：

1. 先放 1 至 4 張互補的官方或專業資訊圖。
2. 再放 1 至 2 張現場照片或新聞配圖。
3. 超過 5 張時刪除重複、低資訊、過時或驗收失敗圖片。
4. 若資訊圖已占滿但有高價值現場照，刪除較弱資訊圖，保留至少一張現場照。

## 取得順序

逐張依序嘗試：

1. 來源頁原始圖片或官方下載資產。
2. 官方產品頁、PDF、圖表或資料頁截圖。
3. 新聞來源頁中的完整圖片。
4. 主要媒體引用的同一官方圖資。
5. 來源頁可見區域截圖。

優先保存為可直接顯示的本地附件。不得只貼短網址、追蹤跳轉網址、裸 CDN 連結或需要讀者另開頁面的圖片。

## 視覺驗收

下載或截圖後必須實際開啟檢查：

- 有實際畫面，不是空白、破圖、登入頁、錯誤頁、搜尋結果殼或未載入框架。
- 主體與圖說、事件及來源一致。
- 日期、發布時間、統計截止與事件階段合理。
- 圖中真正包含宣稱的路徑、震央、雨量、病例、警戒或統計內容。
- 影像沒有誤導性裁切，文字可辨識。
- 不是無關舊照、資料庫示意照或被錯誤歸屬的畫面。

失敗時依取得順序重試。若來源已確認有可用圖片，重試仍失敗也不得省略後交付；維持未完成狀態，讓主控只重跑圖片模組。不得只留下「圖一」文字。

## 與候選來源確認共同發布

圖片驗收與候選來源確認在 `publish_news_brief.py` 同一個 fail-closed 閘門執行。發布時必須同時提供候選稽核檔；任一來源未完成、未按站內前 30 則及強制例外入池、候選缺少 SS–E 評級理由、達標事件漏入 manifest，或圖片附件／來源頁確認失敗，均不得產生 release。圖片技能不修改候選稽核；候選問題仍回到 `select-news-events`／`audit-news-candidates` 修復。

## 時間與區域

- 專業資訊圖必須接近新聞更新或事件階段。
- 專業圖的發布時間、有效時間與統計截止必須逐張檢查；不得以過期預測圖或較早事件圖補位。
- 來源選擇跟隨主要影響地區。例如日本豪雨先查日本氣象廳、地方氣象台與地方防災單位；中國防汛查中國氣象局、中央氣象台與受影響省市單位。
- 颱風仍影響台灣時優先台灣官方圖；已登陸或殘餘環流主要影響其他地區時，改查主要影響地區官方氣象與防災圖。
- 不得用多日前早期預測圖冒充最新災情；殘餘環流事件優先最新雨量、降雨落區、警戒、防汛、雷達、衛星或災害影響圖。
- 地震圖一優先官方震央或震度圖；疫情圖一優先最新官方統計或分布圖；現場照片排後。

## 圖說

每張圖保存：

- 繁體中文內容說明。
- 拍攝、發布或統計截止時間。
- 來源名稱與原始頁網址。
- 必要的資料限制，不寫下載或驗收流程。

## 輸出

只寫入：

- `images.required`
- `images.status`
- `images.source_checks[].source_url`
- `images.source_checks[].checked`
- `images.source_checks[].checked_at`
- `images.source_checks[].inspection_method`
- `images.source_checks[].evidence_path`
- `images.source_checks[].detected_image_urls`
- `images.source_checks[].usable_image_found`
- `images.source_checks[].attempts`
- `images.source_checks[].outcome`
- `images.source_checks[].failure_detail`
- `images.professional_visual_required`
- `images.professional_visual_status`
- `images.professional_source_checks[]`
- `images.professional_omission_reason`
- `images.assets[].path`
- `images.assets[].caption`
- `images.assets[].source_name`
- `images.assets[].source_url`
- `images.assets[].kind`
- `images.assets[].published_at`
- `images.assets[].visual_checked`
- `images.assets[].time_checked`
- `images.assets[].width`
- `images.assets[].height`
- `images.omission_reason`

所有來源確實沒有圖片時，保存後台原因但讀者版省略圖片欄。來源有圖但取得失敗時不得進入讀者版輸出。
