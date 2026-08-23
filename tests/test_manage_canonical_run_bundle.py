import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "manage_canonical_run_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("manage_canonical_run_bundle", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanonicalRunBundleTests(unittest.TestCase):
    def test_large_json_and_binary_attachment_round_trip_losslessly(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "candidate-audit.json"
            image = root / "photo.jpg"
            original_audit = json.dumps(
                {"article_dispositions": ["事件證據" * 80 for _ in range(40)]},
                ensure_ascii=False,
            ).encode("utf-8")
            original_image = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 5 + b"\xff\xd9"
            audit.write_bytes(original_audit)
            image.write_bytes(original_image)
            transport = root / "transport"
            manifest_path = root / "bundle-manifest.json"

            manifest = module.pack_bundle(
                run_id="gnb-20260823T000000Z-deadbeef",
                artifacts=[
                    ("candidate-audit.json", audit),
                    ("attachments/photo.jpg", image),
                ],
                transport_dir=transport,
                manifest_path=manifest_path,
                max_blob_bytes=1024,
            )

            audit_record = next(
                item for item in manifest["artifacts"]
                if item["logical_path"] == "candidate-audit.json"
            )
            self.assertEqual(audit_record["storage"]["mode"], "chunked")
            self.assertGreater(len(audit_record["storage"]["upload_ids"]), 1)
            for upload in manifest["uploads"]:
                self.assertLessEqual(upload["raw_size"], 1024)
                self.assertEqual(upload["encoding"], "base64")
                self.assertTrue(upload["git_blob_sha"])

            audit.unlink()
            image.unlink()
            module.verify_bundle(manifest_path=manifest_path, transport_dir=transport)
            restored = root / "restored"
            module.restore_bundle(
                manifest_path=manifest_path,
                transport_dir=transport,
                output_dir=restored,
            )
            self.assertEqual((restored / "candidate-audit.json").read_bytes(), original_audit)
            self.assertEqual((restored / "attachments/photo.jpg").read_bytes(), original_image)

    def test_verify_rejects_tampered_transport_chunk(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "candidate-audit.json"
            source.write_bytes(b"x" * 4096)
            transport = root / "transport"
            manifest_path = root / "bundle-manifest.json"
            manifest = module.pack_bundle(
                run_id="gnb-20260823T000000Z-deadbeef",
                artifacts=[("candidate-audit.json", source)],
                transport_dir=transport,
                manifest_path=manifest_path,
                max_blob_bytes=1024,
            )
            first = transport / manifest["uploads"][0]["transport_file"]
            first.write_text("AAAA", encoding="ascii")

            with self.assertRaisesRegex(ValueError, "upload sha256 mismatch"):
                module.verify_bundle(manifest_path=manifest_path, transport_dir=transport)


if __name__ == "__main__":
    unittest.main()
