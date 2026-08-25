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

import run_identity


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
    "修復紀錄",
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
MARKDOWN_IMAGE_RE = re.compile(
    r"(?m)^!\[([^\]\r\n]*)\]\(([^)\r\n]+)\)[ \t]*\r?$"
)
GENERIC_FOLLOW_UP_PHRASES = {
    "追蹤官方後續更新與實際影響。",
    "追蹤官方後續更新。",
    "追蹤官方是否更新影響範圍、數字或處置進度。",
    "追蹤是否出現其他獨立來源。",
}
FIGURE_PREFIXES = {
    "map": "地圖",
    "charts": "資料圖表",
    "images": "圖",
}
CHINESE_NUMERALS = ("一", "二", "三", "四", "五")
REDUNDANT_MAP_CAPTION_RE = re.compile(r"完整(?:世界|台灣|中國|板塊)?.{0,8}(?:地圖|底圖|行政界線)")
NUMERIC_MARKER_RE = re.compile(r"標記\s*[0-9０-９一二三四五六七八九十]+")
TRADITIONAL_CHINESE_LANGUAGE_RE = re.compile(r"繁體|正體|zh[-_](?:tw|hant)", re.IGNORECASE)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
PROFESSIONAL_VISUAL_RE = re.compile(
    r"颱風|風暴|豪雨|洪水|淹水|乾旱|熱浪|地震|海嘯|火山|野火|疫情|傳染病|"
    r"公共衛生|戰爭|軍事|航運|海峽|航道|漏油|油污|海洋污染|化學事故|核事故|"
    r"typhoon|storm|flood|drought|heatwave|earthquake|tsunami|volcano|wildfire|"
    r"outbreak|epidemic|war|military|shipping|oil spill|marine pollution",
    re.IGNORECASE,
)


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
    elif not (path.startswith("sandbox:/") or Path(path).is_absolute()):
        errors.append(f"{label} 路徑必須是絕對路徑或 sandbox 絕對路徑：{path}")


def _professional_visual_expected(event: dict[str, Any]) -> bool:
    selection = event.get("selection") if isinstance(event.get("selection"), dict) else {}
    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    text = " ".join(
        str(value) for value in (
            event.get("title", ""), selection.get("category", ""),
            selection.get("impact_scope", ""), selection.get("reason", ""),
            detail.get("event_details", ""), detail.get("analysis", ""),
        ) if value
    )
    return bool(PROFESSIONAL_VISUAL_RE.search(text))


def _validate_media_result(
    event_id: str,
    field: str,
    result: Any,
    errors: list[str],
    output_language: str = "",
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
    if field == "images" and len(assets) > 2:
        errors.append(f"{label} 超過每則 2 張圖片上限")
    if field == "charts" and len(assets) > 3:
        errors.append(f"{label} 超過每則 3 張自製資料圖表上限")

    paths: set[str] = set()
    image_hashes: set[str] = set()
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
        if field == "images":
            if asset.get("materialized_by") != "scripts/materialize_news_images.py":
                errors.append(
                    f"{asset_label}.materialized_by 必須是 scripts/materialize_news_images.py"
                )
            content_sha256 = asset.get("content_sha256")
            if not isinstance(content_sha256, str) or not re.fullmatch(
                r"[0-9a-f]{64}", content_sha256
            ):
                errors.append(f"{asset_label}.content_sha256 必須是小寫 SHA-256")
            elif content_sha256 in image_hashes:
                errors.append(f"{label} 重複圖片內容 SHA-256：{content_sha256}")
            else:
                image_hashes.add(content_sha256)
            if index == 2 and not (
                isinstance(asset.get("incremental_information"), str)
                and asset["incremental_information"].strip()
            ):
                errors.append(f"{asset_label} 第二張圖片必須說明新增資訊")
        for dimension in ("width", "height"):
            value = asset.get(dimension)
            if not isinstance(value, int) or value < 1:
                errors.append(f"{asset_label}.{dimension} 必須是大於零的整數")
        if field == "map":
            urls = asset.get("source_urls")
            if not isinstance(urls, list) or not urls:
                errors.append(f"{asset_label} 缺少定位依據來源")
            if asset.get("style_id") != "yellow-admin-v2":
                errors.append(
                    f"{asset_label} 未使用核准的 yellow-admin-v2 黃底行政界線風格"
                )
            if asset.get("style_reference") != "maps/style.json":
                errors.append(f"{asset_label} 未綁定 maps/style.json")
            if asset.get("generator") != "scripts/render_base_maps.py":
                errors.append(
                    f"{asset_label} 未使用 canonical renderer，禁止其他藍底或平台預設地圖"
                )
            labels = asset.get("place_labels")
            if not isinstance(labels, list) or not labels:
                errors.append(f"{asset_label} 缺少地名標籤；禁止只用數字標記")
            elif any(
                not isinstance(item, str)
                or not item.strip()
                or re.fullmatch(r"[0-9０-９一二三四五六七八九十]+", item.strip())
                for item in labels
            ):
                errors.append(f"{asset_label}.place_labels 必須是具體地名，不得使用 1、2、3 等純數字")
            elif TRADITIONAL_CHINESE_LANGUAGE_RE.search(output_language) and any(
                not CJK_RE.search(item) for item in labels
            ):
                errors.append(
                    f"{asset_label}.place_labels 必須符合輸出語言繁體中文，不得只使用英文或其他語言地名"
                )
            caption = asset.get("caption", "")
            if isinstance(caption, str) and REDUNDANT_MAP_CAPTION_RE.search(caption):
                errors.append(f"{asset_label} 圖說不得重複說明世界／板塊底圖或行政界線")
            if isinstance(caption, str) and NUMERIC_MARKER_RE.search(caption):
                errors.append(f"{asset_label} 圖說不得以標記1、2、3代替地名")
            event_section = label.split(".", 1)[0].split("-", 1)[0]
            expected_scope = "full_world" if event_section == "GLB" else "full_section"
            if asset.get("canvas_scope") != expected_scope:
                errors.append(
                    f"{asset_label} 必須顯示完整板塊底圖，禁止裁切或局部放大"
                )
            canonical_base_maps = {
                "TWN": "maps/generated/taiwan-counties-yellow-v2.png",
                "CHN": "maps/generated/china-provinces-yellow-v2.png",
                "GLB": "maps/generated/world-countries-pacific-robinson-yellow-v2.png",
            }
            expected_base_map = canonical_base_maps.get(event_section)
            if expected_base_map and asset.get("base_map") != expected_base_map:
                errors.append(
                    f"{asset_label} 未綁定 {event_section} canonical 完整板塊底圖"
                )
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
    """Block delivery unless every selected event has evidence-backed source-image checks."""

    event_id = str(event.get("event_id", "事件"))
    images = event.get("images")
    if not isinstance(images, dict):
        return
    if images.get("required") is not True:
        errors.append(f"{event_id}.images：所有入選事件都必須啟用來源圖片檢查")

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
    usable_source_urls: set[str] = set()
    detected_by_source: dict[str, set[str]] = {}
    for index, check in enumerate(checks, start=1):
        label = f"{event_id}.images.source_checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{label} 必須是物件")
            continue
        _need(
            check,
            [
                "source_url", "checked", "checked_at", "inspection_method",
                "evidence_path", "detected_image_urls", "usable_image_found",
                "attempts", "outcome", "failure_detail",
            ],
            label,
            errors,
        )
        source_url = check.get("source_url")
        if isinstance(source_url, str) and source_url:
            checked_urls.add(source_url)
        if check.get("checked") is not True:
            errors.append(f"{label} 尚未完成來源頁圖片檢查")
        checked_at = check.get("checked_at")
        if not isinstance(checked_at, str) or not checked_at.strip():
            errors.append(f"{label}.checked_at 必須記錄實際檢查時間")
        if check.get("inspection_method") not in {"browser", "html_extract", "official_api"}:
            errors.append(f"{label}.inspection_method 無效")
        evidence_path = check.get("evidence_path")
        _validate_asset_path(evidence_path, f"{label}.evidence_path", errors)
        detected_urls = check.get("detected_image_urls")
        if not isinstance(detected_urls, list) or any(
            not isinstance(url, str) or not url.startswith(("http://", "https://"))
            for url in detected_urls
        ):
            errors.append(f"{label}.detected_image_urls 必須是已檢出的圖片網址陣列")
        elif isinstance(source_url, str):
            detected_by_source[source_url] = set(detected_urls)
            if source_url in detected_urls:
                errors.append(f"{label} 文章頁網址不得冒充圖片網址")
        if not isinstance(check.get("attempts"), int) or check.get("attempts", 0) < 1:
            errors.append(f"{label}.attempts 必須至少為 1")
        if check.get("outcome") not in {"attached", "no_usable_image", "acquisition_failed"}:
            errors.append(f"{label}.outcome 無效")
        if check.get("usable_image_found") is True:
            usable_found = True
            if isinstance(source_url, str):
                usable_source_urls.add(source_url)
            if not detected_urls:
                errors.append(f"{label} 宣告找到圖片但沒有保存檢出的圖片網址")
            if check.get("outcome") != "attached":
                errors.append(f"{label} 找到可用圖片時 outcome 必須是 attached")
        elif check.get("outcome") == "no_usable_image" and not check.get("failure_detail"):
            errors.append(f"{label} 宣告來源無可用圖片時必須保存具體判定理由")
        if check.get("usable_image_found") is False and check.get("outcome") == "attached":
            errors.append(f"{label} 未找到可用圖片時 outcome 不得是 attached")
        if check.get("outcome") == "acquisition_failed" and final_status == "ready":
            errors.append(f"{label} 圖片取得失敗尚未恢復，必須送回 collect-news-images 重做")

    missing_urls = expected_urls - checked_urls
    if missing_urls:
        errors.append(
            f"{event_id}.images 尚未檢查所有引用來源頁：{', '.join(sorted(missing_urls))}"
        )

    if final_status != "ready":
        return
    assets = images.get("assets", []) if isinstance(images.get("assets"), list) else []
    if images.get("status") == "ready":
        materialization_path = images.get("materialization_manifest_path")
        if not isinstance(materialization_path, str) or not materialization_path:
            errors.append(f"{event_id}.images.ready 缺少 materialization_manifest_path")
        else:
            _validate_asset_path(
                materialization_path,
                f"{event_id}.images.materialization_manifest_path",
                errors,
            )
    asset_source_urls = {
        asset.get("source_url") for asset in assets if isinstance(asset, dict)
    }
    missing_attachments = usable_source_urls - asset_source_urls
    if missing_attachments:
        errors.append(
            f"{event_id}.images 找到來源圖片但缺少對應附件：{', '.join(sorted(missing_attachments))}"
        )
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            continue
        label = f"{event_id}.images.assets[{index}]"
        source_url = asset.get("source_url")
        source_image_url = asset.get("source_image_url")
        if not isinstance(source_image_url, str) or not source_image_url.startswith(("http://", "https://")):
            errors.append(f"{label}.source_image_url 必須是實際下載的 HTTP(S) 圖片網址")
            continue
        if source_image_url == source_url:
            errors.append(f"{label} 文章頁網址不得冒充圖片網址")
        if not isinstance(source_url, str) or source_image_url not in detected_by_source.get(source_url, set()):
            errors.append(f"{label}.source_image_url 必須出現在同一來源頁的 detected_image_urls")
    if usable_found:
        if images.get("status") != "ready" or not images.get("assets"):
            errors.append(
                f"{event_id}.images 已找到可用來源圖片，未附上合格附件前不得完成簡報"
            )
    elif images.get("status") != "omitted":
        errors.append(
            f"{event_id}.images 未找到可用來源圖片時，必須以 omitted 保存後台原因"
        )
    elif not isinstance(images.get("reader_omission_note"), str) or not images["reader_omission_note"].strip():
        errors.append(f"{event_id}.images 無合格圖片時必須提供讀者可見的 reader_omission_note")

    professional_required = images.get("professional_visual_required")
    expected_professional = _professional_visual_expected(event)
    if professional_required is not expected_professional:
        errors.append(
            f"{event_id}.images.professional_visual_required 必須依事件類型判定為 {str(expected_professional).lower()}，不得使用事件編號或評級白名單"
        )
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
        for index, check in enumerate(professional_checks, start=1):
            label = f"{event_id}.images.professional_source_checks[{index}]"
            if not isinstance(check, dict):
                errors.append(f"{label} 必須是物件")
                continue
            _need(
                check,
                [
                    "source_url", "checked", "checked_at", "inspection_method",
                    "evidence_path", "detected_image_urls", "usable_image_found",
                    "attempts", "outcome", "failure_detail",
                ],
                label,
                errors,
            )
            _validate_asset_path(check.get("evidence_path"), f"{label}.evidence_path", errors)
            if check.get("checked") is not True:
                errors.append(f"{label} 尚未完成官方專業圖資檢查")
            if not isinstance(check.get("checked_at"), str) or not check.get("checked_at", "").strip():
                errors.append(f"{label}.checked_at 必須記錄實際檢查時間")
            if check.get("inspection_method") not in {"browser", "html_extract", "official_api"}:
                errors.append(f"{label}.inspection_method 無效")
            detected_urls = check.get("detected_image_urls")
            if not isinstance(detected_urls, list) or any(
                not isinstance(url, str) or not url.startswith(("http://", "https://"))
                for url in detected_urls
            ):
                errors.append(f"{label}.detected_image_urls 必須是已檢出的圖片網址陣列")
            if not isinstance(check.get("attempts"), int) or check.get("attempts", 0) < 1:
                errors.append(f"{label}.attempts 必須至少為 1")
            if check.get("outcome") not in {"attached", "no_usable_image", "acquisition_failed"}:
                errors.append(f"{label}.outcome 無效")
            if check.get("usable_image_found") is True and not detected_urls:
                errors.append(f"{label} 宣告找到官方圖資但沒有保存圖片網址")
            if check.get("usable_image_found") is True and check.get("outcome") != "attached":
                errors.append(f"{label} 找到官方圖資時 outcome 必須是 attached")
            if check.get("usable_image_found") is False and check.get("outcome") == "attached":
                errors.append(f"{label} 未找到官方圖資時 outcome 不得是 attached")
            if check.get("outcome") == "no_usable_image" and not check.get("failure_detail"):
                errors.append(f"{label} 宣告無官方圖資時必須保存具體判定理由")
            if check.get("outcome") == "acquisition_failed" and final_status == "ready":
                errors.append(f"{label} 官方圖資取得失敗尚未恢復，必須送回 collect-news-images 重做")
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
            ["run_id", "main_sha", "generated_at", "timezone", "window_start", "window_end", "language"],
            "run",
            errors,
        )
        if not run_identity.is_valid_run_id(str(run.get("run_id", ""))):
            errors.append("run.run_id 必須使用 gnb-UTC秒-8碼隨機值格式")
        if not re.fullmatch(r"[0-9a-f]{40}", str(run.get("main_sha", ""))):
            errors.append("run.main_sha 必須是 40 碼小寫 Git commit SHA")
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

        output_language = str(run.get("language", "")) if isinstance(run, dict) else ""
        map_paths = _validate_media_result(label, "map", event.get("map"), errors, output_language)
        chart_paths = _validate_media_result(label, "charts", event.get("charts"), errors, output_language)
        image_paths = _validate_media_result(label, "images", event.get("images"), errors, output_language)
        _validate_image_gate(event, final_status, errors)
        if final_status == "ready":
            for field_name in ("map", "charts", "images"):
                field_value = event.get(field_name)
                if isinstance(field_value, dict) and field_value.get("status") == "pending":
                    errors.append(f"{label}.{field_name} 尚未完成判斷")
            map_value = event.get("map")
            if (
                isinstance(map_value, dict)
                and map_value.get("required") is True
                and (
                    map_value.get("status") != "ready"
                    or not map_value.get("assets")
                )
            ):
                errors.append(
                    f"{label}.map 必要地圖必須為 ready 且至少包含一張附件，"
                    "不得以 omitted 完成發布"
                )
        for left_name, left_paths, right_name, right_paths in (
            ("地圖", map_paths, "資料圖表", chart_paths),
            ("地圖", map_paths, "圖片", image_paths),
            ("資料圖表", chart_paths, "圖片", image_paths),
        ):
            overlap = left_paths & right_paths
            if overlap:
                errors.append(
                    f"{label} 同一附件同時出現在{left_name}與{right_name}：{', '.join(sorted(overlap))}"
                )

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

    run = data.get("run") if isinstance(data.get("run"), dict) else {}
    expected_identity = [
        f"執行編號：{run.get('run_id')}",
        f"程式版本：{run.get('main_sha')}",
        "正式發布：是",
    ]
    if nonempty[1:4] != expected_identity:
        errors.append("讀者版必須在日期後顯示與 manifest 一致的執行編號、程式版本與正式發布狀態")

    section_counts = []
    events = data.get("events", [])
    for section in data.get("sections", []):
        if not isinstance(section, dict):
            continue
        count = sum(
            1 for event in events
            if isinstance(event, dict) and event.get("primary_section") == section.get("code")
        )
        section_counts.append(f"{section.get('name')} {count} 則")
    expected_summary = f"本期共 {len(events)} 則新聞：{'、'.join(section_counts)}。"
    if len(nonempty) < 5 or nonempty[4] != expected_summary:
        errors.append(f"日期行後必須簡短列出本期新聞總數與各板塊數量：{expected_summary}")

    h2 = re.findall(r"(?m)^## ([^\r\n]+)\r?$", text)
    if h2 != REQUIRED_H2:
        errors.append("讀者版只能有今日總覽、逐條詳報、後續觀察三個二級標題，且順序固定")

    for phrase in BACKEND_PHRASES:
        if phrase in text:
            errors.append(f"讀者版含有後台文字：{phrase}")
    for token in FORBIDDEN_RENDER_TOKENS:
        if token in text:
            errors.append(f"讀者版使用禁止的圖廊、疊圖或動態元件：{token}")

    visible_time_values: list[str] = []
    for line in text.splitlines():
        if line.startswith("**時間：**"):
            visible_time_values.append(line)
        elif line.lstrip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 4 and EVENT_ID_RE.fullmatch(cells[0]):
                visible_time_values.append(cells[1])
    visible_timezone_re = re.compile(
        r"(?i)(?:\b(?:UTC|GMT)\b|(?<!\d)[+-]\d{2}:\d{2}\b|"
        r"\b(?:Africa|America|Antarctica|Asia|Atlantic|Australia|Europe|Indian|Pacific)/[A-Za-z_+-]+\b)"
    )
    if any(visible_timezone_re.search(value) for value in visible_time_values):
        errors.append("讀者可見時間必須先換算為使用者時區，且不得顯示 UTC、GMT、數字偏移或時區標記")

    expected_ids = [event.get("event_id") for event in events if isinstance(event, dict)]

    overview_match = re.search(
        r"(?ms)^## 今日總覽\s*$\n(.*?)^## 逐條詳報\s*$", text
    )
    if overview_match:
        overview = overview_match.group(1)
        event_sections = {
            event.get("primary_section") for event in events if isinstance(event, dict)
        }
        expected_sections = [
            section for section in data.get("sections", [])
            if isinstance(section, dict) and section.get("code") in event_sections
        ]
        expected_section_names = [section.get("name") for section in expected_sections]
        actual_section_names = re.findall(r"(?m)^### ([^\r\n]+)\r?$", overview)
        if actual_section_names != expected_section_names:
            errors.append("今日總覽必須依設定順序為每個有事件的板塊建立獨立標題與表格")
        section_blocks = list(re.finditer(
            r"(?ms)^### (.+?)\s*$\n(.*?)(?=^### |\Z)", overview
        ))
        event_section_by_id = {
            event.get("event_id"): event.get("primary_section")
            for event in events if isinstance(event, dict)
        }
        section_code_by_name = {
            section.get("name"): section.get("code") for section in expected_sections
        }
        seen_overview_ids: set[str] = set()
        for section_match in section_blocks:
            section_name, section_body = section_match.groups()
            section_code = section_code_by_name.get(section_name)
            if section_body.count("| 編號 | 時間 | 事件 | 等級 |") != 1:
                errors.append(f"今日總覽板塊「{section_name}」必須只有一張獨立表格")
            for line in section_body.splitlines():
                if not line.lstrip().startswith("|"):
                    continue
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                if len(cells) == 4 and EVENT_ID_RE.fullmatch(cells[0]):
                    event_id = cells[0]
                    seen_overview_ids.add(event_id)
                    if section_code is None or event_section_by_id.get(event_id) != section_code:
                        errors.append(f"今日總覽事件 {event_id} 被放入錯誤板塊「{section_name}」")
        if seen_overview_ids != set(expected_ids):
            errors.append("今日總覽各板塊表格的事件集合與事件資料不一致")
    else:
        errors.append("無法解析今日總覽板塊")

    detail_matches = [
        match for match in (DETAIL_HEADING_RE.fullmatch(line.strip()) for line in text.splitlines())
        if match
    ]
    actual_detail_ids = [match.group(1) for match in detail_matches]
    if actual_detail_ids != expected_ids:
        errors.append("逐條詳報的事件順序、數量或編號與事件資料不一致")

    blocks = _event_blocks(text)
    separators = len(re.findall(r"(?m)^---\r?$", text))
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
                "**圖片：**", "**圖片說明：**", "**事件細節：**", "**各方說法：**", "**分析：**",
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
        if isinstance(image_result, dict) and image_result.get("status") == "omitted":
            note = image_result.get("reader_omission_note")
            expected_note = f"**圖片說明：**{note}"
            if not isinstance(note, str) or not note.strip() or expected_note not in block:
                errors.append(f"{event_id} 無合格圖片時，讀者版必須完整顯示圖片說明")
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
                            f"{event_id} 漏放{field}附件或格式錯誤：必須逐張使用 Markdown "
                            f"並依序標示{expected_prefix}：{path}"
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

    follow_match = re.search(r"(?m)^## 後續觀察[ \t]*\r?\n([\s\S]*)\Z", text)
    actual_follow_ups: list[tuple[str, str]] = []
    if follow_match:
        for line in follow_match.group(1).splitlines():
            match = re.fullmatch(r"- ([A-Z]{3}-\d{2,3})：(.+)", line.strip())
            if match:
                actual_follow_ups.append((match.group(1), match.group(2).strip()))
    expected_follow_ups = []
    for event in events:
        if not isinstance(event, dict):
            continue
        detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
        follow_up = detail.get("follow_up")
        if isinstance(follow_up, str) and follow_up.strip():
            expected_follow_ups.append((event.get("event_id"), follow_up.strip()))
            if follow_up.strip() in GENERIC_FOLLOW_UP_PHRASES:
                errors.append(
                    f"{event.get('event_id')} 後續觀察必須使用事件特有的具體條件，不得使用通用模板"
                )
    if actual_follow_ups != expected_follow_ups:
        errors.append("後續觀察必須逐項逐字對應 manifest 的 detail.follow_up")
    return errors


def _legacy_section_title(section: dict[str, Any]) -> str:
    code = section.get("code")
    if code == "TWN":
        return "🇹🇼 台灣新聞"
    if code == "CHN":
        return "🇨🇳 中國新聞"
    if code == "GLB":
        return "🌍 國際世界"
    return f"{section.get('name', '')}新聞"


def _expected_reader_assets(
    event: dict[str, Any],
) -> list[tuple[str, str, str, str]]:
    expected: list[tuple[str, str, str, str]] = []
    for field_key in ("map", "charts", "images"):
        result = event.get(field_key)
        if not isinstance(result, dict):
            continue
        for index, asset in enumerate(result.get("assets", []), start=1):
            if not isinstance(asset, dict):
                continue
            number = (
                CHINESE_NUMERALS[index - 1]
                if index <= len(CHINESE_NUMERALS)
                else str(index)
            )
            expected.append(
                (
                    str(asset.get("path", "")),
                    str(asset.get("caption", "")),
                    f"{FIGURE_PREFIXES[field_key]}{number}",
                    field_key,
                )
            )
    return expected


def _next_nonblank_line(text: str, offset: int) -> str | None:
    for line in text[offset:].splitlines():
        if line.strip():
            return line.strip()
    return None


def _validate_story_asset_stream(
    event: dict[str, Any],
    block: str,
    errors: list[str],
) -> None:
    event_id = str(event.get("event_id", "事件"))
    expected = _expected_reader_assets(event)
    matches = list(MARKDOWN_IMAGE_RE.finditer(block))
    actual_paths = [match.group(2) for match in matches]
    expected_paths = [item[0] for item in expected]

    extra_paths = [path for path in actual_paths if path not in expected_paths]
    for path in extra_paths:
        errors.append(f"{event_id} 讀者版圖片未列入 manifest：{path}")

    missing_paths = [path for path in expected_paths if path not in actual_paths]
    for path in missing_paths:
        errors.append(f"{event_id} 漏放附件：{path}")

    if not extra_paths and not missing_paths and actual_paths != expected_paths:
        errors.append(
            f"{event_id} 附件順序錯誤：必須依序放置地圖、資料圖表、來源圖片"
        )

    for index, (path, caption, prefix, _field_key) in enumerate(expected):
        if index >= len(matches) or matches[index].group(2) != path:
            continue
        match = matches[index]
        alt = match.group(1).strip()
        if not alt.startswith(prefix):
            errors.append(f"{event_id} 附件必須依序標示 {prefix}：{path}")
        if _next_nonblank_line(block, match.end()) != caption:
            errors.append(
                f"{event_id} {prefix}圖說必須緊接在附件之後，且與 manifest 一致"
            )


def validate_legacy_sectioned_layout(data: dict[str, Any], text: str) -> list[str]:
    """Validate the reader-visible section/table/story layout used by ChatGPT."""
    errors = validate_manifest_data(data)
    nonempty = [line.strip() for line in text.splitlines() if line.strip()]
    if not nonempty or nonempty[0] != "# 每日新聞讀者版":
        errors.append("讀者版必須使用既有分區格式，第一行為 # 每日新聞讀者版")
    if len(nonempty) < 2 or not nonempty[1].startswith("統計期間："):
        errors.append("既有分區格式缺少統計期間")
    expected_rubric = (
        "評級綜合考量：重要性／嚴重程度、影響範圍、急迫與安全、"
        "結構／政策意義、本期實質新進展、核心板塊關聯。"
    )
    if len(nonempty) < 3 or nonempty[2] != expected_rubric:
        errors.append("既有分區格式缺少六項評級說明")

    forbidden = (
        "## 逐條詳報", "## 後續觀察",
        "**時間：**", "**來源：**", "**事件細節：**", "**分析：**",
        "驗收摘要", "執行編號：", "程式版本：", "正式發布：",
    )
    for phrase in (*BACKEND_PHRASES, *forbidden):
        if phrase in text:
            errors.append(f"既有分區格式含有禁止內容：{phrase}")
    for token in FORBIDDEN_RENDER_TOKENS:
        if token in text:
            errors.append(f"讀者版使用禁止的圖廊、疊圖或動態元件：{token}")

    story_heading_matches = list(
        re.finditer(r"(?m)^### (.+)｜(SS|[SABC][+-]?)\r?$", text)
    )
    story_spans: list[tuple[int, int]] = []
    for index, match in enumerate(story_heading_matches):
        later_headings = [
            candidate.start()
            for candidate in story_heading_matches[index + 1:]
            if candidate.start() > match.start()
        ]
        next_section = re.search(r"(?m)^## [^\r\n]+\r?$", text[match.end():])
        boundaries = later_headings
        if next_section:
            boundaries = boundaries + [match.end() + next_section.start()]
        story_spans.append(
            (match.start(), min(boundaries) if boundaries else len(text))
        )
    for image_match in MARKDOWN_IMAGE_RE.finditer(text):
        if not any(
            start <= image_match.start() < end for start, end in story_spans
        ):
            errors.append(
                "讀者版圖片出現在新聞區塊之外："
                f"{image_match.group(2)}"
            )

    events = [event for event in data.get("events", []) if isinstance(event, dict)]
    populated_sections: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for section in data.get("sections", []):
        if not isinstance(section, dict):
            continue
        section_events = [
            event for event in events if event.get("primary_section") == section.get("code")
        ]
        if section_events:
            populated_sections.append((section, section_events))

    expected_section_h2 = [_legacy_section_title(section) for section, _ in populated_sections]
    expected_h2 = ["今日總覽", *expected_section_h2]
    actual_h2 = re.findall(r"(?m)^## ([^\r\n]+)\r?$", text)
    if actual_h2 != expected_h2:
        errors.append("讀者版必須先有今日總覽，再依設定順序使用分區新聞標題")

    section_matches = list(re.finditer(r"(?m)^## ([^\r\n]+)\r?$", text))
    sections_by_title: dict[str, str] = {}
    for index, match in enumerate(section_matches):
        end = section_matches[index + 1].start() if index + 1 < len(section_matches) else len(text)
        sections_by_title[match.group(1)] = text[match.end():end]

    overview_body = sections_by_title.get("今日總覽", "")
    overview_matches = list(re.finditer(r"(?m)^### ([^\r\n]+)\r?$", overview_body))
    overview_by_title: dict[str, str] = {}
    for index, match in enumerate(overview_matches):
        end = overview_matches[index + 1].start() if index + 1 < len(overview_matches) else len(overview_body)
        overview_by_title[match.group(1)] = overview_body[match.end():end]
    if [match.group(1) for match in overview_matches] != expected_section_h2:
        errors.append("今日總覽必須依設定順序列出每個有新聞的板塊")

    visible_timezone_re = re.compile(
        r"(?i)(?:\b(?:UTC|GMT)\b|(?<!\d)[+-]\d{2}:\d{2}\b|"
        r"\b(?:Africa|America|Antarctica|Asia|Atlantic|Australia|Europe|Indian|Pacific)/[A-Za-z_+-]+\b)"
    )
    for section, section_events in populated_sections:
        section_title = _legacy_section_title(section)
        body = sections_by_title.get(section_title)
        if body is None:
            continue
        overview_section = overview_by_title.get(section_title, "")
        if overview_section.count("| 時間 | 事件 | 評級 |") != 1:
            errors.append(f"今日總覽的板塊「{section_title}」必須只有一張時間／事件／評級清單")
        if "| 時間 | 事件 | 評級 |" in body:
            errors.append(f"板塊「{section_title}」不得重複今日總覽清單")

        rows: list[tuple[str, str, str]] = []
        for line in overview_section.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] not in {"時間", "---"} and not set(cells[0]) <= {"-", ":"}:
                rows.append((cells[0], cells[1], cells[2]))
        expected_rows = [
            (
                str(event.get("detail", {}).get("overview_time", "")),
                str(event.get("title", "")),
                str(event.get("grade", "")),
            )
            for event in section_events
        ]
        if rows != expected_rows:
            errors.append(f"板塊「{section_title}」總清單與事件資料不一致")
        if any(visible_timezone_re.search(row[0]) for row in rows):
            errors.append("讀者可見時間不得顯示 UTC、GMT、數字偏移或時區標記")

        heading_matches = list(re.finditer(r"(?m)^### (.+)｜(SS|[SABC][+-]?)\r?$", body))
        actual_headings = [(match.group(1), match.group(2)) for match in heading_matches]
        expected_headings = [
            (str(event.get("title", "")), str(event.get("grade", "")))
            for event in section_events
        ]
        if actual_headings != expected_headings:
            errors.append(f"板塊「{section_title}」新聞標題、評級或順序不一致")

        for index, event in enumerate(section_events):
            if index >= len(heading_matches):
                break
            start = heading_matches[index].start()
            end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(body)
            block = body[start:end]
            grade = str(event.get("grade", ""))
            if f"評為{grade}級" not in block:
                errors.append(f"{event.get('event_id')} 缺少「評為{grade}級」的評級評論")
            _validate_story_asset_stream(event, block, errors)
            verification = event.get("verification", {})
            if isinstance(verification, dict):
                if verification.get("finding") == "single_reliable_source" and SINGLE_SOURCE_NOTE not in block:
                    errors.append(f"{event.get('event_id')} 讀者版缺少單一來源說明")
                for source in verification.get("sources", []):
                    if isinstance(source, dict) and source.get("url") not in block:
                        errors.append(f"{event.get('event_id')} 缺少來源連結：{source.get('url')}")
            for field_key in ("map", "charts", "images"):
                result = event.get(field_key, {})
                if not isinstance(result, dict):
                    continue
                if field_key == "images" and result.get("status") == "omitted":
                    note = result.get("reader_omission_note")
                    if not isinstance(note, str) or f"**圖片說明：**{note}" not in block:
                        errors.append(f"{event.get('event_id')} 無合格圖片時必須顯示圖片說明")
    return errors


def validate_canonical_reader(data: dict[str, Any], text: str) -> list[str]:
    """Validate the only reader layout accepted by canonical publication."""
    return validate_legacy_sectioned_layout(data, text)


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
    brief.add_argument(
        "--reader-layout",
        choices=("legacy-sectioned",),
        default="legacy-sectioned",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "manifest":
            data = load_json(args.input)
            image_stage = data.get("stage_status", {}).get("collect-news-images")
            if image_stage in {"pending", "running", "failed", "skipped"}:
                print(
                    "DEFERRED: final-manifest validator requires collect-news-images "
                    "completed; continue the pipeline without marking the run failed"
                )
                return 0
            return print_result(validate_manifest_data(data))
        if args.command == "stage":
            return print_result(
                validate_stage_data(load_json(args.before), load_json(args.after), args.stage)
            )
        manifest = load_json(args.manifest)
        text = Path(args.input).read_text(encoding="utf-8")
        return print_result(validate_canonical_reader(manifest, text))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
