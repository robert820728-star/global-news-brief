#!/usr/bin/env python3
"""Repository-level invariant checker for the one and only delivery gate."""
from __future__ import annotations

import argparse
from pathlib import Path

CANONICAL_GATE = "scripts/publish_news_brief.py"
RELEASE_FILENAMES = ("news-brief.md", "release-receipt.json")


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    scripts = root / "scripts"
    publisher = scripts / "publish_news_brief.py"
    if not publisher.is_file():
        return [f"缺少唯一發布器：{CANONICAL_GATE}"]

    for path in scripts.rglob("*"):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.suffix.lower() in {".pyc", ".pyo"}
            or path.name in {"publish_news_brief.py", "check_unique_delivery_gate.py"}
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for filename in RELEASE_FILENAMES:
            if filename in text:
                errors.append(
                    f"偵測到替代交付路徑：{path.relative_to(root)} 含保留發布檔名 {filename}"
                )

    prompt = root / "daily-schedule-prompt.md"
    if prompt.is_file():
        text = prompt.read_text(encoding="utf-8")
        marker = "DELIVERY_GATE_CANONICAL=scripts/publish_news_brief.py"
        if text.count(marker) != 1:
            errors.append("daily-schedule-prompt.md 必須且只能宣告一次 DELIVERY_GATE_CANONICAL")
        if "--checkpoint <checkpoint>" not in text:
            errors.append("daily-schedule-prompt.md 的唯一發布命令缺少 --checkpoint")
        deliver = "--deliver-receipt <release-dir>/release-receipt.json --checkpoint <checkpoint>"
        if deliver not in text:
            errors.append("daily-schedule-prompt.md 缺少 canonical gate 的 receipt 綁定交付命令")
        if text.count(deliver) != 1:
            errors.append("daily-schedule-prompt.md 必須且只能宣告一次 canonical receipt 交付命令")
    else:
        errors.append("缺少 daily-schedule-prompt.md")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    errors = validate_repository(Path(args.root))
    for error in errors:
        print("FAIL:", error)
    if not errors:
        print("OK: unique delivery gate")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
