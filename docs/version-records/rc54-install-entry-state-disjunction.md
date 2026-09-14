# rc.54 Install Entry-State Disjunction / 安裝入口狀態互斥

## Creation reason / 建立原因

- EN: A conflict audit found that fresh installation text unconditionally required authoritative inventory while exact-ID context recovery prohibited another inventory.
- 中文：衝突專項審核發現，全新安裝文字無條件要求 authoritative inventory，但 exact-ID 上下文恢復又禁止重新 inventory。
- EN: The prompt gate also called prompt submission the first control-plane step, conflicting with the inventory-before-mutation rule.
- 中文：prompt gate 另把 prompt 提交稱為第一個控制面步驟，與 mutation 前先 inventory 的規則衝突。

## Implementation / 實作方式

- EN: Split the control-plane entry into three mutually exclusive states: `new_without_exact_id`, `known_exact_id_resume`, and `create_outcome_unknown`.
- 中文：將控制面入口拆成三個互斥狀態：`new_without_exact_id`、`known_exact_id_resume`、`create_outcome_unknown`。
- EN: Defined prompt submission as the first mutation after entry-state resolution, followed by smoke validation.
- 中文：明定 prompt 提交是入口狀態解析後的第一個 mutation，之後才進行 smoke 驗證。
- EN: Aligned INSTALL, README, the paste-ready mobile starter, and the runtime contract. No Scheduled Task was mutated.
- 中文：同步 INSTALL、README、可貼入的 mobile starter 與 runtime contract；未修改任何 Scheduled Task。

## Changed entry points / 修改入口

- `INSTALL.md`
- `README.md`
- `mobile-chatgpt-start-prompt.md`
- `daily-schedule-prompt.md`
- `tests/test_schedule_prompt_control_plane.py`

## Validation / 驗證

- EN: The new regression test was observed failing before the documentation change, then the full schedule-control test module passed 22/22.
- 中文：新回歸測試已先觀察到修正前失敗；修改後排程控制面測試模組 22/22 通過。

## Result and next decision / 結果與下一步

- EN: Candidate fix is ready for full repository and final-state audit. Promotion is not claimed until those independent checks pass.
- 中文：候選修正已可進入完整 repository 與 final-state audit；在獨立檢查通過前不宣稱可發布。
