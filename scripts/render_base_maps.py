#!/usr/bin/env python3
"""Render reusable base maps from GeoJSON source files."""

from __future__ import annotations

import json
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
            raise ValueError("highlight.match 必須指定至少一個行政區欄位")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("highlight.label 必須是非空白地名")
        if role not in {"primary", "secondary"}:
            raise ValueError("highlight.role 必須是 primary 或 secondary")
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
            raise ValueError(f"找不到指定行政區：{criteria}")
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
        raise ValueError("地圖 style_id 不符合 maps/style.json")
    if not polygons:
        raise ValueError(f"{name} 沒有可繪製的 GeoJSON polygons")
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
        return [
            (
                margin + (x - minx) / span_x * (width - 2 * margin),
                height - margin - (y - miny) / span_y * (height - 2 * margin),
            )
            for x, y in ring
        ]

    land_fill = style.get("land_fill", "#f3e6b8")
    boundary_color = style.get("boundary_color", "#53606f")
    background = style.get("background", "#ffffff")
    line_width = max(1, round(float(style.get("boundary_width", 0.42)) * 2))
    image = Image.new("RGB", (width, height), background)
    drawing = ImageDraw.Draw(image)
    for ring in base_polygons:
        points = pixels(ring)
        if len(points) >= 3:
            drawing.polygon(points, fill=land_fill)
    for ring in polygons:
        points = pixels(ring)
        if len(points) >= 3:
            drawing.polygon(points, fill=land_fill, outline=boundary_color, width=line_width)
    highlight_colors = {
        "primary": style.get("primary_highlight", "#c7362f"),
        "secondary": style.get("secondary_highlight", "#f28e2b"),
    }
    for group in highlight_groups:
        for ring in group["rings"]:
            points = pixels(ring)
            if len(points) >= 3:
                drawing.polygon(
                    points,
                    fill=highlight_colors[group["role"]],
                    outline=boundary_color,
                    width=line_width,
                )

    font_size = max(14, round(min(width, height) * 0.026))
    try:
        label_font = ImageFont.load_default(size=font_size)
    except TypeError:  # Pillow < 10.1 compatibility
        label_font = ImageFont.load_default()
    label_positions = []
    for group in highlight_groups:
        label_ring = max(group["rings"], key=len)
        points = pixels(label_ring)
        x = sum(point[0] for point in points) / len(points)
        y = sum(point[1] for point in points) / len(points)
        drawing.text(
            (x, y),
            group["label"],
            fill="#111111",
            font=label_font,
            anchor="mm",
            stroke_width=2,
            stroke_fill="#ffffff",
        )
        label_positions.append((group["label"], x, y))

    destination = OUT / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    png_path = destination.with_suffix(".png")
    svg_path = destination.with_suffix(".svg")
    image.save(png_path, format="PNG", optimize=True)

    svg_polygons = []
    for ring in base_polygons:
        points = pixels(ring)
        if len(points) >= 3:
            coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            svg_polygons.append(f'<polygon points="{coords}" fill="{land_fill}" stroke="none"/>')
    for ring in polygons:
        points = pixels(ring)
        if len(points) >= 3:
            coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            svg_polygons.append(
                f'<polygon points="{coords}" fill="{land_fill}" '
                f'stroke="{boundary_color}" stroke-width="{line_width}"/>'
            )
    for group in highlight_groups:
        for ring in group["rings"]:
            points = pixels(ring)
            if len(points) >= 3:
                coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
                svg_polygons.append(
                    f'<polygon points="{coords}" fill="{highlight_colors[group["role"]]}" '
                    f'stroke="{boundary_color}" stroke-width="{line_width}"/>'
                )
    svg_labels = "".join(
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" dominant-baseline="middle" '
        f'font-size="{font_size}" fill="#111111" stroke="#ffffff" stroke-width="3" '
        f'paint-order="stroke">{escape(label)}</text>'
        for label, x, y in label_positions
    )
    svg_path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" '
        f'fill="{background}"/>{"".join(svg_polygons)}{svg_labels}</svg>\n',
        encoding="utf-8",
    )
    base_name = spec.get("canonical_base_name", name)
    return {
        "path": png_path.as_posix(),
        "base_map": f"maps/generated/{base_name}.png",
        "place_labels": [group["label"] for group in highlight_groups],
        "style_id": STYLE_CONFIG["style_id"],
        "width": width,
        "height": height,
    }


def render_event_spec(spec_path: Path):
    with Path(spec_path).open("r", encoding="utf-8") as handle:
        event_spec = json.load(handle)
    section = event_spec.get("section")
    if section not in SECTION_BASE_MAPS:
        raise ValueError("event map section 必須是 TWN、CHN 或 GLB")
    output = Path(event_spec.get("output", ""))
    if not output.parts or output.is_absolute() or ".." in output.parts:
        raise ValueError("event map output 必須是 maps/generated 之下的相對路徑")
    base_name = SECTION_BASE_MAPS[section]
    spec = {
        **MAPS[base_name],
        "canonical_base_name": base_name,
        "highlights": event_spec.get("highlights", []),
    }
    if not spec["highlights"]:
        raise ValueError("event map 至少需要一個行政區 highlight")
    return render(output.as_posix(), spec)


def section_specs():
    """Load initialized custom-section map specifications."""
    directory = OUT / "sections"
    if not directory.is_dir():
        return
    for metadata_path in sorted(directory.glob("*-base.json")):
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        source_path = ROOT / metadata["source_geojson"]
        spec = {
            "file": source_path,
            "title": metadata.get("name", metadata["code"]),
            "figsize": (8.5, 7.0),
            "bounds": tuple(metadata["bounds"]),
            "projection": metadata.get("projection", "regional"),
            "standard_lat": metadata.get("standard_lat") or 0.0,
            "central_lon": metadata.get("central_lon"),
            "base_country_iso": metadata.get("base_country_iso"),
            "style_id": metadata.get("style_id", STYLE_CONFIG["style_id"]),
            "style": metadata.get("style", {}),
        }
        if spec["projection"] in {"pacific_centered", "robinson_pacific"}:
            spec["cut_lon"] = metadata.get("cut_lon", -30.0)
        yield f"sections/{metadata['code']}-base", spec, metadata_path, metadata


def main(argv=()):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--overlay-spec", type=Path)
    args = parser.parse_args(argv)
    if args.overlay_spec:
        print(json.dumps(render_event_spec(args.overlay_spec), ensure_ascii=False))
        return
    for name, spec in MAPS.items():
        render(name, spec)
    for name, spec, _, _ in section_specs() or ():
        render(name, spec)


if __name__ == "__main__":
    main(None)
