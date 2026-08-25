# Version Record / 版本紀錄

This file records the current installable contract. Earlier implementation attempts remain available through Git history so retired behavior cannot leak into the runtime repository surface.

本檔只記錄目前可安裝契約；較早的實作嘗試由 Git history 保存，避免退役行為繼續留在執行中的 repository 表面。

## v0.5.6 — Event-type floor and install CLI removal / 事件類型保底與安裝指令缺口清除

- Reason / 建立原因：A reverse contract audit found active prose that assigned a minimum final grade to named industry events and referred to a rank-30 overflow exception even though the current pool is uncapped. A separate executable-document audit found that `INSTALL.md` described publisher outputs without showing the actual creation and delivery CLI. / 反向契約稽核發現，正式文件仍對具名產業事件指定最低總等級，並在完整不截斷入池規則下提到排名 30 之外的例外；另一項文件可執行性稽核則發現 `INSTALL.md` 只描述 publisher 產物，沒有列出實際建立與交付 CLI。
- Approach / 作法：Remove rank cutoffs and event-type grade floors from the settings and selection skill; require all such events to use evidence facts, fourteen-day material delta, and the six weighted dimensions. Document the exact publisher, bundle verification/restoration, and conversation-delivery commands. / 從設定與選稿技能移除排名截斷及事件類型保底；所有此類事件一律使用 evidence facts、十四天實質增量及六項加權評分。於 INSTALL 明列 publisher、bundle 驗證／還原與對話交付的實際命令。
- Entry points / 入口：`news-brief-settings.md`, `.agents/skills/select-news-events/SKILL.md`, `INSTALL.md`, obsolete-contract guards, pipeline-contract tests, and this version record. / 新聞設定、選稿技能、INSTALL、淘汰契約 guard、pipeline 契約測試及本版本紀錄。
- Important configuration / 重要設定：`news-source-pool.json.ranking` remains the sole scoring authority; no event name, type, discovery rank, or single dimension may set a final grade. `publish_news_brief.py` has flags rather than a `release` subcommand. / `news-source-pool.json.ranking` 仍是唯一評分權威；事件名稱、類型、discovery 名次或單一維度都不得指定最終等級。`publish_news_brief.py` 使用參數，沒有 `release` 子命令。
- Validation / 驗證：The new guards first failed on seven active hard-grade/rank phrases, and the INSTALL CLI test first failed on the missing command. Promotion requires a fresh complete regression, semantic scan, rebuilt capsule, GitHub workflow, and clean remote export. / 新 guard 先因七處正式硬式等級／名次敘述失敗，INSTALL CLI 測試也先因缺少命令而失敗；晉升仍須重新完成完整回歸、語義掃描、capsule 重建、GitHub workflow 與遠端乾淨匯出。
- Result / 結果：Candidate prepared for fresh verification; no completion claim is made yet. / 候選版本已準備重新驗證，目前尚未宣告完成。
- Rollback / 回復：Use the immediately preceding Git commit. / 使用前一個 Git commit。

## v0.5.5 — Migration and hard-grade residue removal / 遷移與硬式等級殘留清除

- Reason / 建立原因：A new independent version-marker and semantic-scale audit found an active V1-named count receipt, a CI migration script already superseded by the checked-in checkpoint contract, and examples/design files that still mapped casualty bands directly to final grades. / 全新版本標記與語義尺度稽核發現，正式 count receipt 仍帶 V1 名稱、CI 仍執行已被現行 checkpoint 契約取代的 migration script，且範例／設計檔仍把傷亡區間直接映射成最終等級。
- Approach / 作法：Use the versionless current marker `PIPELINE_COUNT_RECEIPT`; build the capsule directly from checked-in source; remove the obsolete migration program and stale design surfaces; rewrite disaster examples so casualties set only the `public_impact` floor and every final grade comes from the six weighted dimensions. / 使用無版本的現行標記 `PIPELINE_COUNT_RECEIPT`；直接由已提交 source 建立 capsule；移除過期 migration 程式與設計表面；重寫災害範例，使傷亡只設定 `public_impact` floor，最終等級一律來自六項加權。
- Entry points / 入口：`INSTALL.md`, both execution prompts, audit skill, `news-brief-examples.md`, capsule workflow, obsolete-contract tests, and pipeline-contract tests. / `INSTALL.md`、兩份執行 prompt、audit skill、新聞範例、capsule workflow、淘汰契約測試與 pipeline 契約測試。
- Important configuration / 重要設定：`canonical-run-bundle-v1` remains the current validated wire-format identifier; it is not a fallback branch. Checkpoint bootstrap schema remains `1.1.0`; CI may verify it but no longer rewrites it. / `canonical-run-bundle-v1` 保留為目前受驗證的 wire-format 識別值，並非 fallback 分支；checkpoint bootstrap schema 維持 `1.1.0`，CI 只驗證而不再重寫。
- Validation / 驗證：The new guards must fail on the old marker, migration path, direct casualty-to-grade prose, and full-runtime-only mobile completion claim, then pass after removal; complete clean-export regression and remote capsule binding remain required. / 新 guard 必須先因舊標記、migration 路徑、傷亡直接映射總等級及 full-runtime-only mobile completion 敘述而失敗，清除後再通過；仍須完成乾淨匯出完整回歸與遠端 capsule 綁定。
- Result / 結果：Candidate prepared for fresh verification; no promotion claim is made until the new source tree and generated capsule pass. / 候選版本已準備重新驗證；新 source tree 與產生的 capsule 通過前不宣告晉升。
- Rollback / 回復：Use the immediately preceding Git commit. / 使用前一個 Git commit。

## v0.5.4 — Current names and current-only run logs / 現行命名與僅接受現行 run log

- Reason / 建立原因：A fresh semantic inventory found that the only canonical reader layout still used retired identifiers and the mobile ledger still migrated retired schemas through an obsolete completion state. / 全新語義盤點發現，唯一正式 reader 版型仍使用退役識別字，mobile ledger 仍透過過期的完成狀態遷移已退役 schema。
- Approach / 作法：Rename the reader gate, validator, test fixture, and CLI choice to `canonical-sectioned`; reject non-current mobile run-log schemas; remove the retired durable-audit state and stale compatibility plans. / 將 reader gate、validator、測試 fixture 與 CLI 選項改為 `canonical-sectioned`；拒絕非現行 mobile run-log schema；移除退役的 durable-audit 狀態與過期相容計畫。
- Entry points / 入口：`INSTALL.md`, `.agents/skills/collect-news-images/SKILL.md`, `daily-schedule-prompt.md`, `mobile-chatgpt-daily-prompt.md`, `news-brief-template.md`, `scripts/validate_news_brief.py`, `scripts/manage_mobile_run_log.py`, `schemas/mobile-run-log.schema.json`, and regression tests. / `INSTALL.md`、圖片技能、兩份執行 prompt、reader template、兩個執行 script、mobile schema 與回歸測試。
- Important configuration / 重要設定：The sole reader layout identifier is `canonical-sectioned`; accepted durable-audit statuses are `not_started`, `updated`, `preserved_merge_deferred`, and `current_run_only`; run-log schema remains `1.3.0`. / 唯一 reader 版型識別字為 `canonical-sectioned`；durable-audit 僅接受四個現行狀態；run-log schema 維持 `1.3.0`。
- Validation / 驗證：Focused tests must first fail on the retired identifiers and schema migration, then pass after removal. Promotion additionally requires four consecutive independent checks from the same final tree. / 針對性測試必須先因退役識別字與 schema 遷移而失敗，移除後才通過；晉升另須同一最終檔案樹連續通過四種獨立檢查。
- Result / 結果：The candidate now uses current-only executable names and rejects retired run-log shapes; it is not promoted until all four independent checks pass without another finding. / 候選版本已只使用現行可執行名稱並拒絕退役 run-log 形狀；四種獨立檢查未連續全數通過前不晉升。
- Next decision / 下一步：Any new finding resets the counter to 0/4; otherwise publish the verified tree and its rebuilt capsule to `main`. / 任一新發現即歸零為 0/4；否則將已驗證檔案樹與重建 capsule 發布至 `main`。
- Rollback / 回復：Use the immediately preceding Git commit. / 使用前一個 Git commit。

## v0.5.3 — Semantic compatibility hardening / 語義相容殘留強化清除

- Reason / 建立原因：A fresh semantic audit found that exact-token scans could miss abbreviated migration prose, a noncanonical preprocessing alias, and a rule marker omitted from the installation entry. / 全新語義稽核發現，精確字串掃描可能漏掉縮寫的遷移敘述、非 canonical 的 preprocess 輸入別名，以及安裝入口遺漏的規則標記。
- Approach / 作法：Require canonical `items` input, name the uncapped discovery contract in `INSTALL.md`, remove obsolete migration design surfaces, and use neutral current-contract identifiers in the audit validator. / 強制使用 canonical `items` 輸入、在 `INSTALL.md` 明列完整入池契約、移除過期遷移設計表面，並在 audit validator 使用中性的現行契約識別名稱。
- Validation / 驗證：Four independent post-change checks are mandatory: semantic residue inventory, authority-document crosswalk, white-box adversarial data flow, and remote clean-room regression with capsule binding. / 修改後必須通過四種獨立檢查：語義殘留盤點、權威文件交叉對表、白箱對抗資料流，以及含 capsule 綁定的遠端乾淨環境回歸。
- Result / 結果：Promoted only when all four checks pass consecutively on the same final source state. / 僅在同一最終 source 狀態連續通過四種檢查後晉升。
- Rollback / 回復：Use the immediately preceding Git commit. / 使用前一個 Git commit。

## v0.5.2 — Current-contract residue removal / 現行契約殘留清除

- Reason / 建立原因：Disabled compatibility fields and historical runtime branches could still preserve retired behavior even when ordinary happy-path tests passed. / 停用的相容欄位與歷史執行分支，即使一般成功路徑測試通過，仍可能保留退役行為。
- Approach / 作法：Keep only the three configured discovery routes, require the current normalized scoring schema for every retained run, reject unknown source-coverage fields, and make verification evidence selection depend on event and claim roles. / 僅保留三條已設定的 discovery routes；所有保留 run 一律使用目前的正規化評分 schema；拒絕未知的 source-coverage 欄位；驗證證據依事件與主張角色選取。
- Entry points / 入口：`INSTALL.md`, scheduling prompts, candidate-audit schema and validator, source materializers, skills, and regression tests. / `INSTALL.md`、排程提示、候選稽核 schema 與驗證器、來源 materializer、技能及回歸測試。
- Validation / 驗證：Three consecutive post-change audits are required: repository-wide semantic review, white-box data-flow and adversarial validation, then clean-export full regression plus remote-main verification. Any finding resets the count. / 修改後必須連續通過三次檢查：全庫語義檢查、白箱資料流與對抗驗證、乾淨匯出完整回歸及遠端 main 核驗；任一次發現問題即歸零重算。
- Result / 結果：Promoted after three consecutive independent checks covering repository semantics, executable data flow, clean-room regression, capsule integrity, and remote-main binding. / 已在全庫語義、可執行資料流、乾淨環境回歸、capsule 完整性及遠端 main 綁定連續通過三次獨立檢查後晉升。
- Rollback / 回復：Use the immediately preceding Git commit. / 使用前一個 Git commit。

## v0.5.1 — Public-value evidence binding / 公共價值證據綁定

- Reason / 建立原因：Dimension scores required enforceable semantic links to realized evidence. / 六項分數需要可由程式強制的現況證據語義連結。
- Approach / 作法：Use six normalized 0–100 dimensions, configured weights, realized-versus-potential consequence classes, policy stage, material delta, fact reuse rationale, high-score challenge, evidence confidence, and validated-only publication. / 採六項 0–100 正規化分數、設定權重、現況與潛在後果分類、政策階段、實質增量、事實重用理由、高分反向審查、證據信心及僅發布 validated grade。
- Validation / 驗證：Schema, validator, calibrated fixtures, publisher checks, and full regression. / Schema、驗證器、校準 fixtures、發布檢查及完整回歸。
- Result / 結果：Promoted into the current contract. / 已納入目前契約。
