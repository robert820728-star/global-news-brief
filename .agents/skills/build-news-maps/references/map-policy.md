# 定位地圖規則

## 需要地圖

- 伊波拉等疾病由單一地區擴散至多省或多國。
- 地震與海嘯位置、火山所在地及可能影響海域。
- 多州熱浪、野火、洪水、乾旱、寒潮與暴雨範圍。
- 荷姆茲海峽、紅海、巴拿馬運河、港口、航運瓶頸與禁運路線。
- 海域軍事互動、邊境衝突、難民跨境移動與國際救援範圍。
- 讀者不熟悉的城市、島嶼或區域，且位置會影響事件理解。

## 通常不用

- 空間站、衛星任務、純科學或技術突破。
- 人工智慧、晶片、公司產品、單一財報與平台功能。
- 諾貝爾獎、數學猜想、一般論文發表。
- 人物任命、訴訟、文化獎項及娛樂事件。
- 地點只是公司總部、研究機構或記者會所在地。

例外是發射場、墜落區、觀測範圍、廠區災損、供應鏈地理瓶頸或其他位置本身就是新聞核心。

## 底圖

| 尺度 | 首選 |
|---|---|
| 台灣 | `maps/source/taiwan-counties-alt.geojson` |
| 中國 | `maps/source/china-provinces.geojson` |
| 全球／其他國家或區域 | `maps/source/world-countries.geojson` |

使用 `scripts/render_base_maps.py` 產生淡黃色底圖；可用 `maps/generated/taiwan-counties-yellow-v2.png`、`maps/generated/china-provinces-yellow-v2.png` 與 `maps/generated/world-countries-pacific-robinson-yellow-v2.png` 對照核准比例與投影。若檔名更新，以 `maps/README.md` 為準。

## 地圖與圖片

- 地圖欄：自製全域定位、高亮、標點、範圍或簡化路線。
- 圖片欄：所有官方、媒體與專業資訊圖。
- 地圖不計入每則 1 至 5 張圖片。
- 已有官方資訊圖不必然取消定位圖；只有官方圖本身具清楚全域定位時才可省略定位圖。
