---
name: collect-news-images
description: Collect, download or screenshot, prioritize, visually inspect, and attach reliable news images for selected events. Use after verification when a news brief needs official information graphics, maps, charts, route or hazard products, and complementary source photos without losing existing event data.
---

# 新聞圖片取得與驗收

只修改事件資料的 `images`。不得修改事件編號、板塊、標題、等級、驗證內容或自製定位地圖。

## 必讀

依事件類型讀取 `references/image-policy.md`，並使用驗證階段已確認的來源清單。

## 適用門檻

- B 以上事件：只要本則引用來源提供可信且相關圖片，必須嘗試下載或截圖。
- C／C−事件：不強制；圖片能明顯幫助理解政策、產業、統計或事件內容時可以加入。
- 圖片取得失敗不改變事件等級。
- 自製定位地圖由 `build-news-maps` 處理，不得放進 `images`。

## 雙軌選圖

### 資訊圖

優先回答範圍、數字、路徑、風險與時間變化：

- 官方路徑、雨量、警戒、雷達及衛星圖。
- 官方震央、震度、烈度、海嘯警戒圖。
- 疫情統計、曲線、分布與病例圖。
- 戰況、航線、災害影響、財務或政策圖表。

### 新聞配圖

補充現場狀態、人物、設施與事件辨識：

- 災害、戰爭、救援與公共安全現場。
- 關鍵人物、機構、設備、工廠、港口或受影響對象。
- 本則引用媒體的新聞頁首圖或具實質資訊的照片。

官方資訊圖成功不代表刪除新聞配圖；兩者互補時都保留。

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

失敗時依取得順序重試；仍失敗才省略圖片及其圖說。不得只留下「圖一」文字。

## 時間與區域

- 專業資訊圖必須接近新聞更新或事件階段。
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

沒有來源圖片或重試失敗時，保存後台原因但讀者版省略圖片欄。
