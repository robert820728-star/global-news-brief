#!/usr/bin/env python3
"""Render reusable base maps from GeoJSON source files."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "maps" / "source"
OUT = ROOT / "maps" / "generated"
STYLE_PATH = ROOT / "maps" / "style.json"
with STYLE_PATH.open("r", encoding="utf-8") as style_handle:
    STYLE_CONFIG = json.load(style_handle)
CANONICAL_STYLE = {
    **STYLE_CONFIG["colors"],
    "boundary_width": STYLE_CONFIG.get("line_width", 0.42),
}


MAPS = {
    "taiwan-counties-yellow-v2": {
        "file": SOURCE / "taiwan-counties-alt.geojson",
        "title": "Taiwan counties",
        "figsize": (7.0, 9.0),
        "bounds": (119.7, 122.2, 21.7, 25.5),
        "projection": "regional",
        "standard_lat": 23.7,
    },
    "china-provinces-yellow-v2": {
        "file": SOURCE / "china-provinces.geojson",
        "title": "China provinces",
        "figsize": (10.0, 8.4),
        "bounds": (72.0, 136.0, 17.0, 55.0),
        "projection": "regional",
        "standard_lat": 35.0,
    },
    "world-countries-pacific-robinson-yellow-v2": {
        "file": SOURCE / "world-countries.geojson",
        "title": "World countries",
        "figsize": (10.0, 5.8),
        "bounds": (-30.0, 330.0, -60.0, 85.0),
        "projection": "robinson_pacific",
        "standard_lat": 0.0,
        "cut_lon": -30.0,
        "central_lon": 150.0,
        "use_data_bounds": True,
    },
}

LABEL_FONT_CANDIDATES = (
    ROOT / "maps" / "fonts" / "NotoSansTC-Regular.otf",
    Path("C:/Windows/Fonts/NotoSansTC-VF.ttf"),
    Path("C:/Windows/Fonts/msjh.ttc"),
    Path("C:/Windows/Fonts/mingliu.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-TC-Regular.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
)


def label_font_size(width: int, height: int) -> int:
    """Return a phone-readable label size for a rendered map."""
    return max(36, round(min(width, height) * 0.034))


def _font_has_traditional_chinese(font) -> bool:
    glyphs = [bytes(font.getmask(character)) for character in "è‡ºç£åœ‹éš›"]
    return all(glyphs) and len(set(glyphs)) == len(glyphs)


def load_label_font(size: int):
    """Load a cross-platform font with verified Traditional Chinese glyphs."""
    configured = os.environ.get("NEWS_MAP_FONT")
    candidates = ((Path(configured),) if configured else ()) + LABEL_FONT_CANDIDATES
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            font = ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
        if _font_has_traditional_chinese(font):
            return font
    raise RuntimeError(
        "No Traditional Chinese map font found; install Noto Sans CJK/TC, "
        "Microsoft JhengHei, or set NEWS_MAP_FONT"
    )
SECTION_BASE_MAPS = {
    "TWN": "taiwan-counties-yellow-v2",
    "CHN": "china-provinces-yellow-v2",
    "GLB": "world-countries-pacific-robinson-yellow-v2",
}


def iter_rings(geometry: dict):
    """Yield exterior rings from GeoJSON Polygon or MultiPolygon geometry."""
    if not geometry:
        return
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        if coords:
            yield coords[0]
    elif gtype == "MultiPolygon":
        for poly in coords:
            if poly:
                yield poly[0]


def split_antimeridian(ring):
    """Drop world-map rings that jump across the antimeridian."""
    if len(ring) < 3:
        return []
    segments = []
    current = [ring[0]]
    last_lon = ring[0][0]
    for point in ring[1:]:
        lon = point[0]
        if abs(lon - last_lon) > 180:
            if len(current) >= 3:
                segments.append(current)
            current = [point]
        else:
            current.append(point)
        last_lon = lon
    if len(current) >= 3:
        segments.append(current)
    return segments


def split_cutline_for_pacific(ring, cut_lon: float):
    """Split rings at the map edge before shifting longitudes to a Pacific-centered map."""
    if len(ring) < 3:
        return []
    segments = []
    current = [ring[0]]
    last_side = ring[0][0] < cut_lon
    for point in ring[1:]:
        side = point[0] < cut_lon
        if side != last_side:
            if len(current) >= 3:
                segments.append(current)
            current = [point]
        else:
            current.append(point)
        last_side = side
    if len(current) >= 3:
        segments.append(current)
    return segments


def collect_polygons(path: Path, spec: dict):
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    polygons = []
    filter_iso3 = spec.get("filter_iso3")
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        if filter_iso3 and properties.get("ISO_A3") != filter_iso3:
            continue
        for ring in iter_rings(feature.get("geometry")):
            if spec.get("projection") in {"pacific_centered", "robinson_pacific"}:
                polygons.extend(split_cutline_for_pacific(ring, spec.get("cut_lon", -30.0)))
            else:
                polygons.extend(split_antimeridian(ring))
    return polygons


def collect_highlights(path: Path, spec: dict):
    highlights = spec.get("highlights", [])
    if not highlights:
        return []
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    groups = []
    for item in highlights:
        match = item.get("match")
        label = item.get("label")
        role = item.get("role", "primary")
        if not isinstance(match, dict) or not match:
            raise ValueError("highlight.match å¿…é ˆæŒ‡å®šè‡³å°‘ä¸€å€‹è¡Œæ”¿å€æ¬„ä½")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("highlight.label å¿…é ˆæ˜¯éžç©ºç™½åœ°å")
        if role not in {"primary", "secondary"}:
            raise ValueError("highlight.role å¿…é ˆæ˜¯ primary æˆ– secondary")
        rings = []
        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            if not all(str(properties.get(key)) == str(value) for key, value in match.items()):
                continue
            for ring in iter_rings(feature.get("geometry")):
                if spec.get("projection") in {"pacific_centered", "robinson_pacific"}:
                    rings.extend(split_cutline_for_pacific(ring, spec.get("cut_lon", -30.0)))
                else:
                    rings.extend(split_antimeridian(ring))
        if not rings:
            criteria = ", ".join(f"{key}={value}" for key, value in match.items())
            raise ValueError(f"æ‰¾ä¸åˆ°æŒ‡å®šè¡Œæ”¿å€ï¼š{criteria}")
        groups.append({"label": label.strip(), "role": role, "rings": rings})
    return groups


ROBINSON_TABLE = [
    (0, 1.0000, 0.0000),
    (5, 0.9986, 0.0620),
    (10, 0.9954, 0.1240),
    (15, 0.9900, 0.1860),
    (20, 0.9822, 0.2480),
    (25, 0.9730, 0.3100),
    (30, 0.9600, 0.3720),
    (35, 0.9427, 0.4340),
    (40, 0.9216, 0.4958),
    (45, 0.8962, 0.5571),
    (50, 0.8679, 0.6176),
    (55, 0.8350, 0.6769),
    (60, 0.7986, 0.7346),
    (65, 0.7597, 0.7903),
    (70, 0.7186, 0.8435),
    (75, 0.6732, 0.8936),
    (80, 0.6213, 0.9394),
    (85, 0.5722, 0.9761),
    (90, 0.5322, 1.0000),
]


def interpolate_robinson(abs_lat: float):
    if abs_lat >= 90:
        return ROBINSON_TABLE[-1][1], ROBINSON_TABLE[-1][2]
    for idx in range(len(ROBINSON_TABLE) - 1):
        lat0, x0, y0 = ROBINSON_TABLE[idx]
        lat1, x1, y1 = ROBINSON_TABLE[idx + 1]
        if lat0 <= abs_lat <= lat1:
            t = (abs_lat - lat0) / (lat1 - lat0)
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    return ROBINSON_TABLE[-1][1], ROBINSON_TABLE[-1][2]


def project_point(lon: float, lat: float, spec: dict):
    """Project lon/lat for reader-friendly news maps without GIS dependencies."""
    import math

    projection = spec.get("projection", "regional")
    if projection == "robinson_pacific":
        central_lon = spec.get("central_lon", 150.0)
        dlon = ((lon - central_lon + 180.0) % 360.0) - 180.0
        xcoef, ycoef = interpolate_robinson(abs(lat))
        x = 0.8487 * math.radians(dlon) * xcoef
        y = 1.3523 * ycoef
        if lat < 0:
            y = -y
        return x, y
    if projection == "pacific_centered":
        cut_lon = spec.get("cut_lon", -30.0)
        shifted_lon = lon if lon >= cut_lon else lon + 360
        return shifted_lon, lat
    if projection == "world":
        # Equal Earth projection approximation, good enough for full-world locator maps.
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        a1 = 1.340264
        a2 = -0.081106
        a3 = 0.000893
        a4 = 0.003796
        theta = math.asin((math.sqrt(3) / 2.0) * math.sin(lat_rad))
        theta2 = theta * theta
        denom = 3 * (9 * a4 * theta2 + 7 * a3) * theta2 + 3 * a2 * theta2 + a1
        x = (2 * math.sqrt(3) * lon_rad * math.cos(theta)) / denom
        y = a4 * theta**9 + a3 * theta**7 + a2 * theta**3 + a1 * theta
        return x, y

    scale = math.cos(math.radians(spec.get("standard_lat", 0.0)))
    return lon * scale, lat


def project_ring(ring, spec: dict):
    return [project_point(float(lon), float(lat), spec) for lon, lat, *_ in ring]


def project_bounds(bounds, spec: dict):
    minx, maxx, miny, maxy = bounds
    corners = [
        project_point(minx, miny, spec),
        project_point(minx, maxy, spec),
        project_point(maxx, miny, spec),
        project_point(maxx, maxy, spec),
    ]
    xs = [x for x, _ in corners]
    ys = [y for _, y in corners]
    return min(xs), max(xs), min(ys), max(ys)


def data_bounds(polygons):
    xs = []
    ys = []
    for ring in polygons:
        for x, y in ring:
            xs.append(x)
            ys.append(y)
    return min(xs), max(xs), min(ys), max(ys)


def add_padding(bounds, pad_ratio=0.035):
    minx, maxx, miny, maxy = bounds
    dx = maxx - minx
    dy = maxy - miny
    return (
        minx - dx * pad_ratio,
        maxx + dx * pad_ratio,
        miny - dy * pad_ratio,
        maxy + dy * pad_ratio,
    )


def render(name: str, spec: dict):
    polygons = [project_ring(ring, spec) for ring in collect_polygons(spec["file"], spec)]
    highlight_groups = [
        {
            **group,
            "rings": [project_ring(ring, spec) for ring in group["rings"]],
        }
        for group in collect_highlights(spec["file"], spec)
    ]
    style = {**CANONICAL_STYLE, **spec.get("style", {})}
    if spec.get("style_id", STYLE_CONFIG["style_id"]) != STYLE_CONFIG["style_id"]:
        raise ValueError("åœ°åœ– style_id ä¸ç¬¦åˆ maps/style.json")
    if not polygons:
        raise ValueError(f"{name} æ²’æœ‰å¯ç¹ªè£½çš„ GeoJSON polygons")
    base_country_iso = spec.get("base_country_iso")
    base_polygons = []
    if base_country_iso:
        base_spec = {**spec, "filter_iso3": base_country_iso}
        base_rings = collect_polygons(SOURCE / "world-countries.geojson", base_spec)
        base_polygons = [project_ring(ring, spec) for ring in base_rings]
    bounds = data_bounds(polygons) if spec.get("use_data_bounds") else project_bounds(spec["bounds"], spec)
    minx, maxx, miny, maxy = add_padding(bounds)
    width = max(320, round(float(spec["figsize"][0]) * 180))
    height = max(240, round(float(spec["figsize"][1]) * 180))
    margin = max(8, round(min(width, height) * 0.02))
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)

    def pixels(ring):
    Ûkh‘éì¶»§q«^tÍÁ…¹}à€¨€¡Ý¥‘Ñ €´€È€¨µ…É¥¸¤°4(€€€€€€€€€€€€€€€¡•¥¡Ð€´µ…É¥¸€´€¡ä€´µ¥¹ä¤€¼ÍÁ…¹}ä€¨€¡¡•¥¡Ð€´€È€¨µ…É¥¸¤°4(€€€€€€€€€€€€¤4(€€€€€€€€€€€™½Èà°ä¥¸É¥¹œ4(€€€€€€€t4(4(€€€±…¹‘}™¥±°€ôÍÑå±”¹•Ð ‰±…¹‘}™¥±°ˆ°€ˆ˜Í”Ùˆàˆ¤4(€€€‰½Õ¹‘…Éå}½±½È€ôÍÑå±”¹•Ð ‰‰½Õ¹‘…Éå}½±½Èˆ°€ˆŒÔÌØÀÙ˜ˆ¤4(€€€‰…­É½Õ¹€ôÍÑå±”¹•Ð ‰‰…­É½Õ¹ˆ°€ˆ™™™™™˜ˆ¤4(€€€±¥¹•}Ý¥‘Ñ €ôµ…à Ä°É½Õ¹¡™±½…Ð¡ÍÑå±”¹•Ð ‰‰½Õ¹‘…Éå}Ý¥‘Ñ ˆ°€À¸ÐÈ¤¤€¨€È¤¤4(€€€¥µ…”€ô%µ…”¹¹•Ü ‰Iˆ°€¡Ý¥‘Ñ °¡•¥¡Ð¤°‰…­É½Õ¹¤4(€€€‘É…Ý¥¹œ€ô%µ…•É…Ü¹É…Ü¡¥µ…”¤4(€€€™½ÈÉ¥¹œ¥¸‰…Í•}Á½±å½¹Ìè4(€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡É¥¹œ¤4(€€€€€€€¥˜±•¸¡Á½¥¹ÑÌ¤€øô€Ìè4(€€€€€€€€€€€‘É…Ý¥¹œ¹Á½±å½¸¡Á½¥¹ÑÌ°™¥±°õ±…¹‘}™¥±°¤4(€€€™½ÈÉ¥¹œ¥¸Á½±å½¹Ìè(€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡É¥¹œ¤(€€€€€€€¥˜±•¸¡Á½¥¹ÑÌ¤€øô€Ìè(€€€€€€€€€€€‘É…Ý¥¹œ¹Á½±å½¸¡Á½¥¹ÑÌ°™¥±°õ±…¹‘}™¥±°°½ÕÑ±¥¹”õ‰½Õ¹‘…Éå}½±½È°Ý¥‘Ñ õ±¥¹•}Ý¥‘Ñ ¤(€€€¡¥¡±¥¡Ñ}½±½ÉÌ€ôì(€€€€€€€€‰ÁÉ¥µ…ÉäˆèÍÑå±”¹•Ð ‰ÁÉ¥µ…Éå}¡¥¡±¥¡Ðˆ°€ˆŒÜÌØÉ˜ˆ¤°(€€€€€€€€‰Í•½¹‘…ÉäˆèÍÑå±”¹•Ð ‰Í•½¹‘…Éå}¡¥¡±¥¡Ðˆ°€ˆ˜Èá”Éˆˆ¤°(€€€ô(€€€™½ÈÉ½ÕÀ¥¸¡¥¡±¥¡Ñ}É½ÕÁÌè(€€€€€€€™½ÈÉ¥¹œ¥¸É½ÕÁl‰É¥¹Ì‰tè(€€€€€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡É¥¹œ¤(€€€€€€€€€€€¥˜±•¸¡Á½¥¹ÑÌ¤€øô€Ìè(€€€€€€€€€€€€€€€‘É…Ý¥¹œ¹Á½±å½¸ (€€€€€€€€€€€€€€€€€€€Á½¥¹ÑÌ°(€€€€€€€€€€€€€€€€€€€™¥±°õ¡¥¡±¥¡Ñ}½±½ÉÍmÉ½ÕÁl‰É½±”‰ut°(€€€€€€€€€€€€€€€€€€€½ÕÑ±¥¹”õ‰½Õ¹‘…Éå}½±½È°(€€€€€€€€€€€€€€€€€€€Ý¥‘Ñ õ±¥¹•}Ý¥‘Ñ °(€€€€€€€€€€€€€€€€¤((€€€™½¹Ñ}Í¥é”€ô±…‰•±}™½¹Ñ}Í¥é”¡Ý¥‘Ñ °¡•¥¡Ð¤(€€€±…‰•±}™½¹Ð€ô±½…‘}±…‰•±}™½¹Ð¡™½¹Ñ}Í¥é”¤(€€€±…‰•±}Á½Í¥Ñ¥½¹Ì€ômt(€€€™½ÈÉ½ÕÀ¥¸¡¥¡±¥¡Ñ}É½ÕÁÌè(€€€€€€€±…‰•±}É¥¹œ€ôµ…à¡É½ÕÁl‰É¥¹Ì‰t°­•äõ±•¸¤(€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡±…‰•±}É¥¹œ¤(€€€€€€€à€ôÍÕ´¡Á½¥¹ÑlÁt™½ÈÁ½¥¹Ð¥¸Á½¥¹ÑÌ¤€¼±•¸¡Á½¥¹ÑÌ¤(€€€€€€€ä€ôÍÕ´¡Á½¥¹ÑlÅt™½ÈÁ½¥¹Ð¥¸Á½¥¹ÑÌ¤€¼±•¸¡Á½¥¹ÑÌ¤(€€€€€€€‘É…Ý¥¹œ¹Ñ•áÐ (€€€€€€€€€€€€¡à°ä¤°(€€€€€€€€€€€É½ÕÁl‰±…‰•°‰t°(€€€€€€€€€€€™¥±°ôˆŒÄÄÄÄÄÄˆ°(€€€€€€€€€€€™½¹Ðõ±…‰•±}™½¹Ð°(€€€€€€€€€€€…¹¡½Èô‰µ´ˆ°(€€€€€€€€€€€ÍÑÉ½­•}Ý¥‘Ñ ôÈ°(€€€€€€€€€€€ÍÑÉ½­•}™¥±°ôˆ™™™™™˜ˆ°(€€€€€€€€¤(€€€€€€€±…‰•±}Á½Í¥Ñ¥½¹Ì¹…ÁÁ•¹ ¡É½ÕÁl‰±…‰•°‰t°à°ä¤¤(4(€€€‘•ÍÑ¥¹…Ñ¥½¸€ô=UP€¼¹…µ”4(€€€‘•ÍÑ¥¹…Ñ¥½¸¹Á…É•¹Ð¹µ­‘¥È¡Á…É•¹ÑÌõQÉÕ”°•á¥ÍÑ}½¬õQÉÕ”¤4(€€€Á¹}Á…Ñ €ô‘•ÍÑ¥¹…Ñ¥½¸¹Ý¥Ñ¡}ÍÕ™™¥à ˆ¹Á¹œˆ¤4(€€€ÍÙ}Á…Ñ €ô‘•ÍÑ¥¹…Ñ¥½¸¹Ý¥Ñ¡}ÍÕ™™¥à ˆ¹ÍÙœˆ¤4(€€€¥µ…”¹Í…Ù”¡Á¹}Á…Ñ °™½Éµ…Ðô‰A9ˆ°½ÁÑ¥µ¥é”õQÉÕ”¤4(4(€€€ÍÙ}Á½±å½¹Ì€ômt4(€€€™½ÈÉ¥¹œ¥¸‰…Í•}Á½±å½¹Ìè4(€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡É¥¹œ¤4(€€€€€€€¥˜±•¸¡Á½¥¹ÑÌ¤€øô€Ìè4(€€€€€€€€€€€½½É‘Ì€ô€ˆ€ˆ¹©½¥¸¡˜‰íàè¸É™ô±íäè¸É™ôˆ™½Èà°ä¥¸Á½¥¹ÑÌ¤4(€€€€€€€€€€€ÍÙ}Á½±å½¹Ì¹…ÁÁ•¹¡˜œñÁ½±å½¸Á½¥¹ÑÌô‰í½½É‘Íôˆ™¥±°ô‰í±…¹‘}™¥±±ôˆÍÑÉ½­”ô‰¹½¹”ˆ¼øœ¤4(€€€™½ÈÉ¥¹œ¥¸Á½±å½¹Ìè(€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡É¥¹œ¤4(€€€€€€€¥˜±•¸¡Á½¥¹ÑÌ¤€øô€Ìè4(€€€€€€€€€€€½½É‘Ì€ô€ˆ€ˆ¹©½¥¸¡˜‰íàè¸É™ô±íäè¸É™ôˆ™½Èà°ä¥¸Á½¥¹ÑÌ¤4(€€€€€€€€€€€ÍÙ}Á½±å½¹Ì¹…ÁÁ•¹ (€€€€€€€€€€€€€€€˜œñÁ½±å½¸Á½¥¹ÑÌô‰í½½É‘Íôˆ™¥±°ô‰í±…¹‘}™¥±±ôˆ€œ(€€€€€€€€€€€€€€€˜ÍÑÉ½­”ô‰í‰½Õ¹‘…Éå}½±½ÉôˆÍÑÉ½­”µÝ¥‘Ñ ô‰í±¥¹•}Ý¥‘Ñ¡ôˆ¼øœ(€€€€€€€€€€€€¤(€€€™½ÈÉ½ÕÀ¥¸¡¥¡±¥¡Ñ}É½ÕÁÌè(€€€€€€€™½ÈÉ¥¹œ¥¸É½ÕÁl‰É¥¹Ì‰tè(€€€€€€€€€€€Á½¥¹ÑÌ€ôÁ¥á•±Ì¡É¥¹œ¤(€€€€€€€€€€€¥˜±•¸¡Á½¥¹ÑÌ¤€øô€Ìè(€€€€€€€€€€€€€€€½½É‘Ì€ô€ˆ€ˆ¹©½¥¸¡˜‰íàè¸É™ô±íäè¸É™ôˆ™½Èà°ä¥¸Á½¥¹ÑÌ¤(€€€€€€€€€€€€€€€ÍÙ}Á½±å½¹Ì¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€€€€˜œñÁ½±å½¸Á½¥¹ÑÌô‰í½½É‘Íôˆ™¥±°ô‰í¡¥¡±¥¡Ñ}½±½ÉÍmÉ½ÕÁl‰É½±”‰uuôˆ€œ(€€€€€€€€€€€€€€€€€€€˜ÍÑÉ½­”ô‰í‰½Õ¹‘…Éå}½±½ÉôˆÍÑÉ½­”µÝ¥‘Ñ ô‰í±¥¹•}Ý¥‘Ñ¡ôˆ¼øœ(€€€€€€€€€€€€€€€€¤(€€€ÍÙ}±…‰•±Ì€ô€ˆˆ¹©½¥¸ (€€€€€€€˜œñÑ•áÐàô‰íàè¸É™ôˆäô‰íäè¸É™ôˆÑ•áÐµ…¹¡½Èô‰µ¥‘‘±”ˆ‘½µ¥¹…¹Ðµ‰…Í•±¥¹”ô‰µ¥‘‘±”ˆ€œ(€€€€€€€˜™½¹ÐµÍ¥é”ô‰í™½¹Ñ}Í¥é•ôˆ™½¹Ðµ™…µ¥±äô‰9½Ñ¼M…¹ÌQ°5¥É½Í½™Ð)¡•¹!•¤°A¥¹…¹œQ°Í…¹ÌµÍ•É¥˜ˆ€œ(€€€€€€€˜™¥±°ôˆŒÄÄÄÄÄÄˆÍÑÉ½­”ôˆ™™™™™˜ˆÍÑÉ½­”µÝ¥‘Ñ ôˆÌˆ€œ(€€€€€€€˜Á…¥¹Ðµ½É‘•Èô‰ÍÑÉ½­”ˆùí•Í…Á”¡±…‰•°¥ôð½Ñ•áÐøœ(€€€€€€€™½È±…‰•°°à°ä¥¸±…‰•±}Á½Í¥Ñ¥½¹Ì(€€€€¤(€€€ÍÙ}Á…Ñ ¹ÝÉ¥Ñ•}Ñ•áÐ (€€€€€€€˜œñÍÙœáµ±¹Ìô‰¡ÑÑÀè¼½ÝÝÜ¹ÜÌ¹½Éœ¼ÈÀÀÀ½ÍÙœˆÝ¥‘Ñ ô‰íÝ¥‘Ñ¡ôˆ¡•¥¡Ðô‰í¡•¥¡Ñôˆ€œ(€€€€€€€˜Ù¥•Ý	½àôˆÀ€ÀíÝ¥‘Ñ¡ôí¡•¥¡ÑôˆøñÉ•ÐÝ¥‘Ñ ôˆÄÀÀ”ˆ¡•¥¡ÐôˆÄÀÀ”ˆ€œ(€€€€€€€˜™¥±°ô‰í‰…­É½Õ¹‘ôˆ¼ùìˆˆ¹©½¥¸¡ÍÙ}Á½±å½¹Ì¥õíÍÙ}±…‰•±Íôð½ÍÙœùq¸œ°(€€€€€€€•¹½‘¥¹œô‰ÕÑ˜´àˆ°(€€€€¤(€€€‰…Í•}¹…µ”€ôÍÁ•Œ¹•Ð ‰…¹½¹¥…±}‰…Í•}¹…µ”ˆ°¹…µ”¤(€€€É•ÑÕÉ¸ì(€€€€€€€€‰Á…Ñ ˆèÁ¹}Á…Ñ ¹…Í}Á½Í¥à ¤°(€€€€€€€€‰‰…Í•}µ…Àˆè˜‰µ…ÁÌ½•¹•É…Ñ•½í‰…Í•}¹…µ•ô¹Á¹œˆ°(€€€€€€€€‰Á±…•}±…‰•±ÌˆèmÉ½ÕÁl‰±…‰•°‰t™½ÈÉ½ÕÀ¥¸¡¥¡±¥¡Ñ}É½ÕÁÍt°(€€€€€€€€‰ÍÑå±•}¥ˆèMQe1}=9%l‰ÍÑå±•}¥‰t°(€€€€€€€€‰Ý¥‘Ñ ˆèÝ¥‘Ñ °(€€€€€€€€‰¡•¥¡Ðˆè¡•¥¡Ð°(€€€ô(()‘•˜É•¹‘•É}•Ù•¹Ñ}ÍÁ•Œ¡ÍÁ•}Á…Ñ èA…Ñ ¤è(€€€Ý¥Ñ A…Ñ ¡ÍÁ•}Á…Ñ ¤¹½Á•¸ ‰Èˆ°•¹½‘¥¹œô‰ÕÑ˜´àˆ¤…Ì¡…¹‘±”è(€€€€€€€•Ù•¹Ñ}ÍÁ•Œ€ô©Í½¸¹±½…¡¡…¹‘±”¤(€€€Í•Ñ¥½¸€ô•Ù•¹Ñ}ÍÁ•Œ¹•Ð ‰Í•Ñ¥½¸ˆ¤(€€€¥˜Í•Ñ¥½¸¹½Ð¥¸MQ%=9}	M}5ALè(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰•Ù•¹Ðµ…ÀÍ•Ñ¥½¸ƒ–þ¦‚#šb¼Q];Ž!8ƒš"X1ˆ¤(€€€½ÕÑÁÕÐ€ôA…Ñ ¡•Ù•¹Ñ}ÍÁ•Œ¹•Ð ‰½ÕÑÁÕÐˆ°€ˆˆ¤¤(€€€¥˜¹½Ð½ÕÑÁÕÐ¹Á…ÉÑÌ½È½ÕÑÁÕÐ¹¥Í}…‰Í½±ÕÑ” ¤½È€ˆ¸¸ˆ¥¸½ÕÑÁÕÐ¹Á…ÉÑÌè(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰•Ù•¹Ðµ…À½ÕÑÁÕÐƒ–þ¦‚#šb¼µ…ÁÌ½•¹•É…Ñ•ƒ’æ/’â/žjžnã–Â7¢Þ¿–úDˆ¤(€€€‰…Í•}¹…µ”€ôMQ%=9}	M}5AMmÍ•Ñ¥½¹t(€€€ÍÁ•Œ€ôì(€€€€€€€€¨©5AMm‰…Í•}¹…µ•t°(€€€€€€€€‰…¹½¹¥…±}‰…Í•}¹…µ”ˆè‰…Í•}¹…µ”°(€€€€€€€€‰¡¥¡±¥¡ÑÌˆè•Ù•¹Ñ}ÍÁ•Œ¹•Ð ‰¡¥¡±¥¡ÑÌˆ°mt¤°(€€€ô(€€€¥˜¹½ÐÍÁ•l‰¡¥¡±¥¡ÑÌ‰tè(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰•Ù•¹Ðµ…Àƒ¢Ï–ÂG¦r¢š’â–/¢†3šRÿ–6 ¡¥¡±¥¡Ðˆ¤(€€€É•ÑÕÉ¸É•¹‘•È¡½ÕÑÁÕÐ¹…Í}Á½Í¥à ¤°ÍÁ•Œ¤(4(4)‘•˜Í•Ñ¥½¹}ÍÁ•Ì ¤è4(€€€€ˆˆ‰1½…¥¹¥Ñ¥…±¥é•ÕÍÑ½´µÍ•Ñ¥½¸µ…ÀÍÁ•¥™¥…Ñ¥½¹Ì¸ˆˆˆ4(€€€‘¥É•Ñ½Éä€ô=UP€¼€‰Í•Ñ¥½¹Ìˆ4(€€€¥˜¹½Ð‘¥É•Ñ½Éä¹¥Í}‘¥È ¤è4(€€€€€€€É•ÑÕÉ¸4(€€€™½Èµ•Ñ…‘…Ñ…}Á…Ñ ¥¸Í½ÉÑ•¡‘¥É•Ñ½Éä¹±½ˆ ˆ¨µ‰…Í”¹©Í½¸ˆ¤¤è4(€€€€€€€Ý¥Ñ µ•Ñ…‘…Ñ…}Á…Ñ ¹½Á•¸ ‰Èˆ°•¹½‘¥¹œô‰ÕÑ˜´àˆ¤…Ì¡…¹‘±”è4(€€€€€€€€€€€µ•Ñ…‘…Ñ„€ô©Í½¸¹±½…¡¡…¹‘±”¤4(€€€€€€€Í½ÕÉ•}Á…Ñ €ôI==P€¼µ•Ñ…‘…Ñ…l‰Í½ÕÉ•}•½©Í½¸‰t4(€€€€€€€ÍÁ•Œ€ôì4(€€€€€€€€€€€€‰™¥±”ˆèÍ½ÕÉ•}Á…Ñ °4(€€€€€€€€€€€€‰Ñ¥Ñ±”ˆèµ•Ñ…‘…Ñ„¹•Ð ‰¹…µ”ˆ°µ•Ñ…‘…Ñ…l‰½‘”‰t¤°4(€€€€€€€€€€€€‰™¥Í¥é”ˆè€ à¸Ô°€Ü¸À¤°4(€€€€€€€€€€€€‰‰½Õ¹‘ÌˆèÑÕÁ±”¡µ•Ñ…‘…Ñ…l‰‰½Õ¹‘Ì‰t¤°4(€€€€€€€€€€€€‰ÁÉ½©•Ñ¥½¸ˆèµ•Ñ…‘…Ñ„¹•Ð ‰ÁÉ½©•Ñ¥½¸ˆ°€‰É•¥½¹…°ˆ¤°4(€€€€€€€€€€€€‰ÍÑ…¹‘…É‘}±…Ðˆèµ•Ñ…‘…Ñ„¹•Ð ‰ÍÑ…¹‘…É‘}±…Ðˆ¤½È€À¸À°4(€€€€€€€€€€€€‰•¹ÑÉ…±}±½¸ˆèµ•Ñ…‘…Ñ„¹•Ð ‰•¹ÑÉ…±}±½¸ˆ¤°4(€€€€€€€€€€€€‰‰…Í•}½Õ¹ÑÉå}¥Í¼ˆèµ•Ñ…‘…Ñ„¹•Ð ‰‰…Í•}½Õ¹ÑÉå}¥Í¼ˆ¤°4(€€€€€€€€€€€€‰ÍÑå±•}¥ˆèµ•Ñ…‘…Ñ„¹•Ð ‰ÍÑå±•}¥ˆ°MQe1}=9%l‰ÍÑå±•}¥‰t¤°4(€€€€€€€€€€€€‰ÍÑå±”ˆèµ•Ñ…‘…Ñ„¹•Ð ‰ÍÑå±”ˆ°íô¤°4(€€€€€€€ô4(€€€€€€€¥˜ÍÁ•l‰ÁÉ½©•Ñ¥½¸‰t¥¸ì‰Á…¥™¥}•¹Ñ•É•ˆ°€‰É½‰¥¹Í½¹}Á…¥™¥Œ‰ôè4(€€€€€€€€€€€ÍÁ•l‰ÕÑ}±½¸‰t€ôµ•Ñ…‘…Ñ„¹•Ð ‰ÕÑ}±½¸ˆ°€´ÌÀ¸À¤4(€€€€€€€å¥•±˜‰Í•Ñ¥½¹Ì½íµ•Ñ…‘…Ñ…l½‘”uôµ‰…Í”ˆ°ÍÁ•Œ°µ•Ñ…‘…Ñ…}Á…Ñ °µ•Ñ…‘…Ñ„4(4(4)‘•˜µ…¥¸¡…ÉØô ¤¤è(€€€Á…ÉÍ•È€ôÉÕµ•¹ÑA…ÉÍ•È¡‘•ÍÉ¥ÁÑ¥½¸õ}}‘½}|¤(€€€Á…ÉÍ•È¹…‘‘}…ÉÕµ•¹Ð ˆ´µ½Ù•É±…äµÍÁ•Œˆ°ÑåÁ”õA…Ñ ¤(€€€…ÉÌ€ôÁ…ÉÍ•È¹Á…ÉÍ•}…ÉÌ¡…ÉØ¤(€€€¥˜…ÉÌ¹½Ù•É±…å}ÍÁ•Œè(€€€€€€€ÁÉ¥¹Ð¡©Í½¸¹‘ÕµÁÌ¡É•¹‘•É}•Ù•¹Ñ}ÍÁ•Œ¡…ÉÌ¹½Ù•É±…å}ÍÁ•Œ¤°•¹ÍÕÉ•}…Í¥¤õ…±Í”¤¤(€€€€€€€É•ÑÕÉ¸(€€€™½È¹…µ”°ÍÁ•Œ¥¸5AL¹¥Ñ•µÌ ¤è(€€€€€€€É•¹‘•È¡¹…µ”°ÍÁ•Œ¤(€€€™½È¹…µ”°ÍÁ•Œ°|°|¥¸Í•Ñ¥½¹}ÍÁ•Ì ¤½È€ ¤è(€€€€€€€É•¹‘•È¡¹…µ”°ÍÁ•Œ¤(4(4)¥˜}}¹…µ•}|€ôô€‰}}µ…¥¹}|ˆè(€€€µ…¥¸¡9½¹”¤(