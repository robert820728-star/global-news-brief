#!/usr/bin/env python3
"""Fetch canonical news source routes using only the Python standard library."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping


USER_AGENT = "Mozilla/5.0 CodexNewsValidation/1.0"


def resolve_route_url(route: Mapping, now: datetime | None = None) -> str:
    route_date = (now or datetime.now().astimezone()).date() + timedelta(
        days=int(route.get("date_offset_days", 0))
    )
    values = {
        "{yyyy-MM-dd}": route_date.strftime("%Y-%m-%d"),
        "{yyyyMMdd}": route_date.strftime("%Y%m%d"),
        "{MMdd}": route_date.strftime("%m%d"),
        "{yyyy}": route_date.strftime("%Y"),
        "{MM}": route_date.strftime("%m"),
        "{dd}": route_date.strftime("%d"),
    }
    url = str(route["request_url_template"])
    for token, value in values.items():
        url = url.replace(token, value)
    return url


def decode_body(body: bytes, content_encoding: str) -> bytes:
    encoding = content_encoding.lower().strip()
    if encoding == "gzip":
        return gzip.decompress(body)
    if encoding == "deflate":
        try:
            return zlib.decompress(body)
        except zlib.error:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def value_at_path(value, path):
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def parse_page_time(value: str, boundary: datetime) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=boundary.tzinfo)


def safe_snapshot_path(snapshot_dir: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"invalid snapshot_name: {name}")
    target = (snapshot_dir / relative).resolve()
    target.relative_to(snapshot_dir.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def fetch_one(route: Mapping, snapshot_dir: Path, timeout_seconds: int) -> dict:
    request_url = resolve_route_url(route)
    snapshot_path = safe_snapshot_path(snapshot_dir, str(route["snapshot_name"]))
    method = str(route.get("request_method", "GET")).upper()
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    headers.update({str(key): str(value) for key, value in route.get("request_headers", {}).items()})
    body = None
    if "request_json" in route:
        body = json.dumps(
            route["request_json"], ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(
        request_url, data=body, headers=headers, method=method,
    )
    last_status = None
    last_content_type = None
    last_error = None
    for attempt in range(2):
        response = None
        try:
            try:
                response = urllib.request.urlopen(request, timeout=timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            status = int(getattr(response, "status", response.getcode()))
            response_headers = response.headers
            response_body = decode_body(
                response.read(), response_headers.get("Content-Encoding", "")
            )
            last_status = status
            last_content_type = response_headers.get("Content-Type")
            ready = 200 <= status < 300 and bool(response_body)
            if ready:
                snapshot_path.write_bytes(response_body)
                return {
                    "source_id": str(route["source_id"]), "route": str(route["route"]),
                    "request_method": method, "request_url": request_url,
                    "http_status": status, "content_type": last_content_type,
                    "bytes": len(response_body), "snapshot_path": str(snapshot_path),
                    "sha256": hashlib.sha256(response_body).hexdigest(), "route_ready": True,
                    "json_exhaustion_path": route.get("json_exhaustion_path"),
                    "source_exhaustion_marker": route.get("source_exhaustion_marker"),
                    "retry_count": attempt, "error": None,
                }
            last_error = "HTTP response was not successful or body was empty"
        except Exception as error:  # noqa: BLE001 - record each route failure.
            last_error = str(error)
        finally:
            if response is not None:
                response.close()
        if attempt == 0:
            time.sleep(1)
    return {
        "source_id": str(route.get("source_id", "")), "route": str(route.get("route", "")),
        "request_method": method, "request_url": request_url,
        "http_status": last_status, "content_type": last_content_type,
        "bytes": 0, "snapshot_path": None, "sha256": None, "route_ready": False,
        "json_exhaustion_path": route.get("json_exhaustion_path"),
        "source_exhaustion_marker": route.get("source_exhaustion_marker"),
        "retry_count": 1, "error": last_error,
    }


def fetch_date_variants(route: Mapping, snapshot_dir: Path, timeout_seconds: int) -> dict:
    offsets = route.get("date_offsets_days")
    if not isinstance(offsets, list) or not offsets:
        return fetch_one(route, snapshot_dir, timeout_seconds)
    minimum_ready = int(route.get("minimum_ready_variants", len(offsets)))
    base = Path(str(route["snapshot_name"]))
    attempts = []
    ready = []
    for offset_value in offsets:
        offset = int(offset_value)
        variant = dict(route)
        variant.pop("date_offsets_days", None)
        variant.pop("minimum_ready_variants", None)
        variant["date_offset_days"] = offset
        suffix = base.suffix or ".bin"
        variant["snapshot_name"] = (
            f"{base.stem}.date-offset-{offset:+d}{suffix}"
        )
        result = fetch_one(variant, snapshot_dir, timeout_seconds)
        result["date_offset_days"] = offset
        attempts.append(result)
        if result.get("route_ready"):
            ready.append(result)
    if not ready:
        failed = dict(attempts[0])
        failed.update(
            date_variant_attempts=attempts,
            date_variant_ready_count=0,
            error="no dated route variant was available",
        )
        return failed
    primary = dict(ready[0])
    primary["page_snapshots"] = [
        {
            **{key: value for key, value in item.items()
               if key not in {"source_id", "route", "route_ready"}},
            "page_index": index,
        }
        for index, item in enumerate(ready[1:], start=2)
    ]
    primary["date_variant_attempts"] = attempts
    primary["date_variant_ready_count"] = len(ready)
    if len(ready) < minimum_ready:
        primary.update(
            route_ready=False,
            error=(
                f"dated route produced {len(ready)} successful variants; "
                f"requires {minimum_ready}"
            ),
        )
    return primary


def fetch_page(route: Mapping, request_url: str, snapshot_path: Path,
               timeout_seconds: int, page_index: int) -> tuple[dict, bytes | None]:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    headers.update({str(key): str(value) for key, value in route.get("request_headers", {}).items()})
    headers.update({
        str(key): str(value)
        for key, value in route.get("pagination", {}).get("request_headers", {}).items()
    })
    last_error = None
    last_status = None
    last_content_type = None
    for attempt in range(2):
        response = None
        try:
            request = urllib.request.Request(request_url, headers=headers, method="GET")
            try:
                response = urllib.request.urlopen(request, timeout=timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            status = int(getattr(response, "status", response.getcode()))
            response_headers = response.headers
            response_body = decode_body(
                response.read(), response_headers.get("Content-Encoding", "")
            )
            last_status = status
            last_content_type = response_headers.get("Content-Type")
            if 200 <= status < 300 and response_body:
                snapshot_path.write_bytes(response_body)
                return ({
                    "page_index": page_index, "request_url": request_url,
                    "http_status": status, "content_type": last_content_type,
                    "bytes": len(response_body), "snapshot_path": str(snapshot_path),
                    "sha256": hashlib.sha256(response_body).hexdigest(),
                    "retry_count": attempt, "error": None,
                }, response_body)
            last_error = "HTTP response was not successful or body was empty"
        except Exception as error:  # noqa: BLE001 - record canonical page failure.
            last_error = str(error)
        finally:
            if response is not None:
                response.close()
        if attempt == 0:
            time.sleep(1)
    return ({
        "page_index": page_index, "request_url": request_url,
        "http_status": last_status, "content_type": last_content_type,
        "bytes": 0, "snapshot_path": None, "sha256": None,
        "retry_count": 1, "error": last_error,
    }, None)


def fetch_pagination(route: Mapping, result: dict, snapshot_dir: Path,
                     timeout_seconds: int, window_start: str | None) -> dict:
    pagination = route.get("pagination")
    if not isinstance(pagination, dict):
        return result
    if not window_start:
        result.update(route_ready=False, error="pagination requires window_start")
        return result
    boundary = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
    items_path = pagination.get("items_path", [])
    published_path = pagination.get("published_path", [])
    start_page = int(pagination.get("start_page", 2))
    max_pages = int(pagination.get("max_pages", 60))
    template = resolve_route_url({"request_url_template": pagination["request_url_template"]})
    base = Path(str(route["snapshot_name"]))
    page_snapshots = []
    complete = False
    for page_index in range(start_page, start_page + max_pages):
        request_url = template.replace("{page}", str(page_index))
        snapshot_name = f"{base.stem}.page-{page_index:04d}.json"
        snapshot_path = safe_snapshot_path(snapshot_dir, snapshot_name)
        page, raw = fetch_page(route, request_url, snapshot_path, timeout_seconds, page_index)
        page_snapshots.append(page)
        if raw is None:
            result.update(route_ready=False, page_snapshots=page_snapshots, error=page["error"])
            return result
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            result.update(route_ready=False, page_snapshots=page_snapshots, error=str(error))
            return result
        items = value_at_path(payload, items_path)
        if not isinstance(items, list):
            result.update(
                route_ready=False, page_snapshots=page_snapshots,
                error="pagination items_path did not resolve to an array",
            )
            return result
        if not items:
            result["pagination_exhausted"] = True
            complete = True
            break
        published = [
            parse_page_time(value_at_path(item, published_path), boundary)
            for item in items if isinstance(item, dict)
        ]
        if any(value is not None and value <= boundary for value in published):
            complete = True
            break
    result["page_snapshots"] = page_snapshots
    if not complete:
        result.update(
            route_ready=False,
            error=f"pagination did not reach window_start within {max_pages} pages",
        )
    return result


def fetch_routes(route_config: Path, output_dir: Path, timeout_seconds: int,
                 window_start: str | None = None) -> dict:
    config = json.loads(route_config.read_text(encoding="utf-8-sig"))
    output_dir = output_dir.resolve()
    snapshot_dir = output_dir / "route-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for route in config.get("routes", []):
        result = fetch_date_variants(route, snapshot_dir, timeout_seconds)
        if result.get("route_ready"):
            result = fetch_pagination(
                route, result, snapshot_dir, timeout_seconds, window_start
            )
        results.append(result)
    ready_count = sum(bool(item["route_ready"]) for item in results)
    minimum_ready = int(config.get("minimum_ready_routes", len(results)))
    coverage = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now().astimezone().isoformat(),
        "route_ready_count": ready_count,
        "route_total_count": len(results),
        "minimum_ready_routes": minimum_ready,
        "status": (
            "ready" if ready_count == len(results)
            else "degraded" if ready_count >= minimum_ready
            else "failed"
        ),
        "results": results,
    }
    (output_dir / "source-route-coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=25)
    parser.add_argument("--window-start")
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 120:
        parser.error("--timeout-seconds must be between 1 and 120")
    coverage = fetch_routes(
        Path(args.route_config),
        Path(args.output_dir),
        args.timeout_seconds,
        args.window_start,
    )
    print(json.dumps(coverage, ensure_ascii=False, separators=(",", ":")))
    return 0 if coverage["route_ready_count"] >= coverage["minimum_ready_routes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
