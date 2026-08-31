# 每日新聞排程執行契約

`EVERY_DAILY_NEWS_EXECUTION_GATE`

`VISIBLE_MEDIA_SCHEDULE_ELIGIBILITY_GATE`

Any daily-news invocation—manual, single-run, test, first-run, recurring, or resume—uses the same news and visible-image requirements. full-runtime may download or directly screenshot and materialize local attachments. A no-local-Python ChatGPT Scheduled Task may use its native image card or direct page/image-region screenshot path after that same host passed the installation smoke. Trigger type never relaxes visible attachment delivery, but original files and original quality are not required.

`NATIVE_IMAGE_QUERY_RESULT_IS_NOT_CAPABILITY_GATE`: A callable native image-search tool returning no qualified `image_ref` for one query is a content/query result, not proof that the host lacks image transport. It must not stop before discovery or become `HOST_VISIBLE_MEDIA_TRANSPORT_UNAVAILABLE`; continue the same-event alternate-source and alternate-query path.

`NON_TEXT_MEDIA_CONTENT_BLOCK_GATE`: Literal `image_group`, `async_image_group`, `image_ref`, `turn...image...`, or JSON inside ordinary assistant text is never visible-image delivery. A Scheduled Task succeeds only when the host creates a non-text image/media content block and renders non-zero-size pixels. A structured readback containing only `agentMessage text` must fail image delivery and may not claim image PASS or canonical completion.

`LOCAL_ATTACHMENT_FIRST_WHEN_RUNTIME_AVAILABLE_GATE`: when the host has a writable filesystem and executable runtime, it must resolve the original article, official source, or reliable republication media; download or screenshot it into a real image file; validate decode, dimensions, and hash; and deliver that local attachment. Native image search may locate a candidate but cannot replace the attachment. Only a host without local file/runtime capability may use a native image card; a serialized text ref fails immediately and must fall through to a page-image screenshot and the next reliable source without waiting.

`WIRE_PROVIDER_SUBSTITUTION_GATE`: When a current wire-service article has an image but its query yields no qualified ref, do not repeat the same wire, caption, or CDN. For Reuters, try an AP same-event report next, then official/party sources, local reliable media with a local-language query, and other reliable media. Deliver the first verified same-event ref.

## Discovery first, verification second

`DISCOVERY_THEN_VERIFY`

- The pre-selection list uses exactly three configured discovery sources: GDELT for broad global discovery, CNA as the Taiwan supplement, and China News Service as the China supplement.
- `GDELT_RESILIENT_ACQUISITION` uses the official 15-minute export archives as primary discovery. Only when the archive is unavailable may it make one non-blocking DOC API request; never wait or retry after a 429, and label any DOC result as incomplete supplemental coverage.
- A regional-supplement discovery failure does not block another covered section. When the run includes the fallback/global section, `GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE` prefers a successful configured primary aggregator. After every configured primary route is exhausted, verified cross-source global results may be materialized as the reserved `web_fallback` coverage row and admitted as candidates. That row must remain incomplete/degraded, preserve replayable search evidence and every admitted URL, and cannot satisfy configured-route completeness or impersonate GDELT. If neither primary discovery nor verified `web_fallback` yields candidates, remain at source-scan even when regional candidates exist.
- The fixed order is `discover -> deduplicate -> score -> independently verify selected C-or-higher events -> collect images -> render`.
- `PIPELINE_COUNT_RECEIPT`: candidate audit 的最新一輪必須保存 `merged_article_row_count`、`in_window_article_row_count`、`canonical_url_count`、`provisional_title_cluster_count`、`semantic_event_count`、`scored_event_count`、`c_or_higher_scored_event_count`、`selected_event_count`，以及 `event_evidence_article_row_count`、`non_news_article_row_count`、`unresolved_article_row_count`、`unresolved_exhausted_article_row_count`。各欄必須由實際 artifact 重算並依序守恆；文章列數不得稱為語意事件數，網址正規化或標題分群也不得冒充語意去重。數量小計不相等時，停止宣稱該數字已驗證，但不得因此停止以可核實候選發布讀者版。
- `SEMANTIC_EVENT_LEDGER_GATE`: 只有語意事件才算新聞、才可進入六項評分。前處理的網址正規化與標題分群只產生文章層 `provisional_article_groups`，不得當成事件。選稿必須讀取文章內容或來源支援摘要，為每個真正事件建立唯一 `semantic_event_id` 與完整 `event_identity`，並逐列寫入 `article_dispositions`。每列只能是 `event_evidence`、`non_news`、`unresolved` 或 `unresolved_exhausted`；仍在恢復的 `unresolved` 必須歸零，已完整窮盡內容恢復鏈者保留為 `unresolved_exhausted` 並使 coverage 降級，但不得阻止其他已驗證事件。文章列數、網址數與標題群組數不得稱為新聞數或完成評分數。
- `EVENT_REGION_AND_TIME_IDENTITY_GATE`: 建立語意事件後、六項評分前，必須從文章內容獨立填寫 `event_identity.country_codes`、`primary_country_code`、`location_evidence`、`event_occurred_at`、`material_update_at`、`material_update_type`、`material_update_evidence` 與 `temporal_review`。來源分桶、來源媒體國別及候選清單的 `section` 只供 discovery，不是事件地區證據；事件板塊由 `country_codes` 對照本輪有序 `section_scopes`（成員國與唯一 fallback）決定。時間資格必須由模型比較文章內容、十四天事件時間線與本輪數據，分成 `new_event`、`ongoing_current_impact`、`material_update` 或 `old_restatement`；程式只驗證結論與證據一致性。舊事件重新整理、回顧、週年、換標題或重刊一律 `non_news`；但開始較早且有證據顯示仍持續跨越本輪時間窗、仍造成當下影響的事件，可列 `ongoing_current_impact`，不要求硬湊新增傷亡。地區或時間身分缺漏、矛盾時維持 `unresolved`，不得評分或刊出。
- `POLICY_GOVERNANCE_EVIDENCE_GATE`: 事件身分與時間資格確認後、六項評分前，先證明政策／法規／主管機關處置／平台治理事件真正是什麼。最新一輪每個候選必須填 `policy_governance_review`；rumor 保存可歸屬報導與來源限制但不得編法律依據或官方行動，consideration 要有官方正在評估的證據但可無法律文本，proposal 及後續階段才要求相應正式程序證據。未經證實的指控必須放入 `unverified_allegations`，不得併入事件身分、直接後果或六項分數。草評後逐項核對公共影響、範圍、結構意義與窗內增量；任何矛盾或未解都必須退回重審並重新評分。具有官方行動、實際業者效果及跨機關／外溢證據但低於 B 時，必須填具體 `why_not_b`；不得自動升 B，也不得略過反向挑戰。
- The system must score and deduplicate before independent verification. Verification dynamically selects the original report, official or primary evidence, and genuinely independent evidence appropriate to each event and claim.
- The system must collect images only after verification. Discovery image URLs are hints only and cannot satisfy the reader-visible image gate.

`IMAGE_FALLBACK_EXHAUSTION_GATE`

- `VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE`／`DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE`：不要求原始檔或原畫質。檢查原引用文章時可解析 `img`、`srcset`、`og:image` 後下載，也可直接截取文章、官方頁或可靠轉載頁中的同事件圖片區域；兩者沒有固定先後，任一方法取得可追溯、事件與日期相符的本機圖片即可物化並嘗試可見附件交付。搜尋卡沒有 image ref 不等於圖片不可取得；外部 URL、Markdown 圖片字串或純文字連結本身不算可見交付。
- `IMAGE_PROXY_ORIGINAL_URL_UNWRAP_GATE`：若圖片是 resize／redirect／代理 URL，逐層 URL-decode `url`、`u`、`src`、`source` 或 `image` 參數，並嘗試內嵌原始 JPEG／WebP及保留內嵌來源參數的最小代理 URL；代理失敗不能讓未嘗試候選被記成 `direct_media_url_attempted=true`。
- `NON_SHORT_CIRCUIT_IMAGE_DELIVERY_GATE`：較早事件圖片失敗時仍須處理全部後續入選事件。已有 native image ref／圖片卡者必須實際嘗試交付；禁止用 `native_card_available_but_canonical_reader_blocked_by_prior_event` 或同義結果跳過，最後才彙整全部未交付事件。
- 圖片取得不得因原引用來源、原始圖片 URL、原生圖片卡或單一媒體交付失敗而停止。每則事件在宣告 `NATIVE_MEDIA_UNAVAILABLE`、`source_exhausted` 或任何圖片 blocker 前，必須依序實際搜尋：原引用來源 → 官方機關／當事組織 → 原始通訊社 → 其他可靠媒體的同事件合法刊載／轉載圖片；可使用不同但與同一事件、日期、人物／地點相符且可追溯的合格新聞照片。
- 每則 image evidence 必須保存 `original_source_attempted`、`direct_media_url_attempted`、`official_fallback_attempted`、`wire_fallback_attempted`、`reliable_media_fallback_attempted`、`qualified_image_found`、`delivery_attempted` 與 `delivery_result`。宣告 `NATIVE_MEDIA_UNAVAILABLE` 或 source exhaustion 前，`direct_media_url_attempted` 必須為 `true`；任一來源層尚未實際搜尋時不得宣告 fallback exhaustion、圖片不可取得或不可恢復 blocker。直接文章原圖已成功可見交付時，不必再做無增量的後續來源搜尋。
- 找到原文中存在圖片，不代表圖片只能從該原文取得。圖片證據來源與文字驗證來源可以不同，但圖片來源必須可信、合法公開刊載、可追溯，且事件、日期、人物或地點一致。不得用搜尋縮圖、無法追溯的搬運站、舊照或無關示意圖。

### Category-appropriate verification

`CATEGORY_APPROPRIATE_EVIDENCE_ROUTE`

- Every C-or-higher candidate must be checked with evidence appropriate to the claim category. A generic news rewrite is not a substitute for the closest available primary record.
- `TECH_SCIENCE_EVIDENCE_ROUTE`: for science, medicine, and technology claims, locate the paper, journal or proceedings record, research institution material, and peer-review status. Check independent expert assessment or follow-up research when available; label preprints, press releases, and unreplicated claims explicitly.
- `CONFLICT_MULTI_SIDE_EVIDENCE_ROUTE`: for war and military claims, compare the parties' accounts and add a credible independent or third-party source when available. Casualties, battlefield gains, and attribution that cannot be cross-checked must remain clearly labelled as a party's claim.
- `DISASTER_OFFICIAL_STATISTICS_ROUTE`: for disasters and accidents, prefer timestamped statistics from disaster agencies, local authorities, emergency services, hospitals, or international organizations. Media totals are leads; when counts conflict, state the discrepancy and use the newest attributable official count without presenting it as final.
- `OFFICIAL_SOURCE_BIAS_GUARD`: official publication proves what an authority reported, not that the account is complete or impartial. For China in particular, and for any authority with an interest in the outcome, compare non-official reporting, revisions, omissions, and independent evidence. If concealment or reporting limits cannot be excluded, disclose the limitation and reduce confidence or grade when it affects the claimed significance.
- Other categories follow the same rule: economics uses official statistics, regulatory filings and market data; law uses judgments, indictments or statutes; policy uses the signed or published text; elections use election authorities plus plural observation; public health uses health agencies, international bodies and research evidence.
- `MEDIA_TRANSCRIPTION_IS_NOT_VERIFICATION`: two outlets repeating the same wire copy, press release, anonymous post, or upstream claim count as one evidence chain, not independent confirmation. Trace the shared claim to its earliest attributable record before assigning reliability.
- `DOMAIN_EXPERTISE_MATCH`: an assessment only strengthens verification when its author or institution has relevant expertise and a transparent method. General reporting may establish that a claim circulated, but cannot replace technical, scientific, legal, statistical, medical, military, or other domain evidence.
- `TIMELINESS_WITH_SOURCE_LIMIT_NOTE`: the absence of an official record does not by itself prohibit publication of a timely event. Reliable on-scene reporting, attributable imagery, or multiple genuinely independent observations may support publication, but the reader must be told which official statistics or primary records are still unavailable; disputed numbers, attribution, and technical conclusions remain provisional and receive lower verification confidence until updated.

## Same-source recovery order

`SAME_SOURCE_RECOVERY_ORDER`

The required order for every configured discovery route is: `canonical route -> same-site direct fetch -> same-site alternate non-browser route -> browser-rendered snapshot`.

- Run `scripts/recover_same_source_leads.py` for a verified coverage lead; never inject a search result directly into selection.
- `browser is the final fallback only`. It is permitted only after the direct article fetch and all configured same-site non-browser alternatives have failed and those failures were logged.
- A browser DOM snapshot must pass the same same-source host, SHA-256, publication-window, evidence, coverage, and candidate validators as direct evidence.
- Recovery applies only to the affected configured discovery route. It must not restart routes that already have verified evidence.


本文件是排程執行時的主控契約。所有新聞內容、選稿、驗證、地圖、圖表、圖片、恢復與發布規則，以 repository 內最新版設定、skills、schemas 與 scripts 為準；不得由模型自行另造平行流程。

## 固定輸出設定

- 預設區域：`TWN`、`CHN`、`GLB`；本輪明確指定的國家、區域、洲別或國際組織板塊覆寫預設。
- 語言：沿用使用者既有設定；未設定時預設繁體中文。
- 時區語意：沿用本 Scheduled Task／使用者設定的時區；只有宿主無法判斷且使用者未指定時才預設 `Asia/Taipei`。
- 新聞時間窗：以本輪**實際執行時間**為 `window_end`，精確向前 24 小時為 `window_start`。不得用「今天 00:00 起」或排程原定時間替代。
- 不設定任意篇數上限；依 `news-brief-settings.md` 的評級、門檻與 continuity 規則決定事件數量。
- 讀者版標題固定為「每日新聞」；若宿主可控制對話標題則使用此名稱。

## 執行輸入正規化

`RUN_INPUT_NORMALIZATION_GATE`

- 使用者只需說明「依 GitHub 規定執行」，並另外列出本輪區域與監控類型；其餘 discovery、事件去重、六項評分、驗證、圖片、地圖、reader 與發布規則全部由本 repository 決定，不要求使用者重貼。
- 區域正規化為 `sections`：國家優先使用 ISO 3166-1 alpha-3；跨國區域使用穩定三碼。未指定區域時才使用 `TWN`、`CHN`、`GLB`。
- 監控類型正規化為 `topic_weights`。先比對既有主題鍵；沒有完全相同鍵時保存使用者原詞與最接近的主題映射，不得靜默忽略，也不得因此改變六項評分公式或設定篇數上限。
- 正規化結果必須在 discovery 前寫入本輪 manifest／audit 的設定證據；後段不得自行改區域或監控類型。

## Stage -1：先取得可執行 workspace

### Scheduled-host capability routing

`SCHEDULED_HOST_CAPABILITY_ROUTING`

`SCHEDULE_PROMPT_UPDATE_PRECEDES_SMOKE_GATE` applies before capability routing: installation or repair first writes and reads back the newest complete `scheduled-task-prompt-template.md`. Only then does `SAME_SCHEDULED_HOST_VISIBLE_SCREENSHOT_SMOKE_GATE` require the same ChatGPT Scheduled Task host to show a native image card or directly screenshot a public page's image region. The smoke does not require a verified workspace, repository map, original download, or original quality. A URL, Markdown hotlink, path string, caption, or broken placeholder does not pass. Failure retains the newest prompt and pauses the task; it must never leave an old prompt enabled.

Before reading the recursive tree, capsule manifest, helpers, payload, or chunks, perform exactly one no-network capability probe using the host's native execution tool. The probe only checks whether this run has both a writable temporary workspace and a Python runtime able to execute a standard-library statement. A shell or container command is not required when the host exposes Python through a native data-analysis tool.

- If the no-network probe succeeds, attempt `VERIFIED_BOOTSTRAP_SEED_ROUTE` before creating a news checkpoint or execution-mode ledger occurrence; the early diagnostic run id and best-effort issue comment below remain permitted: fetch the loader from the exact pinned raw URL, verify its Git blob SHA against the recursive tree, and only then execute it. Continue as `full-runtime` only after the verified loader has materialized and verified the manifest, payload, runtime files, and workspace receipt.
- If the local execution backend is absent, or the pinned loader seed cannot be obtained and the host has no lossless connector-to-local file handoff, classify the diagnostic as `host_execution_unavailable` or `bootstrap_seed_transport_unavailable`, not as a repository defect. If the same Scheduled Task host already passed the native visible-image smoke, route this occurrence to `mobile-chatgpt-daily-prompt.md`; do not wait for a nonexistent future full-runtime worker.
- `mobile-chatgpt-daily-prompt.md` is the active no-local-Python Scheduled Task route. It must execute discovery, scoring, verification, per-event image fallback, visible native screenshot/card delivery, and Reader production; it cannot claim that Python validators or local materializers ran.
- The repository never prepares a future occurrence before the Scheduled Task actually fires. The selected executor creates/resumes the occurrence with immutable `execution_mode=full-runtime` or `mobile-native`. The next scheduled occurrence probes capabilities again and resolves fresh `main`; it must not create a second task merely to retry missing runtime.

`PRE_PROBE_METADATA_READ_RECOVERY`: if the executor accidentally reads only repository tree, manifest, helper, payload, or chunk metadata before the capability probe, that ordering mistake must not fail the run. The recovery must occur before any news source or prior result is read: immediately perform the one probe, discard the pre-read metadata, and continue through the selected execution mode. The executor must not reuse any pre-read tree, manifest, helper, payload, or chunk; it must refetch the required metadata from the same pinned SHA after routing. This recovery does not permit pre-reading news, an old reader, candidate audit, or source results, and it does not relax any capsule hash or workspace verification.

This routing is deliberately limited to host capability selection. It adds no new gate, framework, capsule, or retry system.

任何 `scripts/*.py` 執行前，先完整遵守 `bootstrap-workspace.md`。

GitHub connector 可見 repository 不代表 shell 已有 repository。每輪都必須重新解析當下最新版 `main`，再使用該輪 SHA 的 verified runtime capsule：

1. `PRE_CONTRACT_MAIN_RESOLUTION`：排程外層指令必須先以 fresh UTC nonce 呼叫 `/branches/main?cache_bust=<nonce-a>` 與 `/commits/main?cache_bust=<nonce-b>`，再從兩者同意的 SHA 讀取本檔。These are the **only permitted pre-contract GitHub reads**；因執行器在讀到本契約前不可能受本契約的 run-id 順序約束。此例外只允許 single named `main` branch lookup、latest-main pin 與本檔讀取，不得讀 tree、manifest、來源、舊 reader 或執行新聞工作。
2. `EARLY_DIAGNOSTIC_MAIN_PINNED`：兩個端點必須回傳 same SHA。若不一致，以兩個全新 nonce 各重讀一次；第二次仍不一致就停止 Stage -1，不得猜測何者較新。The task must not enumerate repository branches, must not reuse a commit SHA、前次 workspace、排程建立時的固定 SHA 或模型記憶來決定本輪版本。
3. `EARLY_DIAGNOSTIC_RUN_ID`：同一 SHA 的本契約載入後，立即在工作記憶中 **without a tool call** 產生唯一 `<run-id>`、UTC `started_at` 與後續請求用 nonce；格式固定為 `gnb-YYYYMMDDThhmmssZ-xxxxxxxx`。Workspace 建立後再用 `scripts/run_identity.py` 驗證格式；不得因前置 main pin 發生在 run-id 之前而判定失敗。
4. `EARLY_DIAGNOSTIC_RUN_STARTED`：run-id 建立後，**before any recursive tree read**，立即在 GitHub Issue #3 建立本輪唯一 run-started comment，內容只含 `run_id`、`commit`、`status=running`、`stage=bootstrap-main-pinned`、`progress=0/unknown`、`updated_at`、`last_error=null`。等待此留言呼叫回傳並在工作記憶保存 comment id 後，才可讀 tree。此步只嘗試一次；無寫入權限或呼叫失敗就記住 `external_ledger: unavailable` 並繼續，不得阻擋新聞。
5. `EARLY_DIAGNOSTIC_TREE_VERIFIED`：從固定 SHA 取得 recursive tree；只保留後續驗證所需的 path／blob SHA，不得在回答中重印 tree。成功後 **update the same comment** 為 `stage=bootstrap-tree-verified`。
6. `EARLY_DIAGNOSTIC_MANIFEST_VERIFIED`：從固定 SHA 取得並驗證 `bootstrap/capsule-manifest.json`；成功後 update the same comment 為 `stage=bootstrap-manifest-verified` 與 `progress=0/<chunks_total>`。
7. 驗證 capsule 與本輪 tree／commit 關係：manifest 的每個 runtime file 與 payload blob 必須對應本輪固定 SHA；任何 stale capsule、缺檔或 blob 不一致都停止 full-runtime 路徑。
8. `VERIFIED_BOOTSTRAP_SEED_ROUTE`：從已驗證 tree 取得 `bootstrap/bootstrap_loader.py` 的 Git blob SHA；只用宿主 Python 標準庫讀取精確 pinned raw loader URL，於記憶體重算 Git blob SHA，完全一致後才寫入 staging。這是 verified loader 執行前唯一允許的 raw helper 讀取；不得要求 connector 回傳內容再手工或有損地寫入本機。
9. 執行已驗證 loader，傳入同一固定 SHA 的 `--manifest-url`、`--payload-url` 與 manifest Git blob SHA。Loader 必須先驗 manifest Git blob SHA，再驗 payload size／SHA-256／Git blob SHA、tar safety 與每個 runtime file，最後才建立 workspace。
10. Loader 成功後，使用 workspace 內已驗證的 `bootstrap/bootstrap_progress.py` 建立 `bootstrap-progress.json`，匯入 early ledger 狀態並記錄 `transport=direct-payload`。
11. pinned seed 或 direct loader transport 不可用時，只有宿主具備 lossless connector-to-local byte handoff 才可使用既有 segmented connector fallback。沒有該能力時，正式循環排程必須依前述 eligibility gate 停在 occurrence 與 discovery 之前，要求改在合格的 desktop/local-project surface 安裝；不得記成 repository materialization failure、不得建立 replacement run，也不得改走 production `mobile-native`。
12. segmented fallback 才逐 block 讀取 chunks，依既有 16-line grouped／8-line fallback 與 SHA-256 契約驗證。每個固定 SHA／固定 line range 使用 one initial attempt plus at most three retries，退避 2、5、10 秒；不得用 connector 搬運未驗證 helper，也不得重啟已驗證部分。
13. loader 成功產生 `bootstrap-workspace.json` 後，才可建立 news checkpoint。下一輪必須重新解析最新 main，不得直接重用本輪 SHA。

Stage -1 loader 可用宿主的 `python3` 執行，因 loader 與 resolver 只依賴標準庫；它不得直接成為新聞 pipeline runtime。Workspace 建立後，若宿主提供的 bundled-runtime Python 絕對路徑可取得，必須優先傳入 `python3 scripts/resolve_bundled_python.py --preferred-python <host-bundled-python>`；否則執行 `python3 scripts/resolve_bundled_python.py`，由 resolver 依環境變數及跨平台 Codex runtime 位置尋找。Resolver 回傳 `status=ready` 前必須實際以候選 executable 匯入 Pillow；以它回傳的同一個 `<bundled-python>` 執行 checkpoint、route fetcher 與本輪所有 canonical Python scripts。不得直接假設 PATH 上的 `python`／`python3` 具有 Pillow，不得把啟動 resolver 的 Python 當成已驗證 runtime；所有候選皆失敗才回報 Stage -1 blocker。Materialized runtime 的 receipt 綁定檔視為唯讀；generated PNG/SVG 可以重建，但 renderer 不得改寫 capsule 內既有的 section metadata 或其他 receipt 綁定檔。

禁止 Stage -1 使用 shell `git clone`、`curl`、`wget`、未固定 SHA 的 URL 或任意 raw GitHub HTTP。唯一例外是已驗證 loader 對上述精確 pinned payload URL 的單次請求；內容仍須完整通過 manifest 驗證。禁止逐 blob 搬完整 repository，也禁止 workspace 失敗後人工直接寫新聞。

若 Stage -1 無法完成，最早 blocker 固定回報為：

`repository materialization / executable workspace acquisition`

此時不得產生 checkpoint、manifest、release receipt 或假讀者版。

所有可控制的成功或失敗結束都必須由 `bootstrap/bootstrap_progress.py` 輸出固定 `RUN_RECEIPT`，至少包含 run id、main SHA、最後完成 stage、chunk／block、last error、retry count、external ledger 與 canonical delivery。GitHub 外部台帳沒有寫入權限或更新失敗時，必須顯示 `external_ledger: unavailable`，但不得因此中止新聞流程。失敗時保留完整本地進度；只有正式讀者版 canonical delivery 成功、最終 receipt 已輸出後才清除本地進度。

若具 GitHub 留言權限，依 `bootstrap/RUN_LEDGER_PROTOCOL.md` 將 issue #3 作為 **best-effort** 外部台帳：每輪使用 **one comment per run_id**，manifest/helper 驗證後更新、之後 **every 8 completed chunks**、全部 chunks、workspace、新聞 stages、失敗與成功時更新同一則 comment。一般新聞階段 **at most once every 3 minutes**，失敗與最終成功立即更新。任何台帳錯誤都改記 `external_ledger: unavailable`，且 **must never block the news pipeline**。

## 必讀 runtime 契約

Stage -1 完成後，至少讀取並遵守：

- `.agents/skills/daily-news-brief/SKILL.md`
- `news-brief-settings.md`
- `news-brief-template.md`
- `user-preferences.example.yaml` 或本輪明確偏好
- `news-source-pool.json`
- `schemas/news-event-manifest.schema.json`
- `schemas/news-candidate-audit.schema.json`
- `scripts/news_run_checkpoint.py`
- `scripts/preprocess_news_candidates.py`
- `scripts/validate_selection_freshness.py`
- `scripts/manage_candidate_audit.py`
- `scripts/recover_news_run.py`
- `scripts/validate_map_decisions.py`
- `scripts/validate_news_brief.py`
- `scripts/check_unique_delivery_gate.py`
- `scripts/publish_news_brief.py`
- select / audit / verify / maps / charts / images / recovery skills 與其 references。

只有格式或示例需求時才讀 `news-brief-examples.md`，不得用 examples 取代正式 schema/settings。

## 本輪唯一 checkpoint

以實際執行時間計算精確 24 小時窗後，建立唯一 `<run-id>`，並初始化唯一 checkpoint：

```bash
<bundled-python> scripts/news_run_checkpoint.py init \
  --output <checkpoint> \
  --run-id <run-id> \
  --window-start <window-start> \
  --window-end <window-end> \
  --bootstrap-receipt <workspace>/bootstrap-workspace.json
```

所有 pre-manifest 狀態都必須沿用同一份 checkpoint；不得失敗後另開 checkpoint 來抹掉前一輪證據。

## 固定 pipeline

依序執行，不得跳關：

1. `source-scan`
   - 必須先調用 `acquire-news-candidates`，依 `news-source-pool.json.discovery_sources` 取得 GDELT、中央社與中新社候選並產生 `work/source-candidates.json`；其餘來源只在評分後作事件驗證。
   - 來源擷取必須以 Stage -1 回傳的 `<bundled-python> scripts/fetch_source_routes.py --route-config source-route-config.json --output-dir <run-work-dir> --window-start <window-start>` 執行；此跨平台 canonical fetcher 保存逐站及已設定分頁的原始 bytes、SHA-256、page chain 與 `source-route-coverage.json`。不得改用 PowerShell web cmdlet、Node `fetch` 或臨時 helper 重試同一批路由。
   - `source-route-config.json` 只定義 GDELT、中央社與中新社三個 discovery routes；`minimum_ready_routes=1`。中新社抓執行日與前一日日索引；中央社依 `NextPageIdx` 翻頁至跨過窗起點或耗盡。GDELT 只有預期 archive 分片全部成功才是 `coverage_complete`，部分成功必須標 `degraded_partial`；archive 不可用時才可發送一次不阻塞的 DOC API 補充請求，最後才使用有效快取。`FULL_DISCOVERY_POOL_UNCAPPED` 要求每個成功 route 的完整窗內清單全部進入去重；`REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE` 要求 regional supplements 全數進模型，GDELT 弱 signal 進 `lightweight_semantic_review` 後仍保留於模型輸入，heat 與關鍵字不得在模型前排除事件。語意合併與六項評分前執行 `validate_local_source_admission.py`，失敗不得繼續。
   - route fetch 完成後必須執行 `scripts/materialize_source_scans.py --checkpoint <checkpoint> --source-pool news-source-pool.json --route-coverage <route-coverage> --output-dir <source-scans-dir> --coverage-output <source-coverage.json>`；只有此 canonical materializer 產生的逐站 scans、terminal proof、完整 ranked_items 與 discovery priority 可進入 candidate audit。不得改用 run 目錄內的臨時 helper。
   - materializer 必須為每條 configured discovery route 產生 source coverage row。`scan_status=completed` 只表示已取得頁面成功物化；coverage 是否完整另由 `coverage_complete`／`coverage_status` 決定。部分來源的已驗證列可繼續入池，失敗來源以 `scan_status=failed`、零 counts 與 `coverage_status=unavailable` 保留；不得在 candidate audit 或 release receipt 洗成完整 coverage。`GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE`：本輪有 fallback／全球板塊時，優先要求 `primary_aggregator` 成功；GDELT 的 archive、一次 DOC 與有效 cache 全部不可用後，必須嘗試受控 `web_fallback`。只有逐筆可重算且固定為 `coverage_complete=false`／`degraded_partial` 的備援候選可繼續，不能用區域補充把世界零筆當成正常完成；primary 與備援都無可核實候選才停在 source-scan。
   - 每個站內海選條目只保存 `discovery_priority_score`、`discovery_signals` 與 `discovery_priority_reason`；這是 discovery 排序提示，不是 `public_value_v2`、`importance_score` 或正式等級。正式 V2 只在語意事件階段產生。
   - 直接 API／RSS／HTML 失敗時先切同站替代入口；只有目前工具契約明確允許時才可用完整瀏覽器渲染並保存 DOM。瀏覽器不得是完成排程的必要依賴，不得用別站冒充該站本輪掃描完成。
   - `TAIWAN_DOMESTIC_COVERAGE_GUARD`：中央社 discovery 另按 `taiwan_coverage_sweeps` 對經濟產業、食藥消費安全、中央政策制度各做最多 `5 results` 的補漏；中央社不可用或明顯過舊時才用網頁搜尋作最後候選備援。任何補漏仍先查重與評分，只有完成獨立驗證且達 C 級才進 selection，之後才開始圖片工作。
2. `preprocess-news-candidates`
3. `select-news-events`
   - 事件與候選映射只能由本輪 `source-candidates.json`／`preprocessed-candidates.json` 建立；不得匯入或執行舊 `work/validation-run-*` 的 selection driver、事件常數或 URL 映射，也不得要求本輪保留已無 fresh URL 的歷史事件編號。
   - 產生 `selection-results.json` 後，必須先執行 `scripts/validate_selection_freshness.py --selection <selection-results> --source-candidates <source-candidates>`。此 gate 必須確認每個事件 URL 都在本輪 fresh pool、所有 C 級以上候選都有有效 `selected_event_id`，且映射事件實際存在；首次失敗即停止，不能刪單筆後重跑掩蓋。
4. `audit-news-candidates`
   - 十四天稽核必須保留完整海選清單及每筆六項大分數；本輪所有 C 級以上候選（含合併項）都必須以 `selected_event_id` 對應到 manifest 與讀者版，不得無聲消失。
   - 最新一輪每個候選必須依 `EVIDENCE_BEFORE_SCORE_GATE` 先建 `evidence_facts` 與 `consequence_evidence`，再以 `dimension_evidence` 引用 fact ID，保存最終 0–100 `importance_breakdown`、`weighted_score`／`importance_score`、`policy_stage`、`delta_facts`、中點／跨維理由、單項及整體 `high_score_challenges`、`evidence_confidence`／`confidence_band`、`grade_status` 與 `local_disaster_review`。死亡、地域或任何單項都不直接指定最終等級；加權總分必須依 `SCORE_TO_GRADE_BANDS_V2` 換算。軍事／衝突事件先做分類與連續性判定，再用本輪新增後果重算六項，不得繼承母事件等級；只有 validated grade 可物化進 manifest／Reader。
5. `materialize-manifest`
   - 完成條件是將本輪 audit 選中事件一對一物化並綁定 checkpoint 的 `manifest` artifact；此處不需要執行 final-manifest validator。
6. `verify-news-events`
   - 將本階段每則事件的 `verification` 結果寫成獨立 patch JSON，並且只使用 `<bundled-python> scripts/apply_event_stage_patch.py --stage verify-news-events --manifest <before-manifest> --patch <verification-patch.json> --output <after-manifest>` 合併；禁止使用 jq 或 shell 字串插值改寫 manifest，避免 `$n`、`$d`、`$e` 等內容被當成 jq 變數而產生空檔。
   - 此階段只能用 `scripts/validate_news_brief.py stage --stage verify-news-events --before <before-manifest> --after <after-manifest>` 檢查欄位所有權；不得在此時執行 final-manifest validator，因地圖、圖表與圖片欄位尚未完成。
7. `build-news-maps`
   - 必須以 Stage -1 已解析、確認含 Pillow 的 bundled Python 執行 `scripts/render_base_maps.py`；不得回退到 PATH Python、不得安裝 matplotlib。執行前後都必須重驗 bootstrap integrity，若任何 receipt 綁定檔改變，該 stage 不得完成。
   - 先執行一次無參數 renderer，確認三個 canonical 底圖 `taiwan-counties-yellow-v2.png`、`china-provinces-yellow-v2.png`、`world-countries-pacific-robinson-yellow-v2.png` 都由本輪 workspace 產生。每個事件先判定 `map.required` 與 `map.claim_critical`；需要地圖時建立 overlay JSON，依行政區精確鍵值著色並提供繁中 `label`，以 `<bundled-python> scripts/render_base_maps.py --overlay-spec <file>` 產生事件圖。非主張關鍵地圖產生失敗時可記為 `omitted` 並繼續文字 reader；主張關鍵地圖仍須 `ready`。
8. `build-news-charts`
9. `collect-news-images`
   - `IMAGE_FALLBACK_EXHAUSTION_GATE` applies before every image blocker. With a writable filesystem and runtime, the Scheduled Task resolves media across original source → official/party → original wire → local reliable media with a local-language query → other reliable same-event publication/reprint, then downloads or screenshots a real image file and delivers the validated local attachment. Only a host without local capability may use native image search as a candidate locator; a serialized ref fails immediately and falls through to a page-image screenshot and the next source. A bare URL is not delivery. Save `original_source_attempted`, `direct_media_url_attempted`, `official_fallback_attempted`, `wire_fallback_attempted`, `reliable_media_fallback_attempted`, `qualified_image_found`, `delivery_attempted`, and `delivery_result`. Text verification and image provenance may use different reliable sources when the image is legal, traceable, and matches the same event/date/person/location.
    - 對已選取且有候選來源圖片的事件，建立包含 `event_id`、`source_page_url`、`source_image_url`、可選 `screenshot_path`、`alt`、`credit` 的 JSON 陣列。可直接下載 `source_image_url`，也可先將文章／官方／可靠轉載頁的同事件圖片區域截成實體檔並以 `screenshot_path` 交給 `<bundled-python> scripts/materialize_news_images.py --input <image-candidates.json> --output-dir <materialized-image-dir> --manifest <materialized-images.json>`；截圖不必等待原圖下載失敗。已有 `status=ready`、可解碼且含 `local_path`、MIME、尺寸與 SHA-256 的 JPEG 時，必須實際嘗試宿主支援的本機附件呈現；不得預判不可交付。
   - 單張下載、解碼或寫檔失敗只影響該事件圖片，不得重跑 discovery、評分、驗證或 reader 文字；保留既有 checkpoint。沒有實際可見附件時，reader 完整省略圖片與圖說，只在內部 evidence 保存原因；需要補圖時只重做圖片交付。
   - 只有 checkpoint 的 `collect-news-images` completed 後，才可第一次執行 `scripts/validate_news_brief.py manifest --input <final-manifest>`；final-manifest validator 不得提前到 verify、map 或 chart 階段。
   - 若執行者誤在圖片階段完成前呼叫該命令，script 會輸出 `DEFERRED` 並以成功狀態返回；這不是 validator 通過，也不得標記整輪失敗。立即繼續原定 pipeline，並在 `collect-news-images` completed 後重新執行到真正輸出 `OK`。
10. `render`
   - `images.status=omitted` 的事件不得在讀者版顯示圖片說明、caption 或占位文字；`images.reader_omission_note` 只屬內部 evidence／receipt。
11. validators / unique delivery gate
12. canonical publisher release
13. canonical receipt delivery

### Checkpoint 防跳關標準

每個 pipeline stage 開始前，必須先以 `news_run_checkpoint.py mark --status running` 記錄；只有前一階段已是 `completed` 才能開始下一階段。完成時必須再次執行 `mark --status completed`，並綁定下列階段產物。不得直接把 `pending` 改成 `completed`，不得使用空 evidence，也不得以無關檔案名稱代替必要產物。

| Stage | completed 必要 artifact 名稱 |
|---|---|
| `source-scan` | `source_candidates`, `relevance_gate`, `model_source_candidates` |
| `preprocess-news-candidates` | `preprocessed_candidates` |
| `select-news-events` | `selection_results` |
| `audit-news-candidates` | `candidate_audit` |
| `materialize-manifest` | `manifest` |
| `verify-news-events` | `manifest` |
| `build-news-maps` | `manifest` |
| `build-news-charts` | `manifest` |
| `collect-news-images` | `manifest` |
| `render` | `brief`, `manifest`（最終 bytes） |

`news_run_checkpoint.py validate` 與 canonical publisher 都必須拒絕順序不合法、未經 `running`、缺少必要 artifact、artifact binding 格式無效或 evidence 狀態不一致的 checkpoint。

來源掃描必須保存站點、快照／證據、SHA-256、時間邊界、翻頁與停止理由。403、登入牆、timeout、解析失敗或單一來源異常不得假裝成功，也不得因此直接整輪放棄；按 skills/settings 做局部恢復與替代來源處理。

Manifest 建立以前，候選與選稿必須有 candidate audit；manifest 建立後，事件內容只能由 manifest 驅動，不得直接從搜尋結果或模型記憶補事件。

每個已選事件都必須經 verify、map decision、chart decision、image decision。地圖、圖表與圖片互相獨立，不能互相替代。capsule 不搬運可重建的 generated basemap PNG/SVG；需要時由 workspace 內 canonical map source/style 與 renderer 重建。

## 恢復

Manifest 前發生中斷或 stage failure：

```bash
<bundled-python> scripts/news_run_checkpoint.py plan --input <checkpoint>
```

只從最早未完成 pre-manifest stage 繼續，不清除已完成且 artifact binding 仍有效的 stage。

Manifest 後發生事件級失敗：

```bash
<bundled-python> scripts/recover_news_run.py plan --input <manifest> --brief <brief>
```

只重跑失敗事件／stage 與必要後續依賴。不得對 `recover_news_run.py` 虛構不存在的 `--checkpoint` 參數。

一般來源、圖片、地圖、圖表、格式與 validator failure 都應先局部恢復；只有無法排除的硬性 execution blocker 才可停止整輪。

## 唯一發布閘門

DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py

Repository 內只有 canonical publisher 可以建立 reader-facing release。其他 script、模型回答、草稿、舊 release、manifest 或中間 renderer stdout 都不是正式交付。

`READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE`：任何「修復紀錄」、429／HTTP 狀態、重試等待、archive 備援、去重效能修正、圖片補救與 checkpoint 重建都只屬內部 run log／audit receipt，不得出現在 canonical reader 或 reader bytes 的對話副本。

`CANONICAL_THREE_PART_READER_LAYOUT_GATE`：canonical reader 必須使用 `news-brief-template.md` 的三段式版型：標題、統計期間、六項評級說明後，依序輸出 `## 今日總覽`、`## 逐條詳報`、`## 後續觀察`。總覽依板塊列出 `編號｜時間｜事件｜等級` 完整清單；逐條詳報依 manifest 順序使用「事件編號. 事件名稱 - 等級」，並保留 `時間／來源／事件細節／分析` 必填欄位，地圖／資料圖表／圖片／各方說法依 manifest 條件式顯示。沒有實際附件時省略對應視覺欄位，不得顯示圖說或占位文字；兩則事件間固定一條 `---`。簡化分區新聞卡不得發布。格式錯誤只重做 reader render。

`CANONICAL_RUN_BUNDLE_GATE`：canonical publisher 成功後，run-logs 的同一 `logs/runs/<run_id>/` 必須持久化可獨立重算的 `candidate-audit.json`（含完整 `article_dispositions`）、`image-evidence/`、`materialized-images.json`、map decisions、checkpoint、counts、event manifest、reader、attachments index、release receipt 與 bundle manifest；每項保存 path、size、SHA-256 與 Git blob SHA。只有上述 bundle 與 canonical release 具有 byte identity，且 `logs/current.json` 原子指向本輪 completed run 後，才可宣稱 GitHub canonical delivery 完成。缺少證據時不得用本機路徑、聊天文字或舊 artifact 代替。

Bundle persistence is executable, not a prose-only obligation. First run `scripts/manage_canonical_run_bundle.py pack` over every required artifact, then run its `verify` command before upload. An artifact larger than the connector-safe limit must use `storage.mode=chunked`; every upload record uses `encoding=base64` and binds raw size, SHA-256, target path, and the expected Git blob SHA. The uploader creates each small blob from its transport file, rejects any returned blob SHA mismatch, and publishes all bundle paths together with `logs/current.json` in one atomic tree/commit. S5 must download and reconstruct chunked artifacts through the same script and prove byte identity before accepting the bundle. Truncation, summaries, placeholder files, and omission of binary evidence are forbidden.

發布前必須：

- 所有 checkpoint required stages = completed；
- candidate audit 與 source-scan 證據有效；
- manifest/schema 有效；
- map decisions、reader brief 與附件 validators 通過；
- 每個 `map.claim_critical=true` 的事件皆為 `map.status=ready` 且至少有一張地圖附件；非關鍵地圖或圖片若省略，已保存後台原因與讀者說明；
- reader 中所有 Markdown 圖片都逐一對應 manifest，位於所屬新聞內，依地圖、資料圖表、來源圖片排序，並由緊接附件的地圖一／資料圖表一／圖一／圖二圖說識別；reader 其他位置不得有圖片；
- unique delivery gate 通過；
- publisher 建立 `release-receipt.json`；
- 交付當下 publisher 再次 revalidate bootstrap binding、checkpoint、manifest、audit、source pool、brief、attachments 與 map decisions。

最後正式輸出只能由以下命令的 stdout 直接交付，不得在 stdout 前後自行添加文字，也不得重新讀取 release 後轉貼。`--conversation-transport` 只把 canonical Markdown 的本機圖片路徑轉成 ChatGPT 可顯示的 `sandbox:` URI；不得改寫 canonical release、receipt、文字、圖說或 SHA-256：

```bash
<bundled-python> scripts/publish_news_brief.py --deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint> --conversation-transport
```

若此命令失敗或 stdout 為空，回到對應 recovery stage；不得改用手工摘要或舊 release 冒充成功。

## 成功與失敗的判定

只有 canonical delivery command 成功輸出 reader bytes，才算本輪每日新聞成功。

下列都不算成功：

- 只完成搜尋或整理；
- 只建立 manifest；
- 只完成 render；
- 只建立 release receipt；
- pipeline 未跑但模型直接寫出看似完整的新聞簡報。

若停止，必須回報**最早不可恢復 blocker**及已完成到哪個 stage，不得把後續未執行階段誤報成故障來源。


## Conditional pre-manifest recovery boundary

`CONDITIONAL_RECOVERY_BUNDLE_POLICY`

After `preprocess-news-candidates` completes, record each artifact's local hash in the checkpoint. `FIRST_SELECT_NEWS_EVENTS_EXECUTION` may start immediately when the workspace is durable and the local hash/checkpoint binding validates. Do not make a remote recovery bundle a routine selection gate.

Create and verify the recovery bundle only for a real `cross-host handoff`, an `ephemeral workspace`, or an approaching `warning or timeout boundary`:

```powershell
python scripts/manage_canonical_run_bundle.py pack-recovery --run-id <run-id> --checkpoint <checkpoint> --source-candidates <source-candidates> --relevance-gate <relevance-gate> --admitted-candidates <model-source-candidates> --preprocessed-candidates <preprocessed-candidates> --batch-index <content-hydration-batches> --transport-dir <transport-dir> --manifest <recovery-bundle-manifest>
python scripts/manage_canonical_run_bundle.py verify --manifest <recovery-bundle-manifest> --transport-dir <transport-dir>
python scripts/manage_canonical_run_bundle.py restore --manifest <recovery-bundle-manifest> --transport-dir <transport-dir> --output-dir <restore-proof-dir>
```

The optional bundle contains these six logical artifacts:

- `recovery/checkpoint.json`
- `recovery/source-candidates.json`
- `recovery/news-relevance-gate.json`
- `recovery/model-source-candidates.json`
- `recovery/preprocessed-candidates.json`
- `recovery/content-hydration-batches.json`

If a handoff or workspace loss occurs, `restore` these artifacts from the same run's verified bundle and resume only the first incomplete batch. Never create a replacement run to conceal missing recovery inputs. Bundle creation failure is blocking only when the declared handoff or workspace-risk condition makes that bundle necessary.



