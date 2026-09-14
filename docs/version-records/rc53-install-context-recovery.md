# rc.53 安裝上下文恢復 / Install Context Recovery

- 建立原因 / Reason: A real singleton update retained the pinned SHA and exact task ID, but context compaction caused the installer to stop because prior readback output and canonical prompt bytes were no longer in active model memory.
- 實作方法 / Approach: Treat immutable repository content plus exact-ID control-plane state as recovery authorities. Reconstruct the prompt and fingerprint from the already pinned SHA, then repeat read-only exact-ID verification without rerunning inventory, creating another task, changing `main`, or using missing output as authority to update.
- 變更入口 / Changed entry points: `INSTALL.md`, `README.md`, `mobile-chatgpt-start-prompt.md`, and `tests/test_schedule_prompt_control_plane.py`.
- 重要參數 / Important parameters: frozen immutable SHA; previously acquired exact task ID; unchanged region and monitor substitutions; exact-ID `saved prompt`, `enabled`, `timezone`, `next_run_time`, and current-conversation binding.
- 驗證方法 / Validation: TDD red/green contract test, focused schedule/install suites, complete repository suite, capsule regeneration/verification, tracked-only clean export, GitHub Actions, and two final-state audit cycles.
- 目前結果 / Current result: Implementation candidate; final result is recorded after independent verification and publication.
- 下一決策 / Next decision: Automatically repair any independently observed in-scope defect; otherwise keep the real formal task untouched until a separately authorized live control-plane validation.
- Git 身分 / Git identity: Starts from `a234fd556a0fe17123d6f9b84f8ede2da18c12d2`; final source and capsule identities are filled by Git history and the final audit receipt.
- 回復來源 / Rollback source: Parent commit `a234fd556a0fe17123d6f9b84f8ede2da18c12d2` and a reversible Git diff.
