import importlib.util
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manage_candidate_audit", ROOT / "scripts" / "manage_candidate_audit.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def source_pool():
    return MODULE.load(ROOT / "news-source-pool.json")


def candidate(grade="C", decision="selected", reason_code="selected_threshold_met"):
    return {
        "candidate_id": "c", "dedup_key": "c", "title": "測試", "section": "GLB",
        "provisional_grade": grade, "grade_reason": "依公共影響評級",
        "decision": decision, "reason_code": reason_code, "reason": "決定理由",
        "selected_event_id": "GLB-01" if decision == "selected" else None,
        "candidate_urls": ["https://example.com/reuters"], "source_ids": ["reuters"],
        "source_audit": {"reliable_source_count": 2},
        "continuity": {"status": "new", "material_changes": [], "unchanged_elements": [], "comparison_note": "首次"},
    }


def valid_audit(candidates=None, per_source_count=1):
    evidence_root = Path(tempfile.mkdtemp(prefix="source-scan-test-"))
    window_start = "2026-08-13T06:00:00+08:00"
    window_end = "2026-08-14T06:00:00+08:00"
    coverage = []
    for item in source_pool()["sources"]:
        source_id = item["source_id"]
        ranked_items = [
            {"url": f"https://example.com/{source_id}/{index}", "title": f"{source_id}-{index}",
             "published_at": "2026-08-13T05:00:00+00:00", "importance_score": 100 - index / 10,
             "importance_reason": "依公共影響、範圍與結構意義排序"}
            for index in range(per_source_count)
        ]
        old_url = f"https://example.com/{source_id}/before-window"
        old_time = "2026-08-12T21:00:00+00:00"
        snapshot_text = " ".join(
            part for ranked in ranked_items
            for part in (ranked["url"], ranked["published_at"])
        ) + f" {old_url} {old_time}"
        snapshot_path = evidence_root / f"{source_id}.html"
        snapshot_path.write_text(snapshot_text, encoding="utf-8")
        extracted = [
            {"url": ranked["url"], "title": ranked["title"], "published_at": ranked["published_at"], "url_evidence": ranked["url"], "published_evidence": ranked["published_at"]}
            for ranked in ranked_items
        ] + [{"url": old_url, "title": "時間邊界", "published_at": old_time, "url_evidence": old_url, "published_evidence": old_time}]
        scan = {
            "schema_version": "1.0.0", "collector": "candidate-audit-test-fixture", "generated_at": window_end,
            "window_start": window_start, "window_end": window_end,
            "pages": [{"request_url": item["homepage"], "fetched_at": window_end, "http_status": 200, "snapshot_path": str(snapshot_path), "sha256": hashlib.sha256(snapshot_text.encode()).hexdigest(), "next_url": None, "extracted_items": extracted}],
            "terminal_proof": {"type": "crossed_window_start", "page_index": 1, "witness_url": old_url},
        }
        scan_path = evidence_root / f"{source_id}.json"
        scan_path.write_text(json.dumps(scan), encoding="utf-8")
        coverage.append({
            "source_id": source_id, "status": "completed",
            "within_window_count": per_source_count, "ranked_count": per_source_count,
            "ranked_items": ranked_items,
            "selected_for_pool_count": min(per_source_count, 30),
            "selected_item_urls": [item["url"] for item in ranked_items[:30]],
            "mandatory_overflow_items": [],
            "ranking_completed": True, "ranking_method": "public_value_v1", "failure_reason": None,
            "scan_window_start": window_start, "scan_window_end": window_end,
            "scan_evidence_path": str(scan_path),
        })
    items = candidates if candidates is not None else [candidate()]
    all_urls = [url for item in coverage for url in item["selected_item_urls"]]
    for index, item in enumerate(items):
        item["candidate_urls"] = [all_urls[index]] if index < len(all_urls) else []
        item["source_ids"] = [all_urls[index].split("/")[3]] if index < len(all_urls) else []
    if items and len(all_urls) > len(items):
        items[0]["candidate_urls"].extend(all_urls[len(items):])
        items[0]["source_ids"] = sorted({url.split("/")[3] for url in items[0]["candidate_urls"]})
    now = window_end
    return {
        "schema_version": "1.1.0", "retention_days": 14, "updated_at": now,
        "runs": [{"run_id": "r", "generated_at": now, "window_start": window_start, "window_end": window_end,
                  "source_coverage": coverage, "raw_item_count": 10 * min(per_source_count, 30),
                  "deduplicated_candidate_count": len(items), "candidates": items}],
    }


class CandidateAuditTests(unittest.TestCase):
    def test_cultural_suspension_novelty_rule_is_locked(self):
        pool = source_pool()
        pool["cultural_industry_event_rule"]["first_large_award_suspension_min_grade"] = "C-"
        errors = MODULE.validate(valid_audit(), pool)
        self.assertTrue(any("首次停辦最低為 C" in error for error in errors))

    def test_ten_sources_each_take_top_thirty(self):
        self.assertEqual([], MODULE.validate(valid_audit(per_source_count=73), source_pool()))

    def test_source_with_more_than_thirty_cannot_submit_fewer(self):
        audit = valid_audit(per_source_count=73)
        audit["runs"][0]["source_coverage"][0]["selected_for_pool_count"] = 29
        audit["runs"][0]["source_coverage"][0]["selected_item_urls"].pop()
        audit["runs"][0]["raw_item_count"] -= 1
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("前 30 則" in error for error in errors))

    def test_ranked_item_after_thirty_requires_mandatory_trigger(self):
        audit = valid_audit(per_source_count=35)
        source = audit["runs"][0]["source_coverage"][0]
        overflow_url = source["ranked_items"][32]["url"]
        source["mandatory_overflow_items"] = [{
            "url": overflow_url,
            "trigger": "cultural_industry_or_creator_ecosystem",
            "reason": "獨立獎項停辦反映創作者生態與資金結構，不得因排名截斷",
        }]
        source["selected_item_urls"].append(overflow_url)
        source["selected_for_pool_count"] += 1
        audit["runs"][0]["raw_item_count"] += 1
        audit["runs"][0]["candidates"][0]["candidate_urls"].append(overflow_url)
        self.assertEqual([], MODULE.validate(audit, source_pool()))
        source["mandatory_overflow_items"][0]["trigger"] = "celebrity_gossip"
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("觸發類型無效" in error for error in errors))

    def test_every_source_item_must_reach_a_deduplicated_candidate(self):
        audit = valid_audit()
        audit["runs"][0]["candidates"][0]["candidate_urls"].pop()
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("禁止候選無聲消失" in error for error in errors))

    def test_c_and_above_must_be_selected_without_quota(self):
        items = []
        for index in range(30):
            item = candidate("S")
            item["candidate_id"] = item["dedup_key"] = str(index)
            item["selected_event_id"] = f"GLB-{index + 1:02d}"
            items.append(item)
        self.assertEqual([], MODULE.validate(valid_audit(items, per_source_count=3), source_pool()))
        items[0]["decision"] = "excluded"
        errors = MODULE.validate(valid_audit(items, per_source_count=3), source_pool())
        self.assertTrue(any("C 以上必須入選" in error for error in errors))

    def test_c_minus_requires_explicit_use_reason(self):
        item = candidate("C-", "selected", "c_minus_selected_need")
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("C- 取用" in error for error in errors))
        item["c_minus_use_reason"] = "使用者明確追蹤此主題"
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_d_and_e_are_audit_only(self):
        errors = MODULE.validate(valid_audit([candidate("D")]), source_pool())
        self.assertTrue(any("D/E 不得入選" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
