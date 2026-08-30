# Historical mobile run reference / 歷史 mobile run 參考

`DEPRECATED_NON_EXECUTABLE_MOBILE_NEWS_PATH`

This file is not a daily-news prompt. It must not be loaded, copied, summarized, or used to start, resume, score, verify, illustrate, render, or publish a daily-news run.

本檔不是每日新聞執行指令。不得載入、複製、摘要或用於開始、恢復、評分、查證、圖片處理、渲染或發布每日新聞。

All manual, single-run, test, first-run, recurring, and resume executions use the verified desktop/local-project `full-runtime` described by `INSTALL.md` and `scheduled-task-prompt-template.md`. A host that cannot download, take a direct screenshot, materialize a file, and deliver a visible local attachment must stop before occurrence creation and discovery.

所有手動、單次、測試、首次、循環 occurrence 與恢復執行，均使用 `INSTALL.md` 與 `scheduled-task-prompt-template.md` 規定的 desktop/local-project `full-runtime`。無法下載、直接截圖、物化檔案及交付可見本機附件的宿主，必須在 occurrence 與 discovery 前停止。

Historical mobile ledgers and artifacts may be inspected only to import the first incomplete stage into a full-runtime checkpoint. They cannot be advanced in place and cannot establish publication authority. Their formats remain documented in `docs/mobile-run-ledger.md` and `schemas/mobile-run-log.schema.json` solely for audit and recovery compatibility.

歷史 mobile ledger 與 artifacts 只能用來定位 first incomplete stage，並匯入 full-runtime checkpoint；不得原地推進，也沒有發布權威。其格式僅為稽核與恢復相容性保留於 `docs/mobile-run-ledger.md` 與 `schemas/mobile-run-log.schema.json`。

Image delivery follows `VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE`: original files and original quality are not required. Full-runtime may immediately screenshot a traceable same-event image from the cited article, an official page, a wire service, or a reliable republication. An external URL, Markdown hotlink, path string, caption, or broken placeholder is not delivery.

圖片交付遵守 `VISIBLE_IMAGE_OVER_ORIGINAL_FILE_GATE`：不要求原始檔或原畫質。full-runtime 可立即截取引用文章、官方頁、通訊社或可靠轉載頁中可追溯的同事件圖片。外部 URL、Markdown 熱連結、路徑字串、圖說或破圖框都不算交付。
