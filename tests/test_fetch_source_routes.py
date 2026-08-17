import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "fetch_source_routes", ROOT / "scripts" / "fetch_source_routes.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FetchSourceRoutesTests(unittest.TestCase):
    def test_configured_json_pagination_stops_after_crossing_window_start(self):
        requested_pages = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/primary":
                    body = b"<html><body>primary</body></html>"
                    content_type = "text/html; charset=utf-8"
                else:
                    page = int(self.path.split("page=", 1)[1])
                    requested_pages.append(page)
                    dates = {
                        2: ["2026-08-17 20:00", "2026-08-17 19:00"],
                        3: ["2026-08-17 18:00", "2026-08-16 21:30"],
                        4: ["2026-08-16 20:00"],
                    }[page]
                    body = json.dumps({
                        "lists": [
                            {
                                "titleLink": f"/news/story/1/{page}{index}",
                                "title": f"page {page} item {index}",
                                "time": {"date": value},
                            }
                            for index, value in enumerate(dates)
                        ]
                    }).encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                port = server.server_address[1]
                config = root / "routes.json"
                config.write_text(json.dumps({"routes": [{
                    "source_id": "udn",
                    "route": "html_direct",
                    "request_url_template": f"http://127.0.0.1:{port}/primary",
                    "snapshot_name": "udn.route-probe.bin",
                    "pagination": {
                        "request_url_template": f"http://127.0.0.1:{port}/api/more?page={{page}}",
                        "start_page": 2,
                        "max_pages": 5,
                        "items_path": ["lists"],
                        "published_path": ["time", "date"],
                    },
                }]}), encoding="utf-8")

                coverage = MODULE.fetch_routes(
                    config, root / "out", 5, "2026-08-16T22:00:00+08:00"
                )

                result = coverage["results"][0]
                self.assertTrue(result["route_ready"])
                self.assertEqual([2, 3], requested_pages)
                self.assertEqual([2, 3], [page["page_index"] for page in result["page_snapshots"]])
                self.assertTrue(all(Path(page["snapshot_path"]).is_file() for page in result["page_snapshots"]))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
