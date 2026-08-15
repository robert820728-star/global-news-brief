#!/usr/bin/env python3
"""Fail-closed publisher for a validated daily news brief."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

import validate_map_decisions
import validate_news_brief
import manage_candidate_audit


ROOT = Path(__file__).resolve().parents[1]


def local_attachment_path(value: str) -> Path:
    if value.startswith("sandbox:"):
        value = value.removeprefix("sandbox:")
    return Path(value)


def validate_canonical_map_pixels(path: Path, label: str) -> list[str]:
    errors: list[str] = []
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return errors
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((320, 320))
            pixels = list(image.getdata())
    except (OSError, ValueError) as error:
        return [f"{label} 無法讀取地圖像素：{error}"]
    if not pixels:
        return [f"{label} 地圖沒有可驗收像素"]
    yellow = 0
    blue = 0
    for red, green, blue_value in pixels:
        if (
            abs(red - 243) <= 20
            and abs(green - 230) <= 20
            and abs(blue_value - 184) <= 20
        ):
            yellow += 1
        if blue_value > red + 20 and blue_value > green + 10:
            blue += 1
    total = len(pixels)
    if yellow / total < 0.01:
        errors.append(f"{label} 未檢出核准的淡黃色陸地底色 #f3e6b8")
    if blue / total > 0.05:
        errors.append(f"{label} 藍色背景比例過高，不符合 yellow-admin-v2")
    return errors


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
                elif field == "map":
                    errors.extend(
                        validate_canonical_map_pixels(
                            local, f"{event_id}.{field}.assets[{index}]"
                        )
                    )
        images = event.get("images", {})
        if isinstance(images, dict):
            for check_group in ("source_checks", "professional_source_checks"):
                for index, check in enumerate(images.get(check_group, []), start=1):
                    if not isinstance(check, dict):
                        continue
                    path = check.get("evidence_path")
                    if not isinstance(path, str):
                        continue
                    local = local_attachment_path(path)
                    if not local.is_file() or local.stat().st_size < 1:
                        errors.append(
                            f"{event_id}.images.{check_group}[{index}] 檢查證據不存在或為空：{path}"
                        )
    return errors


def candidate_confirmation_errors(audit: dict, manifest: dict, source_pool: dict) -> list[str]:
    errors = manage_candidate_audit.validate(audit, source_pool)
    runs = audit.get("runs", [])
    if not runs:
        return errors + ["候選稽核沒有本輪紀錄"]
    latest = runs[-1]
    selected_ids = {
        candidate.get("selected_event_id")
        for candidate in latest.get("candidates", [])
        if candidate.get("decision") == "selected"
    }
    selected_ids.discard(None)
    manifest_ids = {
        event.get("event_id") for event in manifest.get("events", []) if isinstance(event, dict)
    }
    if selected_ids != manifest_ids:
        errors.append("候選稽核的入選事件與 manifest 不一致；禁止漏放達標事件或額外補新聞")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--source-pool", default=str(ROOT / "news-source-pool.json"))
    parser.add_argument("--brief", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    audit_path = Path(args.audit)
    source_pool_path = Path(args.source_pool)
    brief_path = Path(args.brief)
    if not manifest_path.is_file():
        print("RELEASE BLOCKED: manifest 不存在", file=sys.stderr)
        return 2
    if not audit_path.is_file() or not source_pool_path.is_file():
        print("RELEASE BLOCKED: 候選稽核或固定來源池不存在", file=sys.stderr)
        return 2
    if not brief_path.is_file() or not brief_path.read_text(encoding="utf-8").strip():
        print("RELEASE BLOCKED: 讀者版草稿不存在或為空；回到 render", file=sys.stderr)
        return 2

    try:
        manifest = validate_news_brief.load_json(manifest_path)
        audit = validate_news_brief.load_json(audit_path)
        source_pool = validate_news_brief.load_json(source_pool_path)
        brief = brief_path.read_text(encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"RELEASE BLOCKED: {error}", file=sys.stderr)
        return 2

    errors = []
    errors.extend(candidate_confirmation_errors(audit, manifest, source_pool))
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
        "candidate_audit": str(audit_path.resolve()),
        "brief": str(release_path.resolve()),
        "sha256": digest,
        "validators": {
            "source_pool_candidates_and_images": "passed",
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
