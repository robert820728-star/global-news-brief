# rc.55 Usable-First Schedule Install / 可用優先排程安裝

## Creation reason / 建立原因

- EN: The installation contract had accumulated contradictory gates: a successful canonical create/update could still be reversed by unavailable saved-prompt readback, next-run metadata, or visible-media smoke.
- 中文：安裝契約累積了互相衝突的閘門：canonical create／update 即使成功，仍可能因 saved-prompt readback、next-run metadata 或 visible-media smoke 無法取得而被反向判定失敗。
- EN: Paste-ready starters duplicated the internal control-plane state machine and became stale whenever INSTALL changed.
- 中文：可貼入 starter 重複內嵌控制面狀態機，INSTALL 一更新就容易產生過期衝突。

## Implementation / 實作方式

- EN: Added `USABLE_FIRST_SCHEDULE_INSTALL_GATE`: one canonical mutation submits the complete prompt, daily 06:00 schedule, account timezone, current-conversation delivery, and `enabled=true`; an acknowledged exact task ID is the usable installation boundary.
- 中文：新增 `USABLE_FIRST_SCHEDULE_INSTALL_GATE`：單一 canonical mutation 同時提交完整 prompt、每日 06:00、帳號時區、目前對話 delivery 與 `enabled=true`；控制面成功回傳 exact task ID 即為可用安裝邊界。
- EN: Added `POST_INSTALL_DIAGNOSTICS_GATE`: saved-prompt/timezone/next-run readback and visible-media smoke remain evidence-producing diagnostics, but missing or truncated evidence is `verification_partial` and cannot pause, disable, delete, recreate, or duplicate the formal task.
- 中文：新增 `POST_INSTALL_DIAGNOSTICS_GATE`：saved-prompt／timezone／next-run readback 與 visible-media smoke 保留為證據診斷，但缺失或截斷只記為 `verification_partial`，不得暫停、停用、刪除、重建或另建正式 task。
- EN: Kept strict visible-media gates for real news occurrences while removing installation-smoke dependency from runtime capability routing.
- 中文：真正新聞 occurrence 仍保留嚴格可見媒體閘門，但 runtime capability routing 不再依賴安裝 smoke。
- EN: Shortened the user starter to delegate internal state-machine details to fresh `INSTALL.md` while preserving singleton intent and full canonical saved prompt requirements.
- 中文：縮短使用者 starter，將內部狀態機交由 fresh `INSTALL.md` 管理，同時保留 singleton 意圖與完整 canonical saved prompt 要求。

## Changed entry points / 修改入口

- `INSTALL.md`
- `README.md`
- `daily-schedule-prompt.md`
- `mobile-chatgpt-start-prompt.md`
- `scheduled-task-prompt-template.md`
- `tests/test_schedule_prompt_control_plane.py`
- `tests/test_pipeline_contract.py`
- `docs/superpowers/specs/2026-09-15-usable-first-schedule-install-design.md`
- `docs/superpowers/plans/2026-09-15-usable-first-schedule-install.md`

## Parameters and rollback / 參數與回復來源

- EN: Formal schedule remains daily 06:00 in the account timezone with current-conversation delivery; this repository change does not mutate the live Scheduled Task.
- 中文：正式排程仍為帳號時區每日 06:00 並回覆目前對話；本次 repository 修改不會操作線上 Scheduled Task。
- EN: Rollback source is main commit `1e90094339518b6dbb6411181b7517d796c676be` plus the reversible branch diff.
- 中文：回復來源為 main commit `1e90094339518b6dbb6411181b7517d796c676be` 與可逆的分支差異。

## Validation / 驗證

- EN: New schedule-control tests were observed failing before the contract edits. After repair, schedule-control, pipeline-contract, and fault-penetration suites pass 124/124.
- 中文：新的排程控制面測試已先觀察到修正前失敗；修正後 schedule-control、pipeline-contract 與 fault-penetration 測試合計 124/124 通過。
- EN: Reverse-contract searches found and removed a late lifecycle clause that still allowed pausing a smoke-failed candidate.
- 中文：反向契約搜尋找到並移除一條仍允許因 smoke 失敗暫停 candidate 的漏網 lifecycle 規則。

## Result and next decision / 結果與下一步

- EN: Repository subgate remains a candidate pending the complete suite, capsule verification, clean-export checks, remote CI, and two unchanged-state audit cycles. The live ChatGPT task control plane remains outside this repository-only mutation.
- 中文：repository 子閘門目前仍是候選，需完成完整測試、capsule、clean export、remote CI 與兩輪不變狀態 audit；線上 ChatGPT task 控制面不在本次 repository 修改範圍內。
