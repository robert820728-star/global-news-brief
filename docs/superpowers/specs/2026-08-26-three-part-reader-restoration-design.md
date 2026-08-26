# Three-Part Reader Restoration Design

## Decision

Restore the user-approved reader presentation contract as the sole production layout:

1. `# 每日新聞讀者版`
2. manifest-derived `統計期間：...`
3. the current six-dimension scoring explanation
4. `## 今日總覽`
5. `## 逐條詳報`
6. `## 後續觀察`

This is a presentation-only restoration. Discovery, Public Value V2, coverage accounting, verification, media evidence, recovery, run ownership, and publication readiness remain unchanged.

## Detailed Story Contract

Each selected event keeps its manifest event ID and uses this ordered structure:

- `### <event_id>. <title> - <grade>`
- `**時間：**`
- `**來源：**`
- `**地圖：**` only when a verified map asset exists
- `**資料圖表：**` only when a verified chart asset exists
- `**圖片：**` only when a verified source-image asset exists
- `**事件細節：**`
- `**各方說法：**` only when substantive differing positions exist
- `**分析：**`

Two consecutive event blocks are separated by exactly one `---`. The last event has no trailing separator.

## Media Truthfulness

The restored layout does not restore the former no-image placeholder. If no visible verified asset exists, the corresponding visual field is omitted. Internal omission notes remain in evidence and receipts only. Claim-critical visual requirements continue to fail closed through the manifest and publisher gates.

## Header and Internal Data

Do not restore historical reader-visible run IDs, commit SHAs, release markers, candidate counts, or repair logs. Those remain internal. The current title, statistical window, and scoring rubric are retained.

## Implementation Boundary

- Promote the existing field-based validation semantics to the only canonical reader validator.
- Remove the simplified section-per-board story validator and its CLI layout identifier rather than retaining a compatibility mode.
- Synchronize the template, settings, INSTALL, schedule/mobile prompts, rule matrix, active skill references, tests, and version record.
- Keep historical documents as historical evidence; active documents must not describe the simplified layout as current.

## Acceptance

- A valid three-part reader passes the same validator used by the publisher and unique-delivery gate.
- The simplified `板塊標題 → 標題｜評級 → 摘要 → 評級評論` reader fails.
- Missing required fields, wrong event order, wrong follow-up text, visible omission placeholders, attachment drift, and separator drift fail.
- The complete repository suite and bootstrap-capsule verification pass after generated artifacts are rebuilt.

