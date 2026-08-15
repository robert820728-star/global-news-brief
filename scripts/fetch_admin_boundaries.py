#!/usr/bin/env python3
"""Resolve and cache first-level administrative boundaries by ISO alpha-3 code."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API_TEMPLATE = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM1/"
USER_AGENT = "global-news-brief/1.0"


def request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError(f"資料源回傳格式錯誤：{url}")
    return data


def download_geojson(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    data = json.loads(payload)
    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
        or not data["features"]
    ):
        raise ValueError(f"行政界線 GeoJSON 無有效 features：{url}")
    return data


def fetch_adm1(iso3: str, output: str | Path) -> dict[str, Any]:
    code = iso3.upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise ValueError("ISO3 必須是三個大寫英文字母")
    metadata_url = API_TEMPLATE.format(iso3=code)
    metadata = request_json(metadata_url)
    download_url = metadata.get("simplifiedGeometryGeoJSON")
    if not isinstance(download_url, str) or not download_url:
        raise ValueError(f"{code} 沒有可用的 ADM1 簡化 GeoJSON")

    geojson = download_geojson(download_url)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(geojson, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return {
        "iso3": code,
        "boundary_level": "ADM1",
        "feature_count": len(geojson["features"]),
        "source_name": "geoBoundaries gbOpen",
        "metadata_url": metadata_url,
        "source_url": download_url,
        "license": metadata.get("boundaryLicense"),
        "license_url": metadata.get("licenseSource"),
        "boundary_name": metadata.get("boundaryName"),
        "boundary_year": metadata.get("boundaryYearRepresented"),
        "output": str(destination),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso3", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = fetch_adm1(args.iso3, args.output)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "ready", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
