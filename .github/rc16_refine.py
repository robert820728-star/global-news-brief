from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> str:
    return (ROOT / path).read_bytes().decode("utf-8")


def save(path: str, text: str) -> None:
    (ROOT / path).write_bytes(text.encode("utf-8"))


def replace_once(path: str, old: str, new: str) -> None:
    text = load(path)
    candidates = [(old, new)]
    crlf_old = old.replace("\n", "\r\n")
    if crlf_old != old:
        candidates.append((crlf_old, new.replace("\n", "\r\n")))
    hits = [(o, n) for o, n in candidates if text.count(o) == 1]
    if len(hits) != 1:
        raise SystemExit(
            f"{path}: expected one refinement target for {old[:80]!r}, "
            f"counts={[text.count(o) for o, _ in candidates]}"
        )
    source, replacement = hits[0]
    save(path, text.replace(source, replacement, 1))


# Narrow the reservation exception to the observed case only: an earlier adhoc
# executor may replace a pristine future reservation. A later occurrence keeps
# the original rotation/interruption evidence semantics.
replace_once(
    "scripts/manage_mobile_run_log.py",
    '''        pristine_reservation = _is_pristine_reservation(previous)
        try:''',
    '''        pristine_reservation = _is_pristine_reservation(previous)
        replace_pristine_earlier = False
        try:''',
)
replace_once(
    "scripts/manage_mobile_run_log.py",
    '''            if incoming_occurrence < current_occurrence and not pristine_reservation:
                raise ValueError("cannot replace current.json with an older scheduled occurrence")''',
    '''            replace_pristine_earlier = (
                incoming_occurrence < current_occurrence
                and pristine_reservation
            )
            if incoming_occurrence < current_occurrence and not replace_pristine_earlier:
                raise ValueError("cannot replace current.json with an older scheduled occurrence")''',
)
replace_once(
    "scripts/manage_mobile_run_log.py",
    "        if not pristine_reservation:\n",
    "        if not replace_pristine_earlier:\n",
)

# Make the packaged schedule authority truthful: the repository-supplied
# Scheduled Task profile is fixed; this release does not invent generic mobile
# timezone/profile state.
replace_once("INSTALL.md", "## 二、只詢問三件事", "## 二、只詢問必要偏好")
replace_once(
    "INSTALL.md",
    '''3. 執行設定：repository 內建的 durable `mobile-native` profile 固定為每日 06:00、`Asia/Taipei`、繁體中文，不再另外詢問 mobile 時間／時區；`full-runtime` 若要自訂每日時間，必須產生與該 profile 一致的 schedule prompt，不能與內建 mobile watchdog 混用。

Repository 內建排程 profile 的輸出語言為繁體中文、時區語意為 `Asia/Taipei`；自訂 full-runtime profile 必須在安裝時一致產生，不得只改排程時間而沿用另一套固定時區契約。''',
    '''3. 內建排程 profile：repository packaged Scheduled Task 固定每日 06:00、`Asia/Taipei`、繁體中文；安裝時只詢問監控板塊與主題偏好，不再詢問排程時間／時區。若需要其他 mobile 時間或時區，不得沿用內建 05:58 watchdog 或共用 `run-logs/current.json`，且本 repository 不宣稱該自訂 mobile profile 受支援。''',
)
replace_once(
    "INSTALL.md",
    '''full-runtime 依 [daily-schedule-prompt.md](daily-schedule-prompt.md) 建立每日獨立排程；repository 內建的 durable mobile-native profile 依 [mobile-chatgpt-start-prompt.md](mobile-chatgpt-start-prompt.md) 固定為每日 06:00、`Asia/Taipei`，05:58 watchdog 只服務這個預設 profile。不得把不同時間／時區的 mobile schedule 與內建 watchdog 共用同一 `run-logs/current.json`。兩種模式的 24 小時窗都從實際 executor 啟動時刻精確倒推，個人偏好不回寫公共 `main`。''',
    '''repository packaged Scheduled Task profile 固定為每日 06:00、`Asia/Taipei`：宿主具備 verified runtime 時走 full-runtime，否則依同一排程 occurrence 進入 mobile-native fallback；05:58 watchdog 只服務這個內建 profile。不得把不同時間／時區的 mobile schedule 與內建 watchdog 共用同一 `run-logs/current.json`。兩種執行模式的 24 小時窗都從實際 executor 啟動時刻精確倒推，個人偏好不回寫公共 `main`。''',
)
replace_once(
    "INSTALL.md",
    "公開 repo 的讀取不要求 GitHub 帳號；跨日 audit 與 run ledger 的持久化依工作區或 repository 寫入權限降級，但不能阻止有效的當日 reader。",
    "公開 repo 的讀取不要求 GitHub 帳號。full-runtime 的外部 diagnostic ledger 可依既有規則 best-effort 降級；但可恢復的 durable mobile-native Scheduled Task 必須具備 `run-logs` 寫入權限，缺少寫入權限時不得宣稱 durable resume／continuity。一次性 reader 可在當前執行完成，但不屬於 durable mobile profile。",
)
replace_once(
    "INSTALL.md",
    "以上是 operator-facing necessary closure；完整 capsule runtime closure 以 `bootstrap/capsule-manifest.json.runtime_files` 為機器權威，不在 INSTALL 重複列出全部 runtime files。",
    "以上是 operator-facing necessary closure；完整 capsule runtime closure 以 `bootstrap/capsule-manifest.json` 裡的 `runtime_files` 欄位為機器權威，不在 INSTALL 重複列出全部 runtime files。",
)

replace_once(
    "README.md",
    "安裝時只需確認三件事：",
    "安裝時只需確認兩項偏好；內建排程 profile 固定如下：",
)
replace_once(
    "README.md",
    '''3. 執行 profile：full-runtime 可在安裝時產生一致的自訂排程；repository 內建的 durable mobile-native profile 固定為每日 06:00、`Asia/Taipei`。

Repository 內建排程 profile 固定使用繁體中文與 `Asia/Taipei`。若自訂 full-runtime 排程，語言、時間與時區必須在同一 profile 內一致產生；不要只改外層排程卻沿用內建 mobile watchdog。''',
    '''3. 內建 Scheduled Task profile 固定為每日 06:00、`Asia/Taipei`、繁體中文；宿主可用 verified runtime 時走 full-runtime，否則同一 occurrence 走 mobile-native fallback。其他 mobile 時間／時區不得沿用內建 05:58 watchdog 或共用 `run-logs/current.json`。''',
)
replace_once(
    "README.md",
    "台帳失敗只降低診斷能力，不會阻擋每日新聞。 / Only full-runtime fetches and verifies the capsule, creates a local checkpoint, and falls back to segmented chunks when needed. Mobile-native pins fresh main and resumes the same scheduled occurrence through the existing run ledger and run-scoped artifacts without claiming a capsule, workspace, or local checkpoint.",
    "full-runtime 的 external diagnostic ledger 失敗只降低診斷能力；可恢復的 durable mobile-native 則必須具備 `run-logs` 寫入權限，不能套用這個降級。 / Only full-runtime fetches and verifies the capsule, creates a local checkpoint, and may degrade its external diagnostic ledger. Durable mobile-native pins fresh main and resumes through the writable `run-logs` ledger and run-scoped artifacts without claiming a capsule, workspace, or local checkpoint.",
)

# Version record must describe the narrowed exception, not a generic alternate
# occurrence replacement policy.
replace_once(
    "VERSION-RECORD.md",
    "Derive a pristine-reservation predicate from existing fields only. A different occurrence may replace an unconsumed `schedule-prepared/awaiting_executor` reservation without writing false interruption history; once `executor-started` is reached, older occurrences remain forbidden.",
    "Derive a pristine-reservation predicate from existing fields only. An earlier adhoc/install occurrence may replace an unconsumed `schedule-prepared/awaiting_executor` future reservation without writing false interruption history; later occurrences retain normal rotation history, and once `executor-started` is reached, older occurrences remain forbidden.",
)
replace_once(
    "VERSION-RECORD.md",
    "僅以既有欄位推導 pristine reservation；不同 occurrence 可取代尚未消耗 executor 的 `schedule-prepared/awaiting_executor` reservation，且不得寫入假的 interruption history；一旦進入 `executor-started`，older occurrence 仍嚴格禁止。",
    "僅以既有欄位推導 pristine reservation；較早的 adhoc／安裝測試 occurrence 可取代尚未消耗 executor 的 `schedule-prepared/awaiting_executor` future reservation，且不得寫入假的 interruption history；較晚 occurrence 仍保留正常 rotation 歷史，一旦進入 `executor-started`，older occurrence 仍嚴格禁止。",
)

# Refine the existing bootstrap receipt test. The original preflight list remains
# the full-runtime receipt authority; the new support inventory is operator-facing
# and is validated for existence instead of being forced into BOOTSTRAP_REQUIRED_PATHS.
p = ROOT / "tests/test_news_run_checkpoint.py"
text = p.read_text(encoding="utf-8")
old = '''        preflight = install.split("## 一、安裝前驗證", 1)[1].split("## 二、", 1)[0]
        expected = set(re.findall(
            r"`((?:\\.agents|bootstrap|scripts|schemas|maps)/[^`]+|[^`/]+\\.(?:md|json|yaml))`",
            preflight,
        ))

        self.assertTrue(expected.issubset(set(MODULE.BOOTSTRAP_REQUIRED_PATHS)))
'''
new = '''        preflight = install.split("## 一、安裝前驗證", 1)[1].split("## 二、", 1)[0]
        runtime_preflight, operator_support = preflight.split("### Bootstrap infrastructure", 1)
        expected = set(re.findall(
            r"`((?:\\.agents|bootstrap|scripts|schemas|maps)/[^`]+|[^`/]+\\.(?:md|json|yaml))`",
            runtime_preflight,
        ))
        self.assertTrue(expected.issubset(set(MODULE.BOOTSTRAP_REQUIRED_PATHS)))

        support_paths = set(re.findall(
            r"`((?:\\.agents|bootstrap|scripts|schemas|maps)/[^`]+|[^`/]+\\.(?:md|json|yaml))`",
            "### Bootstrap infrastructure" + operator_support,
        ))
        for rel in support_paths:
            self.assertTrue((ROOT / rel).exists(), rel)
'''
if text.count(old) != 1:
    raise SystemExit("test_news_run_checkpoint preflight block mismatch")
p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")

# Direct regression for the active prose/authority surfaces that produced the
# repository-wide consistency findings.
p = ROOT / "tests/test_pipeline_contract.py"
text = p.read_text(encoding="utf-8")
marker = "    def test_candidate_discovery_uses_dynamic_verification_selection(self):\n"
addition = '''    def test_rc16_mobile_authority_closure(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        mobile = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")
        bootstrap = (ROOT / "bootstrap-workspace.md").read_text(encoding="utf-8")
        ledger = (ROOT / "docs" / "mobile-run-ledger.md").read_text(encoding="utf-8")
        start = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")
        watchdog = (ROOT / ".github" / "workflows" / "prepare-mobile-run-ledger.yml").read_text(encoding="utf-8")

        for document in (install, mobile, ledger):
            self.assertIn("PRISTINE_RESERVATION_REPLACEMENT_GATE", document)
        for document in (install, readme, mobile, ledger):
            self.assertIn("run-logs", document)
        self.assertIn("寫入權限", install)
        self.assertIn("寫入權限", readme)
        self.assertIn("寫入權限", mobile)
        self.assertIn("write access", ledger)
        for document in (install, readme, start, watchdog):
            self.assertIn("06:00", document)
            self.assertIn("Asia/Taipei", document)
        self.assertIn("native image search/image-card", bootstrap)
        self.assertIn("must not claim local", bootstrap)
        self.assertNotIn("first attempt source-image download, screenshot fallback", bootstrap)

'''
if text.count(marker) != 1:
    raise SystemExit("test_pipeline_contract insertion marker mismatch")
p.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8", newline="\n")

# Preserve intentional CRLF in -text runtime files; collapse only accidental
# doubled CR produced by replacement tooling.
for name in (
    "scripts/manage_mobile_run_log.py",
    "bootstrap-workspace.md",
    "INSTALL.md",
    "README.md",
    "mobile-chatgpt-daily-prompt.md",
    "docs/mobile-run-ledger.md",
    "mobile-chatgpt-start-prompt.md",
    ".github/workflows/prepare-mobile-run-ledger.yml",
    "VERSION-RECORD.md",
):
    p = ROOT / name
    data = p.read_bytes()
    while b"\r\r\n" in data:
        data = data.replace(b"\r\r\n", b"\r\n")
    p.write_bytes(data)
