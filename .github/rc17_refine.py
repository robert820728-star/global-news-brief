from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), newline


def save(path, text, newline):
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    (ROOT / path).write_bytes(text.encode("utf-8"))


def replace_once(path, old, new):
    text, nl = load(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one refinement target, found {count}: {old[:120]!r}")
    save(path, text.replace(old, new, 1), nl)


install = "INSTALL.md"
replace_once(
    install,
    '''| -1 fresh main 與 bootstrap | `bootstrap-workspace.md`、雙端點 current main、fresh nonce；full-runtime 另讀 capsule manifest／payload | full-runtime 產生經 blob SHA、payload SHA-256、runtime fingerprint 驗證的 workspace 與 `bootstrap-receipt.json`；mobile-native 只固定 fresh main 並使用既有 occurrence ledger，不冒充 capsule 已物化 | full-runtime receipt 未通過前不得建立 news checkpoint；mobile-native 不執行 unavailable bootstrap，而由同一 `scheduled_for`／`run_id` 接續 |''',
    '''| -1 fresh main 與 bootstrap | `bootstrap-workspace.md`、雙端點 current main、fresh nonce；full-runtime 另讀 capsule manifest／payload | 先完成 capability routing；full-runtime 產生經 blob SHA、payload SHA-256、runtime fingerprint 驗證的 workspace 與 `bootstrap-receipt.json`；mobile-native 在 actual task trigger 後建立／接續該 `scheduled_for` 的 occurrence ledger，不冒充 capsule 已物化 | full-runtime receipt 未通過前不得建立 news checkpoint；mobile-native 不執行 unavailable bootstrap，只從同一 actual occurrence 的 first incomplete stage 接續 |''',
)
replace_once(
    install,
    '''| 0 checkpoint init | run id、精確 24 小時窗；full-runtime 另需 bootstrap receipt | full-runtime 執行 canonical checkpoint CLI：`<bundled-python> scripts/news_run_checkpoint.py init ...`；mobile-native 沿用既有 occurrence ledger 的 `logs/current.json` 保存 run id、窗、main 與 first incomplete stage | 兩種模式都綁定同一輪 main 與時間窗；mobile-native 不宣稱執行 `news_run_checkpoint.py` |''',
    '''| 0 checkpoint init | run id、精確 24 小時窗；full-runtime 另需 bootstrap receipt | full-runtime 執行 canonical checkpoint CLI：`<bundled-python> scripts/news_run_checkpoint.py init ...`；mobile-native 在 capability routing 選定後建立或 resume `logs/current.json`，保存 run id、窗、main 與 first incomplete stage | 兩種模式都綁定同一輪 main 與時間窗；mobile-native 不宣稱執行 `news_run_checkpoint.py` |''',
)
replace_once(
    install,
    '''`SCHEDULED_OCCURRENCE_SINGLE_RUN_GATE`：mobile ledger 以 `scheduled_for` 作 occurrence key。同一 occurrence 的 `current.json` 只要存在，就沿用原 `run_id` 並從 first incomplete stage 接續；即使 reader 已保存但尚未 `delivery-handoff`，也不得 rotate、建立 replacement run 或重跑新聞階段。已進入 `executor-started` 或之後的 occurrence 仍只有 `scheduled_for` 嚴格較晚的下一個真實 occurrence 才可 rotate，且非 terminal 前輪才標為 `interrupted_by_next_run`。同一 run 只能留在原 stage 或前進至緊鄰的下一 stage，不得跳級，也不得執行 stage regression。''',
    '''`SCHEDULED_OCCURRENCE_SINGLE_RUN_GATE`：mobile ledger 以 Scheduled Task 真正觸發的 `scheduled_for` 作 occurrence key；repository 不預建 future key。同一 occurrence 的 `current.json` 只要存在，就沿用原 `run_id` 並從 first incomplete stage 接續；即使 reader 已保存但尚未 `delivery-handoff`，也不得 rotate、建立 replacement run 或重跑新聞階段。只有 `scheduled_for` 嚴格較晚的下一個實際觸發 occurrence 才可 rotate，且非 terminal 前輪才標為 `interrupted_by_next_run`；相同 key resume、較舊 key 一律拒絕。同一 run 只能留在原 stage 或前進至緊鄰的下一 stage，不得跳級，也不得執行 stage regression。''',
)

mobile = "mobile-chatgpt-daily-prompt.md"
replace_once(
    mobile,
    '''3. 每次用 GitHub contents API 更新同一個 `current.json`，必須先取得目前 blob SHA；檔案更新失敗時只重試一次，仍失敗就改在 Issue #3 建立或更新本輪單一留言，不得因紀錄失敗重跑已完成的新聞搜尋。''',
    '''3. 每次用 GitHub contents API 更新同一個 `current.json`，必須先取得目前 blob SHA；檔案更新失敗時只重試一次。仍失敗就停在目前 stage 並回報 `run-logs` write blocker；Issue #3 只能留下診斷留言，不能替代 `current.json`、不能宣稱 durable resume，也不得因紀錄失敗重跑已完成的新聞搜尋。''',
)

daily = "daily-schedule-prompt.md"
replace_once(
    daily,
    "- 語言：繁體中文。",
    "- 語言：沿用使用者既有設定；未設定時預設繁體中文。",
)

# Guard against reintroducing the retired architecture in active authority files.
test_path = ROOT / "tests/test_pipeline_contract.py"
text = test_path.read_text(encoding="utf-8")
marker = "    def test_candidate_discovery_uses_dynamic_verification_selection(self):\n"
addition = '''    def test_trigger_owned_occurrence_contract_has_no_future_reservation(self):
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").exists()
        )
        documents = (
            ROOT / "INSTALL.md",
            ROOT / "README.md",
            ROOT / "daily-schedule-prompt.md",
            ROOT / "mobile-chatgpt-daily-prompt.md",
            ROOT / "docs" / "mobile-run-ledger.md",
        )
        for path in documents:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("PRISTINE_RESERVATION_REPLACEMENT_GATE", content, path.name)
            self.assertNotIn("05:58 watchdog", content, path.name)
            self.assertNotIn("05:58 守望", content, path.name)
        manager = (ROOT / "scripts" / "manage_mobile_run_log.py").read_text(encoding="utf-8")
        self.assertNotIn("_is_pristine_reservation", manager)
        self.assertIn('required=True', manager)
        self.assertIn("task 真正觸發", (ROOT / "INSTALL.md").read_text(encoding="utf-8"))
        self.assertIn("external full-runtime visual-recovery executor", (ROOT / "docs" / "mobile-run-ledger.md").read_text(encoding="utf-8"))

'''
if text.count(marker) != 1:
    raise SystemExit("tests/test_pipeline_contract.py: insertion marker mismatch")
test_path.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8", newline="\n")

print("rc17 refinement applied")
