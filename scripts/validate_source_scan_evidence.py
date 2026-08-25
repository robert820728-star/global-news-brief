#!/usr/bin/env python3
"""Validate evidence that a source scan reached the rolling-window boundary.

The gate deliberately has no minimum item count. A source with zero items is valid
only when its snapshots prove either exhaustion or traversal past window_start.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def normalize_url(value):
    parts = urlsplit(value)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def normalized_host(value):
    return urlsplit(str(value)).netloc.lower().removeprefix("www.")


def local_path(value):
    return Path(str(value).removeprefix("sandbox:"))


def evidence_in_snapshot(value, content):
    value = str(value or "")
    if value in content:
        return True
    escaped = json.dumps(value, ensure_ascii=False)[1:-1].replace("/", r"\/")
    return escaped in content


def validate_scan(scan, coverage, source, label="source_scan"):
    errors = []
    if not isinstance(scan, dict):
        return [f"{label} 缺少可重算的來源掃描證據"]
    coverage_fields = {
        "coverage_complete", "coverage_status", "coverage_reason",
        "missing_segments", "missing_date_variants",
    }
    required = {
        "schema_version", "collector", "generated_at", "window_start", "window_end",
        "pages", "terminal_proof", *coverage_fields,
    }
    missing = sorted(required - set(scan))
    if missing:
        errors.append(f"{label} 缺少欄位：{', '.join(missing)}")
        return errors
    if scan.get("schema_version") != "1.0.0":
        errors.append(f"{label}.schema_version 必須是 1.0.0")
    for field in sorted(coverage_fields):
        if scan.get(field) != coverage.get(field):
            errors.append(f"{label}.{field} 與 candidate audit source coverage 不一致")
    if not isinstance(scan.get("coverage_complete"), bool):
        errors.append(f"{label}.coverage_complete 必須是布林值")
    if scan.get("coverage_status") not in {
        "complete", "degraded_partial", "degraded_cached", "unavailable"
    }:
        errors.append(f"{label}.coverage_status 無效")
    if scan.get("coverage_complete") is True and scan.get("coverage_status") != "complete":
        errors.append(f"{label} 完整 coverage 必須使用 coverage_status=complete")
    if scan.get("coverage_complete") is False and scan.get("coverage_status") == "complete":
        errors.append(f"{label} 不完整 coverage 不得使用 coverage_status=complete")
    for field in ("missing_segments", "missing_date_variants"):
        if not isinstance(scan.get(field), list):
            errors.append(f"{label}.{field} 必須是陣列")
    if not str(scan.get("collector", "")).strip():
        errors.append(f"{label}.collector 必須記錄實際抓取器")
    try:
        start, end = parse_time(scan["window_start"]), parse_time(scan["window_end"])
    except (TypeError, ValueError):
        return errors + [f"{label} 時間窗無法解析"]
    pages = scan.get("pages")
    if not isinstance(pages, list) or not pages:
        return errors + [f"{label}.pages 必須保存至少一頁原始回應"]

    all_items = []
    previous_next = None
    for index, page in enumerate(pages, 1):
        page_label = f"{label}.pages[{index}]"
        if not isinstance(page, dict):
            errors.append(f"{page_label} 必須是物件")
            continue
        for key in ("request_url", "fetched_at", "http_status", "snapshot_path", "sha256", "next_url", "extracted_items"):
            if key not in page:
                errors.append(f"{page_label} 缺少 {key}")
        request_url = page.get("request_url")
        if index > 1 and previous_next != request_url:
            errors.append(f"{page_label} 與上一頁 next_url 不連續")
        previous_next = page.get("next_url")
        if page.get("http_status") != 200:
            errors.append(f"{page_label} HTTP 狀態不是 200；不得把中斷當作掃描完成")
        snapshot = local_path(page.get("snapshot_path", ""))
        if not snapshot.is_file():
            errors.append(f"{page_label} 原始快照不存在：{snapshot}")
            content = ""
        else:
            raw = snapshot.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != page.get("sha256"):
                errors.append(f"{page_label} 快照 SHA-256 不符")
            content = raw.decode("utf-8", errors="ignore")
        items = page.get("extracted_items")
        if not isinstance(items, list):
            errors.append(f"{page_label}.extracted_items 必須是陣列")
            continue
        for item_index, item in enumerate(items, 1):
            item_label = f"{page_label}.extracted_items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label} 必須是物件")
                continue
            for key in ("url", "title", "published_at", "url_evidence", "published_evidence"):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{item_label} 缺少 {key}")
            if not evidence_in_snapshot(item.get("url_evidence"), content):
                errors.append(f"{item_label}.url_evidence 不存在於原始快照")
            if not evidence_in_snapshot(item.get("published_evidence"), content):
                errors.append(f"{item_label}.published_evidence 不存在於原始快照")
            all_items.append(item)

    supplemental_pages = scan.get("supplemental_pages", [])
    if not isinstance(supplemental_pages, list):
        errors.append(f"{label}.supplemental_pages must be an array")
        supplemental_pages = []
    source_host = normalized_host(source.get("homepage", ""))
    for index, page in enumerate(supplemental_pages, 1):
        page_label = f"{label}.supplemental_pages[{index}]"
        if not isinstance(page, dict):
            errors.append(f"{page_label} must be an object")
            continue
        for key in ("request_url", "fetched_at", "http_status", "snapshot_path", "sha256", "next_url", "extracted_items", "recovery_route"):
            if key not in page:
                errors.append(f"{page_label} missing {key}")
        if normalized_host(page.get("request_url", "")) != source_host:
            errors.append(f"{page_label}.request_url violates same-source boundary")
        if page.get("http_status") != 200:
            errors.append(f"{page_label} HTTP status must be 200")
        snapshot = local_path(page.get("snapshot_path", ""))
        if not snapshot.is_file():
            errors.append(f"{page_label} snapshot is missing: {snapshot}")
            content = ""
        else:
            raw = snapshot.read_bytes()
            if hashlib.sha256(raw).hexdigest() != page.get("sha256"):
                errors.append(f"{page_label} snapshot SHA-256 mismatch")
            content = raw.decode("utf-8", errors="ignore")
        items = page.get("extracted_items")
        if not isinstance(items, list):
            errors.append(f"{page_label}.extracted_items must be an array")
            continue
        for item_index, item in enumerate(items, 1):
            item_label = f"{page_label}.extracted_items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label} must be an object")
                continue
            for key in ("url", "title", "published_at", "url_evidence", "published_evidence"):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{item_label} missing {key}")
            if not evidence_in_snapshot(item.get("url_evidence"), content):
                errors.append(f"{item_label}.url_evidence is absent from snapshot")
            if not evidence_in_snapshot(item.get("published_evidence"), content):
                errors.append(f"{item_label}.published_evidence is absent from snapshot")
            if normalized_host(item.get("url", "")) != source_host:
                errors.append(f"{item_label}.url violates same-source boundary")
            all_items.append(item)

    urls = [item.get("url") for item in all_items]
    if len(urls) != len(set(urls)):
        errors.append(f"{label} 跨頁解析出重複文章網址")
    homepage = normalize_url(source.get("homepage", ""))
    for index, url in enumerate(urls, 1):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            errors.append(f"{label} 第 {index} 筆不是有效文章網址")
        elif normalize_url(url) == homepage:
            errors.append(f"{label} 第 {index} 筆以來源首頁冒充單篇新聞")

    terminal = scan.get("terminal_proof")
    if not isinstance(terminal, dict):
        errors.append(f"{label}.terminal_proof 必須是物件")
    else:
        kind = terminal.get("type")
        page_index = terminal.get("page_index")
        if not isinstance(page_index, int) or not 1 <= page_index <= len(pages):
            errors.append(f"{label}.terminal_proof.page_index 無效")
        elif kind == "crossed_window_start":
            witness_url = terminal.get("witness_url")
            witness = next((item for item in pages[page_index - 1].get("extracted_items", []) if item.get("url") == witness_url), None)
            if witness is None:
                errors.append(f"{label} 時間邊界見證文章不存在於指定快照")
            else:
                try:
                    if parse_time(witness.get("published_at")) > start:
                        errors.append(f"{label} 見證文章尚未抵達 window_start")
                except (TypeError, ValueError):
                    errors.append(f"{label} 見證文章時間無法解析")
        elif kind == "source_exhausted":
            page = pages[page_index - 1]
            marker = terminal.get("terminal_marker")
            snapshot = local_path(page.get("snapshot_path", ""))
            content = snapshot.read_text(encoding="utf-8", errors="ignore") if snapshot.is_file() else ""
            if page.get("next_url") is not None:
                errors.append(f"{label} 宣告來源耗盡時最後一頁仍有 next_url")
            if not isinstance(marker, str) or not marker or marker not in content:
                errors.append(f"{label} 來源耗盡標記不存在於原始快照")
        else:
            errors.append(f"{label}.terminal_proof.type 只能是 crossed_window_start 或 source_exhausted")

    within = []
    for item in all_items:
        try:
            published = parse_time(item.get("published_at"))
        except (TypeError, ValueError):
            errors.append(f"{label} 文章時間無法解析：{item.get('url')}")
            continue
        if start < published <= end:
            within.append(item)
    ranked = coverage.get("ranked_items", [])
    ranked_urls = [item.get("url") for item in ranked if isinstance(item, dict)]
    within_urls = [item.get("url") for item in within]
    if set(ranked_urls) != set(within_urls) or len(ranked_urls) != len(within_urls):
        errors.append(f"{label} 原始快照重算的24小時文章與 ranked_items 不一致")
    if coverage.get("within_window_count") != len(within):
        errors.append(f"{label} within_window_count 必須由原始快照重算，不得自行填寫")
    if scan.get("window_start") != coverage.get("scan_window_start") or scan.get("window_end") != coverage.get("scan_window_end"):
        errors.append(f"{label} 掃描證據時間窗與來源稽核時間窗不一致")
    return errors


def resolve_source_inputs(scan, coverage, source):
    source_id = scan.get("source_id") if isinstance(scan, dict) else None
    if isinstance(coverage, list):
        coverage = next(
            (item for item in coverage if isinstance(item, dict) and item.get("source_id") == source_id),
            None,
        )
    if isinstance(source, dict) and isinstance(source.get("discovery_sources"), list):
        source = next((
            item
            for item in source.get("discovery_sources", [])
            if isinstance(item, dict) and item.get("source_id") == source_id
        ), None)
    if not isinstance(coverage, dict):
        raise ValueError(f"{source_id or 'unknown'}: aggregate coverage 找不到對應來源")
    if not isinstance(source, dict):
        raise ValueError(f"{source_id or 'unknown'}: source pool 找不到對應來源")
    return coverage, source


def main():
    parser = argparse.ArgumentParser()
    scan_input = parser.add_mutually_exclusive_group(required=True)
    scan_input.add_argument("--scan")
    scan_input.add_argument("--scan-dir")
    parser.add_argument("--coverage", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    coverage = json.loads(Path(args.coverage).read_text(encoding="utf-8"))
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    if args.scan:
        scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
        try:
            coverage, source = resolve_source_inputs(scan, coverage, source)
        except ValueError as error:
            print("FAIL:", error)
            return 1
        errors = validate_scan(scan, coverage, source)
        source_count = 1
    else:
        sources = source.get("discovery_sources") if isinstance(source, dict) else None
        if not isinstance(sources, list) or not sources:
            print("FAIL: --scan-dir 模式需要含 discovery_sources 的 aggregate source pool")
            return 1
        coverage_items = coverage if isinstance(coverage, list) else []
        minimum_ready = int(source.get("discovery_policy", {}).get(
            "minimum_ready_sources", len(sources)
        ))
        if len(coverage_items) < minimum_ready:
            print(
                "FAIL: discovery source coverage below minimum: "
                f"{len(coverage_items)}/{minimum_ready}"
            )
            return 1
        errors = []
        scan_dir = Path(args.scan_dir)
        for coverage_item in coverage_items:
            source_id = coverage_item.get("source_id") if isinstance(coverage_item, dict) else None
            scan_path = scan_dir / f"{source_id}.json"
            if not source_id or not scan_path.is_file():
                errors.append(f"source_scan[{source_id or 'unknown'}] 缺少 scan：{scan_path}")
                continue
            scan = json.loads(scan_path.read_text(encoding="utf-8"))
            try:
                coverage_item, resolved_source = resolve_source_inputs(scan, coverage, source)
            except ValueError as error:
                errors.append(str(error))
                continue
            errors.extend(validate_scan(
                scan, coverage_item, resolved_source, f"source_scan[{source_id}]"
            ))
        source_count = len(coverage_items)
    for error in errors:
        print("FAIL:", error)
    if not errors:
        print(f"OK sources={source_count}")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
