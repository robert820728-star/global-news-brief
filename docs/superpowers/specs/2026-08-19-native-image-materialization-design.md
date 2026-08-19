# Native Image Materialization Design

## Goal

Make daily-news image delivery deterministic before the ChatGPT handoff. A source URL is not delivery evidence. The runtime must first create a validated local JPEG or WebP asset and a compact manifest that the delivery layer can upload as a native media attachment.

## Chosen approach

Add one small command-line materializer to the existing pipeline. It accepts a run id and a JSON list of selected event image candidates, downloads at most the declared candidate for each entry, validates the response and decoded pixels, applies EXIF orientation, converts unsupported color modes, scales the longest edge to 640 pixels, and writes deterministic files under an output directory. It also writes one manifest entry per input, including success or a bounded failure reason.

External CDN hosting and direct Markdown rendering are rejected because they do not prove that ChatGPT displayed media. No new service, stage, schema version, renderer, or publishing workflow is introduced.

## Interface and data flow

Input JSON contains `event_id`, `source_url`, and optional `alt` and `credit`. Output assets are named `<safe-event-id>-<index>.jpg` or `.webp`. The manifest records `event_id`, source URL, local path, MIME type, dimensions, SHA-256, alt, credit, and status. Invalid or unreachable images produce a failed entry without fabricating an asset.

The existing delivery prompt consumes only successful manifest entries and uploads the local bytes through a native media-capable surface. Text, URLs, Markdown image syntax, or internal tool previews remain insufficient delivery evidence.

## Error handling and limits

Downloads use a bounded timeout and maximum byte limit. Non-image content, decode failures, zero-sized images, and unsupported output formats fail closed per image, not per news run. Existing reader, audit, grading, and verification checkpoints remain untouched.

## Verification

Freeze three materializer behaviors: a valid JPEG creates an asset and manifest record; corrupt bytes are rejected without an output asset; a large image is resized so its longest edge is 640 pixels. Existing pipeline-contract tests must continue to pass.
