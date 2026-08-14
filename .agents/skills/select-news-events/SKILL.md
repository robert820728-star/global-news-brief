---
name: select-news-events
description: Discover, cluster, deduplicate, select, section, and grade news events for a rolling daily brief. Use after the time window and user preferences are known, before source verification, maps, images, or reader-facing writing.
---

# 新聞海選與評級

只建立或更新事件資料中的選題欄位，不撰寫最終簡報。

## 輸入

- 精確時間窗與時區。
- 使用者板塊、順序、主題權重、每日上限與最低等級。
- repo 根目錄 `news-brief-settings.md`。
- 候選來源網址與基本中繼資料。

## 流程

### 一、廣泛海選

搜尋各設定板塊及公共政策、經濟、科技、資安、國際關係、災害、公衛、公共安全、科學、自然史、文化與產業。

每個候選只記錄：

- 暫定標題。
- 新聞時間與事件時間。
- 來源網址。
- 地區及影響範圍。
- 主題。
- 一句可能重要的原因。

此階段不要產生詳報、地圖或圖片。

### 二、事件聚類

以底層事件而非標題去重：

- 合併不同語言、不同標題、不同媒體轉載及同一事件更新稿。
- 建立穩定 `dedup_key`。
- 保存候選網址，不把報導篇數當成重要性。
- 跨日事件若只是數字或狀態更新，併入原事件時間線；出現重大新轉折才建立新事件。

### 三、套用偏好

- 依使用者設定提高或降低排序，不得把偏好誤當事實重要性。
- 地區板塊可為國家或區域；同一事件只配置一個主要板塊。
- 世界板塊只收跨國系統性事件或其他板塊未涵蓋的重要事件。
- 不為填滿板塊加入弱事件。

### 四、判斷入選

依公共影響、政策、經濟、科技、安全、災害、公衛、產業與文化制度意義判斷。排除：

- 純聲量、普通八卦、宣傳稿及無公共價值熱搜。
- 未經查證社群爆料或內容農場。
- 與時間窗無關的舊聞，除非時間窗內有新的實質發展。
- 同一事件的重複條目。

來源數量不是入選硬門檻。只有一個看似可靠來源的重大候選仍可入選，交由驗證技能繼續搜尋；不得在此自動降級。

### 五、評級

依 `news-brief-settings.md` 的嚴重度標準評定 `SS` 至 `C-`：

- 評級只看影響範圍、強度、持續性、轉折性與結構意義。
- 不依來源篇數、圖片震撼度、媒體聲量或使用者個人興趣抬高等級。
- 產業型平台、網文、創作者經濟、遊戲或電競制度事件可列 `C`／`C-`；重大監管或商業模式轉折可升至 `B`。
- C 級只代表影響較低，不代表查證或格式可以縮水。

### 六、編號

依板塊順序及重要性排序，配置唯一的三碼加兩位流水號，例如 `TWN-01`。事件進入驗證階段後，不任意重新編號。

## 輸出

只寫入：

- `event_id`
- `primary_section`
- `title`
- `grade`
- `selection.dedup_key`
- `selection.category`
- `selection.impact_scope`
- `selection.reason`
- `selection.candidate_urls`
- `selection.news_time`
- `selection.event_time`

不得寫入或清空 `verification`、`map`、`images` 及讀者版詳報。

