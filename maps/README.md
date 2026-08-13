# News Brief Base Maps

Reusable base maps for news brief location highlighting.

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
