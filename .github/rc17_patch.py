from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    newline = "\r\n" if raw.count("\r\n") > 0 else "\n"
    return raw.replace("\r\n", "\n"), newline


def save(path, text, newline):
    p = ROOT / path
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))


def replace_once(path, old, new):
    text, nl = load(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement target, found {count}: {old[:100]!r}")
    save(path, text.replace(old, new, 1), nl)


def regex_once(path, pattern, replacement, flags=0):
    text, nl = load(path)
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"{path}: expected one regex replacement, found {count}: {pattern[:100]!r}")
    save(path, new_text, nl)


# 1) Runtime: occurrence is created only after the task actually fires and the
# capability route has chosen the execution mode. Retire future reservations.
manager = "scripts/manage_mobile_run_log.py"
regex_once(
    manager,
    r"\n\ndef _is_pristine_reservation\(record: dict\[str, Any\]\) -> bool:\n.*?(?=def prepare_run\()",
    "\n\n",
    re.S,
)
replace_once(manager, '    execution_mode: str = "full-runtime",\n', '    execution_mode: str,\n')
regex_once(
    manager,
    r"    if current_path\.exists\(\):\n.*?        _atomic_write\(previous_path, previous\)\n\n    current: dict\[str, Any\] = \{",
    '''    if current_path.exists():
        previous = _read_json(current_path)
        validate_record(previous)
        try:
            incoming_occurrence = datetime.fromisoformat(scheduled_for)
            current_occurrence = datetime.fromisoformat(previous["scheduled_for"])
            if incoming_occurrence == current_occurrence:
                return previous
            if incoming_occurrence < current_occurrence:
                raise ValueError("cannot replace current.json with an older scheduled occurrence")
        except TypeError as error:
            raise ValueError("scheduled_for values must use comparable ISO timestamps") from error
        if previous["status"] in {"awaiting_executor", "running"}:
            previous["status"] = "interrupted_by_next_run"
            previous["last_error"] = {
                "code": "executor_interrupted",
                "message": "The next scheduled run started before this run reached a terminal state.",
            }
            previous["updated_at"] = updated_at
        _atomic_write(previous_path, previous)

    current: dict[str, Any] = {''',
    re.S,
)
replace_once(
    manager,
    '''        if (
            record["execution_mode"] == "mobile-native"
            and record["window"]["timezone"] != "Asia/Taipei"
        ):
            raise ValueError("mobile-native window timezone must be Asia/Taipei")
''',
    "",
)
replace_once(
    manager,
    '    prepare.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES), default="full-runtime")\n',
    '    prepare.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES), required=True)\n',
)

# 2) Manager regressions: no watchdog, arbitrary task clock/timezone, mode still immutable.
tests = "tests/test_manage_mobile_run_log.py"
replace_once(
    tests,
    '''        return self.module.prepare_run(
            self.ledger_dir,
            run_id=run_id,
            scheduled_for=scheduled_for,
            updated_at=at,
        )
''',
    '''        return self.module.prepare_run(
            self.ledger_dir,
            run_id=run_id,
            scheduled_for=scheduled_for,
            updated_at=at,
            execution_mode="full-runtime",
        )
''',
)
replace_once(
    tests,
    '''        workflow = (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("58 21 * * *", workflow)
        self.assertIn("run-logs", workflow)

    def test_mobile_watchdog_prepares_mobile_native(self):
        workflow = (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("--execution-mode mobile-native", workflow)
''',
    '''        self.assertFalse(
            (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").exists()
        )

    def test_prepare_uses_actual_task_occurrence_without_fixed_clock(self):
        current = self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T04:00:00+09:00",
            updated_at="2026-08-17T19:00:00Z",
            execution_mode="mobile-native",
        )
        self.assertEqual("2026-08-18T04:00:00+09:00", current["scheduled_for"])
        self.assertEqual("mobile-native", current["execution_mode"])
''',
)
replace_once(
    tests,
    '''    def test_mobile_window_timezone_must_be_asia_taipei(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T06:00:00+08:00",
            updated_at="2026-08-17T21:58:00Z",
            execution_mode="mobile-native",
        )
        invalid_timezone = dict(RUN_WINDOW)
        invalid_timezone["timezone"] = "banana"
        with self.assertRaisesRegex(ValueError, "mobile-native window timezone must be Asia/Taipei"):
            self.module.advance_run(
                self.ledger_dir,
                run_id=RUN_1,
                stage="executor-started",
                updated_at="2026-08-17T22:00:00Z",
                window=invalid_timezone,
            )
''',
    '''    def test_mobile_window_accepts_task_timezone(self):
        self.module.prepare_run(
            self.ledger_dir,
            run_id=RUN_1,
            scheduled_for="2026-08-18T07:00:00+09:00",
            updated_at="2026-08-17T21:59:00Z",
            execution_mode="mobile-native",
        )
        task_timezone = dict(RUN_WINDOW)
        task_timezone["timezone"] = "Asia/Tokyo"
        result = self.module.advance_run(
            self.ledger_dir,
            run_id=RUN_1,
            stage="executor-started",
            updated_at="2026-08-17T22:00:00Z",
            window=task_timezone,
        )
        self.assertEqual("Asia/Tokyo", result["window"]["timezone"])
''',
)

pristine_test = ROOT / "tests/test_mobile_pristine_reservation.py"
if pristine_test.exists():
    pristine_test.unlink()

# 3) INSTALL: schedule belongs to the Scheduled Task, not the repository clock.
install = "INSTALL.md"
replace_once(
    install,
    '''3. 內建排程 profile：repository packaged Scheduled Task 固定每日 06:00、`Asia/Taipei`、繁體中文；安裝時只詢問監控板塊與主題偏好，不再詢問排程時間／時區。若需要其他 mobile 時間或時區，不得沿用內建 05:58 watchdog 或共用 `run-logs/current.json`，且本 repository 不宣稱該自訂 mobile profile 受支援。國家板塊使用 ISO 3166-1 alpha-3；區域使用穩定不衝突的三碼。本輪 normalized audit 以有序 `section_scopes` 保存每個板塊的 `code`、`member_country_codes` 與唯一 `fallback`；事件板塊只能由其內容確認的 `country_codes` 對照這份權威決定，不得硬編碼成 TWN／CHN／其他皆 GLB。取得建立排程的授權後，直接完成安裝與首次測試，不再分階段重複詢問同一決定。
''',
    '''3. 排程時間與時區：由 ChatGPT Scheduled Task 本身的單次／循環設定決定；使用者已指定就直接沿用，未指定才詢問，仍無偏好時預設每日 06:00 並優先採帳號／裝置時區。repository 不預先建立 future occurrence，也不綁定特定鐘點。國家板塊使用 ISO 3166-1 alpha-3；區域使用穩定不衝突的三碼。本輪 normalized audit 以有序 `section_scopes` 保存每個板塊的 `code`、`member_country_codes` 與唯一 `fallback`；事件板塊只能由其內容確認的 `country_codes` 對照這份權威決定，不得硬編碼成 TWN／CHN／其他皆 GLB。取得建立排程的授權後，直接完成安裝與首次測試，不再分階段重複詢問同一決定。

輸出語言沿用使用者既有設定；未設定時使用安裝對話主要語言。
''',
)
replace_once(
    install,
    '''repository packaged Scheduled Task profile 固定為每日 06:00、`Asia/Taipei`：宿主具備 verified runtime 時走 full-runtime，否則依同一排程 occurrence 進入 mobile-native fallback；05:58 watchdog 只服務這個內建 profile。不得把不同時間／時區的 mobile schedule 與內建 watchdog 共用同一 `run-logs/current.json`。兩種執行模式的 24 小時窗都從實際 executor 啟動時刻精確倒推，個人偏好不回寫公共 `main`。''',
    '''單次與循環 Scheduled Task 都以該 task 真正觸發的 `scheduled_for` 作 occurrence key；04:00、06:00 或其他時間完全走同一流程。repository 不設 pre-trigger watchdog，也不得在 task 實際觸發前寫入 future `current.json`。每輪先 fresh-resolve `main` 並做一次 capability probe；probe 成功才以 `execution_mode=full-runtime` 建立／接續該輪執行狀態，host execution unavailable 時才以 `execution_mode=mobile-native` 建立／接續 mobile ledger。mode 自 actual occurrence 的 `prepare` 起不可切換。兩種模式的 24 小時窗都從實際 executor 啟動時刻精確倒推，個人偏好不回寫公共 `main`。''',
)
regex_once(
    install,
    r"\n`PRISTINE_RESERVATION_REPLACEMENT_GATE`：[^\n]*\n",
    "\n",
)
replace_once(
    install,
    '''`RUN_ARTIFACT_IDENTITY_GATE`：`execution_mode` 在 prepare 建立 occurrence 時固定且其後不可切換；mobile watchdog 必須明確以 `mobile-native` prepare。`window` 在 `schedule-prepared` 必須為 null；第一次進入 `executor-started` 時，以該次實際執行時刻固定 `end`、倒推精確 24 小時得到 `start`，並保存時區，之後同一 occurrence 不得重新計算或修改。`main_sha` 在 `main-pinned` 前必須為 null，進入 `main-pinned` 時必須已設定，且同一 `scheduled_for` 不可再改變。每個 active artifact binding 都必須攜帶並符合 current ledger 的 `run_id`、`main_sha` 與 `window`；candidate audit、verification、map decisions、image evidence 與 Reader 不得另行建立時間窗。任何身分不一致或尚未到對應 stage 卻綁定未來 artifact 時立即拒絕，不得 repin、mode switch、migration 或 compatibility bypass。''',
    '''`RUN_ARTIFACT_IDENTITY_GATE`：排程實際觸發後先完成 capability routing，再由 actual executor 的 `prepare` 以 `full-runtime` 或 `mobile-native` 一次性固定 `execution_mode`；repository 不建立 future reservation，mode 其後不可切換。`window` 在 `schedule-prepared` 必須為 null；第一次進入 `executor-started` 時，以該次實際執行時刻固定 `end`、倒推精確 24 小時得到 `start`，並保存該 task 的時區，之後同一 occurrence 不得重新計算或修改。`main_sha` 在 `main-pinned` 前必須為 null，進入 `main-pinned` 時必須已設定，且同一 `scheduled_for` 不可再改變。每個 active artifact binding 都必須攜帶並符合 current ledger 的 `run_id`、`main_sha` 與 `window`；candidate audit、verification、map decisions、image evidence 與 Reader 不得另行建立時間窗。任何身分不一致或尚未到對應 stage 卻綁定未來 artifact 時立即拒絕，不得 repin、mode switch、migration 或 compatibility bypass。''',
)
replace_once(
    install,
    '''`VISUAL_DELIVERY_ONLY_RECOVERY`：`NATIVE_MEDIA_UNAVAILABLE` 只能存在於同一 run 的 `status=running`、`current_stage=visuals-completed`，且必須已有本輪 image evidence binding。full-runtime 接手時只讀既有 candidate audit、verification、map decisions、image evidence 與已確認的來源圖片 URL，只補下載／截圖／物化／可見附件交付；不得重跑 discovery、scoring、verification、建立 new run 或變更 event IDs。''',
    '''`VISUAL_DELIVERY_ONLY_RECOVERY`：`NATIVE_MEDIA_UNAVAILABLE` 只能存在於同一 run 的 `status=running`、`current_stage=visuals-completed`，且必須已有本輪 image evidence binding。此 run 的 `execution_mode` 仍保持 `mobile-native`；full-runtime 只作為外部 visual-recovery executor，讀既有 candidate audit、verification、map decisions、image evidence 與已確認的來源圖片 URL，只補下載／截圖／物化／可見附件交付。這不是 mode switch；不得重跑 discovery、scoring、verification、建立 new run 或變更 event IDs。''',
)

# Canonical full-runtime commands must use the resolved executable. Bootstrap
# resolver remains the only scripts/* example allowed to use bare python3.
text, nl = load(install)
text = text.replace("python3 scripts/", "<bundled-python> scripts/")
text = text.replace("python scripts/", "<bundled-python> scripts/")
text = text.replace("<bundled-python> scripts/resolve_bundled_python.py", "python3 scripts/resolve_bundled_python.py")
save(install, text, nl)

replace_once(
    install,
    '''可執行 runtime 時，使用已驗證 bundled Python 執行：

```bash
python3 -m unittest discover -s tests -v
<bundled-python> scripts/validate_news_brief.py manifest --input <manifest>
<bundled-python> scripts/validate_news_brief.py brief --manifest <manifest> --input <reader>
<bundled-python> scripts/validate_map_decisions.py --input <manifest>
```

測試失敗只修失敗環節，不重新詢問已確認偏好，不重跑已完成新聞階段。若 real runtime 不可用，必須明確標示未執行的驗證；不能假稱通過。''',
    '''可執行 runtime 時，installation completion 只跑 capsule 內實際存在的 runtime smoke validation，並一律使用已驗證的 `<bundled-python>`：

```bash
<bundled-python> scripts/validate_news_brief.py manifest --input <manifest>
<bundled-python> scripts/validate_news_brief.py brief --manifest <manifest> --input <reader>
<bundled-python> scripts/validate_map_decisions.py --input <manifest>
```

`tests/` 明確不屬於 runtime capsule；完整 `python3 -m unittest discover -s tests -v` 只適用完整 source checkout／repository maintenance／CI，不是 Scheduled Task 安裝完成 gate。runtime smoke validation 失敗只修失敗環節，不重新詢問已確認偏好，不重跑已完成新聞階段。若 real runtime 不可用，必須明確標示未執行的驗證；不能假稱通過。''',
)

# 4) README and mobile start prompt: no fixed repository clock/watchdog.
readme = "README.md"
replace_once(
    readme,
    '''執行進度與最新讀者版會保存在 `run-logs` 分支；repository 內建的 durable mobile profile 固定為每日 06:00、`Asia/Taipei`、繁體中文，05:58 的輕量守望工作只替這個預設 profile 初始化紀錄，不搜尋新聞，也不使用模型額度。''',
    '''執行進度與最新讀者版會保存在 `run-logs` 分支；repository 不預占任何 future occurrence。單次或循環 Scheduled Task 都在實際觸發後才依 capability routing 建立該輪執行狀態，因此 04:00、06:00 或其他使用者設定時間都走相同流程。''',
)
replace_once(readme, "安裝時只需確認兩項偏好；內建排程 profile 固定如下：", "安裝時確認兩項內容偏好與 Scheduled Task 自身的時間／時區：")
replace_once(
    readme,
    '''3. 內建 Scheduled Task profile 固定為每日 06:00、`Asia/Taipei`、繁體中文；宿主可用 verified runtime 時走 full-runtime，否則同一 occurrence 走 mobile-native fallback。其他 mobile 時間／時區不得沿用內建 05:58 watchdog 或共用 `run-logs/current.json`。''',
    '''3. 單次或循環排程時間／時區由 Scheduled Task 自身決定；使用者指定 04:00、06:00 或其他時間都不需要修改 repository。未指定時才預設每日 06:00 並優先使用帳號／裝置時區。每次實際觸發後先 probe capability，再以該輪選定的 full-runtime 或 mobile-native 建立 occurrence。''',
)

start = "mobile-chatgpt-start-prompt.md"
replace_once(
    start,
    '''排程：每天 06:00，時區 Asia/Taipei；這是 repository 內建 durable mobile profile，建立後立即執行一次；如需其他 mobile 時間／時區，不得沿用本 repo 的 05:58 watchdog。''',
    '''排程：使用我在本對話指定的單次或循環時間與時區；若我尚未指定，先詢問，仍無偏好才預設每天 06:00 並優先使用帳號／裝置時區。建立後立即執行一次。repository 不建立任何 pre-trigger reservation。''',
)

# 5) Mobile execution contract: current.json is created by the actual trigger.
mobile = "mobile-chatgpt-daily-prompt.md"
replace_once(
    mobile,
    '''1. 排程外層為取得最新版規則而進行的 `external latest-main resolution` 與 pinned prompt read 不計入本段順序；它們不得讀取新聞或舊成果。載入本 prompt 後，`first runtime GitHub action` 才是讀取 `run-logs/logs/current.json`。同一 `scheduled_for` 是唯一 occurrence key：只要該 occurrence 的 current record 已存在，不論停在 `awaiting_executor`、`running`、`reader-rendered` 或其他非 terminal 階段，都沿用其中的 `run_id`、固定 `window` 與最後階段，從 first incomplete stage 接續；不得建立 replacement run、不得旋轉 current、不得重跑已完成新聞階段。05:58 守望工作已建立當天 `status=awaiting_executor` 時，第一次更新至 `executor-started`、`status=running` 的同時，以當下實際執行時刻固定 `window.end`、倒推精確 24 小時得到 `window.start`，並保存 `timezone=Asia/Taipei`；其後 resume 必須讀回相同 window，不得按恢復時刻重算。''',
    '''1. 排程外層為取得最新版規則而進行的 `external latest-main resolution`、capability routing 與 pinned prompt read 不計入本段順序；它們不得讀取新聞或舊成果。只有 capability routing 已選定 `mobile-native` 後，`first runtime GitHub action` 才讀取 `run-logs/logs/current.json`。同一 Scheduled Task 真正觸發的 `scheduled_for` 是唯一 occurrence key：若該 key 已存在就沿用其 `run_id`、固定 `window` 與最後階段，從 first incomplete stage 接續；若不存在才在此刻建立 `schedule-prepared / awaiting_executor / execution_mode=mobile-native` 的 current record。repository 不得在 task 觸發前預建 future occurrence。第一次更新至 `executor-started`、`status=running` 時，以當下實際執行時刻固定 `window.end`、倒推精確 24 小時得到 `window.start`，並保存該 task 的時區；其後 resume 必須讀回相同 window，不得按恢復時刻重算。''',
)
replace_once(
    mobile,
    '''2. 只有 `scheduled_for` 嚴格晚於 current 的下一個真實每日 occurrence 才可輪替。此時舊 `current.json` 若仍是非 terminal，標為 `interrupted_by_next_run` 並覆寫 `previous.json`；接著建立新 occurrence 的 `current.json`。相同或較舊 `scheduled_for` 絕不可輪替；更舊的 `previous.json` 直接覆寫，不增加第三份歷史紀錄。
`PRISTINE_RESERVATION_REPLACEMENT_GATE`：若 `current.json` 嚴格仍為 `schedule-prepared + awaiting_executor + main_sha=null + window=null`，且 candidate／verification／map／image／reader／durable artifact 全為 null，這只是一筆尚未消耗 executor 的 future reservation。實際 adhoc／安裝測試的 `scheduled_for` 即使較早，也可直接取代該 pristine reservation；不得把未執行 reservation 寫入 `previous.json` 或標 `interrupted_by_next_run`。相同 `scheduled_for` 仍沿用既有 `run_id`；一旦進入 `executor-started`，older occurrence 就不得再取代。較晚的正式 06:00 occurrence 之後依正常規則 rotate adhoc run。
''',
    '''2. 只有 `scheduled_for` 嚴格晚於 current 的下一個實際觸發 occurrence 才可輪替。此時舊 `current.json` 若仍是非 terminal，標為 `interrupted_by_next_run` 並覆寫 `previous.json`；接著建立新 occurrence 的 `current.json`。相同 key 一律 resume；較舊 key 絕不可輪替。由於不存在 pre-trigger future reservation，不需要較早 adhoc replacement 例外。
''',
)
replace_once(
    mobile,
    '''   - `RUN_ARTIFACT_IDENTITY_GATE`：本 mobile occurrence 必須由 watchdog 以 `execution_mode=mobile-native` 建立，mode 此後不可切換。`window` 在 `schedule-prepared` 為 null，第一次進入 `executor-started` 時固定，之後不可更換；`main_sha` 在 `main-pinned` 前必須為 null，進入 `main-pinned` 時必須已設定且之後不可更換。每個 active binding 必須保存與 current 相同的 `run_id`、`main_sha` 與 `window`；candidate audit、verification、map、image 與 Reader 均不得另算時間窗。stage 尚未到達時對應 artifact 必須為 `null`。不一致時拒絕 binding，不得 repin、切換 mode 或沿用前版 artifact。''',
    '''   - `RUN_ARTIFACT_IDENTITY_GATE`：capability routing 選定 mobile-native 後，actual executor 才以 `execution_mode=mobile-native` 建立 occurrence，mode 此後不可切換。`window` 在 `schedule-prepared` 為 null，第一次進入 `executor-started` 時固定，並保存 Scheduled Task 自身的時區，之後不可更換；`main_sha` 在 `main-pinned` 前必須為 null，進入 `main-pinned` 時必須已設定且之後不可更換。每個 active binding 必須保存與 current 相同的 `run_id`、`main_sha` 與 `window`；candidate audit、verification、map、image 與 Reader 均不得另算時間窗。stage 尚未到達時對應 artifact 必須為 `null`。不一致時拒絕 binding，不得 repin、切換 mode 或沿用前版 artifact。''',
)

# 6) Shared daily contract: task timezone, no pre-reservation, recovery executor != run mode.
daily = "daily-schedule-prompt.md"
replace_once(daily, "- 時區語意：`Asia/Taipei`。", "- 時區語意：沿用本 Scheduled Task／使用者設定的時區；只有宿主無法判斷且使用者未指定時才預設 `Asia/Taipei`。")
replace_once(
    daily,
    '''- Record `execution_mode=full-runtime` or `execution_mode=mobile-native` in the run ledger. The next scheduled run probes capabilities again and resolves fresh `main`; it must not create a second task merely to retry the missing runtime.''',
    '''- The repository never prepares a future occurrence before the Scheduled Task actually fires. After the one capability probe chooses the route, that actual executor creates/resumes the occurrence with `execution_mode=full-runtime` or `execution_mode=mobile-native`; the mode is then immutable for that run. The next scheduled occurrence probes capabilities again and resolves fresh `main`; it must not create a second task merely to retry the missing runtime.''',
)
replace_once(
    daily,
    '''A later full-runtime pass resumes only the missing visual delivery and must not rerun the news stages.''',
    '''A later full-runtime visual-recovery executor resumes only the missing visual delivery and must not rerun the news stages; the original run keeps `execution_mode=mobile-native`, so this recovery is not a mode switch.''',
)

# 7) Ledger documentation: trigger-owned occurrence and explicit external visual executor.
ledger = "docs/mobile-run-ledger.md"
regex_once(ledger, r"\n`PRISTINE_RESERVATION_REPLACEMENT_GATE`:[^\n]*\n", "\n")
replace_once(
    ledger,
    '''`RUN_ARTIFACT_IDENTITY_GATE`: `execution_mode` is fixed by `prepare` and immutable for the occurrence; the mobile watchdog explicitly prepares `mobile-native`. The ledger `window` is null at `schedule-prepared`; the first `executor-started` transition records the actual execution time as `end`, derives `start` exactly 24 hours earlier, saves the time zone, and makes the window immutable for the occurrence. Resume reads this saved window and never recalculates it.''',
    '''`RUN_ARTIFACT_IDENTITY_GATE`: the Scheduled Task must actually fire and finish capability routing before `prepare`; the selected actual executor then fixes `execution_mode` for the occurrence, and it is immutable thereafter. No future occurrence is pre-created. The ledger `window` is null at `schedule-prepared`; the first `executor-started` transition records the actual execution time as `end`, derives `start` exactly 24 hours earlier, saves the task time zone, and makes the window immutable for the occurrence. Resume reads this saved window and never recalculates it.''',
)
replace_once(
    ledger,
    '''`VISUAL_DELIVERY_ONLY_RECOVERY` lets existing full-runtime complete visible delivery from the bound news artifacts and confirmed source URL, but forbids discovery, scoring, verification, a new run, or event-ID changes.''',
    '''`VISUAL_DELIVERY_ONLY_RECOVERY` lets an external full-runtime visual-recovery executor complete visible delivery from the bound news artifacts and confirmed source URL while the original run keeps `execution_mode=mobile-native`; this is not a mode switch. It forbids discovery, scoring, verification, a new run, or event-ID changes.''',
)
regex_once(
    ledger,
    r"\n## Watchdog\n\n.*?(?=\nIf file writes are unavailable)",
    "\n## Trigger-owned occurrence\n\nThere is no pre-trigger watchdog or future reservation. Single-run and recurring Scheduled Tasks create or resume `current.json` only when the configured task occurrence actually fires, regardless of whether that time is 04:00, 06:00, or another configured clock time. Missing scheduled executions are therefore absence-of-execution evidence, not synthetic `awaiting_executor` runs.\n",
    re.S,
)
replace_once(
    ledger,
    '''If file writes are unavailable, the mobile task falls back to one updated comment in Issue #3. Logging failure is diagnostic degradation and must not cause fabricated news or a false delivery claim.''',
    '''If `run-logs` writes are unavailable, durable mobile-native resume is unavailable and must fail closed before discovery. An Issue comment may record diagnostics, but it is not a substitute for `current.json` and must never be treated as durable occurrence state.''',
)

# 8) Recovery skill: external executor does not mutate run mode.
recover = ".agents/skills/recover-news-run/SKILL.md"
replace_once(
    recover,
    '''`mobile-native` 的 `NATIVE_MEDIA_UNAVAILABLE` 是已完成實際交付嘗試後的能力限制，不寫入 `last_error`；但它是既有視覺恢復條件，必須讓同一 run 保持 `status=running`、`current_stage=visuals-completed`，由 full-runtime 只接續圖片交付，不得完成 reader。''',
    '''`mobile-native` 的 `NATIVE_MEDIA_UNAVAILABLE` 是已完成實際交付嘗試後的能力限制，不寫入 `last_error`；但它是既有視覺恢復條件，必須讓同一 run 保持 `status=running`、`current_stage=visuals-completed`、`execution_mode=mobile-native`，由外部 full-runtime visual-recovery executor 只接續圖片交付，不得完成 reader。這不是 mode switch。''',
)
replace_once(
    recover,
    '''`VISUAL_DELIVERY_ONLY_RECOVERY`：已確認圖片但交付失敗時，existing full-runtime 只讀同一 run 已綁定的 candidate audit、verification、map decisions、image evidence 與 source image URL，只補下載、失敗後截圖、物化與可見附件。禁止 discovery、scoring、verification、new run 或 event-ID 變更。''',
    '''`VISUAL_DELIVERY_ONLY_RECOVERY`：已確認圖片但交付失敗時，外部 full-runtime visual-recovery executor 只讀同一 mobile-native run 已綁定的 candidate audit、verification、map decisions、image evidence 與 source image URL，只補下載、失敗後截圖、物化與可見附件；run.execution_mode 不變。禁止 discovery、scoring、verification、new run 或 event-ID 變更。''',
)

# 9) Test contract updated for exact bundled executable examples.
pipeline_test = "tests/test_pipeline_contract.py"
replace_once(pipeline_test, '            "python3 scripts/publish_news_brief.py --checkpoint <checkpoint> "\n', '            "<bundled-python> scripts/publish_news_brief.py --checkpoint <checkpoint> "\n')
replace_once(pipeline_test, '            "python3 scripts/publish_news_brief.py --deliver-receipt "\n', '            "<bundled-python> scripts/publish_news_brief.py --deliver-receipt "\n')

# 10) Current release record. Historical rc.16 text remains history, not active authority.
version = "VERSION-RECORD.md"
text, nl = load(version)
marker = "## v0.6.0-rc.16"
if text.count(marker) != 1:
    raise SystemExit("VERSION-RECORD.md: rc16 marker mismatch")
entry = '''## v0.6.0-rc.17 — Trigger-owned occurrence routing / 實際觸發才建立 occurrence

- Reason / 建立原因：Operational review showed that a 05:58 watchdog reserving a 06:00 future occurrence created artificial conflicts with adhoc runs and mixed schedule intent with execution capability. The same review found that immutable `execution_mode` wording was ambiguous about full-runtime visual recovery, and INSTALL exposed source-checkout unit tests plus bare `python3` examples as if they were capsule-runtime installation gates. / 實際檢查確認 05:58 watchdog 預占 06:00 future occurrence 會人造 adhoc 衝突，並把排程意圖與執行能力混在一起；同時 immutable `execution_mode` 與 full-runtime 視覺恢復的文字容易被理解成 mode switch，INSTALL 也把 source checkout unit tests 與裸 `python3` 範例誤放成 capsule-runtime 安裝 gate。
- Approach / 作法：Retire the pre-trigger watchdog and pristine-reservation exception. Any one-shot or recurring Scheduled Task creates/resumes its occurrence only after the configured task actually fires and capability routing selects `full-runtime` or `mobile-native`; `execution_mode` remains immutable from that actual `prepare`. Schedule time/timezone come from the task rather than repository constants. Full-runtime visual recovery is an external executor over a mobile-native run and never changes `run.execution_mode`. Installation smoke validation uses only capsule runtime files and `<bundled-python>`; the full unit suite is source-checkout/CI only. / 退役 pre-trigger watchdog 與 pristine-reservation 例外。任何單次或循環 Scheduled Task 都只在設定的 task 真正觸發且 capability routing 選定 `full-runtime` 或 `mobile-native` 後建立／接續 occurrence；`execution_mode` 從該次 actual `prepare` 起保持 immutable。排程時間／時區由 task 本身決定，不由 repository 常數決定。full-runtime 視覺恢復只是 mobile-native run 的外部 executor，不改 `run.execution_mode`。安裝 smoke validation 只使用 capsule runtime 與 `<bundled-python>`；完整 unit suite 僅屬 source checkout／CI。
- Non-goals / 不修改：No scoring, discovery-source, GDELT, qualified-image hard-gate, manifest ownership, capsule transport, new ledger field, new execution mode, receipt, migration layer, or batch/backpressure redesign. / 不修改評分、discovery source、GDELT、合格圖片 hard gate、manifest ownership、capsule transport，也不新增 ledger 欄位、execution mode、receipt、migration layer 或 batch/backpressure 重設。
- Validation / 驗證：Manager regressions verify arbitrary scheduled clock/timezone, absence of the pre-trigger watchdog, strict older-occurrence rejection, same-key resume, immutable execution mode, exact 24-hour window anchoring, and all existing mobile artifact/media gates. Full repository tests and capsule verification must pass before promotion; final review independently searches active authority surfaces for retired watchdog/pristine-reservation semantics and confirms source/capsule SHA binding. / manager 回歸驗證任意排程時間／時區、pre-trigger watchdog 已不存在、older occurrence 嚴格拒絕、same-key resume、execution mode immutable、精確 24 小時 window anchor，以及所有既有 mobile artifact/media gates。promote 前必須通過全庫測試與 capsule verification；最後再獨立掃描 active authority surface，確認 watchdog／pristine-reservation 退役語義已消失並核對 source/capsule SHA binding。

'''
text = text.replace(marker, entry + marker, 1)
save(version, text, nl)

print("rc17 patch applied")
