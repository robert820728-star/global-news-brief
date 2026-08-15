#!/usr/bin/env python3
"""Fail-closed publisher for a validated daily news brief."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import validate_map_decisions
import validate_news_brief


def local_attachment_path(value: str) -> Path:
    if value.startswith("sandbox:"):
        value = value.removeprefix("sandbox:")
    return Path(value)


def attachment_errors(manifest: dict) -> list[str]:
    errors: list[str] = []
    for event in manifest.get("events", []):
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id", "事件")
        for field in ("map", "charts", "images"):
            result = event.get(field, {})
            assets = result.get("assets", []) if isinstance(result, dict) else []
            for index, asset in enumerate(assets, start=1):
                path = asset.get("path") if isinstance(asset, dict) else None
                if not isinstance(path, str):
                    continue
                local = local_attachment_path(path)
                if not local.is_file() or local.stat().st_size < 1:
                    errors.append(
                        f"{event_id}.{field}.assets[{index}] 附件不存在或為空：{path}"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    brief_path = Path(args.brief)
    if not manifest_path.is_file():
        print("RELEASE BLOCKED: manifest 不存在", file=sys.stderr)
        return 2
    if not brief_path.is_file() or not brief_path.read_text(encoding="utf-8").strip():
        print("RELEASE BLOCKED: 讀者版草稿不存在或為空；回到 render", file=sys.stderr)
        return 2

    try:
        manifest = validate_news_brief.load_json(manifest_path)
        brief = brief_path.read_text(encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"RELEASE BLOCKED: {error}", file=sys.stderr)
        return 2

    errors = []
    errors.extend(attachment_errors(manifest))
    errors.extend(validate_map_decisions.validate(manifest))
    errors.extend(validate_news_brief.validate_brief_text(manifest, brief))
    if errors:
        print("RELEASE BLOCKED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print("ACTION: 執行 recover_news_run.py plan，修復後重新發布", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    release_path = output_dir / "news-brief.md"
    receipt_path = output_dir / "release-receipt.json"
    release_path.write_text(brief, encoding="utf-8")
    digest = hashlib.sha256(brief.encode("utf-8")).hexdigest()
    receipt = {
        "status": "ready",
        "published_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "manifest": str(manifest_path.resolve()),
        "brief": str(release_path.resolve()),
        "sha256": digest,
        "validators": {
            "map_decisions": "passed",
            "manifest_and_brief": "passed",
        },
    }
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(release_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
