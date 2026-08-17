import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import test_validate_news_brief as validator_fixture

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


VERIFY = load_module(ROOT / "scripts/verify_bootstrap_capsule.py", "verify_bootstrap_capsule_test")
LOADER = load_module(ROOT / "bootstrap/bootstrap_loader.py", "bootstrap_loader_test")
BUILDER = load_module(ROOT / "scripts/build_bootstrap_capsule.py", "build_bootstrap_capsule_test")


class BootstrapCapsuleTests(unittest.TestCase):
    def test_runtime_closure_includes_source_route_config(self):
        runtime_paths = {
            path.resolve().relative_to(ROOT.resolve()).as_posix()
            for path in BUILDER.collect_runtime_paths(ROOT)
        }
        self.assertIn("source-route-config.json", runtime_paths)
        self.assertIn("scripts/resolve_bundled_python.py", runtime_paths)
        self.assertIn("scripts/fetch_source_routes.py", runtime_paths)
        self.assertIn("bootstrap/bootstrap_progress.py", runtime_paths)
        self.assertIn("bootstrap/bootstrap-progress.schema.json", runtime_paths)
        self.assertIn("bootstrap/RUN_LEDGER_PROTOCOL.md", runtime_paths)
        self.assertNotIn("scripts/resolve_bundled_python.ps1", runtime_paths)
        self.assertNotIn("scripts/fetch_source_routes.ps1", runtime_paths)

    def test_runtime_closure_excludes_generated_section_images(self):
        runtime_paths = {
            path.resolve().relative_to(ROOT.resolve()).as_posix()
            for path in BUILDER.collect_runtime_paths(ROOT)
        }
        generated_images = {
            path for path in runtime_paths
            if path.startswith("maps/generated/sections/")
            and Path(path).suffix.lower() in {".png", ".svg"}
        }
        self.assertEqual(set(), generated_images)

    def test_generated_capsule_verifies_against_checkout(self):
        self.assertEqual(VERIFY.verify(ROOT), [])

    def test_tampered_chunk_is_rejected(self):
        manifest_path = ROOT / "bootstrap/capsule-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for item in manifest["chunks"]:
                shutil.copyfile(ROOT / "bootstrap" / item["name"], target / item["name"])
            first = target / manifest["chunks"][0]["name"]
            raw = bytearray(first.read_bytes())
            raw[0] = ord("A") if raw[0] != ord("A") else ord("B")
            first.write_bytes(bytes(raw))
            with self.assertRaisesRegex(ValueError, "chunk sha256 mismatch"):
                LOADER.verify_chunks(manifest, target)

    def test_payload_extracts_and_matches_runtime_file_count(self):
        manifest_path = ROOT / "bootstrap/capsule-manifest.json"
        manifest = LOADER.load_manifest(manifest_path)
        payload = LOADER.verify_chunks(manifest, manifest_path.parent)
        with tempfile.TemporaryDirectory() as directory:
            files = LOADER.extract_verified(payload, manifest, Path(directory))
            self.assertEqual(len(files), manifest["runtime_file_count"])

    def test_builder_emits_direct_payload_matching_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            manifest = BUILDER.build_capsule(
                ROOT, output_dir, source_commit="test-source"
            )
            payload_path = output_dir / "capsule-payload.tar.xz"
            self.assertTrue(payload_path.is_file(), "direct payload file missing")
            payload = payload_path.read_bytes()
            self.assertEqual(len(payload), manifest["payload_size"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(), manifest["payload_sha256"]
            )
            self.assertNotIn(
                b"\r", (output_dir / "capsule-manifest.json").read_bytes()
            )

    def test_loader_materializes_from_payload_url_without_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capsule_dir = root / "capsule"
            BUILDER.build_capsule(ROOT, capsule_dir, source_commit="test-source")
            for chunk in capsule_dir.glob("capsule.part*.txt"):
                chunk.unlink()
            workspace = root / "workspace"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "bootstrap/bootstrap_loader.py"),
                    "--manifest",
                    str(capsule_dir / "capsule-manifest.json"),
                    "--payload-url",
                    (capsule_dir / "capsule-payload.tar.xz").as_uri(),
                    "--workspace",
                    str(workspace),
                    "--commit-sha",
                    "test-commit",
                    "--manifest-blob-sha",
                    "test-manifest-blob",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            receipt = json.loads(
                (workspace / "bootstrap-workspace.json").read_text(encoding="utf-8")
            )
            self.assertEqual("direct-payload", receipt["capsule"]["transport"])

    def test_extracted_runtime_renders_and_validates_canonical_event_map(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capsule_dir = root / "capsule"
            BUILDER.build_capsule(ROOT, capsule_dir, source_commit="test-source")
            manifest_path = capsule_dir / "capsule-manifest.json"
            capsule_manifest = LOADER.load_manifest(manifest_path)
            payload = LOADER.verify_chunks(capsule_manifest, capsule_dir)
            workspace = root / "workspace"
            LOADER.extract_verified(payload, capsule_manifest, workspace)

            renderer = workspace / "scripts" / "render_base_maps.py"
            subprocess.run(
                [sys.executable, str(renderer)],
                cwd=workspace,
                check=True,
                capture_output=True,
                text=True,
            )
            expected = {
                "taiwan-counties-yellow-v2.png",
                "china-provinces-yellow-v2.png",
                "world-countries-pacific-robinson-yellow-v2.png",
            }
            generated = workspace / "maps" / "generated"
            self.assertEqual(expected, {path.name for path in generated.glob("*-yellow-v2.png")})

            overlay = workspace / "event-map.json"
            overlay.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "section": "TWN",
                        "output": "events/TWN-capsule",
                        "highlights": [
                            {"match": {"county": "臺北市"}, "label": "臺北市", "role": "primary"}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            rendered = subprocess.run(
                [sys.executable, str(renderer), "--overlay-spec", str(overlay)],
                cwd=workspace,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(rendered.stdout)
            event_png = generated / "events" / "TWN-capsule.png"
            event_svg = generated / "events" / "TWN-capsule.svg"
            self.assertTrue(event_png.is_file())
            self.assertIn("臺北市", event_svg.read_text(encoding="utf-8"))
            self.assertEqual(
                "maps/generated/taiwan-counties-yellow-v2.png",
                result["base_map"],
            )

            extracted_validator = load_module(
                workspace / "scripts" / "validate_news_brief.py",
                "extracted_validate_news_brief_test",
            )
            news_manifest = validator_fixture.valid_manifest()
            asset = news_manifest["events"][0]["map"]["assets"][0]
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
            self.assertEqual([], extracted_validator.validate_manifest_data(news_manifest))

    def test_chunks_are_line_framed_for_segmented_connector_reads(self):
        manifest_path = ROOT / "bootstrap/capsule-manifest.json"
        manifest = LOADER.load_manifest(manifest_path)
        self.assertEqual(manifest["line_width"], 256)
        self.assertEqual(manifest["retrieval_block_lines"], 8)
        for item in manifest["chunks"]:
            raw = (ROOT / "bootstrap" / item["name"]).read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            self.assertNotIn(b"\r", raw)
            raw_lines = raw.splitlines(keepends=True)
            lines = raw.decode("ascii").splitlines()
            self.assertEqual(len(lines), item["line_count"])
            self.assertTrue(all(len(line) <= manifest["line_width"] for line in lines))
            if len(lines) > 1:
                self.assertTrue(all(len(line) == manifest["line_width"] for line in lines[:-1]))
            rebuilt = b""
            expected_start = 1
            for block in item["blocks"]:
                self.assertEqual(block["start_line"], expected_start)
                self.assertLessEqual(
                    block["end_line"] - block["start_line"] + 1,
                    manifest["retrieval_block_lines"],
                )
                fragment = b"".join(raw_lines[block["start_line"] - 1:block["end_line"]])
                self.assertEqual(len(fragment), block["size"])
                self.assertEqual(hashlib.sha256(fragment).hexdigest(), block["sha256"])
                rebuilt += fragment
                expected_start = block["end_line"] + 1
            self.assertEqual(rebuilt, raw)
            encoded = "".join(lines).encode("ascii")
            self.assertEqual(len(encoded), item["encoded_size"])
            self.assertEqual(hashlib.sha256(encoded).hexdigest(), item["encoded_sha256"])


if __name__ == "__main__":
    unittest.main()
