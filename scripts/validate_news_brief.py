#!/usr/bin/env python3
"""Validate the shared event manifest, stage ownership, and reader brief."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


EVENT_ID_RE = re.compile(r"^[A-Z]{3}-\d{2,3}$")
DATE_LINE_RE = re.compile(r"^\d{4}/\d{2}/\d{2} 每日新聞$")
DETAIL_HEADING_RE = re.compile(r"^### ([A-Z]{3}-\d{2,3})\. (.+) - (SS|[SABC][+-]?)$")
ALLOWED_GRADES = {
    "SS", "S+", "S", "S-", "A+", "A", "A-",
    "B+", "B", "B-", "C+", "C", "C-",
}
GRADE_BASE_RANK = {"C": 1, "B": 2, "A": 3, "S": 4}
SINGLE_SOURCE_NOTE = "目前僅找到一個可靠來源，尚無其他獨立來源交叉確認。"
STAGE_OWNERS = {
    "verify-news-events": "verification",
    "build-news-maps": "map",
    "build-news-charts": "charts",
    "collect-news-images": "images",
}
RECOVERABLE_STAGES = {
    "verify-news-events",
    "build-news-maps",
    "build-news-charts",
    "collect-news-images",
    "render",
    "validate",
}
REQUIRED_H2 = ["今日總覽", "逐條詳報", "後續觀察"]
BACKEND_PHRASES = [
    "本則 B 以上事件",
    "已下載或截圖",
    "可顯示附件",
    "強制嘗試",
    "下載失敗",
    "來源無圖",
    "視覺驗收成功",
]
FORBIDDEN_RENDER_TOKENS = (
    "async_image_group",
    "charts_widget_v2",
    "genui",
    "<gallery",
    "<carousel",
)
FIGURE_PREFIXES = {
    "map": "地圖",
    "charts": "資料圖表",
    "images": "圖",
}
CHINESE_NUMERALS = ("一", "二", "三", "四", "五")


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("JSON 根節點必須是物件")
    return data


def _need(obj: dict[str, Any], keys: list[str], label: str, errors: list[str]) -> None:
    for key in keys:
        if key not in obj:
            errors.append(f"{label} 缺少欄位 {key}")


def _validate_asset_path(path: Any, label: str, errors: list[str]) -> None:
    if not isinstance(path, str) or not path:
        errors.append(f"{label} 缺少附件路徑")
        return
    if path.startswith(("http://", "https://")):
        errors.append(f"{label} 使用網路直連，必須改成本地附件：{path}")
    elif not path.startswith(("/", "sandbox:/")):
        errors.append(f"{label} 路徑必須是絕對路徑或 sandbox 絕對路徑：{path}")


def _validate_media_result(
    event_id: str,
    field: str,
    result: Any,
    errors: list[str],
) -> set[str]:
    label = f"{event_id}.{field}"
    if not isinstance(result, dict):
        errors.append(f"{label} 必須是物件")
        return set()

    required_keys = ["required", "status", "assets", "omission_reason"]
    if field in {"map", "charts"}:
        required_keys.append("rationale")
    _need(result, required_keys, label, errors)

    status = result.get("status")
    allowed = {"pending", "ready", "not_required", "omitted"}
    if status not in allowed:
        errors.append(f"{label}.status 無效：{status}")
    required = result.get("required")
    if not isinstance(required, bool):
        errors.append(f"{label}.required 必須是布林值")
    elif required and status not in {"pending", "ready", "omitted"}:
        errors.append(f"{label} 已判定需要，status 不得是 {status}")
    elif not required and status not in {"pending", "not_required"}:
        errors.append(f"{label} 已判定不需要，status 不得是 {status}")

    assets = result.get("assets", [])
    if not isinstance(assets, list):
        errors.append(f"{label}.assets 必須是陣列")
        return set()
    if status == "ready" and not assets:
        errors.append(f"{label} 標示 ready 但沒有附件")
    if status in {"not_required", "omitted"} and assets:
        errors.append(f"{label} 標示 {status} 時不應保留附件")
    if status == "omitted" and not result.get("omission_reason"):
        errors.append(f"{label} 省略時必須保存後台原因")
    if field == "images" and len(assets) > 5:
        errors.append(f"{label} 超過每則 5 張圖片上限")
    if field == "charts" and len(assets) > 3:
        errors.append(f"{label} 超過每則 3 張自製資料圖表上限")

    paths: set[str] = set()
    for index, asset in enumerate(assets, start=1):
        asset_label = f"{label}.assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{asset_label} 必須是物件")
            continue
        path = asset.get("path")
        _validate_asset_path(path, asset_label, errors)
        if isinstance(path, str):
            if path in paths:
                errors.append(f"{label} 重複使用附件：{path}")
            paths.add(path)
        if not asset.get("caption"):
            errors.append(f"{asset_label} 缺少圖說")
        if asset.get("visual_checked") is not True:
            errors.append(f"{asset_label} 尚未完成視覺驗收")
        for dimension in ("width", "height"):
            value = asset.get(dimension)
            if not isinstance(value, int) or value < 1:
                errors.append(f"{asset_label}.{dimension} 必須是大於零的整數")
        if field == "map":
            urls = asset.get("source_urls")
            if not isinstance(urls, list) or not urls:
                errors.append(f"{asset_label} 缺少定位依據來源")
        elif field == "charts":
            urls = asset.get("source_urls")
            names = asset.get("source_names")
            if not isinstance(urls, list) or not urls or not isinstance(names, list) or not names:
                errors.append(f"{asset_label} 缺少資料來源")
            if asset.get("data_checked") is not True:
                errors.append(f"{asset_label} 尚未完成數據驗收")
            chart_type = asset.get("chart_type")
            chart_purpose = asset.get("chart_purpose")
            if chart_type not in {"metric_card", "bar", "line", "area", "scatter", "pie", "table"}:
                errors.append(f"{asset_label}.chart_type 無效")
            if chart_purpose not in {"single_metric", "comparison", "trend", "proportion", "distribution", "lookup"}:
                errors.append(f"{asset_label}.chart_purpose 無效")
            if not isinstance(asset.get("data_points"), int) or asset.get("data_points", 0) < 1:
                errors.append(f"{asset_label} 必須包含至少一個具體數值")
            labels = asset.get("labels")
            values = asset.get("numeric_values")
            if not isinstance(labels, list) or len(labels) < 1 or not all(
                isinstance(item, str) and item.strip() for item in labels
            ):
                errors.append(f"{asset_label} 必須列出至少一個實際繪製的資料標籤")
            if not isinstance(values, list) or len(values) < 1 or not all(
                isinstance(item, (int, float)) and not isinstance(item, bool) for item in values
            ):
                errors.append(f"{asset_label} 必須列出至少一個實際繪製的具體數值")
            if isinstance(labels, list) and isinstance(values, list) and len(labels) != len(values):
                errors.append(f"{asset_label} 資料標籤與數值數量不一致")
            if isinstance(values, list) and asset.get("data_points") != len(values):
                errors.append(f"{asset_label}.data_points 必須等於實際繪製數值數量")
            if not isinstance(asset.get("unit"), str) or not asset.get("unit", "").strip():
                errors.append(f"{asset_label} 缺少一致的數值單位")
            if chart_type == "metric_card":
                if chart_purpose != "single_metric":
                    errors.append(f"{asset_label} 單項數據卡的用途必須是 single_metric")
                if isinstance(values, list) and len(values) != 1:
                    errors.append(f"{asset_label} 單項數據卡只能呈現一個具體數值")
                if not isinstance(asset.get("highlight_reason"), str) or not asset.get("highlight_reason", "").strip():
                    errors.append(f"{asset_label} 單項數據卡缺少凸顯理由")
            elif isinstance(values, list) and len(values) < 2:
                errors.append(f"{asset_label} 比較或趨勢圖至少需要兩個同口徑數值")
            if chart_type in {"bar", "line", "area", "scatter"}:
                if not isinstance(asset.get("x_axis_label"), str) or not asset.get("x_axis_label", "").strip():
                    errors.append(f"{asset_label} 缺少 X 軸標籤")
                if not isinstance(asset.get("y_axis_label"), str) or not asset.get("y_axis_label", "").strip():
                    errors.append(f"{asset_label} 缺少 Y 軸標籤")
            if chart_type == "line" and isinstance(values, list) and len(values) < 3:
                errors.append(f"{asset_label} 折線圖至少需要三個時間點；兩點比較應改用柱狀圖")
        else:
            if asset.get("time_checked") is not True:
                errors.append(f"{asset_label} 尚未完成時間驗收")
            if not asset.get("source_name") or not asset.get("source_url"):
                errors.append(f"{asset_label} 缺少圖片來源")
            if asset.get("kind") not in {
                "official_information", "professional_information", "news_photo"
            }:
                errors.append(f"{asset_label}.kind 無效")
    if field == "images":
        kinds = [
            asset.get("kind") for asset in assets
            if isinstance(asset, dict)
        ]
        seen_news_photo = False
        for kind in kinds:
            if kind == "news_photo":
                seen_news_photo = True
            elif seen_news_photo and kind in {"official_information", "professional_information"}:
                errors.append(
                    f"{label} 圖片順序錯誤：官方或專業資訊圖必須排在新聞照片之前"
                )
                break
    return paths


def _is_grade_b_or_above(grade: Any) -> bool:
    if grade == "SS":
        return True
    if not isinstance(grade, str) or not grade:
        return False
    return GRADE_BASE_RANK.get(grade[0], 0) >= GRADE_BASE_RANK["B"]


def _validate_image_gate(
    event: dict[str, Any],
    final_status: Any,
    errors: list[str],
) -> None:
    """Block final delivery when B+ source-image discovery or attachment work is incomplete."""
    if not _is_grade_b_or_above(event.get("grade")):
        return

    event_id = str(event.get("event_id", "事件"))
    images = event.get("images")
    if not isinstance(images, dict):
        return
    if images.get("required") is not True:
        errors.append(f"{event_id}.images：B 級以上事件必須啟用圖片檢查")

    checks = images.get("source_checks")
    if not isinstance(checks, list) or not checks:
        errors.append(f"{event_id}.images 缺少來源頁圖片檢查紀錄")
        return

    verification = event.get("verification")
    sources = verification.get("sources", []) if isinstance(verification, dict) else []
    expected_urls = {
        source.get("url") for source in sources
        if isinstance(source, dict) and isinstance(source.get("url"), str)
    }
    checked_urls: set[str] = set()
    usable_found = False
    for index, check in enumerate(checks, start=1):
        label = f"{event_id}.images.source_checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{label} 必須是物件")
            continue
        _need(
            check,
            ["source_url", "checked", "usable_image_found", "attempts", "outcome"],
            label,
            errors,
        )
        source_url = check.get("source_url")
        if isinstance(source_url, str) and source_url:
            checked_urls.add(source_url)
        if check.get("checked") is not True:
            errors.append(f"{label} 尚未完成來源頁圖片檢查")
        if not isinstance(check.get("attempts"), int) or check.get("attempts", 0) < 1:
            errors.append(f"{label}.attempts 必須至少為 1")
        if check.get("outcome") not in {"attached", "no_usable_image", "acquisition_failed"}:
            errors.append(f"{label}.outcome 無效")
        if check.get("usable_image_found") is True:
            usable_found = True

    missing_urls = expected_urls - checked_urls
    if missing_urls:
        errors.append(
            f"{event_id}.images 尚未檢查所有引用來源頁：{', '.join(sorted(missing_urls))}"
        )

    if final_status != "ready":
        return
    if usable_found:
        if images.get("status") != "ready" or not images.get("assets"):
            errors.append(
                f"{event_id}.images 已找到可用來源圖片，未附上合格附件前不得完成簡報"
            )
    elif images.get("status") != "omitted":
        errors.append(
            f"{event_id}.images 未找到可用來源圖片時，必須以 omitted 保存後台原因"
        )

    professional_required = images.get("professional_visual_required")
    professional_status = images.get("professional_visual_status")
    professional_checks = images.get("professional_source_checks")
    if not isinstance(professional_required, bool):
        errors.append(f"{event_id}.images.professional_visual_required 必須是布林值")
        return
    if professional_status not in {"pending", "ready", "not_required", "not_available"}:
        errors.append(f"{event_id}.images.professional_visual_status 無效")
        return
    if professional_required:
        if not isinstance(professional_checks, list) or not professional_checks:
            errors.append(f"{event_id}.images 缺少官方專業圖資搜尋紀錄")
            return
        professional_found = any(
            isinstance(item, dict) and item.get("usable_image_found") is True
            for item in professional_checks
        )
        professional_assets = [
            asset for asset in images.get("assets", [])
            if isinstance(asset, dict)
            and asset.get("kind") in {"official_information", "professional_information"}
        ]
        if final_status == "ready" and professional_found:
            if professional_status != "ready" or not professional_assets:
                errors.append(
                    f"{event_id}.images 已找到官方專業圖資，未附上合格專業資訊圖前不得完成簡報"
                )
        elif final_status == "ready" and professional_status != "not_available":
            errors.append(
                f"{event_id}.images 未找到官方專業圖資時，必須記錄 not_available"
            )
        if professional_status == "not_available" and not images.get("professional_omission_reason"):
            errors.append(f"{event_id}.images 專業圖資無法取得時必須保存具體原因")
    elif professional_status != "not_required":
        errors.append(
            f"{event_id}.images 不需要專業圖資時，professional_visual_status 必須是 not_required"
        )


def validate_manifest_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _need(
        data,
        ["schema_version", "run", "sections", "stage_status", "recovery", "events", "final_status"],
        "manifest",
        errors,
    )
    if data.get("schema_version") != "1.1.0":
        errors.append("schema_version 必須是 1.1.0")

    run = data.get("run")
    if not isinstance(run, dict):
        errors.append("run 必須是物件")
    else:
        _need(
            run,
            ["generated_at", "timezone", "window_start", "window_end", "language"],
            "run",
            errors,
        )
        try:
            window_start = datetime.fromisoformat(str(run.get("window_start")))
            window_end = datetime.fromisoformat(str(run.get("window_end")))
            if window_end - window_start != timedelta(hours=24):
                errors.append("run 的新聞時間窗必須精確為 24 小時")
        except ValueError:
            errors.append("run.window_start 與 run.window_end 必須是可解析的 ISO 8601 時間")

    final_status = data.get("final_status")
    if final_status not in {"draft", "ready", "failed"}:
        errors.append(f"final_status 無效：{final_status}")
    stage_status = data.get("stage_status")
    expected_stages = [
        "select-news-events",
        "verify-news-events",
        "build-news-maps",
        "build-news-charts",
        "collect-news-images",
        "recover-news-run",
        "render",
        "validate",
    ]
    if not isinstance(stage_status, dict):
        errors.append("stage_status 必須是物件")
    else:
        _need(stage_status, expected_stages, "stage_status", errors)
        allowed_stage_states = {"pending", "running", "completed", "failed", "skipped"}
        for stage_name, state in stage_status.items():
            if stage_name not in expected_stages:
                errors.append(f"stage_status 含有未知階段：{stage_name}")
            elif state not in allowed_stage_states:
                errors.append(f"stage_status.{stage_name} 狀態無效：{state}")
        if final_status == "ready":
            for stage_name in expected_stages:
                if stage_status.get(stage_name) != "completed":
                    errors.append(f"final_status 為 ready 時 {stage_name} 必須 completed")

    recovery = data.get("recovery")
    if not isinstance(recovery, dict):
        errors.append("recovery 必須是物件")
    else:
        _need(
            recovery,
            ["status", "max_attempts_per_target", "attempts", "unresolved_targets"],
            "recovery",
            errors,
        )
        recovery_status = recovery.get("status")
        if recovery_status not in {"pending", "recovering", "completed", "exhausted"}:
            errors.append(f"recovery.status 無效：{recovery_status}")
        max_attempts = recovery.get("max_attempts_per_target")
        if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 5:
            errors.append("recovery.max_attempts_per_target 必須介於 1 至 5")
            max_attempts = 3
        attempts = recovery.get("attempts")
        highest_attempt: dict[tuple[Any, Any], int] = {}
        if not isinstance(attempts, list):
            errors.append("recovery.attempts 必須是陣列")
        else:
            for index, attempt in enumerate(attempts, start=1):
                label = f"recovery.attempts[{index}]"
                if not isinstance(attempt, dict):
                    errors.append(f"{label} 必須是物件")
                    continue
                _need(
                    attempt,
                    [
                        "target_stage", "event_id", "attempt", "started_at",
                        "ended_at", "outcome", "error_code", "message",
                    ],
                    label,
                    errors,
                )
                stage = attempt.get("target_stage")
                if stage not in RECOVERABLE_STAGES:
                    errors.append(f"{label}.target_stage 無效：{stage}")
                number = attempt.get("attempt")
                if not isinstance(number, int) or number < 1:
                    errors.append(f"{label}.attempt 必須至少為 1")
                    continue
                key = (stage, attempt.get("event_id"))
                expected = highest_attempt.get(key, 0) + 1
                if number != expected:
                    errors.append(f"{label}.attempt 應為 {expected}，實際為 {number}")
                highest_attempt[key] = number
                # max_attempts_per_target is a per-strategy rotation threshold;
                # total attempts may exceed it while recovery continues with a new strategy.
                if attempt.get("outcome") not in {"succeeded", "failed"}:
                    errors.append(f"{label}.outcome 無效")
        unresolved = recovery.get("unresolved_targets")
        if not isinstance(unresolved, list):
            errors.append("recovery.unresolved_targets 必須是陣列")
            unresolved = []
        if final_status == "ready":
            if recovery_status != "completed":
                errors.append("final_status 為 ready 時 recovery.status 必須 completed")
            if unresolved:
                errors.append("final_status 為 ready 時不得有未解決恢復目標")
        if recovery_status == "exhausted" and final_status != "failed":
            errors.append("recovery exhausted 時 final_status 必須 failed")

    sections = data.get("sections")
    section_codes: set[str] = set()
    if not isinstance(sections, list) or not sections:
        errors.append("sections 必須是非空陣列")
    else:
        orders: set[int] = set()
        for index, section in enumerate(sections, start=1):
            label = f"sections[{index}]"
            if not isinstance(section, dict):
                errors.append(f"{label} 必須是物件")
                continue
            code = section.get("code")
            order = section.get("order")
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{3}", code):
                errors.append(f"{label}.code 必須是三個大寫英文字母")
            elif code in section_codes:
                errors.append(f"板塊代碼重複：{code}")
            else:
                section_codes.add(code)
            if not section.get("name"):
                errors.append(f"{label} 缺少板塊名稱")
            if not isinstance(order, int) or order < 1:
                errors.append(f"{label}.order 必須是正整數")
            elif order in orders:
                errors.append(f"板塊順序重複：{order}")
            else:
                orders.add(order)

    events = data.get("events")
    if not isinstance(events, list):
        errors.append("events 必須是陣列")
        return errors

    event_ids: set[str] = set()
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"events[{index}] 必須是物件")
            continue
        event_id = event.get("event_id")
        label = event_id if isinstance(event_id, str) else f"events[{index}]"
        _need(
            event,
            [
                "event_id", "primary_section", "title", "grade", "selection",
                "verification", "map", "charts", "images", "detail",
            ],
            label,
            errors,
        )
        if not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id):
            errors.append(f"{label}.event_id 格式錯誤")
        elif event_id in event_ids:
            errors.append(f"事件編號重複：{event_id}")
        else:
            event_ids.add(event_id)
        section = event.get("primary_section")
        if section not in section_codes:
            errors.append(f"{label} 使用不存在的板塊：{section}")
        if isinstance(event_id, str) and isinstance(section, str) and not event_id.startswith(section + "-"):
            errors.append(f"{label} 的事件編號與主要板塊不一致")
        if not event.get("title"):
            errors.append(f"{label} 缺少標題")
        if event.get("grade") not in ALLOWED_GRADES:
            errors.append(f"{label} 等級無效：{event.get('grade')}")

        selection = event.get("selection")
        if not isinstance(selection, dict):
            errors.append(f"{label}.selection 必須是物件")
        else:
            _need(
                selection,
                [
                    "dedup_key", "category", "impact_scope", "reason",
                    "candidate_urls", "news_time", "event_time",
                ],
                f"{label}.selection",
                errors,
            )
            if not isinstance(selection.get("candidate_urls"), list) or not selection.get("candidate_urls"):
                errors.append(f"{label}.selection.candidate_urls 必須是非空陣列")

        verification = event.get("verification")
        if not isinstance(verification, dict):
            errors.append(f"{label}.verification 必須是物件")
        else:
            _need(
                verification,
                [
                    "status", "finding", "search_performed", "independent_source_count",
                    "sources", "claims", "uncertainties", "source_limit_note",
                    "positions", "reader_wording", "verified_at",
                ],
                f"{label}.verification",
                errors,
            )
            if verification.get("status") == "completed" and verification.get("search_performed") is not True:
                errors.append(f"{label} 已完成驗證但沒有記錄多來源搜尋")
            if final_status == "ready" and verification.get("status") != "completed":
                errors.append(f"{label} 尚未完成來源驗證")
            if final_status == "ready" and verification.get("finding") == "pending":
                errors.append(f"{label} 尚未形成來源判斷")
            sources = verification.get("sources", [])
            if not isinstance(sources, list):
                errors.append(f"{label}.verification.sources 必須是陣列")
                sources = []
            source_ids: set[str] = set()
            groups: set[str] = set()
            for source_index, source_item in enumerate(sources, start=1):
                source_label = f"{label}.verification.sources[{source_index}]"
                if not isinstance(source_item, dict):
                    errors.append(f"{source_label} 必須是物件")
                    continue
                _need(
                    source_item,
                    [
                        "source_id", "name", "url", "role", "producer",
                        "independence_group", "published_at", "accessed_at",
                        "evidence_type", "claim_ids", "limitations",
                    ],
                    source_label,
                    errors,
                )
                source_id = source_item.get("source_id")
                if not isinstance(source_id, str) or not source_id:
                    errors.append(f"{source_label} 缺少 source_id")
                elif source_id in source_ids:
                    errors.append(f"{label} 來源編號重複：{source_id}")
                else:
                    source_ids.add(source_id)
                group = source_item.get("independence_group")
                if isinstance(group, str) and group:
                    groups.add(group)
            declared_count = verification.get("independent_source_count")
            if not isinstance(declared_count, int) or declared_count < 0:
                errors.append(f"{label}.verification.independent_source_count 無效")
            elif declared_count != len(groups):
                errors.append(
                    f"{label} 獨立來源數量不一致：宣告 {declared_count}，實際群組 {len(groups)}"
                )
            finding = verification.get("finding")
            if declared_count == 1:
                if finding != "single_reliable_source":
                    errors.append(f"{label} 只有一個獨立來源時 finding 必須是 single_reliable_source")
                if verification.get("source_limit_note") != SINGLE_SOURCE_NOTE:
                    errors.append(f"{label} 缺少固定的單一來源說明")
            elif isinstance(declared_count, int) and declared_count > 1 and finding == "single_reliable_source":
                errors.append(f"{label} 已有多個獨立來源，不應標示 single_reliable_source")

            claims = verification.get("claims", [])
            if not isinstance(claims, list):
                errors.append(f"{label}.verification.claims 必須是陣列")
            else:
                claim_ids: set[str] = set()
                for claim_index, claim in enumerate(claims, start=1):
                    claim_label = f"{label}.verification.claims[{claim_index}]"
                    if not isinstance(claim, dict):
                        errors.append(f"{claim_label} 必須是物件")
                        continue
                    _need(claim, ["claim_id", "text", "status", "source_ids"], claim_label, errors)
                    claim_id = claim.get("claim_id")
                    if isinstance(claim_id, str):
                        if claim_id in claim_ids:
                            errors.append(f"{label} 主張編號重複：{claim_id}")
                        claim_ids.add(claim_id)
                    for source_id in claim.get("source_ids", []):
                        if source_id not in source_ids:
                            errors.append(f"{claim_label} 引用不存在的來源：{source_id}")

        map_paths = _validate_media_result(label, "map", event.get("map"), errors)
        chart_paths = _validate_media_result(label, "charts", event.get("charts"), errors)
        image_paths = _validate_media_result(label, "images", event.get("images"), errors)
        _validate_image_gate(event, final_status, errors)
        if final_status == "ready":
            for field_name in ("map", "charts", "images"):
                field_value = event.get(field_name)
                if isinstance(field_value, dict) and field_value.get("status") == "pending":
                    errors.append(f"{label}.{field_name} 尚未完成判斷")
        overlap = map_paths & image_paths
        if overlap:
            errors.append(f"{label} 同一附件同時出現在地圖與圖片：{', '.join(sorted(overlap))}")

        detail = event.get("detail")
        if not isinstance(detail, dict):
            errors.append(f"{label}.detail 必須是物件")
        else:
            _need(
                detail,
                ["overview_time", "time", "event_details", "positions", "analysis", "follow_up"],
                f"{label}.detail",
                errors,
            )
            for key in ("overview_time", "time", "event_details", "analysis"):
                if not detail.get(key):
                    errors.append(f"{label}.detail.{key} 不得為空")
    return errors


def validate_stage_data(
    before: dict[str, Any],
    after: dict[str, Any],
    stage: str,
) -> list[str]:
    errors: list[str] = []
    owned = STAGE_OWNERS.get(stage)
    if owned is None:
        return [f"不支援的階段：{stage}"]

    before_events = before.get("events")
    after_events = after.get("events")
    if not isinstance(before_events, list) or not isinstance(after_events, list):
        return ["前後資料都必須含有 events 陣列"]
    if len(before_events) != len(after_events):
        errors.append(f"{stage} 不得新增或刪除事件")

    before_ids = [item.get("event_id") for item in before_events if isinstance(item, dict)]
    after_ids = [item.get("event_id") for item in after_events if isinstance(item, dict)]
    if before_ids != after_ids:
        errors.append(f"{stage} 不得重新排序或重新編號事件")

    before_root = copy.deepcopy(before)
    after_root = copy.deepcopy(after)
    before_root.pop("events", None)
    after_root.pop("events", None)
    if before_root != after_root:
        errors.append(f"{stage} 不得修改事件以外的根層資料")

    for index, (old, new) in enumerate(zip(before_events, after_events), start=1):
        if not isinstance(old, dict) or not isinstance(new, dict):
            errors.append(f"events[{index}] 必須是物件")
            continue
        event_id = old.get("event_id", f"events[{index}]")
        keys = set(old) | set(new)
        for key in sorted(keys):
            if key == owned:
                continue
            if old.get(key) != new.get(key):
                errors.append(f"{stage} 越權修改 {event_id}.{key}")
    return errors


def _event_blocks(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^### ([A-Z]{3}-\d{2,3})\. .+$", text))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.start():end]
    return blocks


def validate_brief_text(data: dict[str, Any], text: str) -> list[str]:
    errors = validate_manifest_data(data)
    nonempty = [line.strip() for line in text.splitlines() if line.strip()]
    if not nonempty or not DATE_LINE_RE.fullmatch(nonempty[0]):
        errors.append("讀者版第一個非空白行必須是 YYYY/MM/DD 每日新聞")

    h2 = re.findall(r"(?m)^## (.+)$", text)
    if h2 != REQUIRED_H2:
        errors.append("讀者版只能有今日總覽、逐條詳報、後續觀察三個二級標題，且順序固定")

    for phrase in BACKEND_PHRASES:
        if phrase in text:
            errors.append(f"讀者版含有後台文字：{phrase}")
    for token in FORBIDDEN_RENDER_TOKENS:
        if token in text:
            errors.append(f"讀者版使用禁止的圖廊、疊圖或動態元件：{token}")

    events = data.get("events", [])
    expected_ids = [event.get("event_id") for event in events if isinstance(event, dict)]
    detail_matches = [
        match for match in (DETAIL_HEADING_RE.fullmatch(line.strip()) for line in text.splitlines())
        if match
    ]
    actual_detail_ids = [match.group(1) for match in detail_matches]
    if actual_detail_ids != expected_ids:
        errors.append("逐條詳報的事件順序、數量或編號與事件資料不一致")

    blocks = _event_blocks(text)
    separators = len(re.findall(r"(?m)^---$", text))
    expected_separators = max(0, len(expected_ids) - 1)
    if separators != expected_separators:
        errors.append(f"事件分隔線數量錯誤：應為 {expected_separators}，實際為 {separators}")

    table_rows: dict[str, tuple[str, str, str]] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and EVENT_ID_RE.fullmatch(cells[0]):
            table_rows[cells[0]] = (cells[1], cells[2], cells[3])

    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id", "")
        title = event.get("title", "")
        grade = event.get("grade", "")
        detail = event.get("detail", {}) if isinstance(event.get("detail"), dict) else {}
        row = table_rows.get(event_id)
        if row is None:
            errors.append(f"今日總覽缺少事件 {event_id}")
        else:
            if row[0] != detail.get("overview_time"):
                errors.append(f"{event_id} 總覽時間與事件資料不一致")
            if row[1] != title or row[2] != grade:
                errors.append(f"{event_id} 總覽標題或等級與事件資料不一致")

        expected_heading = f"### {event_id}. {title} - {grade}"
        block = blocks.get(event_id)
        if block is None:
            errors.append(f"逐條詳報缺少事件 {event_id}")
            continue
        if not block.startswith(expected_heading):
            errors.append(f"{event_id} 詳報標題與事件資料不一致")
        required_labels = ["**時間：**", "**來源：**", "**事件細節：**", "**分析：**"]
        positions = [block.find(label) for label in required_labels]
        if any(position < 0 for position in positions):
            errors.append(f"{event_id} 缺少時間、來源、事件細節或分析欄")
        elif positions != sorted(positions):
            errors.append(f"{event_id} 詳報欄位順序錯誤")

        ordered_markers = [
            marker for marker in (
                "**時間：**", "**來源：**", "**地圖：**", "**資料圖表：**",
                "**圖片：**", "**事件細節：**", "**各方說法：**", "**分析：**",
            )
            if marker in block
        ]
        marker_positions = [block.find(marker) for marker in ordered_markers]
        if marker_positions != sorted(marker_positions):
            errors.append(f"{event_id} 地圖、資料圖表、圖片或文字欄位順序錯誤")

        verification = event.get("verification", {})
        if isinstance(verification, dict) and verification.get("finding") == "single_reliable_source":
            if SINGLE_SOURCE_NOTE not in block:
                errors.append(f"{event_id} 讀者版缺少單一來源說明")

        map_result = event.get("map", {})
        chart_result = event.get("charts", {})
        image_result = event.get("images", {})
        for field_key, field, result, marker in (
            ("map", "地圖", map_result, "**地圖：**"),
            ("charts", "資料圖表", chart_result, "**資料圖表：**"),
            ("images", "圖片", image_result, "**圖片：**"),
        ):
            if not isinstance(result, dict):
                continue
            assets = result.get("assets", []) if isinstance(result.get("assets"), list) else []
            if result.get("status") == "ready" and marker not in block:
                errors.append(f"{event_id} 有合格{field}但讀者版缺少{field}欄")
            asset_positions: list[int] = []
            for asset_index, asset in enumerate(assets, start=1):
                if not isinstance(asset, dict):
                    continue
                path = asset.get("path")
                caption = asset.get("caption")
                number = CHINESE_NUMERALS[asset_index - 1] if asset_index <= len(CHINESE_NUMERALS) else str(asset_index)
                expected_prefix = f"{FIGURE_PREFIXES[field_key]}{number}"
                if isinstance(path, str):
                    markdown_pattern = re.compile(
                        rf"!\[{re.escape(expected_prefix)}[^\]]*\]\({re.escape(path)}\)"
                    )
                    match = markdown_pattern.search(block)
                    if not match:
                        errors.append(
                            f"{event_id} {field}附件必須逐張使用 Markdown 並依序標示"
                            f"{expected_prefix}：{path}"
                        )
                    else:
                        asset_positions.append(match.start())
                if not isinstance(caption, str) or not caption.startswith(expected_prefix + "："):
                    errors.append(f"{event_id} {field}圖說必須以 {expected_prefix}：開頭")
                elif caption not in block:
                    errors.append(f"{event_id} 漏放{field}圖說：{caption}")
                elif isinstance(path, str):
                    path_position = block.find(path)
                    caption_position = block.find(caption)
                    if path_position >= 0 and caption_position <= path_position:
                        errors.append(f"{event_id} {expected_prefix}圖說必須緊接在附件之後")
            if asset_positions != sorted(asset_positions):
                errors.append(f"{event_id} {field}附件順序與 manifest 不一致")
    return errors


def print_result(errors: list[str]) -> int:
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="驗證最終事件資料")
    manifest.add_argument("--input", required=True)

    stage = subparsers.add_parser("stage", help="檢查子技能是否越權修改欄位")
    stage.add_argument("--stage", required=True, choices=sorted(STAGE_OWNERS))
    stage.add_argument("--before", required=True)
    stage.add_argument("--after", required=True)

    brief = subparsers.add_parser("brief", help="驗證事件資料與讀者版一致性")
    brief.add_argument("--manifest", required=True)
    brief.add_argument("--input", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "manifest":
            return print_result(validate_manifest_data(load_json(args.input)))
        if args.command == "stage":
            return print_result(
                validate_stage_data(load_json(args.before), load_json(args.after), args.stage)
            )
        manifest = load_json(args.manifest)
        text = Path(args.input).read_text(encoding="utf-8")
        return print_result(validate_brief_text(manifest, text))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
