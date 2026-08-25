import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tests.test_validate_news_brief import (
    MAIN_SHA,
    RUN_ID,
    legacy_sectioned_brief,
    valid_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_news_brief.py"
sys.path.insert(0, str(ROOT / "scripts"))
import news_run_checkpoint
import publish_news_brief


def write_valid_audit(root: Path):
    source_pool = json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8"))
    coverage = []
    for item in source_pool["discovery_sources"]:
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
                "public_impact": 80,
                "geographic_or_population_scope": 80,
                "urgency_and_safety": 80,
                "structural_or_policy_significance": 80,
                "material_new_development": 80,
                "core_section_relevance": 80,
            },
        }]
        coverage.append({
            "source_id": source_id, "status": "completed",
            "within_window_count": 1, "ranked_count": 1,
            "ranked_items": ranked_items, "selected_for_pool_count": 1,
            "selected_item_urls": [article_url],
            "ranking_completed": True, "ranking_method": "public_value_v2",
            "failure_reason": None,
            "scan_window_start": "2026-08-13T06:00:00+08:00",
            "scan_window_end": "2026-08-14T06:00:00+08:00",
            "scan_evidence_path": str(scan_path),
        })
    candidate = {
        "candidate_id": "cand-1", "dedup_key": "test-event", "title": "測試事件",
        "semantic_event_id": "semantic-event-1",
        "event_identity": {
            "who_or_what": "測試事件主體",
            "what_happened": "完成一項可核實的政策變更",
            "where": "台灣",
            "when": "2026-08-14T06:00:00+08:00",
            "country_codes": ["TWN"],
            "primary_country_code": "TWN",
            "location_evidence": "政策內容明確適用台灣，未使用來源媒體分桶。",
            "event_occurred_at": "2026-08-14T06:00:00+08:00",
            "material_update_at": "2026-08-14T06:00:00+08:00",
            "material_update_type": "new_event",
            "material_update_evidence": "本輪完成法定程序並正式生效。",
            "temporal_review": {
                "review_method": "model_content_comparison",
                "window_status": "new_event",
                "active_during_window": True,
                "new_or_changed_facts": ["本輪首次完成法定程序"],
                "repeated_old_facts": [],
                "current_window_impact": ["政策在本輪時間窗內生效"],
                "comparison_evidence": "模型比較內容與既有時間線後確認為新事件。",
            },
            "semantic_merge_basis": "所有文章描述同一主體、行動、地點與時間",
        },
        "section": "TWN", "scoring_method": "public_value_v2",
        "weighted_score": 60, "provisional_grade": "B",
        "importance_score": 60,
        "importance_breakdown": {
            "public_impact": 60,
            "geographic_or_population_scope": 60,
            "urgency_and_safety": 60,
            "structural_or_policy_significance": 60,
            "material_new_development": 60,
            "core_section_relevance": 60,
        },
        "dimension_evidence": {
            "public_impact": ["F01"],
            "geographic_or_population_scope": ["F02"],
            "urgency_and_safety": ["F03"],
            "structural_or_policy_significance": ["F04"],
            "material_new_development": ["F05"],
            "core_section_relevance": ["F06"],
        },
        "consequence_evidence": {
            "realized": ["F01", "F05", "F06"],
            "ongoing": ["F02", "F03"],
            "potential": ["F04"],
            "speculative": [],
        },
        "evidence_facts": [
            {"fact_id": "F01", "fact": "公共服務規則已正式改變", "fact_type": "public_consequence", "consequence_class": "realized", "confidence": 90, "source_urls": ["https://example.com/f01"], "institutional_mechanism": None},
            {"fact_id": "F02", "fact": "全國服務系統持續受影響", "fact_type": "directly_affected_scope", "consequence_class": "ongoing", "confidence": 90, "source_urls": ["https://example.com/f02"], "institutional_mechanism": None},
            {"fact_id": "F03", "fact": "服務提供者需立即調整", "fact_type": "safety_condition", "consequence_class": "ongoing", "confidence": 90, "source_urls": ["https://example.com/f03"], "institutional_mechanism": None},
            {"fact_id": "F04", "fact": "法定程序形成拘束規則", "fact_type": "institutional_change", "consequence_class": "potential", "confidence": 90, "source_urls": ["https://example.com/f04"], "institutional_mechanism": "正式法定程序"},
            {"fact_id": "F05", "fact": "本期完成法定程序", "fact_type": "material_delta", "consequence_class": "realized", "confidence": 90, "source_urls": ["https://example.com/f05"], "institutional_mechanism": None},
            {"fact_id": "F06", "fact": "直接涉及台灣中央制度", "fact_type": "section_centrality", "consequence_class": "realized", "confidence": 90, "source_urls": ["https://example.com/f06"], "institutional_mechanism": None},
        ],
        "policy_stage": "not_applicable",
        "delta_facts": [{"fact_id": "F05", "previous_state": "程序尚未完成", "current_state": "程序已完成", "why_material": "規則開始具拘束力"}],
        "high_score_challenges": [],
        "overall_high_score_challenge": None,
        "cross_dimension_rationales": [],
        "midpoint_rationales": [],
        "evidence_confidence": 85,
        "confidence_band": "high",
        "grade_status": "validated",
        "grade_reason": "本期政策正式生效並造成可驗證的全國公共服務影響，因此評為 B。",
        "grading_evidence": {
            "impact_scope_level": "national",
            "direct_consequences": ["全國公共服務規則正式改變"],
            "structural_significance": "政策正式生效",
            "window_material_changes": ["本期完成法定程序"],
            "why_current_grade": "具全國性實質政策影響",
            "why_not_higher": "沒有跨國或重大系統危機",
            "why_not_lower": "政策已正式生效而非僅為表態",
            "policy_governance_review": {"applies": False},
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
        "source_ids": [item["source_id"] for item in source_pool["discovery_sources"]],
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
            "run_id": RUN_ID, "generated_at": "2026-08-14T06:00:00+08:00",
            "window_start": "2026-08-13T06:00:00+08:00",
            "window_end": "2026-08-14T06:00:00+08:00",
            "source_coverage": coverage, "raw_item_count": len(coverage),
            "processing_counts": {
                "merged_article_row_count": len(coverage),
                "in_window_article_row_count": len(coverage),
                "canonical_url_count": len(coverage),
                "provisional_title_cluster_count": len(coverage),
                "semantic_event_count": 1,
                "scored_event_count": 1,
                "c_or_higher_scored_event_count": 1,
                "selected_event_count": 1,
                "event_evidence_article_row_count": len(coverage),
                "non_news_article_row_count": 0,
                "unresolved_article_row_count": 0,
            },
            "article_dispositions": [{
                "source_id": item["source_id"],
                "url": item["selected_item_urls"][0],
                "disposition": "event_evidence",
                "semantic_event_id": "semantic-event-1",
                "reason": "文章內容已對應至同一語意事件",
            } for item in coverage],
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
    image_asset = manifest["events"][0]["images"]["assets"][0]
    image_asset["path"] = str(image_path)
    image_asset["content_sha256"] = hashlib.sha256(image_path.read_bytes()).hexdigest()
    image_asset["width"] = 100
    image_asset["height"] = 100
    materialization_path = root / "materialized-images.json"
    materialization_path.write_text(json.dumps([{
        "event_id": "TWN-01",
        "source_page_url": image_asset["source_url"],
        "source_image_url": image_asset["source_image_url"],
        "source_url": image_asset["source_image_url"],
        "status": "ready",
        "local_path": str(image_path),
        "mime_type": "image/jpeg",
        "width": 100,
        "height": 100,
        "byte_size": image_path.stat().st_size,
        "sha256": image_asset["content_sha256"],
        "materialized_by": "scripts/materialize_news_images.py",
        "alt": "測試圖片",
        "credit": "官方來源",
    }], ensure_ascii=False), encoding="utf-8")
    manifest["events"][0]["images"]["materialization_manifest_path"] = str(materialization_path)
    manifest["events"][0]["images"]["source_checks"][0]["evidence_path"] = str(source_check_path)
    manifest["events"][0]["images"]["professional_source_checks"][0]["evidence_path"] = str(professional_check_path)
    brief = legacy_sectioned_brief().replace("sandbox:/tmp/map.png", str(map_path)).replace(
        "sandbox:/tmp/image.png", str(image_path)
    )
    manifest_path = root / "manifest.json"
    brief_path = root / "brief.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    brief_path.write_text(brief, encoding="utf-8")
    audit_path = write_valid_audit(root)

    checkpoint = news_run_checkpoint.create_checkpoint(
        RUN_ID, "2026-08-13T06:00:00+08:00", "2026-08-14T06:00:00+08:00"
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
    def test_candidate_mapping_rejects_nonvalidated_manifest_grade(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = json.loads(write_valid_audit(root).read_text(encoding="utf-8"))
            manifest = valid_manifest()
            manifest["events"][0]["grade_status"] = "provisional"

            errors = publish_news_brief.candidate_errors(
                audit,
                manifest,
                json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8")),
            )

            self.assertTrue(any("grade_status" in error and "validated" in error for error in errors))

    def test_candidate_mapping_rejects_manifest_score_different_from_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = json.loads(write_valid_audit(root).read_text(encoding="utf-8"))
            manifest = valid_manifest()
            manifest["events"][0]["validated_importance_score"] = 65

            errors = publish_news_brief.candidate_errors(
                audit,
                manifest,
                json.loads((ROOT / "news-source-pool.json").read_text(encoding="utf-8")),
            )

            self.assertTrue(any("validated_importance_score" in error for error in errors))

    def test_checkpoint_rejects_manifest_from_another_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest_path, audit_path, brief = prepare_inputs(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["run"]["run_id"] = "gnb-20260817T102801Z-deadbeef"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            cp = news_run_checkpoint.load(checkpoint)
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            errors = publish_news_brief.checkpoint_errors(
                cp, manifest, audit,
                {"audit": audit_path, "manifest": manifest_path, "brief": brief},
            )
            self.assertTrue(any("manifest" in error and "run_id" in error for error in errors))

    def test_publish_receipt_binds_main_sha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            release_dir = root / "release"
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, release_dir),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            receipt = json.loads((release_dir / "release-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(MAIN_SHA, receipt["main_sha"])

    def test_publisher_rejects_image_without_matching_materializer_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest_path, audit, brief = prepare_inputs(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            materialization_path = Path(
                manifest["events"][0]["images"]["materialization_manifest_path"]
            )
            materialization_path.write_text("[]", encoding="utf-8")
            result = subprocess.run(
                publish_command(checkpoint, manifest_path, audit, brief, root / "release"),
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("materialized-images", result.stderr)

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

    def test_conversation_delivery_rewrites_only_local_image_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, manifest, audit, brief = prepare_inputs(root)
            release_dir = root / "release"
            result = subprocess.run(
                publish_command(checkpoint, manifest, audit, brief, release_dir),
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            release = release_dir / "news-brief.md"
            canonical_bytes = release.read_bytes()
            receipt = json.loads((release_dir / "release-receipt.json").read_text(encoding="utf-8"))

            delivered = subprocess.run(
                [sys.executable, str(PUBLISHER), "--deliver-receipt",
                 str(release_dir / "release-receipt.json"), "--checkpoint", str(checkpoint),
                 "--conversation-transport"],
                capture_output=True, check=False,
            )

            self.assertEqual(delivered.returncode, 0, delivered.stderr.decode())
            conversation = delivered.stdout.decode("utf-8")
            map_uri = "sandbox:/" + str(root / "map.png").replace("\\", "/")
            image_uri = "sandbox:/" + str(root / "image.png").replace("\\", "/")
            self.assertIn(f"]({map_uri})", conversation)
            self.assertIn(f"]({image_uri})", conversation)
            self.assertNotEqual(delivered.stdout, canonical_bytes)
            self.assertEqual(release.read_bytes(), canonical_bytes)
            self.assertEqual(
                receipt["authorized_release_sha256"], hashlib.sha256(canonical_bytes).hexdigest()
            )

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
