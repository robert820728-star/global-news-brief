# rc.58 GDELT Article Hydration Boundary / GDELT 文章補齊邊界

## Creation reason / 建立原因

- EN: GDELT is an aggregator whose candidate URLs identify external original publishers, but the canonical hydrator treated `gdelt` as a configured publisher domain and rejected every external article before network access.
- 中文：GDELT 是聚合來源，候選網址指向外部原始發布站；canonical hydrator 卻把 `gdelt` 當成固定發布網域，導致所有外部文章在連線前即被拒絕。

## Implementation / 實作方式

- EN: Allow GDELT and verified `web_fallback` rows to hydrate public HTTPS canonical article URLs while binding each row to the canonical hostname.
- 中文：允許 GDELT 與已驗證的 `web_fallback` 列補齊 public HTTPS canonical article，同時逐列鎖定 canonical hostname。
- EN: Reject recovery overrides and HTTP redirects that leave the verified canonical article host. Keep CNA and China News Service restricted to their configured source domains.
- 中文：拒絕離開已驗證 canonical article host 的恢復 override 與 HTTP redirect；中央社與中新社仍限定於各自 configured source domain。

## Changed entry points / 修改入口

- `scripts/hydrate_source_rows.py`
- `scripts/remote_acquisition_bridge_v2.py`
- `tests/test_hydration_recovery_contract.py`
- `INSTALL.md`
- `scheduled-task-prompt-template.md`
- `daily-schedule-prompt.md`
- `mobile-chatgpt-daily-prompt.md`
- `.agents/skills/acquire-news-candidates/SKILL.md`
- `.agents/skills/select-news-events/SKILL.md`
- `.agents/skills/daily-news-brief/SKILL.md`

## Parameters and rollback / 參數與回復來源

- EN: The verified-host comparison uses the normalized exact hostname. Public HTTPS, no credentials, and the existing default-port/private-address restrictions remain enforced.
- 中文：verified-host 比對使用正規化後的精確 hostname；public HTTPS、不得含憑證資訊，以及既有預設連接埠／私有位址限制均保留。
- EN: Rollback sources are source commit `38fbfb5fc60ba353d7aa914eb7f23d89237a6fe0`, verified remote capsule main `d6b6bb8670e670559d32a5c0a255d659671becd1`, and the reversible branch diff.
- 中文：回復來源為 source commit `38fbfb5fc60ba353d7aa914eb7f23d89237a6fe0`、已驗證 remote capsule main `d6b6bb8670e670559d32a5c0a255d659671becd1`，以及可逆分支差異。

## Validation / 驗證

- EN: Four frozen behaviors cover external GDELT hydration, cross-host redirect rejection, cross-host override rejection at both bridge and hydrator boundaries, and unchanged CNA isolation. The first RED run produced 3 failures and 1 existing-protection pass; the GREEN run passed all 15 tests in the module.
- 中文：固定四項行為涵蓋 GDELT 外站補齊、跨 host redirect 拒絕、bridge 與 hydrator 的跨 host override 拒絕，以及 CNA 邊界不變。第一次 RED 為 3 個失敗、1 個既有保護通過；GREEN 後該模組 15/15 通過。
- EN: Focused hydration, fallback, bridge, pipeline-contract, and obsolete-contract suites pass 141/141. Complete-suite and capsule results are recorded after capsule regeneration.
- 中文：hydration、fallback、bridge、pipeline-contract 與 obsolete-contract focused suites 合計 141/141 通過；完整套件與 capsule 結果待重建後記錄。

## Result and next decision / 結果與下一步

- EN: Repository verification is still in progress. The locked historical run cannot change its pinned SHA; a later genuine occurrence must exercise the repaired main. The formal daily 06:00 Scheduled Task is not modified by this repository change.
- 中文：repository 驗證仍在進行。已鎖定的歷史 run 不可更換 pinned SHA；後續真實 occurrence 才能使用修正版 main。此次 repository 修改不會變更正式每日 06:00 Scheduled Task。
