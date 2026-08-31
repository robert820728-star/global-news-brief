---
name: collect-news-images
description: Collect, download or screenshot, prioritize, visually inspect, and attach official or media-published news images for selected events. Use after verification regardless of whether self-made maps or charts already exist; source images must remain an independent output and cannot be replaced by generated graphics.
---

# 新聞圖片取得與驗收

只修改事件資料的 `images`。不得修改事件編號、板塊、標題、等級、驗證內容、自製定位地圖或自製資料圖表。

## 必讀

依事件類型讀取 `references/image-policy.md`，並使用驗證階段已確認的來源清單。

## 適用門檻

`EVERY_DAILY_NEWS_EXECUTION_GATE`：manual, single-run, test, first-run, recurring, or resume 使用相同圖片門檻。full-runtime 可下載或直接截圖後物化本機附件；無本機 Python 的 Scheduled Task 宿主必須在 discovery 前確認能交付原生圖片卡或頁面圖片區域的原生截圖。通過後不得在 discovery 後宣告 `NATIVE_MEDIA_UNAVAILABLE`；沒有本機物化能力不是圖片 blocker。

- 所有入選事件（SS 至 C）：`images.required` 固定為 `true`，逐一開啟 `verification.sources` 的來源頁檢查圖片；評級不得作為跳過圖片流程的條件。
- 每個引用來源都必須寫入 `images.source_checks`；除是否找到可用圖片、嘗試次數與結果外，必須保存 `checked_at`、`inspection_method`、`detected_image_urls` 與 `failure_detail`。full-runtime 另保存本地 `evidence_path`；mobile-native 保存宿主結構化檢查結果。
- full-runtime 的 `evidence_path` 必須是頁面截圖、保存頁面或可重現檢查結果的本地證據，發布器會確認檔案實際存在。mobile-native 宣告 `no_usable_image` 時不得只填布林值，仍須保存已檢查來源與具體理由，但不得假造本地檔案。
- `VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE`：不要求原始檔或原畫質。偵測到官方或媒體圖片時，可直接下載來源頁中的實際媒體檔，也可立即截取文章、官方頁或可靠轉載頁中的同事件圖片區域；截圖不必等待下載失敗。`images.assets[].source_url` 保存來源頁，`images.assets[].source_image_url` 保存該頁可追溯的圖片網址。
- full-runtime 的每張來源圖片必須由 `scripts/materialize_news_images.py` 對 `source_image_url` 下載，或以 `screenshot_path` 讀取既有本機截圖，再解碼、寫檔並保存 `materialized-images.json`；不得只憑 manifest 宣告來源。
- 任一來源找到可信且相關圖片後，`images.status` 只能在至少一張附件通過驗收後改為 `ready`。
- 每則事件必須明確設定 `images.claim_critical`。只有圖片本身是核心主張證據（例如唯一影像證據、衛星圖直接證明攻擊或官方圖是數據主張本體）才設為 `true`；一般新聞配圖、人物照或輔助專業圖設為 `false`。
- `SCHEDULED_NATIVE_IMAGE_SEARCH_FIRST_GATE`：Scheduled Task 對每則事件先實際呼叫原生圖片搜尋；一般 web search、文章 open 與圖片 URL 解析不能冒充 image search。固定查詢精確標題／caption＋日期＋地點、事件＋官方／當事組織、事件＋適用的官方資訊圖／現場照片、事件＋通訊社／可靠媒體。逐張核對 semantic event 與日期；取得合格 image ref 後立即交付原生圖片卡，不得繼續撞已失敗的直接圖片網址。沒有合格 ref 才進入直接文章媒體、宿主實際可用截圖與後續來源；切換來源後以同一事件重新搜尋。
- `NATIVE_IMAGE_QUERY_RESULT_IS_NOT_CAPABILITY_GATE`：原生圖片搜尋工具已可呼叫、但某次查詢沒有回傳合格 `image_ref`，不代表宿主缺少圖片交付能力。不得在 discovery 前或後續 stage 把單次零結果、錯圖、舊圖或某來源未索引宣告為 `HOST_VISIBLE_MEDIA_TRANSPORT_UNAVAILABLE`；只有工具本身不存在、呼叫被拒絕或無法建立任何原生圖片結果物件時才是 capability failure，其餘情況繼續同事件替代來源與替代查詢。
- `WIRE_PROVIDER_SUBSTITUTION_GATE`：通訊社／媒體文章有當期圖片但查詢沒有合格 ref 時，不得反覆查詢同一通訊社、攝影者、caption 或 CDN。第一來源為 Reuters 時，下一個通訊社查詢優先改用 AP 同事件報導，再查官方／當事組織、當地可靠媒體與當地語言查詢，最後查其他可靠媒體；每次以精確事件／地點／日期及新來源名稱重新搜尋，取得合格 ref 即交付。
- `FIXED_VISIBLE_IMAGE_TRANSPORT_SEQUENCE`：Scheduled Task 固定執行原生圖片搜尋並把合格 `image_ref` 放入最終 image group／圖片卡 → 原文章直接媒體取得實際內容或 native ref → 宿主實際存在時截取頁面圖片區域並直接交付 → 官方／當事組織 → 原始通訊社 → 其他可靠媒體；每換來源先重新做同事件 image search，再試直接媒體與截圖。full-runtime 固定用既有 materializer 下載 bytes；下載失敗立即改用本機 `screenshot_path`，通過既有媒體驗證後交付本機實體附件。單一路徑失敗不得停止。
- `DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE`：檢查原引用文章的 `img`、`srcset`、`og:image` 或等價欄位。發現與當期事件相符的直接 JPEG／WebP URL 後，必須實際以宿主可用媒體路徑開啟／取得並嘗試可見交付；搜尋卡沒有 image ref 不等於圖片不可取得。URL／Markdown 本身仍不是可見附件。
- `IMAGE_PROXY_ORIGINAL_URL_UNWRAP_GATE`：圖片 URL 是 resize／redirect／縮圖／媒體代理時，逐層 URL-decode `url`、`u`、`src`、`source` 或 `image` 參數，並嘗試內嵌原始 JPEG／WebP及保留內嵌來源參數的最小代理 URL。代理失敗但這些候選未嘗試時，`direct_media_url_attempted` 不得為 `true`。
- `IMAGE_FALLBACK_EXHAUSTION_GATE`：每則事件依序實際搜尋原引用來源、官方機關／當事組織、原始通訊社及其他可靠媒體的同事件合法刊載／轉載圖片。圖片證據來源與文字驗證來源可以不同；圖片可不是同一張，但必須可信、合法公開刊載、可追溯，且事件、日期、人物／地點一致。每則 image evidence 必須保存 `original_source_attempted`、`direct_media_url_attempted`、`official_fallback_attempted`、`wire_fallback_attempted`、`reliable_media_fallback_attempted`、`qualified_image_found`、`delivery_attempted` 與 `delivery_result`。`delivery_unavailable` 或 source exhaustion 的 `direct_media_url_attempted` 必須為 `true`；任一來源層尚未實際搜尋時不得宣告 `NATIVE_MEDIA_UNAVAILABLE`、source exhaustion 或圖片 blocker。直接文章原圖已成功可見交付時，不必再做後續 fallback。
- `NON_SHORT_CIRCUIT_IMAGE_DELIVERY_GATE`：第一則或任何較早事件失敗時仍須繼續處理其餘全部入選事件；已有 native image ref／圖片卡者必須實際嘗試交付。禁止以 `native_card_available_but_canonical_reader_blocked_by_prior_event` 或同義狀態跳過後續事件，最後才彙整所有未交付事件供同一 run 恢復。
- `NATIVE_MEDIA_CAPABILITY_FALLBACK`／`QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL`：full-runtime 已找到可用圖片時，直接選擇下載或截圖中最快能產生可見附件的方法；Scheduled Task 宿主則直接使用原生圖片卡或頁面圖片區域截圖。不得以原圖／CDN／第一來源失敗阻止截圖或可靠轉載 fallback。四層來源確實沒有合格圖片時才可記 source exhaustion 並省略；已確認存在合格圖片時，不論 `claim_critical` 都必須完成可見交付後才可發布文字 Reader。不得在未嘗試前預判，也不得等待未實際存在的未來 recovery worker。
- 只有四層來源都已實際搜尋且均無可用圖片，才可使用 `omitted`，並保存具體後台原因與繁體中文 `reader_omission_note`；兩者只供內部 evidence／receipt，不得顯示於讀者版。
- 圖片取得失敗不改變事件等級。
- 原引用來源沒有可取得圖片時，依序搜尋官方機關／當事組織、原始通訊社與其他可靠媒體的同事件報導；可檢查多個來源，不限一個，也不要求找到完全相同像素。新來源必須加入事件的圖片證據與來源追溯，並核對發布日期、人物／地點與事件關聯；搜尋縮圖、無法追溯的搬運站、舊照或無關示意圖不得入選。
- 自製定位地圖由 `build-news-maps` 處理，不得放進 `images`。
- 自製資料圖表由 `build-news-charts` 處理，不得放進 `images`。
- `map.assets`、`charts.assets`、`images.assets` 三組附件路徑必須兩兩不重複；任何一種視覺完成都不能改變另外兩種的需求、狀態、檢查紀錄或附件。同一張合格官方／專業來源圖片可以同時滿足來源圖片與專業圖資兩組檢查，但兩組檢查紀錄都必須保留。`IMAGE_ONE_ASSET_MAY_SATISFY_BOTH_SOURCE_AND_PROFESSIONAL`
- `map.status` 或 `charts.status` 已是 `ready`，不代表圖片階段完成；仍須逐一檢查來源頁並取得官方或媒體實際發布的合格圖片。

## 官方專業圖資搜尋與關鍵證據閘門

- 任何入選事件若屬氣象、災害、疫情、公共衛生、地震、海嘯、火山、野火、洪水、乾旱、熱浪、戰爭、軍事、航運、海峽／航道、漏油、油污、海洋污染、化學或核事故，`images.professional_visual_required` 固定為 `true`；此判定必須依事件內容完成，禁止使用評級門檻或事件編號白名單。
- 先依事件類型與主要影響地區，主動搜尋主管機關、監測機構、地方政府或專業組織的圖資；不得只檢查新聞來源頁後就宣告沒有專業圖。
- 每個查過的官方或專業頁面都寫入 `images.professional_source_checks`。至少涵蓋中央主管機關與主要受影響地區主管單位；跨國事件再查國際組織或受影響國官方來源。
- 官方專業圖資檢查同樣必須保存檢查時間、方法、檢出的圖片網址與判定理由；full-runtime 另保存本地頁面證據，mobile-native 保存宿主結構化檢查結果。確實沒有合格專業圖時，只有 `claim_critical=true` 才阻擋；但已確認合格專業圖而交付失敗時，不論 `claim_critical` 都必須進入同一 run 的視覺恢復。
- 找到與事件時間、地區及主張相符的專業圖時，full-runtime 至少一張 `kind` 為 `official_information` 或 `professional_information` 的本地附件通過視覺與時間驗收前，不得把 manifest 的 `images.professional_visual_status` 宣稱為 `ready`；mobile-native 只在 image evidence／ledger 記錄原生卡交付結果。已確認圖片尚未成功交付時不得完成整則事件；`claim_critical` 只決定來源確實無圖時能否省略。
- full-runtime 專業圖可直接下載或直接截取官方產品頁；兩者沒有固定先後。若仍失敗，再依「官方歷史／存檔頁 → 地方主管機關 → 主要媒體引用的同一官方圖」重試；不得因第一次取得失敗就停止。
- 只有完成上述搜尋且確實沒有符合事件階段的專業圖，才可把 `images.professional_visual_status` 設為 `not_available`，並在 `images.professional_omission_reason` 保存具體後台原因。
- 自製定位地圖、自製資料圖表、普通新聞照片與頁首圖均不能滿足專業圖資硬閘門。若同一張 `official_information`／`professional_information` 圖確實出現在已引用來源或本身就是已引用官方來源，且通過時間與內容驗收，可同時滿足來源頁附件與專業圖資硬閘門；不得為形式另附重複照片。

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

官方資訊圖與新聞配圖確實互補時可同時保留；若新聞配圖只重複同一事件辨識，不得為形式追加。

## 禁止以自製內容冒充來源圖片

- 不得自行把新聞文字、各方立場、摘要、結論或三個數字排成卡片後寫入 `images.assets`。
- 不得把文章頁 HTML、搜尋結果頁、模型自製資訊卡或只含標題的占位圖標記為 `official_information`、`professional_information` 或 `news_photo`。
- 不得把「俄羅斯／烏克蘭及盟友」、「安全評估／全面否認」等純文字對照卡當成新聞圖片。
- 自製圖表只限至少兩個可比較的數值、時間序列、比例或分布；必須寫入獨立 `charts` 欄位。
- 自製圖表的圖說須標示「本簡報依○○資料製作」，不得宣稱為該媒體或官方發布的圖片。
- 即使已有合格自製圖表，所有入選事件的來源圖片檢查仍照常執行；自製圖表不得計入來源圖片最多 2 張，也不得冒充來源圖片。非主張關鍵的來源圖片可在取得失敗時省略。

## 數量與順序

`IMAGE_DEFAULT_ONE_ASSET`：每則事件預設 1 張來源圖片，最多 2 張：

1. 第一張選資訊量最高且能獨立幫助理解事件的官方／專業資訊圖或新聞配圖。
2. `IMAGE_SECOND_ASSET_REQUIRES_INCREMENTAL_INFORMATION`：只有第二張提供第一張沒有的範圍、數字、現場或時間變化時才保留，並在 `incremental_information` 寫明新增資訊。
3. 同一張圖能同時通過來源與專業圖資檢查時只附一次；不得用兩個路徑或不同尺寸重複附圖。
4. 超過 2 張時刪除重複、低資訊、過時或驗收失敗圖片。

## full-runtime 低負擔處理

- 下載或截圖後先計算內容 SHA-256，並保存到 `images.assets[].content_sha256`。`IMAGE_SHA256_REUSE`
- 同一輪遇到相同 SHA-256 時，沿用已下載檔案、`640px` 縮圖、轉檔結果及驗收結論；不得重複下載、縮圖或開圖。
- 先以 MIME、實際解碼、寬高與 SHA-256 完成程式檢查，再進入內容驗收。
- 每個唯一 SHA-256 只實際開啟並視覺驗收一次；只有事件相關性、日期、統計截止或畫面內容仍不確定時才加深判讀。`IMAGE_VISUAL_CHECK_ONCE_PER_HASH`
- full-runtime 對行動對話優先沿用同圖最長邊 `640px`、JPEG／WebP 品質 `75–82`、目標 `200KB` 以下；mobile-native 不宣稱自行轉檔，改用宿主原生圖片卡可提供的版本。兩者都不因壓縮能力缺少而中止文字 reader。

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

失敗時依取得順序重試。若來源已確認有可用圖片但重試仍失敗，不論 `claim_critical` 都維持未完成狀態並只重跑圖片模組；來源確實沒有合格圖片時，非關鍵圖片才可改為 `omitted`，只在內部 evidence 保存原因且不在 reader 顯示省略說明。不得只留下「圖一」文字。

## 與候選來源確認共同發布

圖片驗收與候選稽核確認在 `publish_news_brief.py` 同一個閘門執行。發布時必須同時提供候選稽核檔；完全沒有可核實候選、候選缺少 SS–E 評級理由、達標事件漏入 manifest、主張關鍵圖片缺失、已確認圖片尚未交付或來源頁檢查未完成時，不得產生 release。來源確實無圖或非關鍵本機生成視覺失敗才形成可完成的 visual degradation。單一 discovery route 缺失或不完整只記 coverage 降級，不得阻擋其他可用候選。

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

full-runtime 只寫入下列 manifest `images` 欄位；mobile-native 不建立該本機附件 manifest，只把來源檢查、文章直接媒體 URL、原生圖片卡、後續來源與交付結果寫入既有 `image-evidence.json`／ledger：

只寫入：

- `images.required`
- `images.claim_critical`
- `images.status`
- `images.source_checks[].source_url`
- `images.source_checks[].checked`
- `images.source_checks[].checked_at`
- `images.source_checks[].inspection_method`
- `images.source_checks[].evidence_path`（full-runtime 必填）
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
- `images.assets[].source_image_url`
- `images.assets[].kind`
- `images.assets[].published_at`
- `images.assets[].content_sha256`
- `images.assets[].incremental_information`（只有第二張必填）
- `images.assets[].visual_checked`
- `images.assets[].time_checked`
- `images.assets[].width`
- `images.assets[].height`
- `images.omission_reason`
- `images.reader_omission_note`

四層來源 fallback 全部實際搜尋後仍確實沒有合格圖片時，保存後台原因；讀者版完整省略圖片、caption 與占位文字。只要任一路徑找到合格圖片，無論 `claim_critical`，交付失敗都不得改寫成 omission 或完成文字 Reader。



