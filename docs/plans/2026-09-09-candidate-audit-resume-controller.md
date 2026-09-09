# Candidate-Audit Resume Controller / 候選稽核續跑控制器

## Problem / 問題

A live Scheduled Task prepared 877 immutable audit rows and 44 bounded model-input batches, then treated the remaining semantic review workload as an unrecoverable blocker. The repository already stores append-only row-review and event-score checkpoints, but it does not expose one deterministic, run-bound answer to “what is the next legal operation?”. Different issue comments are also allowed to run concurrently, so a multi-batch occurrence can race while committing to `run-logs`.

實跑排程已準備 877 筆不可變 audit rows 與 44 個有界模型批次，卻把尚待完成的語意審查工作量誤判為不可恢復 blocker。repository 已有 append-only row-review 與 event-score checkpoints，但缺少綁定 run、可確定回答「下一個合法操作是什麼」的單一控制面；不同 issue comments 亦可能並行寫入 `run-logs`，使多批次 occurrence 發生提交競態。

## Design / 設計

1. Add a read/derive `candidate_audit_progress` function to the existing transport. It validates immutable audit input and every existing checkpoint, rejects checkpoint gaps or identity/hash/conservation drift, and returns exactly one phase and next operation.
2. Add a zero-payload `candidate_audit_status` bridge operation. Persist its derived projection at `candidate-audit-work/progress.json`; refresh the same projection after every candidate-audit mutation. Checkpoint files remain append-only; the progress file is explicitly a replaceable derived view.
3. Serialize the GitHub issue-comment workflow by issue number, not comment ID, so review/score/finalize operations cannot race each other on `run-logs`.
4. Add `PENDING_CANDIDATE_AUDIT_WORK_IS_NOT_BLOCKER_GATE` to the active Scheduled Task, mobile, install, selection, audit, and orchestration authorities. Pending batch count, row count, elapsed model work, context size, or token concern is ordinary in-progress work. The occurrence must query status, process exactly the returned next unit, wait for its durable commit, and repeat. It must not disable the task, emit a blocker receipt, rescan sources, or create a replacement run for pending work alone.
5. Preserve all publication gates. No heuristic filtering, top-N reduction, synthetic model result, skipped row, or relaxed Public Value validation is introduced.

1. 在既有 transport 新增唯讀推導的 `candidate_audit_progress`，驗證不可變 audit input 與所有既有 checkpoint，拒絕 checkpoint 缺口及身分／雜湊／守恆漂移，並只回傳一個 phase 與下一操作。
2. 新增零 payload 的 `candidate_audit_status` bridge operation，將推導結果保存至 `candidate-audit-work/progress.json`，每次 candidate-audit 寫入後同步刷新。checkpoint 維持 append-only；progress 明確定義為可替換的衍生 view。
3. GitHub issue-comment workflow 改以 issue number 串行，而非 comment ID，避免 review／score／finalize 同時競寫 `run-logs`。
4. 在現行 Scheduled Task、mobile、install、selection、audit 與 orchestration authority 加入 `PENDING_CANDIDATE_AUDIT_WORK_IS_NOT_BLOCKER_GATE`。待處理批次數、row 數、已耗模型工時、context 大小或 token 顧慮都只是正常進行中工作；occurrence 必須查 status、處理唯一 next unit、等待 durable commit 後重複。不得只因 pending work 停用 task、輸出 blocker receipt、重掃來源或另開 run。
5. 所有發布 gate 保持不變；不加入 heuristic 篩選、top-N、偽造模型結果、漏列或放寬 Public Value 驗證。

## Acceptance / 驗收

- Empty work returns row-review batch 1 with exact path and SHA-256.
- Completed row-review batches advance to the first missing sequence; gaps are rejected.
- Complete row review advances to scoring preparation, then the first missing score batch, then finalize, then completed.
- Every returned projection preserves run/main/window identity and exact completed/remaining counts.
- Workflow concurrency is issue-scoped.
- Active contracts explicitly prohibit treating pending candidate-audit work as a blocker or disabling the task for that reason.
- Focused tests, full suite, rebuilt capsule verification, CI, source binding, and two unchanged-fingerprint final-state audits pass before release.

- 空白 work 必須回傳 row-review batch 1 及精確路徑／SHA-256。
- 已完成 row-review 後前進至第一個缺少序號；存在 gap 必須拒絕。
- row review 完整後依序前進 scoring preparation、第一個缺少的 score batch、finalize、completed。
- 每個 projection 保留 run／main／window 身分與精確完成／剩餘數。
- workflow concurrency 綁定 issue。
- 現行契約明文禁止把 pending candidate-audit 工作當 blocker 或因此停用 task。
- 發布前通過 focused、full suite、重建 capsule、CI、source binding 與兩輪相同 fingerprint final-state audit。
