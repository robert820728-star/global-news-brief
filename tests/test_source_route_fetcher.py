import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_FETCHER = ROOT / "scripts" / "fetch_source_routes.py"
ROUTES = ROOT / "source-route-config.json"


class _Handler(BaseHTTPRequestHandler):
    payload = "<html><body>route probe 測試</body></html>".encode("utf-8")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, _format, *_args):
        return


class SourceRouteFetcherTests(unittest.TestCase):
    def test_route_config_covers_every_primary_source(self):
        pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8-sig"))
        config = json.loads(ROUTES.read_text(encoding="utf-8-sig"))
        self.assertEqual(
            {source["source_id"] for source in pool["sources"]},
            {route["source_id"] for route in config["routes"]},
        )
        self.assertEqual(15, len(config["routes"]))

    def test_python_fetcher_persists_exact_snapshot_and_coverage(self):
        self.assertTrue(PYTHON_FETCHER.is_file())
        self._assert_fetcher_contract([sys.executable, str(PYTHON_FETCHER)])

    def _assert_fetcher_contract(self, command):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                route_config = temp_path / "routes.json"
                output_dir = temp_path / "out"
                route_config.write_text(json.dumps({
                    "schema_version": "1.0.0",
                    "routes": [{
                        "source_id": "local",
                        "route": "html_direct",
                        "request_url_template": f"http://127.0.0.1:{server.server_port}/{{yyyy-MM-dd}}/news",
                        "snapshot_name": "local.route-probe.bin",
                    }],
                }), encoding="utf-8")
                arguments = [
                    "--route-config", str(route_config),
                    "--output-dir", str(output_dir),
                    "--timeout-seconds", "5",
                ]
                completed = subprocess.run(
                    command + arguments,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=20,
                )
                self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
                coverage = json.loads((output_dir / "source-route-coverage.json").read_text(encoding="utf-8-sig"))
                self.assertEqual(1, coverage["route_ready_count"])
                result = coverage["results"][0]
                self.assertRegex(result["request_url"], r"/\d{4}-\d{2}-\d{2}/news$")
                snapshot = Path(result["snapshot_path"])
                self.assertEqual(_Handler.payload, snapshot.read_bytes())
                self.assertEqual(hashlib.sha256(_Handler.payload).hexdigest(), result["sha256"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
