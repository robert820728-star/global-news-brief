# News Brief Base Maps

## Canonical style

All self-rendered section and event maps must load `maps/style.json` with style id `yellow-admin-v2`. The approved visual references are the Taiwan, China, and Pacific-centered world `yellow-v2` maps in `maps/generated/`. A new section may change geographic extent and administrative level only; blue backgrounds, platform-default maps, satellite styles, or alternate color systems are not valid outputs.

Reusable base maps for news brief location highlighting.

## Custom sections

- Single-country sections use `scripts/fetch_admin_boundaries.py` with the ISO alpha-3 code to download ADM1 from geoBoundaries gbOpen. Data and provenance are cached under `maps/cache/`, and bounds are calculated from the downloaded geometry.
- Multi-country regions use `maps/source/world-countries.geojson` and an explicit regional extent.
- Every country uses this same resolver and the `yellow-admin-v2` renderer. Country-specific downloaders and platform-default maps are forbidden.

## Files

| Map | Source data | Boundary level | Generated preview |
|---|---|---|---|
| Taiwan | `maps/source/taiwan-counties-alt.geojson` | County/city boundaries | `maps/generated/taiwan-counties.png` |
| China | `maps/source/china-provinces.geojson` | Province-level boundaries | `maps/generated/china-provinces.png` |
| World | `maps/source/world-countries.geojson` | Country boundaries | `maps/generated/world-countries.png` |

## Rendering

Run:

```bash
python scripts/render_base_maps.py
```

The renderer writes PNG and SVG files to `maps/generated/`.

## News Brief Rules

- Use the map that matches the geographic scale of the event, not the news section.
- A full-context map must appear before any cropped or local detail map.
- Use official or source-provided disaster, weather, epidemic, earthquake, and route maps first when available.
- Use these base maps as reader-orientation overlays, especially when a location is not obvious from the story.
- Self-rendered maps should be described as compiled from cited sources, not as official maps.
