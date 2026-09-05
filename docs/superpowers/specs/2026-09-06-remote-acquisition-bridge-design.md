# Remote Acquisition Bridge Design / 遠端取得橋接設計

## Goal / 目標

Close the transport gap of ChatGPT Scheduled Task hosts without weakening canonical discovery, source-media integrity, or visible non-text delivery gates. / 在不降低 canonical discovery、來源媒體完整性與真正非文字圖片交付門檻的前提下，補足 ChatGPT Scheduled Task 宿主的 transport 缺口。

## Root cause / 根因

The repository already has canonical CNA pagination, China News day-0/day-minus-1 acquisition, source-byte decoding, hashing, and local attachment materialization. The failing Scheduled Task host can open pages and execute local Python, but cannot perform the required POST/ZIP/source-byte network operations. Native image search also cannot reliably mint a current-event image object from a known article image. This is a cross-host transport boundary, not a scoring or image-selection defect. / repository 已具備 CNA 分頁、中新社 day-0/day-minus-1、來源 bytes 解碼／雜湊與本機附件物化；失敗宿主能開頁、能執行 Python，卻無法完成必要的 POST／ZIP／來源圖片 bytes 網路操作，原生圖片搜尋也無法穩定把已知文章圖片升格為當期 image object。這是跨宿主 transport 邊界，不是評分或選圖缺陷。

## Design / 設計

1. A strict request validator accepts only an issue-comment envelope bound to one `run_id`, 40-character `main_sha`, exact window, and either `source_scan` or `media_fetch`.
2. An `issue_comment` GitHub Actions workflow runs from the default branch, rejects unauthorized actors and stale main identities, executes the existing canonical CNA/China News acquisition/materialization code, and writes run-scoped outputs to `run-logs` without modifying `main`. GDELT remains on its existing truthful degraded fallback because its 24-hour archive volume is not connector-safe.
3. Media results contain normalized JPEG files plus byte/hash/dimension receipts. The Scheduled Task retrieves each file through the GitHub connector with `encoding=base64`, decodes it through the existing image materializer, and uses the already-probed local attachment handoff. A tool result, URL, or Markdown image is still not delivery.
4. Source-scan results preserve the configured routes, exact window, every admitted row, and source-row ledger so candidate audit resumes without repeating discovery.
5. Scheduled Task prompt installation gains an executable verifier for the emitted payload and optional exact-ID readback. A launcher, extension contamination, truncation, or hash mismatch fails before enablement.

## Failure semantics / 失敗語意

The bridge is selected only after direct host transport fails and the GitHub write/read plus Actions capabilities are proven. Any missing capability, request validation error, stale main, download failure, artifact hash mismatch, base64 handoff failure, or absent visible attachment leaves the same run at its current boundary. No replacement run, fabricated coverage, or image PASS is allowed. / 只有 direct host transport 失敗且 GitHub 讀寫與 Actions 能力已證明時才選用橋接。任何能力缺失、request 驗證錯誤、main 過期、下載失敗、artifact 雜湊不符、base64 handoff 失敗或缺少可見附件，都讓同一 run 留在原邊界；不得另建 run、捏造 coverage 或圖片 PASS。

## Scope / 範圍

This change adds the bridge, prompt verifier, base64 byte input, workflow contract, documentation, and tests. It does not change Public Value V2, selection thresholds, Reader layout, the formal daily 06:00 task, or the deleted ten-minute validation automation. / 本次只新增橋接、prompt verifier、base64 bytes 輸入、workflow 契約、文件與測試；不改 Public Value V2、選稿門檻、Reader 版型、正式每日 06:00 或已刪除的十分鐘驗收 automation。
