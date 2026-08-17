import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from tests import test_validate_news_brief as validator_fixture


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_base_maps.py"
SPEC = importlib.util.spec_from_file_location("render_base_maps", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderBaseMapsTests(unittest.TestCase):
    def test_label_font_has_distinct_traditional_chinese_glyphs(self):
        font = MODULE.load_label_font(36)
        glyphs = [bytes(font.getmask(character)) for character in "臺灣"]
        self.assertNotEqual(glyphs[0], glyphs[1])

    def test_world_map_label_size_is_mobile_readable(self):
        self.assertGreaterEqual(MODULE.label_font_size(1800, 1044), 36)

    def test_renderer_has_no_matplotlib_dependency(self):
        source = SCRIPT.read_text(encoding="utf-8-sig")
        self.assertNotIn("matplotlib", source)

    def test_pillow_renderer_writes_png_and_svg(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [[
                    [120.0, 22.0], [121.0, 22.0], [121.0, 23.0], [120.0, 23.0], [120.0, 22.0]
                ]]},
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "map.geojson"
            source.write_text(json.dumps(geojson), encoding="utf-8")
            old_out = MODULE.OUT
            MODULE.OUT = root / "generated"
            try:
                MODULE.render("fixture", {
                    "file": source, "title": "Fixture", "figsize": (2.0, 2.0),
                    "bounds": (119.5, 121.5, 21.5, 23.5), "projection": "regional",
                    "standard_lat": 23.0,
                })
            finally:
                MODULE.OUT = old_out
            png = root / "generated" / "fixture.png"
            svg = root / "generated" / "fixture.svg"
            self.assertTrue(png.is_file())
            self.assertTrue(svg.is_file())
            with Image.open(png) as image:
                self.assertEqual("PNG", image.format)
                self.assertGreater(image.width, 100)
            self.assertIn("<svg", svg.read_text(encoding="utf-8"))

    def test_main_does_not_mutate_section_metadata(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "properties": {"ADMIN": "Fixture"},
                "geometry": {"type": "Polygon", "coordinates": [[
                    [120.0, 22.0], [121.0, 22.0], [121.0, 23.0], [120.0, 23.0], [120.0, 22.0]
                ]]},
            }],
        }
        metadata = {
            "schema_version": 1, "code": "FIX", "name": "Fixture",
            "source_geojson": "map.geojson", "bounds": [119.5, 121.5, 21.5, 23.5],
            "projection": "regional", "standard_lat": 23.0,
            "status": "spec_ready", "visual_checked": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "map.geojson").write_text(json.dumps(geojson), encoding="utf-8")
            sections = root / "generated" / "sections"
            sections.mkdir(parents=True)
            metadata_path = sections / "FIX-base.json"
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            before = metadata_path.read_bytes()
            old_root, old_out, old_maps = MODULE.ROOT, MODULE.OUT, MODULE.MAPS
            MODULE.ROOT, MODULE.OUT, MODULE.MAPS = root, root / "generated", {}
            try:
                MODULE.main()
            finally:
                MODULE.ROOT, MODULE.OUT, MODULE.MAPS = old_root, old_out, old_maps
            self.assertEqual(before, metadata_path.read_bytes())
            self.assertTrue((sections / "FIX-base.png").is_file())
            self.assertTrue((sections / "FIX-base.svg").is_file())

    def test_clean_runtime_outputs_canonical_basemaps_and_colored_event_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "generated"
            old_out = MODULE.OUT
            MODULE.OUT = generated
            try:
                MODULE.main()
                expected = {
                    "taiwan-counties-yellow-v2.png",
                    "china-provinces-yellow-v2.png",
                    "world-countries-pacific-robinson-yellow-v2.png",
                }
                self.assertEqual(expected, {path.name for path in generated.glob("*-yellow-v2.png")})

                cases = (
                    ("TWN", {"county": "臺北市"}, "臺北市", "taiwan-counties-yellow-v2"),
                    ("CHN", {"id": "44"}, "廣東省", "china-provinces-yellow-v2"),
                    ("GLB", {"ISO_A3": "USA"}, "美國", "world-countries-pacific-robinson-yellow-v2"),
                )
                results = {}
                for section, match, label, base_name in cases:
                    overlay_spec = Path(directory) / f"{section}-event-map.json"
                    overlay_spec.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.0.0",
                                "section": section,
                                "output": f"events/{section}-test",
                                "highlights": [
                                    {"match": match, "label": label, "role": "primary"}
                                ],
                            },
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                    results[section] = MODULE.render_event_spec(overlay_spec)
                    event_png = generated / "events" / f"{section}-test.png"
                    event_svg = generated / "events" / f"{section}-test.svg"
                    self.assertTrue(event_png.is_file())
                    self.assertTrue(event_svg.is_file())
                    svg = event_svg.read_text(encoding="utf-8")
                    self.assertIn(label, svg)
                    self.assertIn(MODULE.STYLE_CONFIG["colors"]["primary_highlight"], svg)
                    with Image.open(event_png) as image:
                        colors = image.getcolors(maxcolors=image.width * image.height)
                        self.assertIn(
                            MODULE.STYLE_CONFIG["colors"]["primary_highlight"].lower(),
                            {"#%02x%02x%02x" % pixel for _, pixel in colors},
                        )
                    self.assertEqual(f"maps/generated/{base_name}.png", results[section]["base_map"])
                    self.assertEqual([label], results[section]["place_labels"])
            finally:
                MODULE.OUT = old_out

            event_png = generated / "events" / "TWN-test.png"
            manifest = validator_fixture.valid_manifest()
            asset = manifest["events"][0]["map"]["assets"][0]
            result = results["TWN"]
            asset.update(
                {
                    "path": event_png.as_posix(),
                    "base_map": result["base_map"],
                    "place_labels": result["place_labels"],
                    "style_id": result["style_id"],
                    "width": result["width"],
                    "height": result["height"],
                }
            )
            self.assertEqual([], validator_fixture.VALIDATOR.validate_manifest_data(manifest))

        readme = (ROOT / "maps" / "README.md").read_text(encoding="utf-8")
        for name in expected:
            self.assertIn(name, readme)


if __name__ == "__main__":
    unittest.main()
