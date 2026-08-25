#!/usr/bin/env python3
"""Fetch canonical news source routes using only the Python standard library."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Mapping


USER_AGENT = "Mozilla/5.0 CodexNewsValidation/1.0"


def retry_delay_seconds(headers, attempt: int, default_interval: float = 1.0,
                        maximum: float = 300.0) -> float:
    """Return a bounded delay, preferring the server's Retry-After value."""
    raw = headers.get("Retry-After") if headers is not None else None
    if raw:
        try:
            return min(maximum, max(0.0, float(raw)))
        except (TypeError, ValueError):
            try:
                target = parsedate_to_datetime(str(raw))
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return min(
                    maximum,
                    max(0.0, (target - datetime.now(timezone.utc)).total_seconds()),
                )
            except (TypeError, ValueError, OverflowError):
                pass
    return min(maximum, max(0.0, float(default_interval)))


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
        parsed = datetime.fromisoformat(
            str(value).replace("/", "-").replace("Z", "+00:00")
        )
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
    max_attempts = max(1, min(6, int(route.get("max_attempts", 2))))
    last_headers = None
    for attempt in range(max_attempts):
        response = None
        try:
            try:
                response = urllib.request.urlopen(request, timeout=timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            status = int(getattr(response, "status", response.getcode()))
            response_headers = response.headers
            last_headers = response_headers
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
                    "acquisition_mode": (
                        "doc_api" if str(route.get("source_id")) == "gdelt"
                        else "primary_route"
                    ),
                }
            last_error = "HTTP response was not successful or body was empty"
        except Exception as error:  # noqa: BLE001 - record each route failure.
            last_error = str(error)
        finally:
            if response is not None:
                response.close()
        if attempt + 1 < max_attempts:
            time.sleep(retry_delay_seconds(
                last_headers, attempt, float(route.get("retry_interval_seconds", 1))
            ))
    return {
        "source_id": str(route.get("source_id", "")), "route": str(route.get("route", "")),
        "request_method": method, "request_url": request_url,
        "http_status": last_status, "content_type": last_content_type,
        "bytes": 0, "snapshot_path": None, "sha256": None, "route_ready": False,
        "json_exhaustion_path": route.get("json_exhaustion_path"),
        "source_exhaustion_marker": route.get("source_exhaustion_marker"),
        "retry_count": max_attempts - 1, "error": last_error,
        "acquisition_mode": "unavailable",
    }


def gdelt_archive_slots(window_start: str, window_end: str | None = None):
    start = datetime.fromisoformat(window_start.replace("Z", "+00:00")).astimezone(timezone.utc)
    end = (
        datetime.fromisoformat(window_end.replace("Z", "+00:00")).astimezone(timezone.utc)
        if window_end else datetime.now(timezone.utc)
    )
    cursor = start.replace(second=0, microsecond=0)
    cursor -= timedelta(minutes=cursor.minute % 15)
    end = end.replace(second=0, microsecond=0)
    end -= timedelta(minutes=end.minute % 15)
    while cursor <= end:
        yield cursor
        cursor += timedelta(minutes=15)


def title_from_gdelt_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    slug = urllib.parse.unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1])
    slug = slug.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()
    if len(slug) >= 8 and not slug.isdigit():
        return " ".join(slug.split())
    return f"{parsed.netloc or 'GDELT'} news report"


def _gdelt_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _gdelt_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_gdelt_export_row(columns: list[str]) -> dict | None:
    """Return the URL, archive time and source-backed GDELT discovery signals."""
    if (
        len(columns) < 61
        or not columns[59]
        or not columns[60].startswith(("http://", "https://"))
    ):
        return None
    countries = sorted({value for value in (columns[7], columns[17]) if value})
    signals = {
        "actor_country_codes": countries,
        "action_geo_country_code": columns[53] or None,
        "event_code": columns[26] or None,
        "event_root_code": columns[28] or None,
        "quad_class": _gdelt_int(columns[29]),
        "goldstein_scale": _gdelt_float(columns[30]),
        "num_mentions": _gdelt_int(columns[31]),
        "num_sources": _gdelt_int(columns[32]),
        "num_articles": _gdelt_int(columns[33]),
        "avg_tone": _gdelt_float(columns[34]),
    }
    return {
        "seen_date": columns[59],
        "url": columns[60],
        "discovery_signals": signals,
    }


def fetch_gdelt_export_part(url: str, timeout_seconds: int) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
        rows = []
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            for name in archive.namelist():
                for line in archive.read(name).decode("utf-8", errors="replace").splitlines():
                    columns = line.split("\t")
                    parsed = parse_gdelt_export_row(columns)
                    if parsed is not None:
                        rows.append(parsed)
        return {
            "url": url, "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body), "rows": rows, "error": None,
        }
    except Exception as error:  # noqa: BLE001 - each archive part is independently auditable.
        return {"url": url, "sha256": None, "bytes": 0, "rows": [], "error": str(error)}


def fetch_gdelt_export_fallback(route: Mapping, snapshot_dir: Path,
                                timeout_seconds: int, window_start: str | None,
                                window_end: str | None = None) -> dict | None:
    fallback = route.get("fallback")
    if not window_start or not isinstance(fallback, Mapping):
        return None
    if fallback.get("type") != "gdelt_export_24h":
        return None
    template = str(fallback["request_url_template"])
    slots = list(gdelt_archive_slots(window_start, window_end))
    urls = [template.replace("{yyyyMMddHHmm}", slot.strftime("%Y%m%d%H%M")) for slot in slots]
    workers = max(1, min(12, int(fallback.get("max_workers", 8))))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(
            lambda url: fetch_gdelt_export_part(url, timeout_seconds), urls
        ))
    successful = [part for part in parts if part["error"] is None]
    if not successful:
        return None
    articles = {}
    for part in successful:
        for row in part["rows"]:
            seen_date, url = row["seen_date"], row["url"]
            candidate = {
                "url": url,
                "title": title_from_gdelt_url(url),
                "seendate": f"{seen_date[:8]}T{seen_date[8:14]}Z",
                "discovery_signals": row["discovery_signals"],
            }
            current = articles.get(url)
            if current is None or candidate["seendate"] > current["seendate"]:
                articles[url] = candidate
    if not articles:
        return None
    payload = json.dumps({
        "articles": list(articles.values()),
        "_gdelt_export_provenance": {
            "requested_parts": len(parts),
            "successful_parts": len(successful),
            "parts": [
                {key: part[key] for key in ("url", "sha256", "bytes", "error")}
                for part in parts
            ],
        },
    }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    snapshot_path = safe_snapshot_path(snapshot_dir, str(route["snapshot_name"]))
    snapshot_path.write_bytes(payload)
    archive_complete = len(successful) == len(parts)
    return {
        "source_id": "gdelt", "route": str(route["route"]),
        "request_method": "GET", "request_url": template,
        "http_status": 200, "content_type": "application/json; charset=utf-8",
        "bytes": len(payload), "snapshot_path": str(snapshot_path),
        "sha256": hashlib.sha256(payload).hexdigest(), "route_ready": True,
        "json_exhaustion_path": route.get("json_exhaustion_path"),
        "source_exhaustion_marker": route.get("source_exhaustion_marker"),
        "retry_count": 0, "error": None, "acquisition_mode": "gdelt_export_24h",
        "gdelt_live_ready": archive_complete,
        "archive_requested_count": len(parts),
        "archive_ready_count": len(successful),
        "archive_complete": archive_complete,
        "coverage_complete": archive_complete,
        "coverage_status": "complete" if archive_complete else "degraded_partial",
    }


def reuse_recent_gdelt_snapshot(route: Mapping, snapshot_dir: Path,
                                output_dir: Path) -> dict | None:
    name = str(route["snapshot_name"])
    candidates = sorted(
        (
            path for path in output_dir.parent.glob(f"*/route-snapshots/{name}")
            if path.resolve() != (snapshot_dir / name).resolve()
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for cached in candidates:
        try:
            body = cached.read_bytes()
            payload = json.loads(body.decode("utf-8-sig"))
            if not isinstance(payload.get("articles"), list) or not payload["articles"]:
                continue
            snapshot_path = safe_snapshot_path(snapshot_dir, name)
            snapshot_path.write_bytes(body)
            age_seconds = max(0, int(time.time() - cached.stat().st_mtime))
            return {
                "source_id": "gdelt", "route": str(route["route"]),
                "request_method": "CACHE", "request_url": str(cached.resolve()),
                "http_status": 200, "content_type": "application/json; charset=utf-8",
                "bytes": len(body), "snapshot_path": str(snapshot_path),
                "sha256": hashlib.sha256(body).hexdigest(), "route_ready": True,
                "json_exhaustion_path": route.get("json_exhaustion_path"),
                "source_exhaustion_marker": route.get("source_exhaustion_marker"),
                "retry_count": 0, "error": None,
                "acquisition_mode": "last_known_good_cache",
                "gdelt_live_ready": False, "cache_age_seconds": age_seconds,
                "coverage_complete": False,
                "coverage_status": "degraded_cached",
            }
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None


def fetch_date_variants(route: Mapping, snapshot_dir: Path, timeout_seconds: int) -> dict:
    offsets = route.get("date_offsets_days")
    if not isinstance(offsets, list) or not offsets:
        result = fetch_one(route, snapshot_dir, timeout_seconds)
        result["coverage_complete"] = bool(result.get("route_ready"))
        result["coverage_status"] = "complete" if result["coverage_complete"] else "unavailable"
        return result
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
    primary["coverage_complete"] = len(ready) >= minimum_ready
    primary["coverage_status"] = (
        "complete" if primary["coverage_complete"] else "degraded_partial"
    )
    if not primary["coverage_complete"]:
        primary["coverage_warning"] = (
            f"dated route produced {len(ready)} successful variants; "
            f"requires {minimum_ready} for complete coverage"
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
    pagination = route.get("pagination", {})
    method = str(pagination.get("request_method", "GET")).upper()
    request_body = None
    if method != "GET" or route.get("request_json"):
        request_json = dict(route.get("request_json") or {})
        page_field = pagination.get("page_field")
        if page_field:
            request_json[str(page_field)] = page_index
        request_body = json.dumps(
            request_json, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    last_error = None
    last_status = None
    last_content_type = None
    max_attempts = max(1, min(6, int(route.get("max_attempts", 2))))
    last_headers = None
    for attempt in range(max_attempts):
        response = None
        try:
            request = urllib.request.Request(
                request_url, data=request_body, headers=headers, method=method
            )
            try:
                response = urllib.request.urlopen(request, timeout=timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            status = int(getattr(response, "status", response.getcode()))
            response_headers = response.headers
            last_headers = response_headers
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
        if attempt + 1 < max_attempts:
            time.sleep(retry_delay_seconds(
                last_headers, attempt, float(route.get("retry_interval_seconds", 1))
            ))
    return ({
        "page_index": page_index, "request_url": request_url,
        "http_status": last_status, "content_type": last_content_type,
        "bytes": 0, "snapshot_path": None, "sha256": None,
        "retry_count": max_attempts - 1, "error": last_error,
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
    template = resolve_route_url({
        "request_url_template": pagination.get("request_url_template")
        or route["request_url_template"]
    })
    base = Path(str(route["snapshot_name"]))
    page_snapshots = list(result.get("page_snapshots") or [])
    complete = False
    next_page_path = pagination.get("next_page_path")
    page_index = start_page
    if isinstance(next_page_path, list) and result.get("snapshot_path"):
        try:
            initial_payload = json.loads(
                Path(result["snapshot_path"]).read_text(encoding="utf-8-sig")
            )
            initial_next = value_at_path(initial_payload, next_page_path)
            if initial_next in (None, ""):
                result.update(
                    pagination_exhausted=True,
                    coverage_complete=True,
                    coverage_status="complete",
                )
                return result
            page_index = int(initial_next)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            result.update(
                coverage_complete=False,
                coverage_status="degraded_partial",
                coverage_warning="initial pagination cursor could not be read",
            )
            return result
    fetched_pages = 0
    while fetched_pages < max_pages:
        request_url = template.replace("{page}", str(page_index))
        snapshot_name = f"{base.stem}.page-{page_index:04d}.json"
        snapshot_path = safe_snapshot_path(snapshot_dir, snapshot_name)
        page, raw = fetch_page(route, request_url, snapshot_path, timeout_seconds, page_index)
        page_snapshots.append(page)
        fetched_pages += 1
        if raw is None:
            result.update(
                page_snapshots=page_snapshots,
                coverage_complete=False,
                coverage_status="degraded_partial",
                coverage_warning=page["error"],
            )
            return result
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            result.update(
                page_snapshots=page_snapshots,
                coverage_complete=False,
                coverage_status="degraded_partial",
                coverage_warning=str(error),
            )
            return result
        items = value_at_path(payload, items_path)
        if not isinstance(items, list):
            result.update(
                page_snapshots=page_snapshots,
                coverage_complete=False,
                coverage_status="degraded_partial",
                coverage_warning="pagination items_path did not resolve to an array",
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
        if isinstance(next_page_path, list):
            next_page = value_at_path(payload, next_page_path)
            if next_page in (None, ""):
                result["pagination_exhausted"] = True
                complete = True
                break
            try:
                page_index = int(next_page)
            except (TypeError, ValueError):
                result.update(
                    page_snapshots=page_snapshots,
                    coverage_complete=False,
                    coverage_status="degraded_partial",
                    coverage_warning="pagination next-page cursor is invalid",
                )
                return result
        else:
            page_index += 1
    result["page_snapshots"] = page_snapshots
    result["coverage_complete"] = complete
    result["coverage_status"] = "complete" if complete else "degraded_partial"
    if not complete:
        result["coverage_warning"] = (
            f"pagination did not reach window_start within {max_pages} pages"
        )
    return result


def fetch_routes(route_config: Path, output_dir: Path, timeout_seconds: int,
                 window_start: str | None = None,
                 window_end: str | None = None) -> dict:
    config = json.loads(route_config.read_text(encoding="utf-8-sig"))
    output_dir = output_dir.resolve()
    snapshot_dir = output_dir / "route-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for route in config.get("routes", []):
        if str(route.get("source_id")) == "gdelt":
            archive_result = fetch_gdelt_export_fallback(
                route, snapshot_dir, timeout_seconds, window_start, window_end
            )
            if archive_result and archive_result.get("route_ready"):
                result = archive_result
                result["optional_doc_api_attempted"] = False
                result["coverage_complete"] = bool(result.get("archive_complete"))
                result["coverage_status"] = (
                    "complete" if result["coverage_complete"] else "degraded_partial"
                )
                result["gdelt_live_ready"] = result["coverage_complete"]
            else:
                doc_result = fetch_date_variants(route, snapshot_dir, timeout_seconds)
                if doc_result.get("route_ready"):
                    result = doc_result
                    result["acquisition_mode"] = "doc_api_optional"
                    result["gdelt_live_ready"] = False
                else:
                    result = reuse_recent_gdelt_snapshot(
                        route, snapshot_dir, output_dir
                    ) or doc_result
                result["archive_attempt"] = {
                    key: (archive_result or {}).get(key)
                    for key in ("http_status", "retry_count", "error", "request_url")
                }
                result["optional_doc_api_attempted"] = True
            result.setdefault("gdelt_live_ready", bool(
                result.get("route_ready")
                and result.get("acquisition_mode") == "gdelt_export_24h"
            ))
        else:
            result = fetch_date_variants(route, snapshot_dir, timeout_seconds)
        if result.get("route_ready"):
            result = fetch_pagination(
                route, result, snapshot_dir, timeout_seconds, window_start
            )
        result.setdefault("coverage_complete", bool(result.get("route_ready")))
        result.setdefault(
            "coverage_status",
            "complete" if result["coverage_complete"] else "unavailable",
        )
        results.append(result)
    ready_count = sum(bool(item["route_ready"]) for item in results)
    minimum_ready = int(config.get("minimum_ready_routes", len(results)))
    gdelt_result = next((item for item in results if item.get("source_id") == "gdelt"), None)
    gdelt_live_ready = bool(gdelt_result and gdelt_result.get("gdelt_live_ready"))
    publication_ready = ready_count >= minimum_ready
    complete_count = sum(bool(item.get("coverage_complete")) for item in results)
    gdelt_configured = gdelt_result is not None
    coverage = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now().astimezone().isoformat(),
        "route_ready_count": ready_count,
        "route_total_count": len(results),
        "coverage_complete_count": complete_count,
        "minimum_ready_routes": minimum_ready,
        "publication_ready": publication_ready,
        "gdelt_live_ready": gdelt_live_ready,
        "gdelt_acquisition_mode": (
            gdelt_result.get("acquisition_mode") if gdelt_result else "not_configured"
        ),
        "status": (
            "ready" if (
                ready_count == len(results)
                and complete_count == len(results)
                and (not gdelt_configured or gdelt_live_ready)
            )
            else "degraded" if publication_ready
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
    parser.add_argument("--window-end")
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 120:
        parser.error("--timeout-seconds must be between 1 and 120")
    coverage = fetch_routes(
        Path(args.route_config),
        Path(args.output_dir),
        args.timeout_seconds,
        args.window_start,
        args.window_end,
    )
    print(json.dumps(coverage, ensure_ascii=False, separators=(",", ":")))
    return 0 if coverage["publication_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
