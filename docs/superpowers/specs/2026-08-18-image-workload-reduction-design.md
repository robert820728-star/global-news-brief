# Image Workload Reduction Design

## Goal

Reduce mobile ChatGPT image processing and delivery pressure without changing source coverage, the C-or-above publication floor, or the selected source image.

## Approved Design

- Default to one attached source image per event.
- Allow a second image only when it contributes materially different reader-visible information; never attach more than two source images.
- Let one qualified official or professional image satisfy both the cited-source image check and the professional-visual check when the same asset genuinely meets both contracts. Keep both audit trails.
- Compute SHA-256 after acquisition. Reuse the local file, resize result, and visual-acceptance result for identical bytes within the run.
- Keep the existing 640 px, JPEG/WebP quality 75–82, under-200 KB preference and original-image fallback.
- Perform MIME, decode, dimensions, and hash checks before visual inspection. Open and visually accept each unique hash once; repeat model inspection only when relevance or date remains uncertain.
- Build a map only when location or spatial extent materially improves understanding. Browser rendering remains the final fallback.

## Scope Boundary

No new external cache, database, service, source reduction, grade-based image exemption, or replacement image is introduced. Maps, charts, and source images remain separate output types.

## Acceptance

The manifest rejects more than two source images and duplicate image bytes. Contract tests require the one-image default, justified second-image exception, SHA reuse, one-time visual acceptance, 640 px delivery, and browser-last fallback.
