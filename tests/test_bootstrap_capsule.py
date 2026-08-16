import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

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
