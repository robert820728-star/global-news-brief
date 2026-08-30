---
name: verify-news-events
description: Verify selected news events through claim decomposition, independent-source searching, authoritative or original-source checks, evidence comparison, and uncertainty reporting. Use after events are selected and graded, before maps, images, analysis writing, or final publication.
---

# 新聞事件複查

對每個已入選事件進行查證。只修改 `verification`，不得改變事件編號、板塊、標題、等級、地圖或圖片。

## 必讀

依事件類型讀取 `references/source-routing.md`。來源選擇以角色、證據源頭與事件類型為準，不按網站數量湊數。

## 核心原則

- 所有入選事件（C 以上）都主動尋找多個獨立可靠來源。
- B 以上提高搜尋深度，原則上涵蓋官方／原始資料與至少一個獨立媒體或第三方角色。
- 多來源是查證目標，不是評級或入選硬門檻。
- 搜尋後只有一個可靠來源時，保留事件及原評級，標記 `single_reliable_source`。
- 中立是依證據品質加權，不是讓每一方得到相同篇幅，也不是把事實與無證據說法各打五十大板。

## 流程

### 一、拆分主張

將事件拆成可驗證的最小主張：

- 發生了什麼。
- 何時、何地發生。
- 數字、規模與統計截止時間。
- 誰採取行動或提出說法。
- 責任歸因、因果解釋與可能影響。
- 圖資或資料的發布時間與適用區域。

每個關鍵主張配置唯一 `claim_id`。

### 二、設計來源組合

依事件類型安排來源角色：

- 官方／監管／原始文件。
- 當地主流媒體或主要通訊社。
- 受影響者、地方現場或產業角色。
- 專家、研究機構、國際組織或可信第三方。
- 涉及爭議時的反對方、被指控方或其他直接當事方。

只在事件確實存在不同立場時搜尋對應角色，不硬湊無意義的正反雙方。

### 三、搜尋與追溯

- 使用事件所在地語言、輸出語言與必要的英文搜尋。
- 從轉述追溯新聞稿、文件、研究、法院紀錄、財報、資料庫或原始採訪。
- 搜尋相反說法、修正稿、撤稿、更新時間及可能推翻目前理解的證據。
- B 以上事件應擴大查找權威機構與不同角色；C 級仍至少完成多來源搜尋嘗試。
- 記錄搜尋過但未找到其他獨立來源的事實，不假裝不存在搜尋限制。

### 四、判斷來源獨立性

以證據源頭分組：

- 多家媒體轉載同一通訊社，只算一個獨立群組。
- 多篇文章都取自同一政府新聞稿，只算官方一方。
- 同一企業集團共用稿件或採訪，不自動視為獨立。
- 官方統計、獨立採訪、地方現場與第三方分析可以是不同證據角色。

記錄 `independence_group`，不要只記網址數量。

### 五、建立證據台帳

每個來源保存：

- 名稱、網址、發布與存取時間。
- 來源角色、資料產生者與獨立群組。
- 支持、部分支持、矛盾或僅提供背景。
- 支持哪些 `claim_id`。
- 限制、利益關係、定義差異及更新狀態。

每個關鍵主張必須能回指實際支持它的來源。列了四個來源但某項死亡數字全出自同一公告，該數字仍屬單一證據源。

### 六、權威資料回查

- 氣象、震央、震度、海嘯警報、疫情統計、財報與監管數字，優先採官方或原始資料作為客觀基準。
- 檢查資料版本、定義、統計截止時間、適用區域及是否已更新。
- 官方對責任歸因、政治指控、軍事成果、疫情是否受控或可能隱匿內容，只算當事一方。
- 官方資料與媒體或現場資訊不一致時，並列差異，不硬湊成單一結論。

### 七、形成判斷

設定：

- `corroborated`：關鍵主張獲多個獨立來源支持。
- `single_reliable_source`：目前只有一個可靠證據源。
- `conflicting`：可靠來源在數字、時間線、責任或因果上有實質矛盾。
- `insufficient`：來源本身不可靠或核心主張缺乏可用證據。

`single_reliable_source` 不得自動改變等級或入選狀態。讀者版加入：

`目前僅找到一個可靠來源，尚無其他獨立來源交叉確認。`

並採歸屬式語氣。若 `conflicting`，在各方說法與分析中清楚呈現差異。若核心主張為 `insufficient`，必須寫 `status=failed`，不得把 verification 標 completed 或繼續發布。先完成既定的事件級驗證恢復；仍不足時由 full-runtime 執行 `news_run_checkpoint.py rewind --stage audit-news-candidates`，只退回同一 run 的 audit 與後續階段，將受影響候選重評或以 `unreliable_or_unverified` 排除，再重新物化 manifest。不得重跑 discovery、preprocess 或 semantic selection，也不得建立替代 run。

## 輸出欄位

只寫入 `verification`：

- `status`
- `finding`
- `search_performed`
- `independent_source_count`
- `sources`
- `claims`
- `uncertainties`
- `source_limit_note`
- `positions`
- `reader_wording`
- `verified_at`

完成後不得撰寫整份讀者版，也不得取得地圖或圖片。
