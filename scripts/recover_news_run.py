#!/usr/bin/env python3
"""Plan and record bounded, stage-local recovery for a daily news run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


GRADE_RANK = {"C": 1, "B": 2, "A": 3, "S": 4}
RECOVERABLE_STAGES = {
    "verify-news-events",
    "build-news-maps",
    "build-news-charts",
    "collect-news-images",
    "render",
    "validate",
}


def load(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("manifest 根節點必須是物件")
    return data


def save(path: str, data: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def is_b_or_above(grade: Any) -> bool:
    if grade == "SS":
        return True
    return isinstance(grade, str) and bool(grade) and GRADE_RANK.get(grade[0], 0) >= 2


def target_key(stage: str, event_id: str | None) -> str:
    return f"{stage}:{event_id or '*'}"


def attempt_counts(data: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    recovery = data.get("recovery", {})
    attempts = recovery.get("attempts", []) if isinstance(recovery, dict) else []
    for item in attempts if isinstance(attempts, list) else []:
        if not isinstance(item, dict):
            continue
        key = target_key(str(item.get("target_stage", "")), item.get("event_id"))
        attempt = item.get("attempt")
        if isinstance(attempt, int):
            counts[key] = max(counts.get(key, 0), attempt)
    return counts


def recovery_plan(data: dict[str, Any]) -> list[dict[str, Any]]:
    recovery = data.get("recovery", {})
    max_attempts = recovery.get("max_attempts_per_target", 3) if isinstance(recovery, dict) else 3
    counts = attempt_counts(data)
    planned: dict[str, dict[str, Any]] = {}

    def add(stage: str, event_id: str | None, reason: str) -> None:
        key = target_key(stage, event_id)
        used = counts.get(key, 0)
        planned[key] = {
            "target_stage": stage,
            "event_id": event_id,
            "reason": reason,
            "next_attempt": used + 1,
            "attempts_remaining": max(0, int(max_attempts) - used),
            "exhausted": used >= int(max_attempts),
        }

    stages = data.get("stage_status", {})
    if isinstance(stages, dict):
        for stage, state in stages.items():
            if stage in RECOVERABLE_STAGES and state == "failed":
                add(stage, None, "階段狀態為 failed")

    for event in data.get("events", []) if isinstance(data.get("events"), list) else []:
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id")
        verification = event.get("verification", {})
        if isinstance(verification, dict) and verification.get("status") in {"pending", "failed"}:
            add("verify-news-events", event_id, "來源驗證未完成")

        map_result = event.get("map", {})
        if isinstance(map_result, dict) and map_result.get("required") is True:
            if map_result.get("status") in {"pending", "omitted"}:
                add("build-news-maps", event_id, "必要定位地圖未完成")

        charts = event.get("charts", {})
        if isinstance(charts, dict) and charts.get("required") is True:
            if charts.get("status") in {"pending", "omitted"}:
                add("build-news-charts", event_id, "必要資料圖表未完成")

        images = event.get("images", {})
        if not isinstance(images, dict) or not is_b_or_above(event.get("grade")):
            continue
        checks = images.get("source_checks", [])
        sources = verification.get("sources", []) if isinstance(verification, dict) else []
        checked_urls = {
            item.get("source_url") for item in checks
            if isinstance(item, dict) and item.get("checked") is True
        }
        expected_urls = {
            item.get("url") for item in sources
            if isinstance(item, dict) and isinstance(item.get("url"), str)
        }
        usable_found = any(
            isinstance(item, dict) and item.get("usable_image_found") is True
            for item in checks
        )
        if expected_urls - checked_urls:
            add("collect-news-images", event_id, "尚未檢查全部引用來源頁")
        elif images.get("status") == "pending":
            add("collect-news-images", event_id, "圖片階段仍為 pending")
        elif usable_found and (images.get("status") != "ready" or not images.get("assets")):
            add("collect-news-images", event_id, "已找到可用圖片但尚無合格附件")

        professional_required = images.get("professional_visual_required") is True
        professional_checks = images.get("professional_source_checks", [])
        professional_found = any(
            isinstance(item, dict) and item.get("usable_image_found") is True
            for item in professional_checks
        )
        professional_assets = [
            item for item in images.get("assets", [])
            if isinstance(item, dict)
            and item.get("kind") in {"official_information", "professional_information"}
        ]
        if professional_required and not professional_checks:
            add("collect-news-images", event_id, "尚未搜尋事件類型對應的官方專業圖資")
        elif professional_required and professional_found and (
            images.get("professional_visual_status") != "ready" or not professional_assets
        ):
            add("collect-news-images", event_id, "已找到官方專業圖資但尚無合格附件")
        elif professional_required and images.get("professional_visual_status") == "pending":
            add("collect-news-images", event_id, "官方專業圖資階段仍為 pending")

    return list(planned.values())


def ensure_recovery(data: dict[str, Any]) -> dict[str, Any]:
    recovery = data.setdefault(
        "recovery",
        {
            "status": "pending",
            "max_attempts_per_target": 3,
            "attempts": [],
            "unresolved_targets": [],
        },
    )
    return recovery


def record(args: argparse.Namespace) -> int:
    data = load(args.input)
    recovery = ensure_recovery(data)
    key = target_key(args.stage, args.event_id)
    counts = attempt_counts(data)
    attempt = counts.get(key, 0) + 1
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    recovery["attempts"].append(
        {
            "target_stage": args.stage,
            "event_id": args.event_id,
            "attempt": attempt,
            "started_at": args.started_at or now,
            "ended_at": now,
            "outcome": args.outcome,
            "error_code": args.error_code,
            "message": args.message,
        }
    )

    unresolved = {
        target_key(item.get("target_stage", ""), item.get("event_id")): item
        for item in recovery.get("unresolved_targets", [])
        if isinstance(item, dict)
    }
    if args.outcome == "succeeded":
        unresolved.pop(key, None)
    else:
        unresolved[key] = {
            "target_stage": args.stage,
            "event_id": args.event_id,
            "last_error_code": args.error_code,
            "last_message": args.message,
        }
    recovery["unresolved_targets"] = list(unresolved.values())

    limit = int(recovery.get("max_attempts_per_target", 3))
    if args.outcome == "failed" and attempt >= limit:
        recovery["status"] = "exhausted"
        data["final_status"] = "failed"
        data.setdefault("stage_status", {})["recover-news-run"] = "failed"
    elif args.outcome == "failed":
        recovery["status"] = "recovering"
        data.setdefault("stage_status", {})["recover-news-run"] = "running"
    else:
        remaining = recovery_plan(data)
        if any(not item["exhausted"] for item in remaining):
            recovery["status"] = "recovering"
            data.setdefault("stage_status", {})["recover-news-run"] = "running"
        elif remaining:
            recovery["status"] = "exhausted"
            data["final_status"] = "failed"
            data.setdefault("stage_status", {})["recover-news-run"] = "failed"
        else:
            recovery["status"] = "completed"
            recovery["unresolved_targets"] = []
            data.setdefault("stage_status", {})["recover-news-run"] = "completed"

    save(args.output, data)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--input", required=True)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--input", required=True)
    record_parser.add_argument("--output", required=True)
    record_parser.add_argument("--stage", required=True, choices=sorted(RECOVERABLE_STAGES))
    record_parser.add_argument("--event-id")
    record_parser.add_argument("--outcome", required=True, choices=["succeeded", "failed"])
    record_parser.add_argument("--error-code")
    record_parser.add_argument("--message", default="")
    record_parser.add_argument("--started-at")

    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(recovery_plan(load(args.input)), ensure_ascii=False, indent=2))
        return 0
    return record(args)


if __name__ == "__main__":
    raise SystemExit(main())
