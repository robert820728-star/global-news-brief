#!/usr/bin/env python3
"""Idempotently migrate checkpoint validation to verified runtime capsules."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/news_run_checkpoint.py"


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"migration anchor not found: {old!r}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'BOOTSTRAP_SCHEMA_VERSION = "1.0.0"',
        'BOOTSTRAP_SCHEMA_VERSION = "1.1.0"',
    )
    text = replace_once(
        text,
        'if receipt.get("materialization_method") != "github-connector":\n'
        '        errors.append("bootstrap.materialization_method 必須是 github-connector")',
        'if receipt.get("materialization_method") != "github-connector-capsule":\n'
        '        errors.append("bootstrap.materialization_method 必須是 github-connector-capsule")',
    )
    text = replace_once(
        text,
        'if receipt.get("materialization_scope") != "full-commit-tree":\n'
        '        errors.append("bootstrap.materialization_scope 必須是 full-commit-tree")',
        'if receipt.get("materialization_scope") != "verified-runtime-capsule":\n'
        '        errors.append("bootstrap.materialization_scope 必須是 verified-runtime-capsule")',
    )
    anchor = (
        '    try:\n'
        '        workspace = Path(str(receipt.get("workspace_root", ""))).resolve()\n'
    )
    capsule_block = (
        '    capsule = receipt.get("capsule")\n'
        '    if not isinstance(capsule, dict):\n'
        '        errors.append("bootstrap.capsule 必須是物件")\n'
        '    else:\n'
        '        manifest_blob_sha = str(capsule.get("manifest_blob_sha", ""))\n'
        '        if len(manifest_blob_sha) != 40 or not HEX_RE.fullmatch(manifest_blob_sha):\n'
        '            errors.append("bootstrap.capsule.manifest_blob_sha 無效")\n'
        '        for field in ("manifest_sha256", "payload_sha256", "runtime_fingerprint"):\n'
        '            value = str(capsule.get(field, ""))\n'
        '            if len(value) != 64 or not HEX_RE.fullmatch(value):\n'
        '                errors.append(f"bootstrap.capsule.{field} 無效")\n'
        '        chunks = capsule.get("chunks")\n'
        '        if not isinstance(chunks, list) or not chunks:\n'
        '            errors.append("bootstrap.capsule.chunks 必須是非空陣列")\n'
        '        elif capsule.get("chunk_count") != len(chunks):\n'
        '            errors.append("bootstrap.capsule.chunk_count 不符")\n'
        '\n'
    )
    if capsule_block not in text:
        if anchor not in text:
            raise RuntimeError("workspace validation anchor not found")
        text = text.replace(anchor, capsule_block + anchor, 1)
    TARGET.write_text(text, encoding="utf-8")
    print("checkpoint bootstrap migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
