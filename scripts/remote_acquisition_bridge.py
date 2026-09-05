#!/usr/bin/env python3
"""Validate and execute a run-bound remote acquisition request."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from scripts.materialize_news_images import materialize, _write_json_atomic


MARKER = "<!-- gnb-remote-acquisition:v1 -->"
RUN_ID_RE = re.compile(r"gnb-\d{8}T\d{6}Z-[0-9a-f]{8}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
ALLOWED_KEYS = {
    "schema_version", "operation", "run_id", "main_sha", "window", "media_inputs",
    "source_ids",
}
MEDIA_KEYS = {
    "event_id", "source_page_url", "source_image_url", "source_base_url", "alt", "credit",
    "expected_source_byte_size", "expected_source_sha256", "expected_source_width",
    "expected_source_height",
}


def extract_request_from_comment(body: str) -> dict[str, Any]:
    if body.count(MARKER) != 1:
        raise ValueError("comment must contain exactly one remote acquisition marker")
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", body, flags=re.S)
    if len(matches) != 1:
        raise ValueError("comment must contain exactly one JSON request block")
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise ValueError(f"request JSON is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("request must be a JSON object")
    return value


def _parse_time(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"window.{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"window.{field} must include a timezone")
    return parsed


def _require_public_https_url(value: Any, field: str) -> None:
    try:
        parsed = urlsplit(str(value))
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field} must be a public HTTPS URL") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        raise ValueError(f"{field} must be a public HTTPS URL")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError(f"{field} must be a public HTTPS URL")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError(f"{field} must be a public HTTPS URL")


def validate_request(value: dict[str, Any], *, expected_main_sha: str) -> dict[str, Any]:
    unknown = set(value) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"unknown request keys: {sorted(unknown)}")
    if value.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    operation = value.get("operation")
    if operation not in {"source_scan", "media_fetch"}:
        raise ValueError("operation must be source_scan or media_fetch")
    if not RUN_ID_RE.fullmatch(str(value.get("run_id", ""))):
        raise ValueError("run_id is invalid")
    main_sha = str(value.get("main_sha", ""))
    if not SHA_RE.fullmatch(main_sha) or main_sha != expected_main_sha:
        raise ValueError("main_sha is invalid or stale")
    window = value.get("window")
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise ValueError("window must contain only start and end")
    start = _parse_time(window["start"], "start")
    end = _parse_time(window["end"], "end")
    if end - start != timedelta(hours=24):
        raise ValueError("window must be exactly 24 hours")

    inputs = value.get("media_inputs")
    source_ids = value.get("source_ids")
    if operation == "source_scan":
        if inputs is not None:
            raise ValueError("source_scan must not contain media_inputs")
        if not isinstance(source_ids, list) or not source_ids or set(source_ids) - {"cna", "chinanews"}:
            raise ValueError("source_scan source_ids must contain only regional routes cna/chinanews")
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_scan source_ids must be unique")
    if operation == "media_fetch":
        if source_ids is not None:
            raise ValueError("media_fetch must not contain source_ids")
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= 50:
            raise ValueError("media_fetch requires 1 to 50 media_inputs")
        for index, item in enumerate(inputs):
            if not isinstance(item, dict) or set(item) - MEDIA_KEYS:
                raise ValueError(f"media_inputs[{index}] contains invalid keys")
            if not str(item.get("event_id", "")).strip():
                raise ValueError(f"media_inputs[{index}].event_id is required")
            for key in ("source_page_url", "source_image_url"):
                _require_public_https_url(item.get(key), f"media_inputs[{index}].{key}")
    return value


def execute_request(request: dict[str, Any], *, runtime_root: Path, run_logs_root: Path) -> Path:
    run_id = request["run_id"]
    output = run_logs_root / "logs" / "runs" / run_id / "remote-acquisition"
    output.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(output / "request.json", request)
    if request["operation"] == "media_fetch":
        records = materialize(request["media_inputs"], output / "media")
        _write_json_atomic(output / "materialized-images.json", records)
        ready = sum(item.get("status") == "ready" for item in records)
        receipt = {
            "schema_version": "1.0",
            "operation": "media_fetch",
            "run_id": run_id,
            "main_sha": request["main_sha"],
            "window": request["window"],
            "status": "completed" if ready == len(records) else "failed",
            "requested_count": len(records),
            "ready_count": ready,
        }
        _write_json_atomic(output / "receipt.json", receipt)
        if receipt["status"] != "completed":
            raise RuntimeError("one or more remote media inputs failed")
        return output

    checkpoint = output / "checkpoint-window.json"
    _write_json_atomic(checkpoint, {
        "window_start": request["window"]["start"],
        "window_end": request["window"]["end"],
    })
    route_output = output / "source-work"
    route_config = json.loads((runtime_root / "source-route-config.json").read_text(encoding="utf-8-sig"))
    route_config["routes"] = [
        route for route in route_config.get("routes", [])
        if route.get("source_id") in request["source_ids"]
    ]
    route_config["minimum_ready_routes"] = len(request["source_ids"])
    filtered_route_config = output / "regional-source-route-config.json"
    _write_json_atomic(filtered_route_config, route_config)
    source_pool = json.loads((runtime_root / "news-source-pool.json").read_text(encoding="utf-8-sig"))
    source_pool["discovery_sources"] = [
        source for source in source_pool.get("discovery_sources", [])
        if source.get("source_id") in request["source_ids"]
    ]
    source_pool.setdefault("discovery_policy", {})["minimum_ready_sources"] = len(request["source_ids"])
    filtered_source_pool = output / "regional-news-source-pool.json"
    _write_json_atomic(filtered_source_pool, source_pool)
    python = sys.executable
    subprocess.run([
        python, str(runtime_root / "scripts/fetch_source_routes.py"),
        "--route-config", str(filtered_route_config),
        "--output-dir", str(route_output),
        "--window-start", request["window"]["start"],
        "--window-end", request["window"]["end"],
    ], check=True)
    route_receipt = json.loads((route_output / "source-route-coverage.json").read_text(encoding="utf-8"))
    incomplete = [
        item.get("source_id") for item in route_receipt.get("results", [])
        if item.get("route_ready") is not True or item.get("coverage_complete") is not True
    ]
    if incomplete or len(route_receipt.get("results", [])) != len(request["source_ids"]):
        raise RuntimeError(f"regional source coverage incomplete: {incomplete}")
    subprocess.run([
        python, str(runtime_root / "scripts/materialize_source_scans.py"),
        "--checkpoint", str(checkpoint),
        "--source-pool", str(filtered_source_pool),
        "--route-coverage", str(route_output / "source-route-coverage.json"),
        "--output-dir", str(output / "source-scans"),
        "--coverage-output", str(output / "source-coverage.json"),
    ], check=True)
    _write_json_atomic(output / "receipt.json", {
        "schema_version": "1.0", "operation": "source_scan", "run_id": run_id,
        "main_sha": request["main_sha"], "window": request["window"],
        "status": "completed", "resume_stage": "source-scan",
    })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    parse = sub.add_parser("parse-comment")
    parse.add_argument("--comment-env", required=True)
    parse.add_argument("--expected-main-sha", required=True)
    parse.add_argument("--output", required=True, type=Path)
    execute = sub.add_parser("execute")
    execute.add_argument("--request", required=True, type=Path)
    execute.add_argument("--expected-main-sha", required=True)
    execute.add_argument("--runtime-root", required=True, type=Path)
    execute.add_argument("--run-logs-root", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "parse-comment":
        request = validate_request(
            extract_request_from_comment(os.environ.get(args.comment_env, "")),
            expected_main_sha=args.expected_main_sha,
        )
        _write_json_atomic(args.output, request)
        return 0
    request = validate_request(
        json.loads(args.request.read_text(encoding="utf-8")),
        expected_main_sha=args.expected_main_sha,
    )
    output = execute_request(request, runtime_root=args.runtime_root, run_logs_root=args.run_logs_root)
    print(json.dumps({"output": str(output), "status": "completed"}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
