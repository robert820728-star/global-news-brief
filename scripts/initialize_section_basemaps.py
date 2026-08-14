#!/usr/bin/env python3
"""Initialize reusable section basemap specifications after user section setup.

This script records a stable section-level geographic canvas derived from the world
country dataset. It does not replace event-specific map rendering: build-news-maps
uses these specs as the first context frame, then adds event points/ranges/routes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "maps" / "source" / "world-countries.geojson"
OUT = ROOT / "maps" / "generated" / "sections"

PRESETS: dict[str, dict[str, Any]] = {
    "AUS": {
        "name": "澳洲",
        "scope": ["Australia"],
        "bounds": [110.0, 155.0, -45.0, -9.0],
        "central_lon": 134.0,
        "standard_lat": -27.0,
        "projection": "regional",
    },
    "OCE": {
        "name": "大洋洲",
        "scope": ["Australia", "New Zealand", "Melanesia", "Micronesia", "Polynesia"],
        "bounds": [110.0, 240.0, -55.0, 30.0],
        "central_lon": 175.0,
        "standard_lat": -15.0,
        "projection": "pacific_centered",
    },
}


def validate_section(section: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    code = section.get("code")
    if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{3}", code):
        errors.append("section.code 必須是三碼大寫英文字母")
    if not isinstance(section.get("name"), str) or not section.get("name", "").strip():
        errors.append("section.name 不得為空")
    bounds = section.get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 4 or not all(isinstance(v, (int, float)) for v in bounds):
        errors.append("section.bounds 必須是 [min_lon,max_lon,min_lat,max_lat]")
    return errors


def initialize(section: dict[str, Any]) -> Path:
    errors = validate_section(section)
    if errors:
        raise ValueError("; ".join(errors))
    code = section["code"]
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": 1,
        "code": code,
        "name": section["name"],
        "scope": section.get("scope", []),
        "source_geojson": str(SOURCE.relative_to(ROOT)),
        "bounds": section["bounds"],
        "projection": section.get("projection", "regional"),
        "central_lon": section.get("central_lon"),
        "standard_lat": section.get("standard_lat"),
        "status": "spec_ready",
        "visual_checked": False,
        "png_path": f"maps/generated/sections/{code}-base.png",
        "svg_path": f"maps/generated/sections/{code}-base.svg",
        "purpose": "section_context_basemap",
    }
    path = OUT / f"{code}-base.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True)
    parser.add_argument("--name")
    parser.add_argument("--bounds", nargs=4, type=float)
    parser.add_argument("--scope", nargs="*")
    args = parser.parse_args()
    code = args.code.upper()
    section = dict(PRESETS.get(code, {}))
    section["code"] = code
    if args.name:
        section["name"] = args.name
    if args.bounds:
        section["bounds"] = args.bounds
    if args.scope is not None:
        section["scope"] = args.scope
    if "name" not in section or "bounds" not in section:
        raise SystemExit("未知板塊必須提供 --name 與 --bounds；區域成員可用 --scope 補充")
    path = initialize(section)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
