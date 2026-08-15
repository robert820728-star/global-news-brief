import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_admin_boundaries as fetcher
import initialize_section_basemaps as initializer

SAMPLE = {"type": "FeatureCollection", "features": [{
    "type": "Feature", "properties": {}, "geometry": {
        "type": "Polygon", "coordinates": [[[1, 2], [5, 2], [5, 8], [1, 8], [1, 2]]]
    }
}]}


class FetchAdminBoundariesTests(unittest.TestCase):
    def test_fetch_adm1_uses_generic_iso_endpoint(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(fetcher, "request_json") as request_json, \
                patch.object(fetcher, "download_geojson", return_value=SAMPLE):
            request_json.return_value = {
                "simplifiedGeometryGeoJSON": "https://example.test/USA-ADM1.geojson",
                "boundaryLicense": "CC BY 4.0", "boundaryName": "United States",
            }
            output = Path(directory) / "usa.geojson"
            result = fetcher.fetch_adm1("usa", output)
            self.assertEqual(result["iso3"], "USA")
            self.assertEqual(result["boundary_level"], "ADM1")
            self.assertEqual(json.loads(output.read_text())["type"], "FeatureCollection")
            self.assertIn("/USA/ADM1/", request_json.call_args.args[0])

    def test_country_bounds_are_derived_from_adm1(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.geojson"
            path.write_text(json.dumps(SAMPLE), encoding="utf-8")
            bounds = initializer.geojson_bounds(path)
            self.assertLess(bounds[0], 1)
            self.assertGreater(bounds[1], 5)
            self.assertLess(bounds[2], 2)
            self.assertGreater(bounds[3], 8)

    def test_scope_selects_country_or_region(self):
        self.assertEqual(initializer.boundary_mode({"scope": ["France", "Germany"]}), "region")
        self.assertEqual(initializer.boundary_mode({"code": "FRA"}), "country")


if __name__ == "__main__":
    unittest.main()
