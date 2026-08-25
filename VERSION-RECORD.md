# Version Record / 版本紀錄

This file records the current installable contract. Earlier implementation attempts remain available through Git history so retired behavior cannot leak into the runtime repository surface.

本檔只記錄目前可安裝契約；較早的實作嘗試由 Git history 保存，避免退役行為繼續留在執行中的 repository 表面。

## v0.5.4 — Current names and current-only run logs / 現行命名與僅接受現行 run log

- Reason / 建立原因：A fresh semantic inventory found that the only canonical reader layout still used `legacy-*` identifiers and the mobile ledger still migrated retired schemas through `legacy_completed`. / 全新語義盤點發現，唯一正式 reader 版型仍使用 `legacy-*` 識別字，mobile ledger 仍透過 `legacy_completed` 遷移已退役 schema。
- Approach / 作法：Rename the reader gate, validator, test fixture, and CLI choice to `canonical-sectioned`; reject non-current mobile run-log schemas; remove the retired durable-audit state and stale compatibility plans. / 將 reader gate、validator、測試 fixture 與 CLI 選項改為 `canonical-sectioned`；拒絕非現行 mobile run-log schema；移除退役的 durable-audit 狀態與過期相容計畫。
- Entry points / 入口：`daily-schedule-prompt.md`, `mobile-chatgpt-daily-prompt.md`, `news-brief-template.md`, `scripts/validate_news_brief.py`, `scripts/manage_mobile_run_log.py`, `schemas/mobile-run-log.schema.json`, and regression tests. / `daily-schedule-prompt.md`、`mobile-chatgpt-daily-prompt.md`、`news-brief-template.md`、兩個執行 script、mobile schema 與回歸測試。
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
