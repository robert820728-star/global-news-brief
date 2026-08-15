---
name: build-news-maps
description: Decide whether a selected news event needs geographic context and create a self-made locator map from repository basemaps. Use for events where location, range, spread, route, affected area, sea lane, epicenter region, border, habitat, migration corridor, protected area, or spatial relationship materially improves understanding.
---

# 新聞定位地圖

只修改事件資料的 `map`。地圖是自製定位輔助，不是官方資訊圖，也不屬於圖片欄。

## 必讀

讀取 `references/map-policy.md` 與 `maps/style.json`。需要底圖時讀取 repo 的 `maps/README.md`、`maps/source/` 與 `scripts/render_base_maps.py`。台灣、中國、世界三張 `yellow-v2` 成品是唯一核准風格基準，不得自行選擇其他底色或地圖樣式。

## 逐事件強制判定

每一個已入選事件都必須進入本技能並產生明確的 map decision；不得因為事件主要分類是統計、保育、政策、產業、科技或其他非地理分類而跳過。

每則事件完成後，`map` 必須且只能落在下列兩類之一：

1. `required: true`，並進一步完成地圖或依恢復規則記錄失敗；
2. `required: false`、`status: not_required`，且 `rationale` 必須具體說明為什麼地理位置、範圍、路線或空間關係不影響讀者理解。

禁止留下未判定狀態後直接進入讀者版；也禁止只因為「已有地名」、「事件屬統計新聞」或「正文可用文字說清楚」就自動判定不需要地圖。

## 判斷是否需要

只要位置、範圍、路線、棲地或空間關係本身有助於理解事件，就使用地圖。下列為強地理訊號，原則上應判定 `required: true`；若例外判定不需要，`rationale` 必須逐項解釋原因：

- 疫情擴散至多省、多州或多國。
- 地震、海嘯、火山、野火、洪水、熱浪、乾旱與大範圍天災。
- 運河、海峽、港口、海域、航線、封鎖線、邊境與軍事衝突區。
- 海洋保育區、珊瑚礁、漁場、海洋污染範圍、海洋熱浪、保護區、棲地與物種遷徙廊道。
- 陸域保護區、森林、流域、濕地、野生動物棲地、遷徙路線或人獸衝突熱區。
- 讀者難以直接定位、且位置會改變風險判斷的城市、島嶼、海域或區域。
- 事件涉及兩個以上地點之間的移動、擴散、依存或空間比較，例如航線、跨境移動、供應鏈瓶頸、遷徙帶。

僅僅出現地名不代表需要地圖。公司財報、科技產品、數學猜想、獎項、一般政策表態、空間站與純技術事件通常不需要；但只要其核心影響與特定地理範圍、路線、保護區或空間關係有關，仍必須回到上述強地理訊號判斷。

### 防漏判檢查

在寫入 `map.required = false` 前，必須對事件標題、`selection.category`、`selection.impact_scope`、`selection.reason`、已驗證主張與詳報內容做一次空間線索掃描。若出現下列概念之一，不得直接 `not_required`：

- 海域、沿岸、海峽、港口、島嶼、礁區、保護區、國家公園、流域、森林、棲地；
- 遷徙、擴散、蔓延、路線、航線、跨境、跨州、跨省、多地、多國；
- 震央、火場、洪水範圍、警戒區、污染範圍、事故位置、救援區域；
- 物種分布、繁殖地、覓食區、遷徙帶、人獸衝突熱點。

只要命中且位置有助理解，就必須 `required: true`。例如「大堡礁鯨豚互動增加」即使主要呈現的是通報統計，事件仍涉及明確海洋保護區與座頭鯨遷徙帶，應建立區域定位圖，而不是因為它是統計／保育新聞而省略。

## 選擇尺度

- 台灣地方事件：使用台灣縣市界線底圖。
- 中國省域事件：使用中國省份界線底圖。
- 跨國或其他國家事件：使用太平洋置中的世界底圖。
- 自訂國家或區域板塊：必須先使用 `maps/generated/sections/<CODE>-base.png` 的淡黃色行政界線底圖；以世界地理資料建立該國或區域範圍，保留國界及資料可用的內部行政界線。底圖尚未生成或未通過視覺驗收時，重跑 `initialize_section_basemaps.py` 與 `render_base_maps.py`，不得改用圖片搜尋、空白底圖或一般新聞圖片。
- 需要局部圖時，先提供可辨識其所在位置的全域圖。不得只給一張無法辨認國家或區域的裁切形狀。
- 南極事件不得裁掉南極洲；世界底圖保持全域完整。

## 製圖

- 固定使用 `maps/style.json` 的 `yellow-admin-v2`：淡黃色陸地 `#f3e6b8`、灰色行政界線 `#53606f`、白色背景 `#ffffff`、紅色主要事件區、橙色次要影響區及深紅點位。禁止藍底、深色底、衛星底圖或任何未核准配色。
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
- `map.assets[].style_id` 必須是 `yellow-admin-v2`，`style_reference` 必須是 `maps/style.json`；任一顏色或行政界線風格不符即驗收失敗並重跑 canonical renderer。

另外，每一個已入選事件都必須完成 map decision coverage 檢查：事件數量必須等於已完成 `map.required` 判定的事件數量。任何事件缺少決定、仍為未判定，或命中強地理訊號卻沒有具體不需要理由，都視為本階段失敗，交由 `recover-news-run` 只重跑該事件的 `build-news-maps`。

## 輸出

只寫入：

- `map.required`
- `map.status`
- `map.rationale`
- `map.assets[].path`
- `map.assets[].caption`
- `map.assets[].style_id`
- `map.assets[].style_reference`
- `map.assets[].generator`
- `map.assets[].source_urls`
- `map.assets[].visual_checked`
- `map.assets[].width`
- `map.assets[].height`
- `map.omission_reason`

不需要時使用 `status: not_required`；需要但重試失敗時使用 `status: omitted` 並保存後台原因。讀者版不顯示原因。
