#!/usr/bin/env python3
"""Fetch canonical news source routes using only the Python standard library."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
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
    request = urllib.request.Request(
        request_url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
    )
    response = None
    try:
        try:
            response = urllib.request.urlopen(request, timeout=timeout_seconds)
        except urllib.error.HTTPError as error:
            response = error
        status = int(getattr(response, "status", response.getcode()))
        headers = response.headers
        body = decode_body(response.read(), headers.get("Content-Encoding", ""))
        snapshot_path.write_bytes(body)
        ready = 200 <= status < 300 and bool(body)
        return {
            "source_id": str(route["source_id"]),
            "route": str(route["route"]),
            "request_url": request_url,
            "http_status": status,
            "content_type": headers.get("Content-Type"),
            "bytes": len(body),
            "snapshot_path": str(snapshot_path),
            "sha256": hashlib.sha256(body).hexdigest(),
            "route_ready": ready,
            "error": None if ready else "HTTP response was not successful or body was empty",
        }
    except Exception as error:  # noqa: BLE001 - coverage must record each route failure.
        return {
            "source_id": str(route.get("source_id", "")),
            "route": str(route.get("route", "")),
            "request_url": request_url,
            "http_status": None,
            "content_type": None,
            "bytes": 0,
            "snapshot_path": None,
            "sha256": None,
            "route_ready": False,
            "error": str(error),
        }
    finally:
        if response is not None:
            response.close()


def fetch_routes(route_config: Path, output_dir: Path, timeout_seconds: int) -> dict:
    config = json.loads(route_config.read_text(encoding="utf-8-sig"))
    output_dir = output_dir.resolve()
    snapshot_dir = output_dir / "route-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    results = [
        fetch_one(route, snapshot_dir, timeout_seconds)
        for route in config.get("routes", [])
    ]
    coverage = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now().astimezone().isoformat(),
        "route_ready_count": sum(bool(item["route_ready"]) for item in results),
        "route_total_count": len(results),
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
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 120:
        parser.error("--timeout-seconds must be between 1 and 120")
    coverage = fetch_routes(
        Path(args.route_config),
        Path(args.output_dir),
        args.timeout_seconds,
    )
    print(json.dumps(coverage, ensure_ascii=False, separators=(",", ":")))
    return 0 if coverage["route_ready_count"] == coverage["route_total_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
