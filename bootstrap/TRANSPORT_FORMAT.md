# Bootstrap capsule transport framing

The runtime capsule is transported through the GitHub connector as UTF-8 text. The connector may truncate a very long single line even when the file itself is small, so capsule chunks are deliberately **line framed**.

Current format (`capsule-manifest.json` schema `1.1.0`):

- logical chunk payload: up to 8192 Base64 characters;
- canonical line width: 256 ASCII characters;
- canonical line ending: LF (`\n`) after every line, including the last line;
- retrieval block: 8 lines (at most 2048 Base64 characters plus line endings);
- each chunk records raw-file SHA-256/size plus unwrapped encoded SHA-256/size;
- each retrieval block records `start_line`, `end_line`, raw byte `size`, and SHA-256.

A scheduled Stage -1 run must fetch chunks **by the line ranges declared in each chunk's `blocks` list**, write each block exactly, verify the block SHA-256 and size locally, concatenate verified blocks in order, then verify the complete chunk SHA-256 and size. It must not request an entire chunk in one connector response.

For lower mobile connector pressure, the normal path may request one **16-line** range spanning two adjacent declared 8-line blocks. `bootstrap/bootstrap_progress.py verify-grouped` must split that response at the declared boundary and verify the original size and SHA-256 of both blocks independently. A grouped response is useful only if both blocks pass. Otherwise discard the grouped response and fall back to the original 8-line block requests; this changes transport batching, not the capsule schema or verification boundary.

The line framing is transport-only. `bootstrap_loader.py` removes the canonical line breaks after validating each raw chunk and reconstructs the original Base64 stream before decoding the `tar.xz` payload.

If a block fetch is truncated or altered, only that block is retried. Each exact commit and line range gets **one initial attempt plus at most three retries**, with bounded backoff of **2, 5, and 10 seconds** when the host permits it. Record each attempt's byte size, SHA-256, and error in `bootstrap-progress.json`. Never re-download or rewrite earlier verified chunks. No unverified block, chunk, payload, or runtime file may be used to initialize the news checkpoint.
