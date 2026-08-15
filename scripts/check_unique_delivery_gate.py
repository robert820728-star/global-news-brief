#!/usr/bin/env python3
"""Repository invariant and delivery-time revalidation for the canonical news gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

CANONICAL_GATE = "scripts/publish_news_brief.py"
RELEASE_FILENAMES = ("news-brief.md", "release-receipt.json")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _arg(name: str) -> str | None:
    try:
        i = sys.argv.index(name)
    except ValueError:
        return None
    return sys.argv[i + 1] if i + 1 < len(sys.argv) else None


def _json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as e:
        errors.append(f"{label} 無法讀取：{e}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} 必須是物件")
        return None
    return value


def _visual_paths(manifest: dict[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for event in manifest.get("events", []):
        if not isinstance(event, dict):
            continue
        eid = str(event.get("event_id", "event"))
        for field in ("map", "charts", "images"):
            block = event.get(field)
            if not isinstance(block, dict):
                continue
            for i, asset in enumerate(block.get("assets", []), 1):
                raw = asset.get("path") if isinstance(asset, dict) else None
                if isinstance(raw, str) and raw:
                    result[f"{eid}.{field}.assets[{i}]"] = Path(raw.removeprefix("sandbox:"))
            if field == "images":
                for group in ("source_checks", "professional_source_checks"):
                    for i, check in enumerate(block.get(group, []), 1):
                        raw = check.get("evidence_path") if isinstance(check, dict) else None
                        if isinstance(raw, str) and raw:
                            result[f"{eid}.images.{group}[{i}]"] = Path(raw.removeprefix("sandbox:"))
    return result


def _runtime_revalidation_errors(root: Path) -> list[str]:
    """Called *inside* the canonical publisher immediately before it emits bytes."""
    if "--deliver-receipt" not in sys.argv:
        return []
    errors: list[str] = []
    receipt_arg, checkpoint_arg = _arg("--deliver-receipt"), _arg("--checkpoint")
    if not receipt_arg or not checkpoint_arg:
        return ["canonical delivery 必須同時提供 receipt 與目前 checkpoint"]
    receipt = _json(Path(receipt_arg), "release receipt", errors)
    if receipt is None:
        return errors
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        return errors + ["release receipt.artifacts 必須是物件"]
    required = ("checkpoint", "manifest", "audit", "source_pool", "brief", "release")
    paths: dict[str, Path] = {}
    for name in required:
        item = artifacts.get(name)
        raw = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw, str) or not raw:
            errors.append(f"receipt 缺少 artifact：{name}")
            continue
        path = Path(raw)
        paths[name] = path
        if not path.is_file():
            errors.append(f"receipt artifact 不存在：{name}")
        elif item.get("sha256") != _sha(path):
            errors.append(f"receipt artifact 已變更：{name}")
    if errors:
        return errors
    try:
        if paths["checkpoint"].resolve() != Path(checkpoint_arg).resolve():
            return ["receipt checkpoint 不是目前執行 checkpoint"]
    except OSError:
        return ["checkpoint 路徑無法解析"]

    cp = _json(paths["checkpoint"], "checkpoint", errors)
    manifest = _json(paths["manifest"], "manifest", errors)
    audit = _json(paths["audit"], "candidate audit", errors)
    pool = _json(paths["source_pool"], "source pool", errors)
    try:
        brief = paths["brief"].read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        errors.append(f"reader brief 無法讀取：{e}")
        brief = ""
    if errors or None in (cp, manifest, audit, pool):
        return errors

    publisher = sys.modules.get("__main__")
    required_helpers = ("checkpoint_errors", "candidate_errors", "attachment_errors", "validate_map_decisions", "validate_news_brief")
    if publisher is None or any(not hasattr(publisher, name) for name in required_helpers):
        return ["delivery revalidation 無法取得 canonical publisher validators"]
    errors += publisher.checkpoint_errors(cp, manifest, audit, paths)
    errors += publisher.candidate_errors(audit, manifest, pool)
    errors += publisher.attachment_errors(manifest)
    errors += publisher.validate_map_decisions.validate(manifest)
    errors += publisher.validate_news_brief.validate_brief_text(manifest, brief)

    visuals = _visual_paths(manifest)
    before: dict[str, str] = {}
    for label, path in visuals.items():
        if not path.is_file():
            errors.append(f"{label} 不存在：{path}")
        else:
            before[label] = _sha(path)
    for label, path in visuals.items():
        if path.is_file() and label in before and _sha(path) != before[label]:
            errors.append(f"{label} 在交付驗證期間遭變更")
    return errors


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    scripts = root / "scripts"
    publisher = scripts / "publish_news_brief.py"
    if not publisher.is_file():
        return [f"缺少唯一發布器：{CANONICAL_GATE}"]
    for path in scripts.rglob("*"):
        if (not path.is_file() or "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}
                or path.name in {"publish_news_brief.py", "check_unique_delivery_gate.py"}):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for filename in RELEASE_FILENAMES:
            if filename in text:
                errors.append(f"偵測到替代交付路徑：{path.relative_to(root)} 含保留發布檔名 {filename}")
    prompt = root / "daily-schedule-prompt.md"
    if not prompt.is_file():
        errors.append("缺少 daily-schedule-prompt.md")
    else:
        text = prompt.read_text(encoding="utf-8")
        marker = "DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py"
        deliver = "--deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>"
        if text.count(marker) != 1:
            errors.append("daily-schedule-prompt.md 必須且只能宣告一次 DELIVERY_GATE_CANONICAL")
        if text.count(deliver) != 1:
            errors.append("daily-schedule-prompt.md 必須且只能宣告一次 canonical receipt 交付命令")
    errors += _runtime_revalidation_errors(root)
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    errors = validate_repository(Path(p.parse_args().root))
    for error in errors:
        print("FAIL:", error)
    if not errors:
        print("OK: unique delivery gate")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
