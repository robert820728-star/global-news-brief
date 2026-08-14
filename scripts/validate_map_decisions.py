#!/usr/bin/env python3
"""Validate map-decision coverage and catch likely geographic false negatives.

This validator is intentionally conservative: it never auto-creates a map. It blocks a
completed/ready run when an event with strong spatial signals is marked not_required
without a concrete exception rationale, forcing build-news-maps to review that event.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SPATIAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "marine_or_coastal": (
        "海域", "沿岸", "海岸", "海峽", "港口", "珊瑚礁", "礁區", "大堡礁",
        "海洋公園", "海洋保護區", "漁場", "海洋污染", "海洋熱浪", "航道",
        "ocean", "marine", "coast", "coastal", "strait", "port", "reef",
    ),
    "habitat_or_wildlife": (
        "棲地", "繁殖地", "覓食區", "物種分布", "遷徙", "遷移", "遷徙帶",
        "遷徙路線", "遷徙廊道", "人獸衝突", "保護區", "國家公園", "濕地",
        "habitat", "migration", "migratory", "breeding ground", "protected area",
    ),
    "spread_or_route": (
        "擴散", "蔓延", "路線", "航線", "跨境", "跨州", "跨省", "多州",
        "多省", "多國", "多地", "流域", "救援區域", "污染範圍", "影響範圍",
        "spread", "route", "cross-border", "multi-state", "multi-country",
    ),
    "hazard_location": (
        "震央", "地震", "海嘯", "火山", "野火", "洪水", "乾旱", "火場",
        "警戒區", "事故位置", "封鎖線", "邊境衝突", "戰區",
        "earthquake", "tsunami", "volcano", "wildfire", "flood", "drought",
    ),
}

WEAK_RATIONALES = {
    "不需要地圖", "無需地圖", "地點已在正文", "只是統計新聞", "統計新聞",
    "只有一個地名", "位置不重要", "not required", "not_required",
}


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("manifest 根節點必須是物件")
    return data


def event_text(event: dict[str, Any]) -> str:
    selection = event.get("selection") if isinstance(event.get("selection"), dict) else {}
    verification = event.get("verification") if isinstance(event.get("verification"), dict) else {}
    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    claims = verification.get("claims") if isinstance(verification.get("claims"), list) else []
    claim_text = " ".join(
        str(item.get("text", "")) for item in claims if isinstance(item, dict)
    )
    parts = [
        event.get("title", ""), selection.get("category", ""),
        selection.get("impact_scope", ""), selection.get("reason", ""), claim_text,
        detail.get("event_details", ""), detail.get("analysis", ""),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def spatial_hits(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for group, patterns in SPATIAL_PATTERNS.items():
        found = [pattern for pattern in patterns if pattern.lower() in text]
        if found:
            hits[group] = found
    return hits


def rationale_is_specific(rationale: Any, hits: dict[str, list[str]]) -> bool:
    if not isinstance(rationale, str) or len(rationale.strip()) < 20:
        return False
    compact = re.sub(r"\s+", "", rationale).lower()
    if compact in {re.sub(r"\s+", "", item).lower() for item in WEAK_RATIONALES}:
        return False
    # A geographic exception must explicitly acknowledge at least one detected signal
    # or explain the absence of a meaningful spatial relationship/range/route.
    hit_terms = {term.lower() for terms in hits.values() for term in terms}
    acknowledgement = any(term in rationale.lower() for term in hit_terms)
    explanation_terms = (
        "不影響理解", "沒有空間關係", "無空間關係", "無範圍差異", "不涉及路線",
        "不涉及擴散", "位置僅為", "僅為所在地", "不具定位價值",
        "does not affect", "no spatial relationship", "location is incidental",
    )
    explanation = any(term in rationale.lower() for term in explanation_terms)
    return acknowledgement and explanation


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    events = data.get("events")
    if not isinstance(events, list):
        return ["manifest.events 必須是陣列"]

    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"events[{index}] 必須是物件")
            continue
        event_id = str(event.get("event_id") or f"events[{index}]")
        map_result = event.get("map")
        if not isinstance(map_result, dict):
            errors.append(f"{event_id}.map 缺少地圖需求判定")
            continue
        required = map_result.get("required")
        status = map_result.get("status")
        rationale = map_result.get("rationale")
        if not isinstance(required, bool):
            errors.append(f"{event_id}.map.required 尚未完成布林判定")
            continue
        if status == "pending":
            errors.append(f"{event_id}.map 仍為 pending，不得視為 build-news-maps 完成")
            continue

        hits = spatial_hits(event_text(event))
        if not required and hits:
            if status != "not_required":
                errors.append(f"{event_id}.map 判定不需要時 status 必須是 not_required")
            if not rationale_is_specific(rationale, hits):
                summary = ", ".join(
                    f"{group}={','.join(terms[:4])}" for group, terms in hits.items()
                )
                errors.append(
                    f"{event_id}.map 疑似漏判：事件命中強地理訊號（{summary}），"
                    "若仍判定 not_required，rationale 必須明確承認命中的地理訊號並說明"
                    "為何位置／範圍／路線不增加理解；否則重跑 build-news-maps。"
                )

        if required and status == "not_required":
            errors.append(f"{event_id}.map required=true 不得標記 not_required")

    stage = data.get("stage_status")
    if isinstance(stage, dict) and stage.get("build-news-maps") == "completed" and errors:
        errors.append("build-news-maps 不得 completed：仍有事件未通過 map decision coverage/gate")
    if data.get("final_status") == "ready" and errors:
        errors.append("final_status 不得 ready：地圖需求判定尚未通過驗證")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="news-event-manifest.json")
    args = parser.parse_args()
    try:
        data = load_manifest(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"MAP DECISION VALIDATION FAILED: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        print("MAP DECISION VALIDATION FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("MAP DECISION VALIDATION OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
