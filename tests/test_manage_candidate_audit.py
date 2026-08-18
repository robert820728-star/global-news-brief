import importlib.util
import hashlib
import json
import subprocess
import sys
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


def importance_breakdown(score=100):
    weights = source_pool()["ranking"]["dimensions"]
    ratio = score / 100
    values = {key: round(weight * ratio, 2) for key, weight in weights.items()}
    difference = round(score - sum(values.values()), 2)
    values[next(iter(values))] = round(values[next(iter(values))] + difference, 2)
    return values


def candidate(grade="C", decision="selected", reason_code="selected_threshold_met"):
    return {
        "candidate_id": "c", "dedup_key": "c", "title": "測試", "section": "GLB",
        "provisional_grade": grade,
        "grade_reason": "本期出現可驗證的新制度變化，影響範圍與直接後果符合目前級距。",
        "grading_evidence": grading_evidence(grade),
        "decision": decision, "reason_code": reason_code, "reason": "決定理由",
        "selected_event_id": "GLB-01" if decision == "selected" else None,
        "candidate_urls": ["https://example.com/reuters"], "source_ids": ["reuters"],
        "source_audit": {"reliable_source_count": 2},
        "continuity": {"status": "new", "material_changes": [], "unchanged_elements": [], "comparison_note": "首次"},
    }


def grading_evidence(grade="C"):
    return {
        "impact_scope_level": "national",
        "direct_consequences": ["已造成可驗證的公共服務變化"] if grade not in {"C", "C-", "D", "E"} else [],
        "structural_significance": "形成可追蹤的制度或公共風險訊號",
        "window_material_changes": ["本期首次正式確認事件"],
        "why_current_grade": "影響範圍與本期增量符合目前級距",
        "why_not_higher": "尚未造成更廣泛的跨國或系統性影響",
        "why_not_lower": "存在具體且可驗證的新進展",
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
             "importance_breakdown": importance_breakdown(100 - index / 10),
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
                  "source_coverage": coverage,
                  "raw_item_count": len(coverage) * min(per_source_count, 30),
                  "deduplicated_candidate_count": len(items), "candidates": items}],
    }


class CandidateAuditTests(unittest.TestCase):
    def test_degraded_discovery_coverage_accepts_one_ready_source(self):
        pool = source_pool()
        pool["discovery_sources"] = [
            next(item for item in pool["sources"] if item["source_id"] == source_id)
            for source_id in ("cna", "chinanews", "reuters")
        ]
        pool["discovery_policy"] = {
            "minimum_ready_sources": 1,
            "source_failure_policy": "degrade_not_block",
        }
        audit = valid_audit()
        run = audit["runs"][0]
        run["source_coverage"] = [
            item for item in run["source_coverage"] if item["source_id"] == "cna"
        ]
        only_url = run["source_coverage"][0]["selected_item_urls"][0]
        run["raw_item_count"] = 1
        run["candidates"][0]["candidate_urls"] = [only_url]
        run["candidates"][0]["source_ids"] = ["cna"]
        self.assertEqual([], MODULE.validate(audit, pool))

    def test_ordinary_local_disaster_under_50_cannot_reach_c(self):
        item = candidate("C", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 49,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("未滿 50 人" in error for error in errors))

    def test_ordinary_local_disaster_at_50_is_c(self):
        item = candidate("C", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 50,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_ordinary_local_disaster_50_to_99_without_special_meaning_is_only_c(self):
        item = candidate("B", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 99,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("50–99 人" in error for error in errors))

    def test_ordinary_local_disaster_at_100_requires_b_baseline(self):
        item = candidate("B+", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 100,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("100–249 人" in error for error in errors))
        item["provisional_grade"] = "B"
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_ordinary_local_disaster_at_250_requires_a_minus_baseline(self):
        item = candidate("B", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 250,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("250 人以上" in error for error in errors))
        item["provisional_grade"] = "A-"
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_verified_special_meaning_can_raise_grade_with_reason(self):
        item = candidate("B+", "selected")
        item["grading_evidence"]["impact_scope_level"] = "national"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 100,
            "special_significance_triggers": ["regulatory_failure_or_systemic_risk"],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("調整理由" in error for error in errors))
        item["grading_evidence"]["local_disaster_review"]["grade_adjustment_reason"] = "官方調查確認監管失靈並形成全國性制度風險。"
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_grade_can_be_lowered_with_concrete_reason(self):
        item = candidate("B", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 260,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("調整理由" in error for error in errors))
        item["grading_evidence"]["local_disaster_review"]["grade_adjustment_reason"] = "事件侷限單一設施，未造成跨區域、關鍵系統或跨國直接影響。"
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_extreme_scope_can_override_sub_50_floor(self):
        item = candidate("A-", "selected")
        item["grading_evidence"]["impact_scope_level"] = "subregional"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 0,
            "special_significance_triggers": [
                "extreme_missing_serious_injury_or_evacuation",
                "mass_housing_or_critical_infrastructure_loss",
            ],
            "grade_adjustment_reason": "數萬人直接撤離且大量住宅毀損，達到城市級極端規模。",
        }
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_monitored_region_conflict_risk_can_override_sub_50_floor(self):
        item = candidate("C", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 3,
            "special_significance_triggers": ["monitored_region_conflict_escalation_risk"],
            "grade_adjustment_reason": "事件可能直接引發指定監控區域內的軍事或其他衝突。",
        }
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_conflict_event_cannot_also_use_local_disaster_gate(self):
        item = candidate("C", "selected")
        item["grading_evidence"]["border_conflict_review"].update({
            "is_border_conflict": True,
            "related_to_monitored_section": True,
            "exception_reason": "事件直接涉及監控板塊，依既有軍事衝突規則評級。",
        })
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 50,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("軍事／衝突規則" in error for error in errors))

    def test_append_creates_missing_output_parent_directory(self):
        audit = valid_audit()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_path = root / "current-run.json"
            run_path.write_text(
                json.dumps(audit["runs"][0], ensure_ascii=False), encoding="utf-8"
            )
            output_path = root / "new-state" / "candidate-audit.json"
            result = subprocess.run(
                [
                    sys.executable, str(ROOT / "scripts" / "manage_candidate_audit.py"),
                    "append", "--history", str(root / "missing-history.json"),
                    "--run", str(run_path), "--output", str(output_path),
                    "--source-pool", str(ROOT / "news-source-pool.json"),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue(output_path.is_file())

    def test_every_shortlist_item_requires_all_major_scores(self):
        audit = valid_audit()
        ranked = audit["runs"][0]["source_coverage"][0]["ranked_items"][0]
        ranked.pop("importance_breakdown")
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("importance_breakdown" in error for error in errors))

    def test_major_scores_must_match_weights_and_total(self):
        audit = valid_audit()
        ranked = audit["runs"][0]["source_coverage"][0]["ranked_items"][0]
        ranked["importance_breakdown"]["public_impact"] = 31
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("大項分數" in error for error in errors))
        self.assertTrue(any("importance_score" in error for error in errors))

    def test_c_or_above_merged_candidate_requires_reader_event_mapping(self):
        item = candidate("C", "merged", "duplicate_merged")
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("selected_event_id" in error for error in errors))

    def test_cultural_suspension_novelty_rule_is_locked(self):
        pool = source_pool()
        pool["cultural_industry_event_rule"]["first_large_award_suspension_min_grade"] = "C-"
        errors = MODULE.validate(valid_audit(), pool)
        self.assertTrue(any("首次停辦最低為 C" in error for error in errors))

    def test_all_configured_sources_each_take_top_thirty(self):
        self.assertEqual([], MODULE.validate(valid_audit(per_source_count=73), source_pool()))

    def test_source_coverage_count_is_driven_by_source_pool(self):
        pool = source_pool()
        self.assertEqual(15, len(pool["sources"]))
        self.assertEqual([], MODULE.validate(valid_audit(), pool))

        missing = valid_audit()
        missing["runs"][0]["source_coverage"].pop()
        missing["runs"][0]["raw_item_count"] -= 1
        errors = MODULE.validate(missing, pool)
        self.assertTrue(any("source coverage" in error for error in errors))

        extra = valid_audit()
        duplicate = dict(extra["runs"][0]["source_coverage"][-1])
        duplicate["source_id"] = "unexpected"
        extra["runs"][0]["source_coverage"].append(duplicate)
        extra["runs"][0]["raw_item_count"] += duplicate["selected_for_pool_count"]
        errors = MODULE.validate(extra, pool)
        self.assertTrue(any("source coverage" in error for error in errors))

    def test_section_source_contract_matches_flat_source_order(self):
        pool = source_pool()
        pool["section_sources"]["GLB"] = pool["section_sources"]["GLB"][:-1]
        errors = MODULE.validate(valid_audit(), pool)
        self.assertTrue(any("primary_sources_per_section" in error for error in errors))
        self.assertTrue(any("展開順序" in error for error in errors))

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

    def test_grade_reason_template_is_rejected(self):
        item = candidate()
        item["grade_reason"] = "值得持續追蹤"
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("模板理由" in error for error in errors))

    def test_non_monitored_border_skirmish_is_forced_to_d(self):
        item = candidate("B", "selected")
        review = item["grading_evidence"]["border_conflict_review"]
        review.update({"is_border_conflict": True, "default_d_applied": False})
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("邊境小衝突必須評為 D" in error for error in errors))

        item = candidate("D", "excluded", "below_public_value_threshold")
        review = item["grading_evidence"]["border_conflict_review"]
        review.update({"is_border_conflict": True, "default_d_applied": True})
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_monitored_border_conflict_can_be_regraded_with_reason(self):
        item = candidate("C", "selected")
        review = item["grading_evidence"]["border_conflict_review"]
        review.update({
            "is_border_conflict": True,
            "related_to_monitored_section": True,
            "exception_reason": "事件直接涉及使用者監控板塊，解除預設 D 後依實際影響評級。",
        })
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_routine_ongoing_war_update_is_forced_to_d(self):
        item = candidate("B", "selected")
        review = item["grading_evidence"]["ongoing_conflict_review"]
        review.update({
            "is_ongoing_conflict": True, "same_conflict_as_history": True,
            "routine_incident": True, "continuity_discount_applied": False,
        })
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("長期戰爭的常態小衝突" in error for error in errors))

    def test_external_system_impact_can_remove_war_discount(self):
        item = candidate("B+", "selected")
        review = item["grading_evidence"]["ongoing_conflict_review"]
        review.update({
            "is_ongoing_conflict": True, "same_conflict_as_history": True,
            "routine_incident": False, "material_change": True,
            "change_types": ["external_system_impact"],
            "external_system_impact": True,
            "exception_reason": "主要航道通行量下降，油價與保險成本出現可驗證的異常上升。",
        })
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_ongoing_war_cannot_bypass_discount_by_marking_non_routine_only(self):
        item = candidate("B", "selected")
        review = item["grading_evidence"]["ongoing_conflict_review"]
        review.update({
            "is_ongoing_conflict": True, "same_conflict_as_history": True,
            "routine_incident": False, "change_types": ["material_escalation"],
            "exception_reason": "僅宣稱不是例行事件，但沒有任何實質變化證據。",
        })
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("未證明戰局" in error for error in errors))

    def test_b_minus_or_higher_requires_direct_consequence(self):
        item = candidate("B-", "selected")
        item["grading_evidence"]["direct_consequences"] = []
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("B- 以上" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
