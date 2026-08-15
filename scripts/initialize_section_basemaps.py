#!/usr/bin/env python3
"""Create a reusable basemap specification for any country or multi-country region."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

from fetch_admin_boundaries import fetch_adm1

ROOT = Path(__file__).resolve().parents[1]
WORLD_SOURCE = ROOT / "maps" / "source" / "world-countries.geojson"
CACHE = ROOT / "maps" / "cache"
OUT = ROOT / "maps" / "generated" / "sections"

PRESETS: dict[str, dict[str, Any]] = {
    "AUS": {"name": "澳洲", "scope": ["Australia"]},
    "JPN": {"name": "日本", "scope": ["Japan"]},
    "OCE": {
        "name": "大洋洲", "boundary_mode": "region",
        "scope": ["Australia", "New Zealand", "Melanesia", "Micronesia", "Polynesia"],
        "bounds": [110.0, 240.0, -55.0, 30.0], "central_lon": 175.0,
        "standard_lat": -15.0, "projection": "pacific_centered",
    },
}


def validate_identity(section: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(section.get("code"), str) or not re.fullmatch(r"[A-Z]{3}", section["code"]):
        errors.append("section.code 必須是 ISO 3166-1 alpha-3 三碼大寫英文字母")
    if not isinstance(section.get("name"), str) or not section["name"].strip():
        errors.append("section.name 不得為空")
    return errors


def coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if (isinstance(value, list) and len(value) >= 2
            and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float))):
        yield float(value[0]), float(value[1])
    elif isinstance(value, list):
        for item in value:
            yield from coordinate_pairs(item)


def geojson_bounds(path: Path, padding_ratio: float = 0.04) -> list[float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    points: list[tuple[float, float]] = []
    for feature in data.get("features", []):
        points.extend(coordinate_pairs(feature.get("geometry", {}).get("coordinates", [])))
    if not points:
        raise ValueError(f"無法從行政界線計算地圖範圍：{path}")
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    lon_pad = max((max(lons) - min(lons)) * padding_ratio, 0.5)
    lat_pad = max((max(lats) - min(lats)) * padding_ratio, 0.5)
    return [min(lons) - lon_pad, max(lons) + lon_pad, min(lats) - lat_pad, max(lats) + lat_pad]


def boundary_mode(section: dict[str, Any]) -> str:
    requested = section.get("boundary_mode", "auto")
    if requested in {"country", "region"}:
        return requested
    scope = section.get("scope")
    return "region" if isinstance(scope, list) and len(scope) > 1 else "country"


def resolve_source(section: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if boundary_mode(section) == "region":
        return WORLD_SOURCE, {
            "boundary_mode": "region", "boundary_level": "country",
            "source_name": "repository world countries",
            "source_url": None, "license": "See maps/source/README.md",
        }
    code = section["code"]
    destination = CACHE / f"{code.lower()}-adm1.geojson"
    sidecar = CACHE / f"{code.lower()}-adm1-source.json"
    if destination.is_file() and sidecar.is_file():
        source_info = json.loads(sidecar.read_text(encoding="utf-8"))
    else:
        source_info = fetch_adm1(code, destination)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(json.dumps(source_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, {"boundary_mode": "country", **source_info}


def initialize(section: dict[str, Any]) -> Path:
    errors = validate_identity(section)
    if errors:
        raise ValueError("; ".join(errors))
    code = section["code"]
    source, source_info = resolve_source(section)
    bounds = section.get("bounds")
    if bounds is None and source_info["boundary_mode"] == "country":
        bounds = geojson_bounds(source)
    if not isinstance(bounds, list) or len(bounds) != 4 or not all(isinstance(v, (int, float)) for v in bounds):
        raise ValueError("跨國區域必須提供 section.bounds；單一國家會由 ADM1 資料自動計算")
    center_lon = section.get("central_lon", (bounds[0] + bounds[1]) / 2)
    standard_lat = section.get("standard_lat", (bounds[2] + bounds[3]) / 2)
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1, "code": code, "name": section["name"],
        "scope": section.get("scope", []),
        "boundary_mode": source_info["boundary_mode"],
        "boundary_level": source_info["boundary_level"],
        "source_geojson": str(source.relative_to(ROOT)),
        "source_name": source_info.get("source_name"), "source_url": source_info.get("source_url"),
        "source_license": source_info.get("license"), "source_license_url": source_info.get("license_url"),
        "source_boundary_name": source_info.get("boundary_name"),
        "source_boundary_year": source_info.get("boundary_year"),
        "source_feature_count": source_info.get("feature_count"),
        "base_country_iso": code if source_info["boundary_mode"] == "country" else None,
        "bounds": bounds, "projection": section.get("projection", "regional"),
        "central_lon": center_lon, "standard_lat": standard_lat,
        "status": "spec_ready", "visual_checked": False,
        "png_path": f"maps/generated/sections/{code}-base.png",
        "svg_path": f"maps/generated/sections/{code}-base.svg",
        "purpose": "section_context_basemap", "style_id": "yellow-admin-v2",
        "style_reference": "maps/style.json", "generator": "scripts/render_base_maps.py",
        "style": {"land_fill": "#f3e6b8", "boundary_color": "#53606f",
                  "background": "#ffffff", "boundary_level": source_info["boundary_level"]},
    }
    path = OUT / f"{code}-base.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="ISO 3166-1 alpha-3 code")
    parser.add_argument("--name")
    parser.add_argument("--bounds", nargs=4, type=float)
    parser.add_argument("--scope", nargs="*")
    parser.add_argument("--boundary-mode", choices=("auto", "country", "region"), default="auto")
    args = parser.parse_args()
    code = args.code.upper()
    section = dict(PRESETS.get(code, {}))
    section["code"] = code
    section["name"] = args.name or section.get("name") or code
    section["boundary_mode"] = args.boundary_mode if args.boundary_mode != "auto" else section.get("boundary_mode", "auto")
    if args.bounds:
        section["bounds"] = args.bounds
    if args.scope is not None:
        section["scope"] = args.scope
    print(initialize(section))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
