# rc.46 Known-Gap Executable Adapters / 已知缺口可執行介面設計

## Outcome / 目標

Turn the three known failure classes into deterministic, testable repository interfaces: canonical Scheduled Task prompt installation, discovery-boundary proof, and source-media byte integrity. The repository must fail closed when the ChatGPT Scheduled Task host cannot supply a required transport; it must never claim that repository code can create a host attachment API that the host does not expose.

將三類已知失敗轉為可重現、可測試的 repository 介面：Scheduled Task canonical prompt 安裝、discovery 邊界證據、來源圖片原始 bytes 完整性。若 ChatGPT Scheduled Task 宿主缺少必要 transport，repository 必須明確 fail closed，不得宣稱 repository 程式能憑空補出宿主未提供的附件 API。

## Scope / 範圍

1. Add a prompt payload builder that copies `scheduled-task-prompt-template.md`, replaces exactly the two permitted placeholder lines, and emits a hash receipt. Diagnostic or smoke configuration is emitted as a separate installation-only sidecar and can never mutate the saved prompt.
2. Reject HTTP 2xx route probes that do not contain their configured exhaustion proof. JSON routes must parse and expose the configured path; text routes must contain their configured marker.
3. Extend image materialization with raw-source receipts and optional expected byte/hash/dimension assertions. Support an explicit local `source_bytes_path`, distinct from a webpage screenshot.
4. Update installation guidance and focused contracts. Preserve existing publication behavior outside these gates.

1. 新增 prompt payload builder：完整複製模板，只替換兩個允許的 placeholder 行，並輸出雜湊收據。診斷／smoke 設定只能存在於獨立的 installation-only sidecar，永不修改 saved prompt。
2. HTTP 2xx 若缺少設定的 exhaustion proof，不得判定 route ready。JSON route 必須可解析且指定 path 存在；文字 route 必須含指定 marker。
3. 圖片 materializer 新增原始來源收據及可選的 bytes／hash／尺寸期望值驗證；新增與頁面截圖語意分離的 `source_bytes_path`。
4. 更新安裝說明及 focused contracts，不改動這些 gate 以外的既有發布行為。

## Interfaces / 介面

### Canonical prompt builder

`scripts/build_scheduled_task_install_payload.py` accepts template, output directory, region, monitor type, resolved main SHA, and an optional test-extension JSON. It writes:

- `saved-prompt.txt`: exact template bytes after only the two authorized line substitutions.
- `install-extension.json`: validated, installation-only metadata; absent when no extension is supplied.
- `install-receipt.json`: source/output hashes, byte and character counts, substitutions, resolved SHA, and an explicit assertion that extension content was not embedded.

The builder rejects missing or duplicate placeholders, malformed SHA values, unknown extension keys, non-installation scope, or any request to mutate the saved prompt.

### Discovery proof

`fetch_source_routes.py` validates the initial response before it writes or admits a snapshot. `json_exhaustion_path` is proven by JSON parsing and key existence, including a present `null` value. `response_integrity_marker` proves only that a response is structurally complete; it is never reused as a source-exhaustion claim. Source exhaustion requires an empty terminal cursor, an explicit pagination-exhausted receipt, or an article at/before the window boundary. Failed proof is reported as `route_ready=false` with a bounded error and no admitted snapshot.

### Source-media receipt

Every successful materialization records the source byte count, SHA-256, decoded dimensions and format, plus `acquisition_method`. Expected source assertions are checked before the normalized output is written. `source_bytes_path` means complete source media bytes handed off by a connector or prior tool; `screenshot_path` remains a verified screenshot and is labeled separately.

## Non-goals / 非目標

- No automation is created or restored.
- The formal daily 06:00 task is not modified.
- No external proxy, hosted service, or undocumented ChatGPT API is introduced.
- A host without source-byte or attachment transport remains `HOST_CAPABILITY_UNAVAILABLE`; this is an honest runtime result, not a repository defect concealed as success.

- 不建立或恢復任何 automation。
- 不修改正式每日 06:00 task。
- 不新增外部 proxy、代管服務或未公開 ChatGPT API。
- 宿主若沒有 source-byte 或附件 transport，維持 `HOST_CAPABILITY_UNAVAILABLE`；這是誠實 runtime 結果，不得包裝成成功。

## Acceptance / 驗收

- Prompt output is byte-for-byte equal to the canonical template after exactly two substitutions; extension tokens never appear in it.
- A 2xx WAF/error page and malformed/missing JSON cursor cannot produce complete coverage.
- The published CNA smoke fixture records 171909 source bytes, 1024×478 and SHA-256 `6262c2e8d26f1881e8a2aeb800a13820f23c6192f42d5d7e8152709f7ccbb8c1` when transport is available.
- Expected-source mismatch creates no asset.
- Focused tests, full suite, capsule verification, and final-state audit pass before completion is claimed.
