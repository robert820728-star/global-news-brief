# 本機語意事件聚類試驗 / Local Semantic Event Clustering Pilot

## 結論 / Conclusion

本機多語 embedding 可以在零 GPT/API token 下處理新聞事件近鄰，但不得單靠 embedding 相似度自動合併。第一輪修正識別碼型標題後，3,000 組固定樣本仍有 1 群明確誤合併。第二輪加入標題表面重疊與事件身分錨點後，修正後的另一份固定 3,000 組樣本產生 41 個多成員事件群，人工逐群審核為 41 群同事件、0 群確認誤合併。第二輪仍是實驗規則，尚未升級正式流程。

Local multilingual embeddings can generate news-event neighbors with zero GPT/API tokens, but embedding similarity alone must not authorize automatic merging. After identifier-like titles were excluded, the first deterministic 3,000-group sample still contained one confirmed false merge. A second iteration added title-surface overlap and event-identity anchors. On a corrected deterministic 3,000-group sample, it produced 41 multi-member clusters; manual cluster-by-cluster review found 41 same-event clusters and zero confirmed false merges. The second iteration remains experimental and has not been promoted to production.

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

## 第二輪：身分閘門與向量綁定 / Iteration 2: Identity Gates and Vector Binding

第二輪仍把 embedding 只當候選產生器。自動合併除了相似度至少 0.86，還必須同時符合標題字元三連詞 Jaccard 至少 0.18、至少一個共同事件身分錨點、48 小時時間閘門，以及傷亡數量級風險閘門；未通過者只能進入模型確認，不得自動淘汰或降級。

Iteration 2 still uses embeddings only as a candidate generator. Automatic merging requires similarity of at least 0.86, title character-trigram Jaccard of at least 0.18, at least one shared event-identity anchor, the 48-hour time gate, and the casualty-magnitude risk gate. Anything that does not pass can only enter model review; it cannot be automatically discarded or downgraded.

| 第二輪指標 / Iteration 2 Metric | 結果 / Result |
|---|---:|
| 修正後固定樣本 / Corrected deterministic sample | 3,000 groups |
| 可用標題母體 / Eligible-title population | 17,791 groups |
| 近鄰候選對 / Neighbor candidate pairs | 581 |
| 自動合併邊 / Automatic merge edges | 57 |
| 多成員事件群 / Multi-member event clusters | 41 |
| 合併減少暫定組 / Consolidated provisional groups | 51 |
| 外部模型確認對 / External model-review pairs | 159 |
| 確認正確自動群 / Confirmed correct automatic clusters | 41 / 41 |
| 確認誤合併 / Confirmed false merges | 0 / 41 |
| 自動刪除／重要性判定 / Automatic deletion or importance decisions | 0 / 0 |
| GPT/API token | 0 |

舊向量檔曾只以「向量筆數相同」判定可重用；修正抽樣母體後，3,000 個向量可能對到不同的 3,000 個事件而不報錯。第二輪已新增向量 manifest，綁定每個向量的 `group_id`、順序、模型名稱與輸入模式；任何不一致都直接停止。修正後向量重建耗時 177.394 秒。同一向量與設定連跑兩次，扣除執行時間欄位後的完整語意結果 SHA-256 均為 `c54573142f3a76ee2fbe9ae67af5c2d1ddf92211e6e3f20d48357f6c577aec76`。

The old vector cache was reusable whenever only the vector count matched. After the sampling population changed, 3,000 vectors could silently map to a different set of 3,000 events. Iteration 2 adds a vector manifest binding every vector to its ordered `group_id`, model name, and input mode; any mismatch now stops the run. Rebuilding the corrected vectors took 177.394 seconds. Two runs with the same vectors and settings produced the same complete semantic-result SHA-256 after excluding the elapsed-time field: `c54573142f3a76ee2fbe9ae67af5c2d1ddf92211e6e3f20d48357f6c577aec76`.

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

第二輪已證明表面身分閘門可以擋住第一輪已知誤合併，且本次 41 個自動群未發現誤合併；但目前的身分錨點仍只是字詞與中文三連詞，不是完整的人物／地點／機構辨識。下一步應先完成 metadata 補取與本機實體／地理標記，再以其他固定樣本重複誤合併審核。達到多批樣本均無確認誤合併後，才考慮離線全量執行。

Iteration 2 shows that surface identity gates block the known first-iteration false merge, with no confirmed false merge among this run's 41 automatic clusters. The present anchors are still word tokens and Chinese trigrams, however, not full person/place/organization recognition. The next step is metadata recovery plus local entity and geographic labeling, followed by repeated false-merge audits on other deterministic samples. A full offline run should be considered only after multiple samples produce no confirmed false merge.

