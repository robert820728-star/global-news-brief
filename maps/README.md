# News Brief Base Maps

## Canonical style

All self-rendered section and event maps must load `maps/style.json` with style id `yellow-admin-v2`. The approved visual references are the Taiwan, China, and Pacific-centered world `yellow-v2` maps in `maps/generated/`. A new section may change geographic extent and administrative level only; blue backgrounds, platform-default maps, satellite styles, or alternate color systems are not valid outputs.

Every event map is permanently bound to its complete section canvas: full Taiwan for `TWN`, full China for `CHN`, and the complete Pacific-centered world for `GLB`. Custom country or regional sections likewise retain their complete initialized section basemap. Event maps may add only markers, labels, routes, or affected-area overlays. Cropping, zooming to the event location, or substituting a local locator map is forbidden. The manifest must record `canvas_scope: full_section` (`full_world` for `GLB`) and the canonical `base_map`.

Reusable base maps for news brief location highlighting.

## Custom sections

- Single-country sections use `scripts/fetch_admin_boundaries.py` with the ISO alpha-3 code to download ADM1 from geoBoundaries gbOpen. Data and provenance are cached under `maps/cache/`, and bounds are calculated from the downloaded geometry.
- Multi-country regions use `maps/source/world-countries.geojson` and an explicit regional extent.
- Every country uses this same resolver and the `yellow-admin-v2` renderer. Country-specific downloaders and platform-default maps are forbidden.

## Files

| Map | Source data | Boundary level | Generated preview |
|---|---|---|---|
| Taiwan | `maps/source/taiwan-counties-alt.geojson` | County/city boundaries | `maps/generated/taiwan-counties-yellow-v2.png` |
| China | `maps/source/china-provinces.geojson` | Province-level boundaries | `maps/generated/china-provinces-yellow-v2.png` |
| World | `maps/source/world-countries.geojson` | Country boundaries | `maps/generated/world-countries-pacific-robinson-yellow-v2.png` |

For an event map, write a compact JSON overlay specification and run `python scripts/render_base_maps.py --overlay-spec <file>`. Use `section` (`TWN`, `CHN`, or `GLB`), a relative `output`, and one or more `highlights`. Each highlight has an exact GeoJSON property `match`, a Traditional Chinese `label`, and `role` (`primary` or `secondary`). The renderer colors the matched administrative polygon and writes the label directly on both PNG and SVG output.

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
