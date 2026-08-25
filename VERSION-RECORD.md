# Version Record / 版本紀錄

This file records the current installable contract. Earlier implementation attempts remain available through Git history so retired behavior cannot leak into the runtime repository surface.

本檔只記錄目前可安裝契約；較早的實作嘗試由 Git history 保存，避免退役行為繼續留在執行中的 repository 表面。

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
