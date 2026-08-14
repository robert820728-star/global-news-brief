---
name: build-news-charts
description: Build optional self-made data charts for verified news events when numeric comparison, trend, proportion, or distribution materially improves understanding. Use after verification and before source-image collection; charts remain independent from maps and official or media images and can never satisfy source-image requirements.
---

# 新聞自製資料圖表

只修改事件資料的 `charts`。不得修改 `map`、`images`、來源、標題、等級或詳報文字。

## 製作門檻

只有符合下列任一條件才製作：

- 至少兩個同口徑數值需要比較。
- 至少三個時間點構成趨勢。
- 比例、分布或區間用圖表比文字更清楚。
- 數值關係是理解事件的核心，而不是裝飾。

純文字立場、摘要、結論、人物說法或三格重點卡一律不製作。這些內容留在事件細節或各方說法。

## 資料要求

- 每個資料點必須能追溯到已驗證的官方、原始或可靠媒體來源。
- 統一口徑、單位、時間區間與幣別；無法統一時不得硬畫。
- 圖說固定表明「本簡報依○○資料製作」，不得冒充來源發布圖。
- 寫入來源名稱、網址、圖表類型、資料點數、尺寸及數據與視覺驗收結果。

## 與地圖及圖片的關係

- `charts`、`map`、`images` 三者獨立，互不覆寫、互不計數。
- 自製圖表不計入來源圖片 1 至 5 張上限。
- 自製圖表不得取代官方統計圖、媒體照片、來源頁首圖或其他來源圖片。
- B 以上事件即使已有圖表，仍必須完整執行 `collect-news-images` 的來源頁檢查與圖片硬閘門。

## 驗收

- 至少兩個可比較資料點；標題、座標、單位與數值可辨識。
- 圖面不誇大比例，不截斷座標造成誤導。
- 圖說與資料來源一致，且附件可直接顯示。
- 只有文字框、沒有可視化數值關係者判定失敗並刪除。
