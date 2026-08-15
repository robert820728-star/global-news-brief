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


class BootstrapCapsuleTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
