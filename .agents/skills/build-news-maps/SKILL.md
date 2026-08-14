---
name: build-news-maps
description: Decide whether a selected news event needs geographic context and create a self-made locator map from repository basemaps. Use for events where location, range, spread, route, affected area, sea lane, epicenter region, border, or spatial relationship materially improves understanding.
---

# 新聞定位地圖

只修改事件資料的 `map`。地圖是自製定位輔助，不是官方資訊圖，也不屬於圖片欄。

## 必讀

讀取 `references/map-policy.md`。需要底圖時讀取 repo 的 `maps/README.md`、`maps/source/` 與 `scripts/render_base_maps.py`。

## 判斷是否需要

只有位置或範圍本身有助於理解事件時才使用地圖：

- 疫情擴散至多省、多州或多國。
- 地震、海嘯、火山、野火、洪水、熱浪、乾旱與大範圍天災。
- 運河、海峽、港口、海域、航線、封鎖線、邊境與軍事衝突區。
- 讀者難以直接定位、且位置會改變風險判斷的事件。

僅僅出現地名不代表需要地圖。公司財報、科技產品、數學猜想、獎項、一般政策表態、空間站與純技術事件通常不需要。

## 選擇尺度

- 台灣地方事件：使用台灣縣市界線底圖。
- 中國省域事件：使用中國省份界線底圖。
- 跨國或其他國家事件：使用太平洋置中的世界底圖。
- 自訂國家或區域板塊：以世界底圖為全域範本，建立該國或區域底圖；保留國界或內部行政界線。
- 需要局部圖時，先提供可辨識其所在位置的全域圖。不得只給一張無法辨認國家或區域的裁切形狀。
- 南極事件不得裁掉南極洲；世界底圖保持全域完整。

## 製圖

- 使用淡黃色陸地底色、清楚邊界與高對比高亮色。
- 依來源資料標點、高亮行政區、繪製範圍或簡化路線。
- 不捏造精確邊界；來源只支持點位時只標點，支持行政區時才高亮行政區。
- 圖說使用繁體中文，註明「依來源資料整理／標示」。
- 不把自製定位圖偽裝成官方預測、警戒或統計圖。

## 專業資訊圖分流

下列內容即使長得像地圖，也屬於 `images`：

- 颱風路徑、雨量、雷達、衛星與警戒圖。
- 震央、震度、烈度及海嘯警戒圖。
- 疫情分布、野火範圍、戰況、航線與新聞資訊圖。
- 政府或專業機構發布的任何資料圖。

自製定位地圖不得取代這些圖；事件需要時兩者同時保留。

## 驗收

每張地圖確認：

- 可開啟且不是空白、破圖、錯誤頁或未載入底圖。
- 全圖沒有非預期裁切、拉伸或高緯度嚴重失真。
- 國界、省界或縣市界線符合所需尺度。
- 高亮、標點或範圍與事件來源一致。
- 圖說、標題與公開文字使用繁體中文。
- 地圖檔案沒有被寫入 `images.assets`。

## 輸出

只寫入：

- `map.required`
- `map.status`
- `map.rationale`
- `map.assets[].path`
- `map.assets[].caption`
- `map.assets[].source_urls`
- `map.assets[].visual_checked`
- `map.assets[].width`
- `map.assets[].height`
- `map.omission_reason`

不需要時使用 `status: not_required`；需要但重試失敗時使用 `status: omitted` 並保存後台原因。讀者版不顯示原因。
