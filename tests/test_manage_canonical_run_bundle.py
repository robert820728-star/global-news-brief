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
    def _write_recovery_inputs(self, root, *, run_id, candidate_count=43):
        window_start = "2026-08-22T08:55:30Z"
        window_end = "2026-08-23T08:55:30Z"
        paths = {
            "checkpoint": root / "checkpoint.json",
            "source": root / "source-candidates.json",
            "gate": root / "news-relevance-gate.json",
            "admitted": root / "model-source-candidates.json",
            "preprocessed": root / "preprocessed-candidates.json",
            "row_admissions": root / "source-row-admissions.json",
            "batch_index": root / "content-hydration-batches.json",
        }
        candidates = [
            {
                "row_id": f"row-{index:024x}",
                "candidate_id": f"candidate-{index:03d}",
                "source_id": "source-a",
                "canonical_url": f"https://example.test/news/{index}",
                "summary_quality": "full",
            }
            for index in range(candidate_count)
        ]
        payloads = {
            "checkpoint": {
                "run_id": run_id,
                "window_start": window_start,
                "window_end": window_end,
            },
            "source": {
                "run_id": run_id,
                "window_start": window_start,
                "window_end": window_end,
                "items": candidates,
            },
            "gate": {"run_id": run_id, "items": []},
            "admitted": {
                "run_id": run_id,
                "window_start": window_start,
                "window_end": window_end,
                "items": candidates,
            },
            "preprocessed": {
                "run_id": run_id,
                "window_start": window_start,
                "window_end": window_end,
                "normalized_articles": candidates,
            },
            "row_admissions": {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "window_start": window_start,
                "window_end": window_end,
                "source_row_count": candidate_count,
                "admitted_row_count": candidate_count,
                "rows": [
                    {"row_id": f"row-{index:03d}"}
                    for index in range(candidate_count)
                ],
            },
        }
        for name, payload in payloads.items():
            paths[name].write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return paths

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

    def test_pre_manifest_recovery_bundle_conserves_and_restores_all_inputs(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "gnb-20260823T085530Z-7f3c9a12"
            paths = self._write_recovery_inputs(root, run_id=run_id)
            transport = root / "transport"
            manifest_path = root / "recovery-bundle-manifest.json"

            manifest = module.pack_pre_manifest_recovery_bundle(
                run_id=run_id,
                checkpoint_path=paths["checkpoint"],
                source_candidates_path=paths["source"],
                relevance_gate_path=paths["gate"],
                admitted_candidates_path=paths["admitted"],
                preprocessed_candidates_path=paths["preprocessed"],
                source_row_admissions_path=paths["row_admissions"],
                batch_index_path=paths["batch_index"],
                transport_dir=transport,
                manifest_path=manifest_path,
                max_batch_rows=20,
                max_blob_bytes=256,
            )

            self.assertEqual("pre-manifest-recovery", manifest["profile"])
            batch_data = json.loads(paths["batch_index"].read_text(encoding="utf-8"))
            self.assertEqual([20, 20, 3], [item["article_row_count"] for item in batch_data["batches"]])
            self.assertEqual(43, batch_data["candidate_count"])
            self.assertTrue(any(
                item["logical_path"] == "recovery/source-row-admissions.json"
                for item in manifest["artifacts"]
            ))
            originals = {
                artifact["logical_path"]: (root / Path(artifact["logical_path"]).name).read_bytes()
                for artifact in manifest["artifacts"]
            }
            for path in paths.values():
                path.unlink()

            module.verify_bundle(manifest_path=manifest_path, transport_dir=transport)
            restored = root / "restored"
            module.restore_bundle(
                manifest_path=manifest_path,
                transport_dir=transport,
                output_dir=restored,
            )
            for logical_path, original in originals.items():
                self.assertEqual(original, (restored / logical_path).read_bytes())

    def test_pre_manifest_recovery_bundle_rejects_duplicate_row_ids(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "gnb-20260823T085530Z-7f3c9a12"
            paths = self._write_recovery_inputs(root, run_id=run_id, candidate_count=2)
            admitted = json.loads(paths["admitted"].read_text(encoding="utf-8"))
            admitted["items"][1]["row_id"] = admitted["items"][0]["row_id"]
            paths["admitted"].write_text(json.dumps(admitted), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "row ids must be non-empty and unique"):
                module.pack_pre_manifest_recovery_bundle(
                    run_id=run_id,
                    checkpoint_path=paths["checkpoint"],
                    source_candidates_path=paths["source"],
                    relevance_gate_path=paths["gate"],
                    admitted_candidates_path=paths["admitted"],
                    preprocessed_candidates_path=paths["preprocessed"],
                    source_row_admissions_path=paths["row_admissions"],
                    batch_index_path=paths["batch_index"],
                    transport_dir=root / "transport",
                    manifest_path=root / "manifest.json",
                )

    def test_pre_manifest_recovery_preserves_repeated_candidate_ids_by_row_id(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "gnb-20260823T085530Z-7f3c9a12"
            paths = self._write_recovery_inputs(root, run_id=run_id, candidate_count=2)
            admitted = json.loads(paths["admitted"].read_text(encoding="utf-8"))
            admitted["items"][1]["candidate_id"] = admitted["items"][0]["candidate_id"]
            paths["admitted"].write_text(json.dumps(admitted), encoding="utf-8")

            module.pack_pre_manifest_recovery_bundle(
                run_id=run_id,
                checkpoint_path=paths["checkpoint"],
                source_candidates_path=paths["source"],
                relevance_gate_path=paths["gate"],
                admitted_candidates_path=paths["admitted"],
                preprocessed_candidates_path=paths["preprocessed"],
                source_row_admissions_path=paths["row_admissions"],
                batch_index_path=paths["batch_index"],
                transport_dir=root / "transport",
                manifest_path=root / "manifest.json",
            )

            batch = json.loads(paths["batch_index"].read_text(encoding="utf-8"))
            self.assertEqual(2, batch["candidate_count"])
            self.assertEqual(2, len({
                item["row_id"] for group in batch["batches"] for item in group["items"]
            }))

    def test_pre_manifest_recovery_bundle_rejects_run_or_window_mismatch(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_id = "gnb-20260823T085530Z-7f3c9a12"
            paths = self._write_recovery_inputs(root, run_id=run_id, candidate_count=2)
            admitted = json.loads(paths["admitted"].read_text(encoding="utf-8"))
            admitted["window_end"] = "2026-08-23T09:00:00Z"
            paths["admitted"].write_text(json.dumps(admitted), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "run/window mismatch"):
                module.pack_pre_manifest_recovery_bundle(
                    run_id=run_id,
                    checkpoint_path=paths["checkpoint"],
                    source_candidates_path=paths["source"],
                    relevance_gate_path=paths["gate"],
                    admitted_candidates_path=paths["admitted"],
                    preprocessed_candidates_path=paths["preprocessed"],
                    source_row_admissions_path=paths["row_admissions"],
                    batch_index_path=paths["batch_index"],
                    transport_dir=root / "transport",
                    manifest_path=root / "manifest.json",
                )


if __name__ == "__main__":
    unittest.main()
