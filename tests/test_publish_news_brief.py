import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from test_validate_news_brief import valid_brief, valid_manifest

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_news_brief.py"
sys.path.insert(0, str(ROOT / "scripts"))
import news_run_checkpoint
import publish_news_brief


def write_valid_audit(root: Path):
    source_pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
    coverage = []
    for item in source_pool["sources"]:
        source_id = item["source_id"]
        article_url = f"https://example.com/{source_id}"
        old_url = f"https://example.com/{source_id}/old"
        article_time = "2026-08-13T05:00:00+00:00"
        old_time = "2026-08-12T21:00:00+00:00"
        snapshot_text = f"{article_url} {article_time} {old_url} {old_time}"
        snapshot_path = root / f"{source_id}-scan.html"
        snapshot_path.write_text(snapshot_text, encoding="utf-8")
        scan = {
            "schema_version": "1.0.0",
            "collector": "publisher-test-fixture",
            "generated_at": "2026-08-14T06:00:00+08:00",
            "window_start": "2026-08-13T06:00:00+08:00",
            "window_end": "2026-08-14T06:00:00+08:00",
            "pages": [{
                "request_url": item["homepage"],
                "fetched_at": "2026-08-14T06:00:00+08:00",
                "http_status": 200,
                "snapshot_path": str(snapshot_path),
                "sha256": hashlib.sha256(snapshot_text.encode()).hexdigest(),
                "next_url": None,
                "extracted_items": [
                    {"url": article_url, "title": source_id, "published_at": article_time,
                     "url_evidence": article_url, "published_evidence": article_time},
                    {"url": old_url, "title": "old", "published_at": old_time,
                     "url_evidence": old_url, "published_evidence": old_time},
                ],
            }],
            "terminal_proof": {
                "type": "crossed_window_start", "page_index": 1, "witness_url": old_url
            },
        }
        scan_path = root / f"{source_id}-scan.json"
        scan_path.write_text(json.dumps(scan), encoding="utf-8")
        ranked_items = [{
            "url": article_url, "title": source_id, "published_at": article_time,
            "importance_score": 80, "importance_reason": "具有公共影響",
            "importance_breakdown": {
                "public_impact": 24,
                "geographic_or_population_scope": 16,
                "urgency_and_safety": 12,
                "structural_or_policy_significance": 12,
                "material_new_development": 8,
                "core_section_relevance": 8,
            },
        }]
        coverage.append({
            "source_id": source_id, "status": "completed",
            "within_window_count": 1, "ranked_count": 1,
            "ranked_items": ranked_items, "selected_for_pool_count": 1,
            "selected_item_urls": [article_url], "mandatory_overflow_items": [],
            "ranking_completed": True, "ranking_method": "public_value_v1",
            "failure_reason": None,
            "scan_window_start": "2026-08-13T06:00:00+08:00",
            "scan_window_end": "2026-08-14T06:00:00+08:00",
            "scan_evidence_path": str(scan_path),
        })
    candidate = {
        "candidate_id": "cand-1", "dedup_key": "test-event", "title": "測試事件",
        "section": "TWN", "provisional_grade": "B",
        "grade_reason": "本期政策正式生效並造成可驗證的全國公共服務影響，因此評為 B。",
        "grading_evidence": {
            "impact_scope_level": "national",
            "direct_consequences": ["全國公共服務規則正式改變"],
            "structural_significance": "政策正式生效",
            "window_material_changes": ["本期完成法定程序"],
            "why_current_grade": "具全國性實質政策影響",
            "why_not_higher": "沒有跨國或重大系統危機",
            "why_not_lower": "政策已正式生效而非僅為表態",
            "local_disaster_review": {"applies": False},
            "border_conflict_review": {
                "is_border_conflict": False, "formal_war": False,
                "de_facto_war_scale": False, "related_to_monitored_section": False,
                "user_weight_elevated": False, "default_d_applied": False,
                "exception_reason": None,
            },
            "ongoing_conflict_review": {
                "is_ongoing_conflict": False, "same_conflict_as_history": False,
                "routine_incident": False, "material_change": False,
                "change_types": [], "reversal_or_escalation_possible": False,
                "external_system_impact": False, "continuity_discount_applied": False,
                "exception_reason": None,
            },
        },
        "decision": "selected", "reason_code": "selected_threshold_met",
        "reason": "達到B級", "selected_event_id": "TWN-01",
        "candidate_urls": [url for item in coverage for url in item["selected_item_urls"]],
        "source_ids": [item["source_id"] for item in source_pool["sources"]],
        "source_audit": {
            "search_performed": True, "reliable_source_count": 1,
            "independent_group_count": 1, "official_or_primary_found": False,
            "source_limit_note": "單一來源",
        },
        "continuity": {
            "status": "new", "material_changes": [], "unchanged_elements": [],
            "comparison_note": "首次",
        },
    }
    audit = {
        "schema_version": "1.1.0", "retention_days": 14,
        "updated_at": "2026-08-14T06:00:00+08:00",
        "runs": [{
            "run_id": "run-1", "generated_at": "2026-08-14T06:00:00+08:00",
            "window_start": "2026-08-13T06:00:00+08:00",
            "window_end": "2026-08-14T06:00:00+08:00",
            "source_coverage": coverage, "raw_item_count": len(coverage),
            "deduplicated_candidate_count": 1, "candidates": [candidate],
        }],
    }
    path = root / "audit.json"
    path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    return path


def prepare_inputs(root: Path):
    map_path = root / "map.png"
    image_path = root / "image.png"
    source_check_path = root / "source-check.png"
    professional_check_path = root / "professional-check.png"
    Image.new("RGB", (100, 100), "#f3e6b8").save(map_path)
    Image.new("RGB", (100, 100), "#cccccc").save(image_path)
    Image.new("RGB", (100, 100), "#ffffff").save(source_check_path)
    Image.new("RGB", (100, 100), "#ffffff").save(professional_check_path)

    manifest = valid_manifest()
    manifest["events"][0]["map"]["assets"][0]["path"] = str(map_path)
    manifest["events"][0]["images"]["assets"][0]["path"] = str(image_path)
    manifest["events"][0]["images"]["source_checks"][0]["evidence_path"] = str(source_check_path)
    manifest["events"][0]["images"]["professional_source_checks"][0]["evidence_path"] = str(professional_check_path)
    brief = valid_brief().replace("sandbox:/tmp/map.png", str(map_path)).replace(
        "sandbox:/tmp/image.png", str(image_path)
    )
    manifest_path = root / "manifest.json"
    brief_path = root / "brief.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    brief_path.write_text(brief, encoding="utf-8")
    audit_path = write_valid_audit(root)

    checkpoint = news_run_checkpoint.create_checkpoint(
        "run-1", "2026-08-13T06:00:00+08:00", "2026-08-14T06:00:00+08:00"
    )
    for stage in news_run_checkpoint.RELEASE_REQUIRED_STAGES:
        news_run_checkpoint.mark_stage(checkpoint, stage, "running")
        artifacts = []
        for name in news_run_checkpoint.REQUIRED_STAGE_ARTIFACTS[stage]:
            if name == "candidate_audit":
                path = audit_path
            elif name == "manifest":
                path = manifest_path
            elif name == "brief":
                path = brief_path
            else:
                path = root / f"{stage}-{name}.json"
                path.write_text("{}", encoding="utf-8")
            artifacts.append(f"{name}={path}")
        news_run_checkpoint.mark_stage(checkpoint, stage, "completed", artifacts)
    checkpoint_path = root / "checkpoint.json"
    news_run_checkpoint.save(checkpoint_path, checkpoint)
    return checkpoint_path, manifest_path, audit_path, brief_path


def publish_command(checkpoint, manifest, audit, brief, release_dir):
    return [
        sys.executable, str(PUBLISHER),
        "--checkpoint", str(checkpoint), "--manifest", str(manifest),
        "--audit", str(audit), "--brief", str(brief),
        "--output-dir", str(release_dir),
    ]


class PublisherTests(unittest.TestCase):
    def test_publish_uses_final_render_manifest_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            checkpoint_data = news_run_checkpoint.load(checkpoint)
            checkpoint_data["stage_evidence"]["materialize-manifest"]["artifacts"]["manifest"]["sha256"] = "0" * 64
            news_run_checkpoint.save(checkpoint, checkpoint_data)
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, root / "release"),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_publish_writes_receipt_and_deliver_emits_exact_authorized_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            release_dir = root / "release"
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, release_dir),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = release_dir / "release-receipt.json"
            self.assertTrue(receipt.is_file())
            delivered = subprocess.run(
                [sys.executable, str(PUBLISHER), "--deliver-receipt", str(receipt),
                 "--checkpoint", str(checkpoint)],
                capture_output=True, check=False,
            )
            self.assertEqual(delivered.returncode, 0, delivered.stderr.decode())
            self.assertEqual(delivered.stdout, (release_dir / "news-brief.md").read_bytes())

    def test_delivery_rejects_receipt_from_different_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            release_dir = root / "release"
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, release_dir),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            other = news_run_checkpoint.create_checkpoint("run-other", "a", "b")
            other_path = root / "other-checkpoint.json"
            news_run_checkpoint.save(other_path, other)
            delivered = subprocess.run(
                [sys.executable, str(PUBLISHER), "--deliver-receipt",
                 str(release_dir / "release-receipt.json"), "--checkpoint", str(other_path)],
                capture_output=True, check=False,
            )
            self.assertNotEqual(delivered.returncode, 0)
            self.assertEqual(delivered.stdout, b"")

    def test_publish_invalidates_stale_release_before_failed_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            release_dir = root / "release"
            release_dir.mkdir()
            (release_dir / "news-brief.md").write_text("STALE", encoding="utf-8")
            (release_dir / "release-receipt.json").write_text("{}", encoding="utf-8")
            Path(brief).write_text("", encoding="utf-8")
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, release_dir),
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((release_dir / "news-brief.md").exists())
            self.assertFalse((release_dir / "release-receipt.json").exists())

    def test_publish_blocks_blue_map(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            manifest_data = json.loads(Path(manifest).read_text(encoding="utf-8"))
            map_path = Path(manifest_data["events"][0]["map"]["assets"][0]["path"])
            Image.new("RGB", (100, 100), "#4d88c7").save(map_path)
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, root / "release"),
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("藍色背景比例過高", result.stderr)

    def test_publish_blocks_selected_candidate_missing_from_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            audit_data = json.loads(Path(audit).read_text(encoding="utf-8"))
            extra = dict(audit_data["runs"][0]["candidates"][0])
            extra.update({
                "candidate_id": "cand-2", "dedup_key": "event-2", "title": "漏放事件",
                "selected_event_id": "GLB-01",
            })
            audit_data["runs"][0]["candidates"].append(extra)
            audit_data["runs"][0]["deduplicated_candidate_count"] = 2
            Path(audit).write_text(json.dumps(audit_data, ensure_ascii=False), encoding="utf-8")
            checkpoint_data = news_run_checkpoint.load(checkpoint)
            news_run_checkpoint.mark_stage(
                checkpoint_data, "audit-news-candidates", "running"
            )
            news_run_checkpoint.mark_stage(
                checkpoint_data, "audit-news-candidates", "completed",
                [f"candidate_audit={audit}"],
            )
            news_run_checkpoint.save(checkpoint, checkpoint_data)
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, root / "release"),
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("入選事件與 manifest 不一致", result.stderr)

    def test_publish_blocks_c_grade_merged_candidate_missing_from_reader_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, manifest, audit, _ = prepare_inputs(root)
            audit_data = json.loads(Path(audit).read_text(encoding="utf-8"))
            original = audit_data["runs"][0]["candidates"][0]
            moved_url = original["candidate_urls"].pop()
            original["source_ids"] = sorted({url.split("/")[3] for url in original["candidate_urls"]})
            extra = json.loads(json.dumps(original))
            extra.update({
                "candidate_id": "cand-merged", "dedup_key": "merged-event",
                "title": "被合併但未映射的 C 級事件", "provisional_grade": "C",
                "decision": "merged", "reason_code": "duplicate_merged",
                "selected_event_id": "GLB-01", "candidate_urls": [moved_url],
                "source_ids": [moved_url.split("/")[3]],
            })
            audit_data["runs"][0]["candidates"].append(extra)
            audit_data["runs"][0]["deduplicated_candidate_count"] = 2
            manifest_data = json.loads(Path(manifest).read_text(encoding="utf-8"))
            pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
            errors = publish_news_brief.candidate_errors(
                audit_data, manifest_data, pool,
            )
            self.assertTrue(any("C 級以上" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
