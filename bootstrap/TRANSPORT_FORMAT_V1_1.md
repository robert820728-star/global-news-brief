# Capsule transport v1.1

This file intentionally duplicates the essential transport contract in a short form for scheduled bootstrap runs.

- Each logical Base64 chunk is at most 8192 characters.
- Each chunk file is wrapped at exactly 256 ASCII characters per line, except the final line.
- Every line, including the final line, ends with LF (`\n`).
- Connector retrieval is performed in blocks of at most 8 lines (2048 Base64 characters plus LF bytes).
- `capsule-manifest.json` records the complete chunk SHA-256/size, the unwrapped Base64 SHA-256/size, line count, and SHA-256/size for every retrieval block.
- A scheduled run fetches each block with `start_line`/`end_line`, verifies it locally, concatenates verified blocks, then verifies the complete chunk before invoking `bootstrap_loader.py`.
- Whole-chunk connector reads are forbidden in Stage -1 because a long single response can be truncated.
