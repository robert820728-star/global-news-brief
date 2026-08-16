import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_base_maps.py"
SPEC = importlib.util.spec_from_file_location("render_base_maps", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RenderBaseMapsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
