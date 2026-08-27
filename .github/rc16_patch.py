from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return (ROOT / path).read_bytes().decode("utf-8")


def save(path, text):
    (ROOT / path).write_bytes(text.encode("utf-8"))


def dominant_nl(text):
    return "\r\n" if text.count("\r\n") > (text.count("\n") - text.count("\r\n")) else "\n"


def lines(text, nl):
    return text.replace("\n", nl)


def replace_once(path, old, new):
    text = load(path)
    candidates = [(old, new), (old.replace("\n", "\r\n"), new.replace("\n", "\r\n"))]
    hits = [(o, n) for o, n in candidates if text.count(o) == 1]
    if len(hits) != 1:
        raise SystemExit(f"{path}: expected exactly one replacement target, found {[text.count(o) for o, _ in candidates]}")
    old_actual, new_actual = hits[0]
    save(path, text.replace(old_actual, new_actual, 1))


def insert_before_once(path, marker, insertion):
    text = load(path)
    if text.count(marker) != 1:
        raise SystemExit(f"{path}: marker count for {marker!r} is {text.count(marker)}")
    nl = dominant_nl(text)
    save(path, text.replace(marker, lines(insertion, nl) + marker, 1))


def replace_between(path, start_marker, end_marker, new_block):
    text = load(path)
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"{path}: start marker not found: {start_marker!r}")
    end_start = text.find(end_marker, start)
    if end_start < 0:
        raise SystemExit(f"{path}: end marker not found: {end_marker!r}")
    end = end_start + len(end_marker)
    nl = dominant_nl(text[start:end])
    save(path, text[:start] + lines(new_block, nl) + text[end:])


# 1) Canonical manager: pristine future reservations are placeholders, not started runs.
manager = "scripts/manage_mobile_run_log.py"
helper = '''\n\ndef _is_pristine_reservation(record: dict[str, Any]) -> bool:
    artifact_fields = (
        "reader_artifact",
        "candidate_audit_artifact",
        "verification_artifact",
        "map_decisions_artifact",
        "image_evidence_artifact",
        "durable_audit_artifact",
    )
    return (
        record["status"] == "awaiting_executor"
        and record["current_stage"] == "schedule-prepared"
        and record["stage_index"] == STAGE_INDEX["schedule-prepared"]
        and record["last_completed_stage"] is None
        and record["main_sha"] is None
        and record["window"] is None
        and record["delivery_profile"] == "full-assets"
        and record["native_media_status"] == "available"
        and record["capability_limitations"] == []
        and record["delivery_status"] == "not_ready"
        and not record["client_confirmation_supported"]
        and record["last_error"] is None
        and record["durable_audit_status"] == "not_started"
        and all(record.get(field) is None for field in artifact_fields)
    )
'''
insert_before_once(manager, "def prepare_run(", helper)

prepare_block = '''    if current_path.exists():
        previous = _read_json(current_path)
        validate_record(previous)
        pristine_reservation = _is_pristine_reservation(previous)
        try:
            incoming_occurrence = datetime.fromisoformat(scheduled_for)
            current_occurrence = datetime.fromisoformat(previous["scheduled_for"])
            if incoming_occurrence == current_occurrence:
                return previous
            if incoming_occurrence < current_occurrence and not pristine_reservation:
                raise ValueError("cannot replace current.json with an older scheduled occurrence")
        except TypeError as error:
            raise ValueError("scheduled_for values must use comparable ISO timestamps") from error

        # A pristine schedule-prepared reservation has never consumed an executor,
        # window, main pin, or artifact. Replacing it is not an interruption and
        # must not create false previous-run history. This permits an immediate
        # adhoc/install test to run before a pre-created future daily reservation.
        if not pristine_reservation:
            if previous["status"] in {"awaiting_executor", "running"}:
                previous["status"] = "interrupted_by_next_run"
                previous["last_error"] = {
                    "code": "executor_interrupted",
                    "message": "The next scheduled run started before this run reached a terminal state.",
                }
                previous["updated_at"] = updated_at
            _atomic_write(previous_path, previous)'''
replace_between(manager, "    if current_path.exists():", "        _atomic_write(previous_path, previous)", prepare_block)

# 2) Focused operational regression tests; no new runtime/state/schema.
test_path = ROOT / "tests/test_mobile_pristine_reservation.py"
test_path.write_text('''import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "manage_mobile_run_log.py"

RUN_A = "gnb-20260827T173900Z-10000001"
RUN_B = "gnb-20260827T220000Z-10000002"
ADHOC_FOR = "2026-08-28T01:39:00+08:00"
FORMAL_FOR = "2026-08-28T06:00:00+08:00"
ADHOC_END = "2026-08-27T17:39:00Z"
FORMAL_END = "2026-08-27T22:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("manage_mobile_run_log_rc16", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def window(end_utc, start_utc):
    return {"start": start_utc, "end": end_utc, "timezone": "Asia/Taipei"}


class PristineReservationTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, run_id, scheduled_for, updated_at):
        return self.module.prepare_run(
            self.ledger,
            run_id=run_id,
            scheduled_for=scheduled_for,
            updated_at=updated_at,
            execution_mode="mobile-native",
        )

    def test_earlier_adhoc_replaces_pristine_future_reservation_without_previous(self):
        self.prepare(RUN_B, FORMAL_FOR, "2026-08-27T14:05:29Z")
        current = self.prepare(RUN_A, ADHOC_FOR, ADHOC_END)
        self.assertEqual(RUN_A, current["run_id"])
        self.assertEqual(ADHOC_FOR, current["scheduled_for"])
        self.assertFalse((self.ledger / "previous.json").exists())

    def test_earlier_adhoc_cannot_replace_started_future_occurrence(self):
        self.prepare(RUN_B, FORMAL_FOR, "2026-08-27T14:05:29Z")
        self.module.advance_run(
            self.ledger,
            run_id=RUN_B,
            stage="executor-started",
            updated_at=FORMAL_END,
            window=window(FORMAL_END, "2026-08-26T22:00:00Z"),
        )
        with self.assertRaisesRegex(ValueError, "older scheduled occurrence"):
            self.prepare(RUN_A, ADHOC_FOR, ADHOC_END)

    def test_later_formal_occurrence_rotates_running_adhoc_normally(self):
        self.prepare(RUN_A, ADHOC_FOR, "2026-08-27T17:38:00Z")
        self.module.advance_run(
            self.ledger,
            run_id=RUN_A,
            stage="executor-started",
            updated_at=ADHOC_END,
            window=window(ADHOC_END, "2026-08-26T17:39:00Z"),
        )
        current = self.prepare(RUN_B, FORMAL_FOR, FORMAL_END)
        previous = self.module._read_json(self.ledger / "previous.json")
        self.assertEqual(RUN_B, current["run_id"])
        self.assertEqual("interrupted_by_next_run", previous["status"])
        self.assertEqual(RUN_A, previous["run_id"])

    def test_matching_pristine_reservation_resumes_same_run(self):
        original = self.prepare(RUN_B, FORMAL_FOR, "2026-08-27T14:05:29Z")
        resumed = self.prepare(RUN_A, FORMAL_FOR, "2026-08-27T17:39:00Z")
        self.assertEqual(original["run_id"], resumed["run_id"])
        self.assertEqual("schedule-prepared", resumed["current_stage"])
        self.assertFalse((self.ledger / "previous.json").exists())


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8", newline="\n")

# 3) Bootstrap capability split: mobile-native never claims local image work.
replace_between(
    "bootstrap-workspace.md",
    "A mobile-native run completes under its declared reader delivery profile.",
    "Only an actual final-mile delivery failure may use",
    '''A mobile-native run completes under its declared reader delivery profile. It must
inspect verified source pages, attempt the host's native image search/image-card
delivery route, and record the structured delivery result. It must not claim local
download, screenshot, materialization, attachment, or pixel validation.
Only an actual final-mile delivery failure may use''',
)
replace_once("bootstrap-workspace.md", "the run must not claim attachment or pixel validation.\n", "")

# 4) INSTALL: operator-facing closure, profile authority, write prerequisite, reservation semantics.
replace_once(
    "INSTALL.md",
    '- `maps/source/world-countries.geojson`\n\n',
    '''- `maps/source/world-countries.geojson`

### Bootstrap infrastructure

- `bootstrap/capsule-manifest.json`
- `bootstrap/bootstrap_loader.py`
- `bootstrap/bootstrap_progress.py`
- `bootstrap/bootstrap-progress.schema.json`
- `bootstrap/RUN_LEDGER_PROTOCOL.md`
- `scripts/resolve_bundled_python.py`
- `scripts/run_identity.py`

### Mobile execution support

- `scripts/manage_mobile_run_log.py`
- `schemas/mobile-run-log.schema.json`
- `mobile-chatgpt-start-prompt.md`
- `mobile-chatgpt-daily-prompt.md`

### Recovery／validation support

- `scripts/recover_same_source_leads.py`
- `scripts/validate_selection_freshness.py`

以上是 operator-facing necessary closure；完整 capsule runtime closure 以 `bootstrap/capsule-manifest.json.runtime_files` 為機器權威，不在 INSTALL 重複列出全部 runtime files。

''',
)
replace_once(
    "INSTALL.md",
    '3. 執行時間：每天幾點？優先使用帳號／裝置時區；無法判斷才追問時區，預設每日 06:00。\n\n輸出語言沿用使用者已設定語言，否則使用安裝對話主要語言。',
    '3. 執行設定：repository 內建的 durable `mobile-native` profile 固定為每日 06:00、`Asia/Taipei`、繁體中文，不再另外詢問 mobile 時間／時區；`full-runtime` 若要自訂每日時間，必須產生與該 profile 一致的 schedule prompt，不能與內建 mobile watchdog 混用。\n\nRepository 內建排程 profile 的輸出語言為繁體中文、時區語意為 `Asia/Taipei`；自訂 full-runtime profile 必須在安裝時一致產生，不得只改排程時間而沿用另一套固定時區契約。',
)
replace_once(
    "INSTALL.md",
    '| 適用環境 | 可執行 bundled Python、物化檔案與 canonical publisher | Scheduled Task／無本機 runtime 的一般 ChatGPT 宿主 |\n',
    '| 適用環境 | 可執行 bundled Python、物化檔案與 canonical publisher | Scheduled Task／無本機 runtime 的一般 ChatGPT 宿主 |\n| 持久化前提 | 外部 ledger 可依 full-runtime 規則 best-effort 降級 | 可恢復的 durable Scheduled Task 必須使用具此 repository `run-logs` 寫入權限的 GitHub app；無寫入權限只可做一次性、不可跨執行恢復的 reader，不得宣稱 durable mobile profile |\n',
)
replace_once(
    "INSTALL.md",
    '依 [daily-schedule-prompt.md](daily-schedule-prompt.md) 建立每日獨立排程：名稱與結果對話名稱均為「每日新聞」，每次建立新結果對話；24 小時窗從實際執行時刻精確倒推。個人偏好保存在使用者自己的排程設定，不回寫公共 `main`。',
    'full-runtime 依 [daily-schedule-prompt.md](daily-schedule-prompt.md) 建立每日獨立排程；repository 內建的 durable mobile-native profile 依 [mobile-chatgpt-start-prompt.md](mobile-chatgpt-start-prompt.md) 固定為每日 06:00、`Asia/Taipei`，05:58 watchdog 只服務這個預設 profile。不得把不同時間／時區的 mobile schedule 與內建 watchdog 共用同一 `run-logs/current.json`。兩種模式的 24 小時窗都從實際 executor 啟動時刻精確倒推，個人偏好不回寫公共 `main`。',
)
replace_once(
    "INSTALL.md",
    '`SCHEDULED_OCCURRENCE_SINGLE_RUN_GATE`：mobile ledger 以 `scheduled_for` 作 occurrence key。同一 occurrence 的 `current.json` 只要存在，就沿用原 `run_id` 並從 first incomplete stage 接續；即使 reader 已保存但尚未 `delivery-handoff`，也不得 rotate、建立 replacement run 或重跑新聞階段。只有 `scheduled_for` 嚴格較晚的下一個真實每日 occurrence 才可把仍非 terminal 的前輪標為 `interrupted_by_next_run`。同一 run 只能留在原 stage 或前進至緊鄰的下一 stage，不得跳級，也不得執行 stage regression。',
    '`SCHEDULED_OCCURRENCE_SINGLE_RUN_GATE`：mobile ledger 以 `scheduled_for` 作 occurrence key。同一 occurrence 的 `current.json` 只要存在，就沿用原 `run_id` 並從 first incomplete stage 接續；即使 reader 已保存但尚未 `delivery-handoff`，也不得 rotate、建立 replacement run 或重跑新聞階段。已進入 `executor-started` 或之後的 occurrence 仍只有 `scheduled_for` 嚴格較晚的下一個真實 occurrence 才可 rotate，且非 terminal 前輪才標為 `interrupted_by_next_run`。同一 run 只能留在原 stage 或前進至緊鄰的下一 stage，不得跳級，也不得執行 stage regression。\n\n`PRISTINE_RESERVATION_REPLACEMENT_GATE`：`schedule-prepared + awaiting_executor + main_sha=null + window=null + 所有 run artifact=null` 代表 watchdog／cutover 建立但尚未消耗 executor 的 pristine future reservation，不是已啟動 run。若實際 adhoc／安裝測試的 `scheduled_for` 早於這筆 reservation，可直接以實際 occurrence 取代 `current.json`，不得把未執行 reservation 寫成 `previous.json` 或 `interrupted_by_next_run`；相同 `scheduled_for` 仍 resume 同一 `run_id`。一旦 reservation 進入 `executor-started`，older occurrence 就恢復嚴格禁止。之後較晚的正式 06:00 occurrence 依正常規則 rotate 已完成或仍 running 的 adhoc run。',
)

# 5) README: built-in mobile profile and GitHub-write boundary.
replace_once(
    "README.md",
    '執行進度與最新讀者版會保存在 `run-logs` 分支；05:58 的輕量守望工作只初始化紀錄，不搜尋新聞，也不使用模型額度。',
    '執行進度與最新讀者版會保存在 `run-logs` 分支；repository 內建的 durable mobile profile 固定為每日 06:00、`Asia/Taipei`、繁體中文，05:58 的輕量守望工作只替這個預設 profile 初始化紀錄，不搜尋新聞，也不使用模型額度。',
)
replace_once(
    "README.md",
    '3. 每日幾點執行。\n\n輸出語言優先沿用使用者已設定的語言；沒有設定時沿用安裝對話的主要語言。時區優先使用帳號、裝置或目前工作區時區，只有無法判斷時才詢問。',
    '3. 執行 profile：full-runtime 可在安裝時產生一致的自訂排程；repository 內建的 durable mobile-native profile 固定為每日 06:00、`Asia/Taipei`。\n\nRepository 內建排程 profile 固定使用繁體中文與 `Asia/Taipei`。若自訂 full-runtime 排程，語言、時間與時區必須在同一 profile 內一致產生；不要只改外層排程卻沿用內建 mobile watchdog。',
)
replace_once(
    "README.md",
    '公開 repo 的規則、技能、模板、地圖與圖片流程都可直接讀取；沒有 GitHub 帳號或寫入權限仍可產生完整每日新聞。',
    '公開 repo 的規則、技能、模板、地圖與圖片流程可在沒有 GitHub 帳號時直接讀取；但可恢復的 durable mobile-native Scheduled Task 必須使用具此 repository `run-logs` 寫入權限的 GitHub app。沒有寫入權限時最多只能在當前執行做一次性 reader，不得宣稱具備跨執行 resume、durable run identity 或 continuity。',
)

# 6) Mobile daily authority: durable write prerequisite + pristine reservation semantics.
replace_once(
    "mobile-chatgpt-daily-prompt.md",
    '使用已連接的 GitHub app，將紀錄寫在同一 repository 的 `run-logs` 分支。正常只維護 `logs/current.json`、`logs/previous.json`、`logs/latest-candidate-audit.json` 與 `logs/latest-reader.md`，不得寫入 `main`，也不得逐新聞或逐工具呼叫建立紀錄。',
    '可恢復的 durable mobile-native Scheduled Task 必須使用已連接且具此 repository `run-logs` 寫入權限的 GitHub app，將紀錄寫在同一 repository 的 `run-logs` 分支。若沒有寫入權限，這個 durable profile 必須在 discovery 前明確 fail closed；可另做一次性 reader，但不得冒充具備本契約的 durable resume／continuity。正常只維護 `logs/current.json`、`logs/previous.json`、`logs/latest-candidate-audit.json` 與 `logs/latest-reader.md`，不得寫入 `main`，也不得逐新聞或逐工具呼叫建立紀錄。',
)
insert_before_once(
    "mobile-chatgpt-daily-prompt.md",
    '3. 每次用 GitHub contents API 更新同一個 `current.json`',
    '''`PRISTINE_RESERVATION_REPLACEMENT_GATE`：若 `current.json` 嚴格仍為 `schedule-prepared + awaiting_executor + main_sha=null + window=null`，且 candidate／verification／map／image／reader／durable artifact 全為 null，這只是一筆尚未消耗 executor 的 future reservation。實際 adhoc／安裝測試的 `scheduled_for` 即使較早，也可直接取代該 pristine reservation；不得把未執行 reservation 寫入 `previous.json` 或標 `interrupted_by_next_run`。相同 `scheduled_for` 仍沿用既有 `run_id`；一旦進入 `executor-started`，older occurrence 就不得再取代。較晚的正式 06:00 occurrence 之後依正常規則 rotate adhoc run。\n\n''',
)

# 7) Ledger docs and start prompt clarify scope without new state/schema.
insert_before_once(
    "docs/mobile-run-ledger.md",
    "The branch tip exposes only two run records.",
    '''`PRISTINE_RESERVATION_REPLACEMENT_GATE`: a record that is still `schedule-prepared` / `awaiting_executor` with null `main_sha`, null `window`, and no bound run artifacts is only an unconsumed future reservation. A real adhoc/install test may replace that reservation even when its `scheduled_for` is earlier, without creating `previous.json` or `interrupted_by_next_run`. Same-key entry still resumes the existing run. Once `executor-started` has been reached, the normal older-occurrence prohibition applies again. A later formal occurrence rotates the adhoc run normally.\n\nDurable mobile-native Scheduled Tasks require GitHub write access to `run-logs`; read-only/no-write execution may produce a one-shot reader but has no durable resume semantics and is not this ledger profile.\n\n''',
)
replace_once(
    "docs/mobile-run-ledger.md",
    '`.github/workflows/prepare-mobile-run-ledger.yml` runs at 05:58 Asia/Taipei and can also be dispatched manually.',
    '`.github/workflows/prepare-mobile-run-ledger.yml` is only the repository\'s default durable mobile profile helper: it runs at 05:58 `Asia/Taipei` to reserve the 06:00 `Asia/Taipei` occurrence and can also be dispatched manually.',
)
replace_once(
    "mobile-chatgpt-start-prompt.md",
    '排程：每天 06:00，時區 Asia/Taipei；建立後立即執行一次。',
    '排程：每天 06:00，時區 Asia/Taipei；這是 repository 內建 durable mobile profile，建立後立即執行一次；如需其他 mobile 時間／時區，不得沿用本 repo 的 05:58 watchdog。',
)
replace_once(
    ".github/workflows/prepare-mobile-run-ledger.yml",
    '# 05:58 Asia/Taipei. Taiwan does not observe daylight-saving time.',
    '# Default durable mobile profile only: reserve the 06:00 Asia/Taipei occurrence at 05:58. Taiwan does not observe daylight-saving time.',
)

# 8) Version record.
version_marker = "## v0.6.0-rc.15 — Mobile window anchor identity closure / Mobile 時間窗錨點身分閉環"
rc16 = '''## v0.6.0-rc.16 — Operational occurrence and mobile authority closure / 單次驗收與 mobile 權責閉環

- Reason / 建立原因：A real one-shot test at 2026-08-28 01:39 +08:00 correctly failed closed because `run-logs/current.json` already held an unstarted 06:00 future reservation; the contract had no legal way to run the earlier adhoc test without either violating occurrence ordering or consuming the formal 06:00 run. Repository-wide review also confirmed three active authority conflicts: packaged schedule/timezone claims, stale mobile local-image wording in bootstrap, and ambiguous no-write mobile support. / 真實單次測試在 2026-08-28 01:39 +08:00 因 `current.json` 已預占尚未啟動的 06:00 future reservation 而正確 fail closed；契約沒有合法方式在不破壞 occurrence ordering 或提前消耗正式 06:00 run 的情況下執行較早 adhoc test。全庫檢查另確認 packaged 排程／時區、bootstrap mobile 圖片能力舊句與無 GitHub write 支援三項 active authority 衝突。
- Approach / 作法：Derive a pristine-reservation predicate from existing fields only. A different occurrence may replace an unconsumed `schedule-prepared/awaiting_executor` reservation without writing false interruption history; once `executor-started` is reached, older occurrences remain forbidden. Define the repository-supplied durable mobile profile as 06:00 `Asia/Taipei` / Traditional Chinese, require `run-logs` write access for resumable mobile Scheduled Tasks, split bootstrap image capabilities correctly, and complete INSTALL's operator-facing support inventory. / 僅以既有欄位推導 pristine reservation；不同 occurrence 可取代尚未消耗 executor 的 `schedule-prepared/awaiting_executor` reservation，且不得寫入假的 interruption history；一旦進入 `executor-started`，older occurrence 仍嚴格禁止。內建 durable mobile profile 明確固定 06:00 `Asia/Taipei`／繁體中文，可恢復 Scheduled Task 要求 `run-logs` 寫入權限，bootstrap 圖片能力重新分流，並補齊 INSTALL operator-facing support inventory。
- Non-goals / 不修改：No new schema field, ledger file, execution mode, receipt, discovery provenance, GDELT escape hatch, content cap, batch cursor, scoring change, image hard-gate relaxation, capsule transport redesign, or state machine. / 不新增 schema 欄位、ledger 檔、execution mode、receipt、discovery provenance、GDELT escape hatch、內容上限、batch cursor、評分修改、圖片 hard gate 放寬、capsule transport 重設或 state machine。
- Validation / 驗證：Focused regressions cover earlier adhoc replacement of a pristine future reservation, rejection after executor start, later formal rotation of a running adhoc run, and same-key resume; then the complete repository test suite runs before promotion. / 目標回歸覆蓋 pristine future reservation 被較早 adhoc 取代、executor start 後禁止 older replacement、較晚正式 occurrence 正常 rotate running adhoc，以及 same-key resume；promote 前再跑完整 repository test suite。
- Result / 結果：This operational fix reopens the frozen runtime only for the observed P1 and closes the confirmed authority conflicts without changing news selection, media completeness, or discovery correctness policy. / 本 operational 修正只針對真實 P1 重新開啟 frozen runtime，並關閉已確認的權責衝突，不改新聞選稿、媒體完整性或 discovery correctness 政策。

'''
insert_before_once("VERSION-RECORD.md", version_marker, rc16)
