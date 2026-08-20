# 本機語意事件聚類試驗 / Local Semantic Event Clustering Pilot

## 結論 / Conclusion

本機多語 embedding 可以在零 GPT/API token 下處理新聞事件近鄰，但目前的 embedding 相似度與時間／傷亡量級閘門仍不足以安全自動合併。修正識別碼型標題後，3,000 組固定樣本產生 22 個多成員事件群，其中 20 群確認為同事件、1 群明確誤合併、1 群資訊不足。確認誤合併率為 4.55%，最壞值為 9.09%。本版不得升級為正式規則。

Local multilingual embeddings can generate news-event neighbors with zero GPT/API tokens, but embedding similarity plus time and casualty-magnitude gates are not yet sufficient for safe automatic merging. After excluding identifier-like titles from embedding, a deterministic 3,000-group sample produced 22 multi-member event clusters: 20 confirmed same-event clusters, one confirmed false merge, and one uncertain cluster. The confirmed false-merge rate is 4.55%; the worst-case rate is 9.09%. This version must not be promoted to production.

## 輸入與資源 / Input and Resources

| 指標 / Metric | 結果 / Result |
|---|---:|
| 原始文章列 / Input article rows | 20,450 |
| 暫定證據組 / Provisional groups | 19,699 |
| 固定樣本 / Deterministic sample | 3,000 |
| 向量維度 / Vector dimensions | 384 |
| 樣本執行時間 / Sample runtime | 172.105 seconds |
| GPT/API token | 0 |
| 既有 unresolved 組 / Existing unresolved groups | 1,297 |
| 新發現識別碼型無效標題 / Newly detected identifier-like titles | 611 |
| 必須補取 metadata 的組 / Groups requiring metadata recovery | 1,908 |

模型為 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，透過 FastEmbed/ONNX 在本機 CPU 執行。第一次把標題與完整摘要一起處理，在 23 分 28 秒硬停，約使用 2.61 GB RAM；第二次只處理全量標題，在約 14 分鐘硬停，約使用 1.71 GB RAM。固定 3,000 組樣本在 172.105 秒完成。兩次中止均未產生可誤用的半成品向量。

The model was `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, executed locally through FastEmbed/ONNX. The first full attempt, embedding titles plus complete summaries, was stopped after 23 minutes 28 seconds at approximately 2.61 GB RAM. The second title-only full attempt was stopped near 14 minutes at approximately 1.71 GB RAM. The deterministic 3,000-group sample completed in 172.105 seconds. Neither stopped run produced a reusable partial vector file.

## 錯誤審核 / Error Audit

初次自動群中有大量 `a1802471`、`arid 41898676`、UUID 片段及 `content 118655472` 類型。根因是既有 `title_quality` 把英數識別碼誤判為 usable，導致這些字串進入 embedding。初次 29 個多成員群中有 9 群錯誤或不可驗證，表面誤合併率為 31.03%。

The initial automatic clusters contained many strings such as `a1802471`, `arid 41898676`, UUID fragments, and `content 118655472`. Root-cause tracing showed that the existing `title_quality` function classified alphanumeric identifiers as usable, allowing them into embedding. Nine of the initial 29 multi-member clusters were false or unverifiable, an apparent false-merge rate of 31.03%.

加入結構性標題資格檢查後，識別碼型組保持 singleton 並等待 metadata，重新分類結果如下：

After adding structural title eligibility, identifier-like groups remained singletons pending metadata recovery. Reclassification produced:

| 審核 / Audit | 數量 / Count | 比率 / Rate |
|---|---:|---:|
| 多成員事件群 / Multi-member clusters | 22 | 100% |
| 確認正確 / Confirmed correct | 20 | 90.91% |
| 確認誤合併 / Confirmed false merge | 1 | 4.55% |
| 資訊不足 / Uncertain | 1 | 4.55% |
| 最壞誤合併率 / Worst-case false-merge rate | 2 | 9.09% |

明確誤合併是兩則無關的中國地方文化／黨派活動新聞；它們在此模型中的相似度達 0.969。這證明不能只靠 embedding 分數自動合併，還必須比對人物、地點、機構及事件動作。

The confirmed false merge joined two unrelated Chinese local culture/party-activity stories at similarity 0.969. This proves that embedding score alone cannot authorize an automatic merge; person, place, organization, and event-action anchors are required.

## 漏合併審核 / Missed-Merge Audit

修正後有 110 個高相似但保持分開的候選對。逐對審核結果為 97 對看似同事件、11 對不同事件、2 對不確定；候選對層級的看似漏合併率為 88.18%。此樣本受到哈利王子返英、川普與金正恩會面等重複主題支配，不是全體事件的無偏估計，但足以證明 0.94 自動門檻過度保守。

After correction, 110 high-similarity pairs remained separate. Pair review found 97 likely same-event pairs, 11 different-event pairs, and two uncertain pairs, giving an apparent candidate-pair missed-merge rate of 88.18%. Repeated themes such as Prince Harry returning to the UK and a Trump–Kim meeting dominate this queue, so it is not an unbiased estimate for all events; it nevertheless proves that the 0.94 automatic threshold is too conservative.

## 無效標題是否可以放棄 / May Invalid Titles Be Dropped?

不可以。2,906 個原本不可用的標題已經能從網址復原；本次又證明既有規則漏抓 611 個識別碼型標題。這些資料應退出 embedding、保持 singleton，並補取 HTML title、Open Graph title、結構化資料或正文，而不是被當成低價值新聞刪除。

No. URL recovery already restored 2,906 originally unusable titles, and this pilot found 611 additional identifier-like titles missed by the prior rule. These rows must leave embedding, remain singletons, and recover HTML titles, Open Graph titles, structured metadata, or body text instead of being deleted as low-value news.

## 下一步 / Next Step

在自動合併前加入可驗證的事件身分錨點：地點、人物、機構、事件動作與時間。傷亡數保留所有原始版本，使用有無死亡與數量級作風險訊號；21→23 不阻止同事件合併，21→2300 則轉入確認。完成後重新使用同一固定樣本，要求確認誤合併率降至可接受門檻，再考慮離線全量執行。

Add verifiable identity anchors before automatic merging: place, person, organization, event action, and time. Preserve every casualty value and use death presence plus magnitude only as risk signals; 21→23 does not block a same-event merge, while 21→2300 enters review. Reuse the same deterministic sample and require an acceptable confirmed false-merge rate before considering an offline full run.


