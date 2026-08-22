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
sys.path.insert(0, str(ROOT / "scripts"))
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


REPRESENTATIVE_GRADE_SCORES = {
    "E": 10, "D": 30, "C-": 42, "C": 47, "C+": 52,
    "B-": 57, "B": 62, "B+": 67, "A-": 72, "A": 77,
    "A+": 82, "S-": 87, "S": 91, "S+": 95, "SS": 99,
}


def candidate(grade="C", decision="selected", reason_code="selected_threshold_met"):
    score = REPRESENTATIVE_GRADE_SCORES[grade]
    breakdown = importance_breakdown(score)
    return {
        "candidate_id": "c", "dedup_key": "c", "title": "測試", "section": "GLB",
        "provisional_grade": grade,
        "importance_score": score,
        "importance_breakdown": breakdown,
        "dimension_evidence": {
            key: f"{key} 具有候選事件的可核實證據。" for key in breakdown
        },
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
            "selected_for_pool_count": per_source_count,
            "selected_item_urls": [item["url"] for item in ranked_items],
            "mandatory_overflow_items": [],
            "ranking_completed": True, "ranking_method": "public_value_v1", "failure_reason": None,
            "scan_window_start": window_start, "scan_window_end": window_end,
            "scan_evidence_path": str(scan_path),
        })
    items = candidates if candidates is not None else [candidate()]
    all_urls = [url for item in coverage for url in item["selected_item_urls"]]
    for index, item in enumerate(items):
        item["semantic_event_id"] = f"semantic-event-{index + 1}"
        item["event_identity"] = {
            "who_or_what": item["title"],
            "what_happened": "發生一項可核實的新進展",
            "where": item["section"],
            "when": window_end,
            "country_codes": ["GLB"],
            "primary_country_code": "GLB",
            "location_evidence": "事件內容確認屬世界板塊，未使用來源媒體分桶。",
            "event_occurred_at": window_end,
            "material_update_at": window_end,
            "material_update_type": "new_event",
            "material_update_evidence": "本輪來源確認一項可獨立辨識的實質新進展。",
            "temporal_review": {
                "review_method": "model_content_comparison",
                "window_status": "new_event",
                "active_during_window": True,
                "new_or_changed_facts": ["本輪首次正式確認事件"],
                "repeated_old_facts": [],
                "current_window_impact": ["事件在本輪時間窗內發生"],
                "comparison_evidence": "模型比較事件內容與十四天時間線後確認為新事件。",
            },
            "semantic_merge_basis": "依主體、行動、地點與時間確認為同一事件",
        }
        item["candidate_urls"] = [all_urls[index]] if index < len(all_urls) else []
        item["source_ids"] = [all_urls[index].split("/")[3]] if index < len(all_urls) else []
    if items and len(all_urls) > len(items):
        items[0]["candidate_urls"].extend(all_urls[len(items):])
        items[0]["source_ids"] = sorted({url.split("/")[3] for url in items[0]["candidate_urls"]})
    event_by_url = {
        url: item["semantic_event_id"]
        for item in items
        for url in item["candidate_urls"]
    }
    article_dispositions = [
        {
            "source_id": coverage_item["source_id"],
            "url": url,
            "disposition": "event_evidence",
            "semantic_event_id": event_by_url[url],
            "reason": "文章內容已對應至語意事件",
        }
        for coverage_item in coverage
        for url in coverage_item["selected_item_urls"]
    ]
    now = window_end
    raw_count = len(coverage) * per_source_count
    c_or_higher = {
        "C", "C+", "B-", "B", "B+", "A-", "A", "A+", "S-", "S", "S+", "SS"
    }
    return {
        "schema_version": "1.1.0", "retention_days": 14, "updated_at": now,
        "runs": [{"run_id": "r", "generated_at": now, "window_start": window_start, "window_end": window_end,
                  "source_coverage": coverage,
                  "raw_item_count": raw_count,
                  "processing_counts": {
                      "merged_article_row_count": raw_count,
                      "in_window_article_row_count": raw_count,
                      "canonical_url_count": raw_count,
                      "provisional_title_cluster_count": raw_count,
                      "semantic_event_count": len(items),
                      "scored_event_count": len(items),
                      "event_evidence_article_row_count": raw_count,
                      "non_news_article_row_count": 0,
                      "unresolved_article_row_count": 0,
                      "c_or_higher_scored_event_count": sum(
                          item["provisional_grade"] in c_or_higher for item in items
                      ),
                      "selected_event_count": sum(
                          item["decision"] == "selected" for item in items
                      ),
                  },
                  "article_dispositions": article_dispositions,
                  "deduplicated_candidate_count": len(items), "candidates": items}],
    }


class CandidateAuditTests(unittest.TestCase):
    @staticmethod
    def add_structured_identity(audit, *, country="CHN", occurred=None,
                                updated=None, update_type="new_event"):
        run = audit["runs"][0]
        identity = run["candidates"][0]["event_identity"]
        identity.update({
            "country_codes": [country],
            "primary_country_code": country,
            "location_evidence": f"事件發生地由內容確認為 {country}，未使用來源媒體分桶。",
            "event_occurred_at": occurred or run["window_end"],
            "material_update_at": updated or run["window_end"],
            "material_update_type": update_type,
            "material_update_evidence": "本輪來源確認一項可獨立辨識的實質新進展。",
        })
        if update_type == "new_event":
            window_status = "new_event"
            new_facts = ["本輪首次發生事件"]
            current_impact = ["事件在本輪時間窗內發生"]
            active = True
        elif update_type == "ongoing_verified_current_impact":
            window_status = "ongoing_current_impact"
            new_facts = []
            current_impact = ["事件在本輪時間窗內仍持續造成影響"]
            active = True
        else:
            window_status = "material_update"
            new_facts = ["本輪首次確認一項實質變更"]
            current_impact = []
            active = False
        identity["temporal_review"] = {
            "review_method": "model_content_comparison",
            "window_status": window_status,
            "active_during_window": active,
            "new_or_changed_facts": new_facts,
            "repeated_old_facts": [],
            "current_window_impact": current_impact,
            "comparison_evidence": "模型已比較事件內容、既有時間線與本輪事實。",
        }
        return run, identity

    def test_china_event_from_taiwan_publisher_is_classified_by_event_location(self):
        audit = valid_audit()
        run, _ = self.add_structured_identity(audit, country="CHN")
        run["candidates"][0]["section"] = "CHN"
        run["candidates"][0]["source_ids"] = ["cna"]
        self.assertEqual([], MODULE.validate(audit, source_pool()))

    def test_event_section_must_match_structured_primary_country(self):
        audit = valid_audit()
        run, _ = self.add_structured_identity(audit, country="CHN")
        run["candidates"][0]["section"] = "TWN"
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("section 必須由 event_identity.primary_country_code" in error for error in errors))

    def test_non_taiwan_non_china_event_maps_to_world(self):
        audit = valid_audit()
        run, _ = self.add_structured_identity(audit, country="KOR")
        run["candidates"][0]["section"] = "GLB"
        self.assertEqual([], MODULE.validate(audit, source_pool()))

    def test_material_update_time_must_be_inside_exact_run_window(self):
        audit = valid_audit()
        self.add_structured_identity(
            audit, country="CHN", updated="2026-08-12T20:59:59+00:00"
        )
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("material_update_at 必須落在精確執行時間窗內" in error for error in errors))

    def test_old_event_recap_cannot_claim_new_event(self):
        audit = valid_audit()
        run, _ = self.add_structured_identity(
            audit,
            country="CHN",
            occurred="2026-07-01T00:00:00+08:00",
            update_type="new_event",
        )
        run["candidates"][0]["section"] = "CHN"
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("舊事件不得以 new_event" in error for error in errors))

    def test_old_event_with_in_window_material_update_can_continue(self):
        audit = valid_audit()
        run, _ = self.add_structured_identity(
            audit,
            country="CHN",
            occurred="2026-07-01T00:00:00+08:00",
            update_type="official_confirmation",
        )
        run["candidates"][0]["section"] = "CHN"
        run["candidates"][0]["continuity"]["status"] = "continuing"
        self.assertEqual([], MODULE.validate(audit, source_pool()))

    def test_latest_event_requires_model_content_temporal_review(self):
        audit = valid_audit()
        del audit["runs"][0]["candidates"][0]["event_identity"]["temporal_review"]
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("temporal_review 必須由模型比較事件內容" in error for error in errors))

    def test_month_long_active_event_can_remain_a_candidate(self):
        audit = valid_audit()
        run, identity = self.add_structured_identity(
            audit,
            country="CHN",
            occurred="2026-07-15T00:00:00+08:00",
            update_type="ongoing_verified_current_impact",
        )
        run["candidates"][0]["section"] = "CHN"
        run["candidates"][0]["continuity"]["status"] = "continuing"
        identity["temporal_review"] = {
            "review_method": "model_content_comparison",
            "window_status": "ongoing_current_impact",
            "active_during_window": True,
            "new_or_changed_facts": [],
            "repeated_old_facts": ["事件於七月開始"],
            "current_window_impact": ["本時間窗仍有可驗證的撤離與交通中斷"],
            "comparison_evidence": "模型比較內文時序後確認影響持續跨越本輪時間窗。",
        }
        self.assertEqual([], MODULE.validate(audit, source_pool()))

    def test_ended_event_with_only_repeated_casualty_data_is_not_a_candidate(self):
        audit = valid_audit()
        run, identity = self.add_structured_identity(
            audit,
            country="CHN",
            occurred="2026-07-01T00:00:00+08:00",
            update_type="official_confirmation",
        )
        run["candidates"][0]["section"] = "CHN"
        run["candidates"][0]["continuity"]["status"] = "continuing"
        identity["temporal_review"] = {
            "review_method": "model_content_comparison",
            "window_status": "old_restatement",
            "active_during_window": False,
            "new_or_changed_facts": [],
            "repeated_old_facts": ["159 人死亡是七月既有數據"],
            "current_window_impact": [],
            "comparison_evidence": "模型比較文章與既有時間線後，未發現本輪新數據。",
        }
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("old_restatement 不得成為語意事件候選" in error for error in errors))

    def test_ended_event_material_update_requires_a_new_or_changed_fact(self):
        audit = valid_audit()
        run, identity = self.add_structured_identity(
            audit,
            country="CHN",
            occurred="2026-07-01T00:00:00+08:00",
            update_type="casualty_or_impact_revision",
        )
        run["candidates"][0]["section"] = "CHN"
        run["candidates"][0]["continuity"]["status"] = "continuing"
        identity["temporal_review"] = {
            "review_method": "model_content_comparison",
            "window_status": "material_update",
            "active_during_window": False,
            "new_or_changed_facts": [],
            "repeated_old_facts": ["文章重複舊傷亡總數"],
            "current_window_impact": [],
            "comparison_evidence": "未找到數據首次公布或修正的證據。",
        }
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("material_update 必須列出本輪新增或變更事實" in error for error in errors))

    def test_non_news_article_is_accounted_without_becoming_a_news_candidate(self):
        audit = valid_audit()
        run = audit["runs"][0]
        disposition = run["article_dispositions"][-1]
        removed_url = disposition["url"]
        disposition.update({
            "disposition": "non_news",
            "semantic_event_id": None,
            "reason": "頁面是導覽索引，不包含可辨識的新聞事件",
        })
        run["candidates"][0]["candidate_urls"].remove(removed_url)
        run["processing_counts"]["event_evidence_article_row_count"] -= 1
        run["processing_counts"]["non_news_article_row_count"] += 1
        self.assertEqual([], MODULE.validate(audit, source_pool()))

    def test_unresolved_article_cannot_complete_semantic_event_audit(self):
        audit = valid_audit()
        audit["runs"][0]["article_dispositions"][0].update({
            "disposition": "unresolved",
            "semantic_event_id": None,
            "reason": "內容解析失敗",
        })
        audit["runs"][0]["processing_counts"]["event_evidence_article_row_count"] -= 1
        audit["runs"][0]["processing_counts"]["unresolved_article_row_count"] += 1
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("unresolved" in error for error in errors))

    def test_latest_candidate_requires_unique_semantic_event_identity(self):
        missing = valid_audit()
        del missing["runs"][0]["candidates"][0]["event_identity"]
        errors = MODULE.validate(missing, source_pool())
        self.assertTrue(any("event_identity" in error for error in errors))

        duplicate = valid_audit([candidate(), candidate()])
        duplicate["runs"][0]["candidates"][1]["semantic_event_id"] = (
            duplicate["runs"][0]["candidates"][0]["semantic_event_id"]
        )
        errors = MODULE.validate(duplicate, source_pool())
        self.assertTrue(any("semantic_event_id" in error for error in errors))

    def test_latest_run_requires_conserved_processing_counts(self):
        missing = valid_audit()
        del missing["runs"][0]["processing_counts"]
        self.assertTrue(any(
            "processing_counts" in error for error in MODULE.validate(missing, source_pool())
        ))

        mismatched = valid_audit()
        mismatched["runs"][0]["processing_counts"]["semantic_event_count"] += 1
        self.assertTrue(any(
            "semantic_event_count" in error
            for error in MODULE.validate(mismatched, source_pool())
        ))

    def test_chongqing_mayor_scores_d_from_all_six_dimensions(self):
        breakdown = {
            "public_impact": 4,
            "geographic_or_population_scope": 3,
            "urgency_and_safety": 1,
            "structural_or_policy_significance": 3,
            "material_new_development": 8,
            "core_section_relevance": 6,
        }
        self.assertEqual("D", MODULE.grade_from_importance_breakdown(breakdown))

    def test_taiwan_three_county_event_can_score_c_without_a_hard_gate(self):
        breakdown = {
            "public_impact": 12,
            "geographic_or_population_scope": 9,
            "urgency_and_safety": 5,
            "structural_or_policy_significance": 7,
            "material_new_development": 8,
            "core_section_relevance": 6,
        }
        self.assertEqual("C", MODULE.grade_from_importance_breakdown(breakdown))

    def test_four_country_event_can_score_b_from_combined_evidence(self):
        breakdown = {
            "public_impact": 15,
            "geographic_or_population_scope": 13,
            "urgency_and_safety": 8,
            "structural_or_policy_significance": 10,
            "material_new_development": 9,
            "core_section_relevance": 7,
        }
        self.assertEqual("B", MODULE.grade_from_importance_breakdown(breakdown))

    def test_severe_single_area_events_rise_by_total_score_not_exceptions(self):
        scenarios = (
            ("C", {"public_impact": 19, "geographic_or_population_scope": 7, "urgency_and_safety": 9, "structural_or_policy_significance": 3, "material_new_development": 7, "core_section_relevance": 3}),
            ("B", {"public_impact": 24, "geographic_or_population_scope": 9, "urgency_and_safety": 11, "structural_or_policy_significance": 10, "material_new_development": 6, "core_section_relevance": 2}),
            ("A", {"public_impact": 27, "geographic_or_population_scope": 8, "urgency_and_safety": 10, "structural_or_policy_significance": 15, "material_new_development": 9, "core_section_relevance": 8}),
            ("S-", {"public_impact": 30, "geographic_or_population_scope": 10, "urgency_and_safety": 15, "structural_or_policy_significance": 14, "material_new_development": 10, "core_section_relevance": 8}),
        )
        for expected_grade, breakdown in scenarios:
            with self.subTest(expected_grade=expected_grade):
                self.assertEqual(
                    expected_grade,
                    MODULE.grade_from_importance_breakdown(breakdown),
                )

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
        run["processing_counts"]["merged_article_row_count"] = 1
        run["processing_counts"]["in_window_article_row_count"] = 1
        run["processing_counts"]["canonical_url_count"] = 1
        run["processing_counts"]["provisional_title_cluster_count"] = 1
        run["processing_counts"]["event_evidence_article_row_count"] = 1
        run["processing_counts"]["non_news_article_row_count"] = 0
        run["processing_counts"]["unresolved_article_row_count"] = 0
        run["article_dispositions"] = [
            item for item in run["article_dispositions"]
            if item["source_id"] == "cna"
        ]
        run["candidates"][0]["candidate_urls"] = [only_url]
        run["candidates"][0]["source_ids"] = ["cna"]
        self.assertEqual([], MODULE.validate(audit, pool))

    def test_local_disaster_death_count_is_evidence_not_a_grade_gate(self):
        item = candidate("C", "selected")
        item["grading_evidence"]["impact_scope_level"] = "local"
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 49,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_casualty_bands_integrate_with_urgency_and_other_dimensions(self):
        scenarios = (
            (49, 14, "D", {"public_impact": 14, "geographic_or_population_scope": 5, "urgency_and_safety": 5, "structural_or_policy_significance": 2, "material_new_development": 8, "core_section_relevance": 4}),
            (50, 18, "C", {"public_impact": 18, "geographic_or_population_scope": 6, "urgency_and_safety": 8, "structural_or_policy_significance": 3, "material_new_development": 8, "core_section_relevance": 4}),
            (100, 23, "B", {"public_impact": 23, "geographic_or_population_scope": 7, "urgency_and_safety": 11, "structural_or_policy_significance": 5, "material_new_development": 9, "core_section_relevance": 5}),
            (250, 27, "A-", {"public_impact": 27, "geographic_or_population_scope": 10, "urgency_and_safety": 13, "structural_or_policy_significance": 8, "material_new_development": 9, "core_section_relevance": 5}),
            (2500, 30, "A", {"public_impact": 30, "geographic_or_population_scope": 11, "urgency_and_safety": 14, "structural_or_policy_significance": 8, "material_new_development": 9, "core_section_relevance": 5}),
        )
        for deaths, expected_floor, expected_grade, breakdown in scenarios:
            with self.subTest(deaths=deaths):
                self.assertEqual(
                    expected_floor,
                    MODULE.public_impact_floor_from_confirmed_deaths(deaths),
                )
                self.assertEqual(
                    expected_grade,
                    MODULE.grade_from_importance_breakdown(breakdown),
                )

        item = candidate("B", "selected")
        item["grading_evidence"]["local_disaster_review"] = {
            "applies": True,
            "confirmed_deaths": 100,
            "special_significance_triggers": [],
            "grade_adjustment_reason": None,
        }
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("死亡證據最低" in error for error in errors))

    def test_verified_special_meaning_can_raise_grade_with_reason(self):
        item = candidate("B+", "selected")
        item["importance_breakdown"] = {
            "public_impact": 23,
            "geographic_or_population_scope": 12,
            "urgency_and_safety": 10,
            "structural_or_policy_significance": 10,
            "material_new_development": 7,
            "core_section_relevance": 5,
        }
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

        audit = valid_audit()
        audit["runs"][0]["candidates"][0].pop("dimension_evidence")
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("dimension_evidence" in error for error in errors))

    def test_major_scores_must_match_weights_and_total(self):
        audit = valid_audit()
        ranked = audit["runs"][0]["source_coverage"][0]["ranked_items"][0]
        ranked["importance_breakdown"]["public_impact"] = 31
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("大項分數" in error for error in errors))
        self.assertTrue(any("importance_score" in error for error in errors))

        item = candidate("D", "excluded", "below_public_value_threshold")
        item["importance_score"] = 97
        item["importance_breakdown"] = importance_breakdown(97)
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("六項總分" in error for error in errors))

    def test_integrated_grade_bands_and_no_hard_cap_policy_are_locked(self):
        pool = source_pool()
        ranking = pool["ranking"]
        self.assertEqual(
            {
                "E": 0, "D": 20, "C-": 40, "C": 45, "C+": 50,
                "B-": 55, "B": 60, "B+": 65, "A-": 70, "A": 75,
                "A+": 80, "S-": 85, "S": 90, "S+": 94, "SS": 97,
            },
            ranking.get("grade_minimum_scores"),
        )
        self.assertEqual(
            {
                "combined_evidence_no_single_dimension_hard_cap": True,
                "importance_severity_is_public_impact": True,
                "scope_is_one_weighted_dimension": True,
            },
            ranking.get("grading_principles"),
        )
        self.assertEqual(
            {"1-9": 8, "10-49": 14, "50-99": 18, "100-249": 23, "250-2499": 27, "2500+": 30},
            ranking.get("casualty_public_impact_floors"),
        )
        self.assertEqual(
            [
                {"score_range": [0, 3], "meaning": "danger ended or no immediate public action required"},
                {"score_range": [4, 7], "meaning": "active local response or bounded safety concern"},
                {"score_range": [8, 11], "meaning": "continuing major danger, rescue window, or stressed essential services"},
                {"score_range": [12, 15], "meaning": "expanding or uncontrolled threat requiring immediate broad action"},
            ],
            ranking.get("dimension_anchors", {}).get("urgency_and_safety"),
        )

        ranking["grade_minimum_scores"]["C"] = 50
        errors = MODULE.validate(valid_audit(), pool)
        self.assertTrue(any("grade_minimum_scores" in error for error in errors))

        schema = MODULE.load(ROOT / "schemas" / "news-candidate-audit.schema.json")
        candidate_properties = schema["$defs"]["candidate"]["properties"]
        self.assertIn("importance_score", candidate_properties)
        self.assertIn("importance_breakdown", candidate_properties)
        self.assertIn("dimension_evidence", candidate_properties)

    def test_c_or_above_merged_candidate_requires_reader_event_mapping(self):
        item = candidate("C", "merged", "duplicate_merged")
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("selected_event_id" in error for error in errors))

    def test_cultural_suspension_novelty_rule_is_locked(self):
        pool = source_pool()
        pool["cultural_industry_event_rule"]["first_large_award_suspension_min_grade"] = "C-"
        errors = MODULE.validate(valid_audit(), pool)
        self.assertTrue(any("首次停辦最低為 C" in error for error in errors))

    def test_all_configured_sources_send_every_ranked_item_to_pool(self):
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

    def test_source_cannot_submit_fewer_than_its_complete_ranked_list(self):
        audit = valid_audit(per_source_count=73)
        audit["runs"][0]["source_coverage"][0]["selected_for_pool_count"] = 72
        audit["runs"][0]["source_coverage"][0]["selected_item_urls"].pop()
        audit["runs"][0]["raw_item_count"] -= 1
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("完整排序清單" in error for error in errors))

    def test_fixed_limit_overflow_list_is_rejected_as_obsolete(self):
        audit = valid_audit(per_source_count=35)
        source = audit["runs"][0]["source_coverage"][0]
        source["mandatory_overflow_items"] = [{
            "url": source["ranked_items"][32]["url"],
            "trigger": "major_disaster",
            "reason": "固定名額已取消，不應再需要溢位例外。",
        }]
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("不得再使用強制溢位" in error for error in errors))

    def test_every_source_item_must_reach_a_deduplicated_candidate(self):
        audit = valid_audit()
        audit["runs"][0]["candidates"][0]["candidate_urls"].pop()
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("candidate_urls 必須精確等於 event_evidence 網址" in error for error in errors))

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
