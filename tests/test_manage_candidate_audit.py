import importlib.util
import hashlib
import json
import copy
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
    return {key: score for key in source_pool()["ranking"]["dimensions"]}


REPRESENTATIVE_GRADE_SCORES = {
    "E": 10, "D": 30, "C-": 40, "C": 45, "C+": 50,
    "B-": 55, "B": 60, "B+": 65, "A-": 70, "A": 75,
    "A+": 80, "S-": 85, "S": 90, "S+": 95, "SS": 100,
}


def candidate(grade="C", decision="selected", reason_code="selected_threshold_met"):
    score = REPRESENTATIVE_GRADE_SCORES[grade]
    breakdown = importance_breakdown(score)
    return {
        "candidate_id": "c", "dedup_key": "c", "title": "測試", "section": "GLB",
        "scoring_method": "public_value_v2",
        "weighted_score": score,
        "provisional_grade": grade,
        "importance_score": score,
        "importance_breakdown": breakdown,
        "dimension_evidence": {
            key: [f"F{index:02d}"]
            for index, key in enumerate(breakdown, 1)
        },
        "consequence_evidence": {
            "realized": ["F01", "F05", "F06"],
            "ongoing": ["F02", "F03"],
            "potential": ["F04"],
            "speculative": [],
        },
        "evidence_facts": [
            {"fact_id": "F01", "fact": "已發生可驗證的公共後果", "fact_type": "public_consequence", "consequence_class": "realized", "confidence": 90, "source_urls": ["https://example.com/f01"], "institutional_mechanism": None},
            {"fact_id": "F02", "fact": "直接影響範圍仍在持續", "fact_type": "directly_affected_scope", "consequence_class": "ongoing", "confidence": 90, "source_urls": ["https://example.com/f02"], "institutional_mechanism": None},
            {"fact_id": "F03", "fact": "目前仍需採取安全行動", "fact_type": "safety_condition", "consequence_class": "ongoing", "confidence": 90, "source_urls": ["https://example.com/f03"], "institutional_mechanism": None},
            {"fact_id": "F04", "fact": "存在具體且高可信的制度機制", "fact_type": "institutional_change", "consequence_class": "potential", "confidence": 90, "source_urls": ["https://example.com/f04"], "institutional_mechanism": "正式制度程序已啟動"},
            {"fact_id": "F05", "fact": "相較十四天紀錄出現新節點", "fact_type": "material_delta", "consequence_class": "realized", "confidence": 90, "source_urls": ["https://example.com/f05"], "institutional_mechanism": None},
            {"fact_id": "F06", "fact": "事件直接涉及板塊核心公共議題", "fact_type": "section_centrality", "consequence_class": "realized", "confidence": 90, "source_urls": ["https://example.com/f06"], "institutional_mechanism": None},
        ],
        "policy_stage": "not_applicable",
        "delta_facts": [{"fact_id": "F05", "previous_state": "尚未出現此節點", "current_state": "本輪正式出現此節點", "why_material": "狀態已實質改變"}],
        "high_score_challenges": [
            {"dimension": key, "claim": f"{key} 達到高分", "counter_question": "哪些已發生事實足以支持此分數？", "supporting_facts": [f"F{index:02d}"], "outcome": "sustained", "rationale": "引用的合格事實足以維持此分數"}
            for index, key in enumerate(breakdown, 1)
        ] if score >= 70 else [],
        "overall_high_score_challenge": {
            "dimension": "overall", "claim": "總分達到 A- 或以上", "counter_question": "相較 B+ 多出哪些具體後果？", "supporting_facts": ["F01", "F05"], "outcome": "sustained", "rationale": "已發生後果與本期增量共同支持 A-"
        } if score >= 70 else None,
        "cross_dimension_rationales": [],
        "midpoint_rationales": [
            {"dimension": key, "lower_anchor": score - 5, "upper_anchor": score + 5, "supporting_facts": [f"F{index:02d}"], "rationale": "證據強度確實介於相鄰十分錨點之間"}
            for index, key in enumerate(breakdown, 1)
        ] if score % 10 == 5 else [],
        "evidence_confidence": 85,
        "confidence_band": "high",
        "grade_status": "validated",
        "grade_reason": "本期出現可驗證的新制度變化，影響範圍與直接後果符合目前級距。",
        "grading_evidence": grading_evidence(grade),
        "decision": decision, "reason_code": reason_code, "reason": "決定理由",
        "selected_event_id": "GLB-01" if decision == "selected" else None,
        "candidate_urls": ["https://example.com/evidence"], "source_ids": ["gdelt"],
        "source_audit": {"reliable_source_count": 2},
        "continuity": {"status": "new", "material_changes": [], "unchanged_elements": [], "comparison_note": "首次"},
    }


def grading_evidence(grade="C"):
    return {
        "impact_scope_level": "national",
        "direct_consequences": ["已造成可驗證的公共服務變化"] if grade not in {"C", "C-", "D", "E"} else [],
        "structural_significance": "形成可追蹤的制度或公共風險訊號",
        "window_material_changes": ["本期首次正式確認事件"],
        "policy_governance_review": policy_governance_review(),
        "local_disaster_review": {"applies": False},
        "border_conflict_review": {
            "applies": False,
            "is_border_conflict": False, "formal_war": False,
            "de_facto_war_scale": False, "related_to_monitored_section": False,
            "user_weight_elevated": False,
            "exception_reason": None,
        },
        "ongoing_conflict_review": {
            "applies": False,
            "is_ongoing_conflict": False, "same_conflict_as_history": False,
            "routine_incident": False, "material_change": False,
            "change_types": [], "reversal_or_escalation_possible": False,
            "external_system_impact": False, "continuity_discount_applied": False,
            "exception_reason": None,
        },
    }


def policy_governance_review(applies=False):
    if not applies:
        return {"applies": False}
    return {
        "applies": True,
        "triggered_by": [
            "official_legal_interpretation",
            "investigation_or_enforcement_referral",
            "platform_or_operator_action",
            "multi_agency_coordination",
            "precedent_or_spillover_risk",
        ],
        "legal_basis": ["主管機關引用現行法律條文並說明適用範圍。"],
        "official_actions": ["主管機關移交調查並要求業者採取合規措施。"],
        "direct_operational_effects": ["多個業者實際下架或修改內容。"],
        "affected_actor_classes": ["全國性內容平台", "境外影視內容提供者"],
        "cross_agency_effects": ["兩個以上中央主管機關共同監督。"],
        "precedent_or_spillover_scope": ["同一解釋可能適用其他平台及相似內容。"],
        "window_material_effects": ["時間窗內平台處置仍生效且主管機關持續執行。"],
        "evidence_urls": ["https://example.com/official-policy-record"],
        "unverified_allegations": [],
        "unverified_allegations_separated": True,
        "score_consistency_review": {
            "public_impact_alignment": "consistent",
            "scope_alignment": "consistent",
            "structural_alignment": "consistent",
            "window_alignment": "consistent",
            "contradiction_reasons": [],
            "why_not_b": "直接影響仍限於特定內容類型，尚未形成更廣泛權利或市場後果。",
            "review_outcome": "consistent",
        },
    }


def valid_audit(candidates=None, per_source_count=1):
    evidence_root = Path(tempfile.mkdtemp(prefix="source-scan-test-"))
    window_start = "2026-08-13T06:00:00+08:00"
    window_end = "2026-08-14T06:00:00+08:00"
    coverage = []
    for item in source_pool()["discovery_sources"]:
        source_id = item["source_id"]
        ranked_items = [
            {"url": f"https://example.com/{source_id}/{index}", "title": f"{source_id}-{index}",
             "published_at": "2026-08-13T05:00:00+00:00", "discovery_priority_score": 50,
             "discovery_signals": {"policy": True},
             "discovery_priority_reason": "依 discovery 訊號安排補齊順序"}
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
            "coverage_complete": True, "coverage_status": "complete",
            "coverage_reason": None, "missing_segments": [], "missing_date_variants": [],
            "pages": [{"request_url": item["homepage"], "fetched_at": window_end, "http_status": 200, "snapshot_path": str(snapshot_path), "sha256": hashlib.sha256(snapshot_text.encode()).hexdigest(), "next_url": None, "extracted_items": extracted}],
            "terminal_proof": {"type": "crossed_window_start", "page_index": 1, "witness_url": old_url},
        }
        scan_path = evidence_root / f"{source_id}.json"
        scan_path.write_text(json.dumps(scan), encoding="utf-8")
        coverage.append({
            "source_id": source_id, "scan_status": "completed",
            "coverage_complete": True, "coverage_status": "complete",
            "coverage_reason": None, "missing_segments": [], "missing_date_variants": [],
            "within_window_count": per_source_count, "ranked_count": per_source_count,
            "ranked_items": ranked_items,
            "selected_for_pool_count": per_source_count,
            "selected_item_urls": [item["url"] for item in ranked_items],
            "discovery_ranking_completed": True,
            "discovery_ranking_method": "discovery_priority_v1", "failure_reason": None,
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
        "schema_version": "1.2.0", "retention_days": 14, "updated_at": now,
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
    def test_historical_mobile_compact_v2_candidate_can_rejoin_full_runtime(self):
        audit = valid_audit()
        historical = copy.deepcopy(audit["runs"][0])
        historical["run_id"] = "historical-mobile-compact"
        historical["generated_at"] = "2026-08-13T06:00:00+08:00"
        for item in historical["candidates"]:
            item["event_date"] = "2026-08-13"
            for field in (
                "grading_evidence",
                "source_audit",
                "candidate_urls",
                "reason_code",
                "grade_reason",
            ):
                item.pop(field, None)
        audit["runs"].insert(0, historical)

        self.assertEqual([], MODULE.validate(audit, source_pool()))

    def test_latest_run_cannot_use_mobile_compact_history_profile(self):
        audit = valid_audit()
        item = audit["runs"][-1]["candidates"][0]
        item["event_date"] = "2026-08-14"
        for field in (
            "grading_evidence",
            "source_audit",
            "candidate_urls",
            "reason_code",
            "grade_reason",
        ):
            item.pop(field, None)

        errors = MODULE.validate(audit, source_pool())

        self.assertTrue(any("grading_evidence" in error for error in errors))
        self.assertTrue(any("缺少原始入池網址" in error for error in errors))

    def test_every_retained_run_requires_the_current_discovery_ranking_method(self):
        audit = valid_audit()
        historical = copy.deepcopy(audit["runs"][0])
        historical["run_id"] = "historical-old-method"
        historical["generated_at"] = "2026-08-13T06:00:00+08:00"
        old_method = "_".join(("public", "value", "v1"))
        for coverage in historical["source_coverage"]:
            coverage["discovery_ranking_method"] = old_method
            coverage.pop("scan_window_start", None)
            coverage.pop("scan_window_end", None)
            coverage.pop("scan_evidence_path", None)
        audit["runs"].insert(0, historical)

        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("discovery_ranking_method" in error for error in errors))

    def test_grading_regression_cases_stay_in_calibrated_ranges(self):
        fixture = json.loads(
            (ROOT / "tests/fixtures/grading-cases.json").read_text(encoding="utf-8")
        )
        self.assertEqual("public_value_v2", fixture["scoring_method"])
        self.assertEqual(6, len(fixture["cases"]))
        for case in fixture["cases"]:
            with self.subTest(case_id=case["case_id"]):
                score = MODULE.weighted_score(
                    case["importance_breakdown"], source_pool()["ranking"]
                )
                self.assertGreaterEqual(score, case["expected_score_range"][0])
                self.assertLessEqual(score, case["expected_score_range"][1])
                self.assertIn(
                    MODULE.grade_from_importance_score(score),
                    case["expected_grades"],
                )

    def test_policy_proposal_may_have_no_direct_operational_effect(self):
        item = candidate("C+")
        item["policy_stage"] = "proposal"
        review = policy_governance_review(applies=True)
        review["direct_operational_effects"] = []
        review["triggered_by"] = ["official_legal_interpretation"]
        review["cross_agency_effects"] = []
        review["precedent_or_spillover_scope"] = []
        item["grading_evidence"]["policy_governance_review"] = review

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertFalse(any("direct_operational_effects" in error for error in errors))

    def test_non_conflict_candidate_uses_minimal_nonapplicable_reviews(self):
        item = candidate("C+")
        item["grading_evidence"]["border_conflict_review"] = {"applies": False}
        item["grading_evidence"]["ongoing_conflict_review"] = {"applies": False}

        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_applicable_conflict_review_requires_its_detail_fields(self):
        item = candidate("B")
        item["grading_evidence"]["border_conflict_review"]["applies"] = True
        item["grading_evidence"]["border_conflict_review"].pop("formal_war")

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("border_conflict_review" in error and "不完整" in error for error in errors))

    def test_v2_weighted_score_uses_configured_weights(self):
        scores = {
            "public_impact": 30,
            "geographic_or_population_scope": 30,
            "urgency_and_safety": 20,
            "structural_or_policy_significance": 80,
            "material_new_development": 60,
            "core_section_relevance": 50,
        }

        self.assertEqual(
            41.0,
            MODULE.weighted_score(scores, source_pool()["ranking"]),
        )

    def test_zero_score_dimension_may_have_no_fact_ids(self):
        item = candidate("C")
        item["importance_breakdown"]["urgency_and_safety"] = 0
        item["dimension_evidence"]["urgency_and_safety"] = []
        self.sync_score(item)

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertFalse(any("urgency_and_safety 必須是非空" in error for error in errors))

    def test_grade_casualty_and_confidence_authority_is_runtime_config(self):
        pool = source_pool()
        ranking = copy.deepcopy(pool["ranking"])
        ranking["grade_minimum_scores"]["B"] = 61
        ranking["confidence_bands"]["high"] = [90, 100]
        ranking["confidence_bands"]["medium"] = [60, 89]
        ranking["casualty_public_impact_floors"]["100-249"] = 70

        self.assertEqual("B-", MODULE.grade_from_importance_score(60, ranking))
        self.assertEqual("medium", MODULE.confidence_band(85, ranking))
        self.assertEqual(70, MODULE.public_impact_floor_from_confirmed_deaths(100, ranking))

    @staticmethod
    def sync_score(item):
        score = MODULE.weighted_score(
            item["importance_breakdown"], source_pool()["ranking"]
        )
        item["weighted_score"] = score
        item["importance_score"] = score
        item["provisional_grade"] = MODULE.grade_from_importance_score(score)

    def test_v2_scores_must_use_five_point_steps(self):
        item = candidate("C")
        item["importance_breakdown"]["public_impact"] = 43
        item["weighted_score"] = 44.4
        item["importance_score"] = 44.4
        item["provisional_grade"] = "C-"

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("5" in error and "public_impact" in error for error in errors))

    def test_five_point_midpoint_requires_between_anchor_rationale(self):
        item = candidate("C")
        item["midpoint_rationales"] = []

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("midpoint_rationale" in error for error in errors))

    def test_potential_fact_cannot_support_actual_impact_scope_or_urgency(self):
        item = candidate("C")
        item["evidence_facts"][0]["consequence_class"] = "potential"
        item["consequence_evidence"]["realized"].remove("F01")
        item["consequence_evidence"]["potential"].append("F01")

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(
            any("potential" in error and "public_impact" in error for error in errors)
        )

    def test_speculative_fact_cannot_support_any_dimension(self):
        item = candidate("C")
        item["evidence_facts"][3]["consequence_class"] = "speculative"
        item["consequence_evidence"]["potential"].remove("F04")
        item["consequence_evidence"]["speculative"].append("F04")

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("speculative" in error for error in errors))

    def test_material_update_at_seventy_requires_delta_fact(self):
        item = candidate("C")
        item["importance_breakdown"]["material_new_development"] = 70
        item["delta_facts"] = []
        self.sync_score(item)

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("delta_fact" in error for error in errors))

    def test_fact_reused_by_three_dimensions_requires_rationale(self):
        item = candidate("C")
        for dimension in (
            "public_impact",
            "geographic_or_population_scope",
            "urgency_and_safety",
        ):
            item["dimension_evidence"][dimension] = ["F01"]

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("cross_dimension" in error for error in errors))

    def test_dimension_at_seventy_requires_sustained_challenge(self):
        item = candidate("C")
        item["importance_breakdown"]["public_impact"] = 70
        self.sync_score(item)

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("high_score_challenge" in error for error in errors))

    def test_total_at_seventy_requires_overall_challenge(self):
        item = candidate("A-")
        item["overall_high_score_challenge"] = None

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("overall_high_score_challenge" in error for error in errors))

    def test_confidence_band_mismatch_does_not_change_importance(self):
        item = candidate("C")
        original_score = item["importance_score"]
        item["evidence_confidence"] = 79

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("confidence_band" in error for error in errors))
        self.assertEqual(original_score, item["importance_score"])

    def test_selected_provisional_candidate_is_rejected(self):
        item = candidate("C")
        item["grade_status"] = "provisional"

        errors = MODULE.validate(valid_audit([item]), source_pool())

        self.assertTrue(any("grade_status=validated" in error for error in errors))

    def test_policy_proposal_can_keep_high_impact_with_realized_evidence(self):
        item = candidate("A-")
        item["policy_stage"] = "proposal"
        item["grading_evidence"]["policy_governance_review"] = policy_governance_review(True)

        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_fourteen_day_completeness_rejects_an_empty_audit_baseline(self):
        audit = {
            "schema_version": "1.2.0",
            "retention_days": 14,
            "updated_at": "2026-08-22T06:00:00+08:00",
            "runs": [],
        }

        errors = MODULE.validate(
            audit, source_pool(), require_fourteen_day_complete=True
        )

        self.assertTrue(any("十四天" in error and "空" in error for error in errors))

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
            "public_impact": 20,
            "geographic_or_population_scope": 20,
            "urgency_and_safety": 0,
            "structural_or_policy_significance": 20,
            "material_new_development": 60,
            "core_section_relevance": 40,
        }
        self.assertEqual("D", MODULE.grade_from_importance_breakdown(breakdown))

    def test_taiwan_three_county_event_can_score_c_without_a_hard_gate(self):
        breakdown = {
            "public_impact": 45,
            "geographic_or_population_scope": 50,
            "urgency_and_safety": 30,
            "structural_or_policy_significance": 45,
            "material_new_development": 65,
            "core_section_relevance": 50,
        }
        self.assertEqual("C", MODULE.grade_from_importance_breakdown(breakdown))

    def test_four_country_event_can_score_b_from_combined_evidence(self):
        breakdown = {
            "public_impact": 55,
            "geographic_or_population_scope": 70,
            "urgency_and_safety": 50,
            "structural_or_policy_significance": 65,
            "material_new_development": 75,
            "core_section_relevance": 65,
        }
        self.assertEqual("B", MODULE.grade_from_importance_breakdown(breakdown))

    def test_severe_single_area_events_rise_by_total_score_not_exceptions(self):
        scenarios = (
            ("C", {"public_impact": 60, "geographic_or_population_scope": 35, "urgency_and_safety": 55, "structural_or_policy_significance": 25, "material_new_development": 50, "core_section_relevance": 30}),
            ("B", {"public_impact": 80, "geographic_or_population_scope": 45, "urgency_and_safety": 75, "structural_or_policy_significance": 55, "material_new_development": 55, "core_section_relevance": 35}),
            ("A", {"public_impact": 90, "geographic_or_population_scope": 40, "urgency_and_safety": 70, "structural_or_policy_significance": 100, "material_new_development": 80, "core_section_relevance": 65}),
            ("S-", {"public_impact": 100, "geographic_or_population_scope": 50, "urgency_and_safety": 100, "structural_or_policy_significance": 95, "material_new_development": 100, "core_section_relevance": 80}),
        )
        for expected_grade, breakdown in scenarios:
            with self.subTest(expected_grade=expected_grade):
                self.assertEqual(
                    expected_grade,
                    MODULE.grade_from_importance_breakdown(breakdown),
                )

    def test_degraded_discovery_coverage_accepts_one_ready_source(self):
        pool = source_pool()
        pool["discovery_policy"] = {
            "minimum_ready_sources": 1,
            "source_failure_policy": "degrade_not_block",
        }
        audit = valid_audit()
        run = audit["runs"][0]
        only_url = next(
            item["selected_item_urls"][0]
            for item in run["source_coverage"] if item["source_id"] == "cna"
        )
        for item in run["source_coverage"]:
            if item["source_id"] == "cna":
                continue
            item.update({
                "scan_status": "failed", "coverage_complete": False,
                "coverage_status": "unavailable", "coverage_reason": "route failed",
                "within_window_count": 0, "ranked_count": 0, "ranked_items": [],
                "selected_for_pool_count": 0, "selected_item_urls": [],
                "discovery_ranking_completed": False, "failure_reason": "route failed",
                "scan_window_start": None, "scan_window_end": None,
                "scan_evidence_path": None,
            })
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
            (49, 45, "D", {"public_impact": 45, "geographic_or_population_scope": 20, "urgency_and_safety": 20, "structural_or_policy_significance": 20, "material_new_development": 40, "core_section_relevance": 30}),
            (50, 60, "C", {"public_impact": 60, "geographic_or_population_scope": 40, "urgency_and_safety": 50, "structural_or_policy_significance": 30, "material_new_development": 60, "core_section_relevance": 40}),
            (100, 75, "B", {"public_impact": 75, "geographic_or_population_scope": 45, "urgency_and_safety": 70, "structural_or_policy_significance": 40, "material_new_development": 70, "core_section_relevance": 50}),
            (250, 90, "A-", {"public_impact": 90, "geographic_or_population_scope": 55, "urgency_and_safety": 80, "structural_or_policy_significance": 55, "material_new_development": 75, "core_section_relevance": 55}),
            (2500, 100, "A", {"public_impact": 100, "geographic_or_population_scope": 60, "urgency_and_safety": 90, "structural_or_policy_significance": 60, "material_new_development": 80, "core_section_relevance": 60}),
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
            "public_impact": 75,
            "geographic_or_population_scope": 65,
            "urgency_and_safety": 65,
            "structural_or_policy_significance": 65,
            "material_new_development": 55,
            "core_section_relevance": 55,
        }
        self.sync_score(item)
        item["midpoint_rationales"] = [
            {
                "dimension": dimension,
                "lower_anchor": score - 5,
                "upper_anchor": score + 5,
                "supporting_facts": [f"F{index:02d}"],
                "rationale": "證據強度介於相鄰十分 anchor 之間。",
            }
            for index, (dimension, score) in enumerate(
                item["importance_breakdown"].items(), start=1
            )
        ]
        item["high_score_challenges"] = [{
            "dimension": "public_impact",
            "claim": "百人死亡已造成重大公共後果",
            "counter_question": "目前已實際發生什麼公共後果足以達到 70？",
            "supporting_facts": ["F01"],
            "outcome": "sustained",
            "rationale": "保守確認死亡與直接公共後果足以支持",
        }]
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
            "applies": True,
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
        ranked.pop("discovery_priority_score")
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("discovery_priority_score" in error for error in errors))

        audit = valid_audit()
        audit["runs"][0]["candidates"][0].pop("dimension_evidence")
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("dimension_evidence" in error for error in errors))

    def test_major_scores_must_match_weights_and_total(self):
        item = candidate("D", "excluded", "below_public_value_threshold")
        item["importance_score"] = 95
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("加權分數" in error for error in errors))

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
            {"1-9": 30, "10-49": 45, "50-99": 60, "100-249": 75, "250-2499": 90, "2500+": 100},
            ranking.get("casualty_public_impact_floors"),
        )
        self.assertEqual(
            [
                {"score": 0, "meaning": "event ended or no immediate risk"},
                {"score": 20, "meaning": "limited precaution"},
                {"score": 40, "meaning": "local response required"},
                {"score": 60, "meaning": "major danger remains active"},
                {"score": 80, "meaning": "rescue window, essential-service stress, or expanding risk"},
                {"score": 100, "meaning": "uncontrolled threat requiring broad immediate action"},
            ],
            ranking.get("dimension_anchors", {}).get("urgency_and_safety"),
        )

        schema = MODULE.load(ROOT / "schemas" / "news-candidate-audit.schema.json")
        candidate_properties = schema["$defs"]["v2Candidate"]["properties"]
        self.assertIn("importance_score", candidate_properties)
        self.assertIn("importance_breakdown", candidate_properties)
        self.assertIn("dimension_evidence", candidate_properties)

    def test_c_or_above_merged_candidate_requires_reader_event_mapping(self):
        item = candidate("C", "merged", "duplicate_merged")
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("selected_event_id" in error for error in errors))

    def test_all_discovery_sources_send_every_ranked_item_to_pool(self):
        self.assertEqual([], MODULE.validate(valid_audit(per_source_count=73), source_pool()))

    def test_source_coverage_count_is_driven_by_source_pool(self):
        pool = source_pool()
        self.assertEqual(3, len(pool["discovery_sources"]))
        self.assertNotIn("sources", pool)
        self.assertNotIn("section_sources", pool)
        self.assertNotIn("primary_sources_per_section", pool)
        self.assertEqual([], MODULE.validate(valid_audit(), pool))

        missing = valid_audit()
        missing["runs"][0]["source_coverage"].clear()
        missing["runs"][0]["raw_item_count"] = 0
        errors = MODULE.validate(missing, pool)
        self.assertTrue(any("source coverage" in error for error in errors))

        extra = valid_audit()
        duplicate = dict(extra["runs"][0]["source_coverage"][-1])
        duplicate["source_id"] = "unexpected"
        extra["runs"][0]["source_coverage"].append(duplicate)
        extra["runs"][0]["raw_item_count"] += duplicate["selected_for_pool_count"]
        errors = MODULE.validate(extra, pool)
        self.assertTrue(any("source coverage" in error for error in errors))

    def test_discovery_source_ids_must_be_unique(self):
        pool = source_pool()
        pool["discovery_sources"].append(dict(pool["discovery_sources"][0]))
        errors = MODULE.validate(valid_audit(), pool)
        self.assertTrue(any("discovery" in error and "唯一" in error for error in errors))

    def test_source_cannot_submit_fewer_than_its_complete_ranked_list(self):
        audit = valid_audit(per_source_count=73)
        audit["runs"][0]["source_coverage"][0]["selected_for_pool_count"] = 72
        audit["runs"][0]["source_coverage"][0]["selected_item_urls"].pop()
        audit["runs"][0]["raw_item_count"] -= 1
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("完整排序清單" in error for error in errors))

    def test_unknown_deprecated_source_coverage_field_is_rejected(self):
        audit = valid_audit(per_source_count=35)
        source = audit["runs"][0]["source_coverage"][0]
        retired_field = "_".join(("mandatory", "overflow", "items"))
        source[retired_field] = [{
            "url": source["ranked_items"][32]["url"],
            "trigger": "major_disaster",
            "reason": "固定名額已取消，不應再需要溢位例外。",
        }]
        errors = MODULE.validate(audit, source_pool())
        self.assertTrue(any("未知欄位" in error for error in errors))

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
        self.assertEqual([], MODULE.validate(valid_audit(items, per_source_count=10), source_pool()))
        items[0]["decision"] = "excluded"
        errors = MODULE.validate(valid_audit(items, per_source_count=10), source_pool())
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

    def test_border_conflict_grade_is_derived_from_dimensions(self):
        item = candidate("B", "selected")
        review = item["grading_evidence"]["border_conflict_review"]
        review.update({"applies": True, "is_border_conflict": True})
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_monitored_border_conflict_can_be_regraded_with_reason(self):
        item = candidate("C", "selected")
        review = item["grading_evidence"]["border_conflict_review"]
        review.update({
            "applies": True,
            "is_border_conflict": True,
            "related_to_monitored_section": True,
            "exception_reason": "事件直接涉及使用者監控板塊，依本輪實際影響與增量評級。",
        })
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_routine_ongoing_war_update_is_scored_from_current_consequences(self):
        item = candidate("B", "selected")
        review = item["grading_evidence"]["ongoing_conflict_review"]
        review.update({
            "applies": True,
            "is_ongoing_conflict": True, "same_conflict_as_history": True,
            "routine_incident": True, "continuity_discount_applied": False,
        })
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_external_system_impact_can_remove_war_discount(self):
        item = candidate("B+", "selected")
        review = item["grading_evidence"]["ongoing_conflict_review"]
        review.update({
            "applies": True,
            "is_ongoing_conflict": True, "same_conflict_as_history": True,
            "routine_incident": False, "material_change": True,
            "change_types": ["external_system_impact"],
            "external_system_impact": True,
            "exception_reason": "主要航道通行量下降，油價與保險成本出現可驗證的異常上升。",
        })
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_ongoing_war_review_does_not_override_weighted_grade(self):
        item = candidate("B", "selected")
        review = item["grading_evidence"]["ongoing_conflict_review"]
        review.update({
            "applies": True,
            "is_ongoing_conflict": True, "same_conflict_as_history": True,
            "routine_incident": False, "change_types": ["material_escalation"],
            "exception_reason": "僅宣稱不是例行事件，但沒有任何實質變化證據。",
        })
        self.assertEqual([], MODULE.validate(valid_audit([item]), source_pool()))

    def test_b_minus_or_higher_requires_direct_consequence(self):
        item = candidate("B-", "selected")
        item["grading_evidence"]["direct_consequences"] = []
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("B- 以上" in error for error in errors))

    def test_strong_policy_governance_below_b_requires_why_not_b(self):
        item = candidate("C+", "selected")
        review = policy_governance_review(applies=True)
        review["score_consistency_review"]["why_not_b"] = ""
        item["grading_evidence"]["policy_governance_review"] = review
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("why_not_b" in error for error in errors))

    def test_unverified_policy_allegations_must_be_separated(self):
        item = candidate("B", "selected")
        review = policy_governance_review(applies=True)
        review["unverified_allegations"] = ["未經可靠來源證實的歷史指控"]
        review["unverified_allegations_separated"] = False
        item["grading_evidence"]["policy_governance_review"] = review
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("unverified_allegations" in error for error in errors))

    def test_policy_score_contradiction_requires_rescoring(self):
        item = candidate("B", "selected")
        review = policy_governance_review(applies=True)
        review["score_consistency_review"]["structural_alignment"] = "contradiction"
        review["score_consistency_review"]["contradiction_reasons"] = [
            "跨機關規範外溢與結構分數不一致。"
        ]
        review["score_consistency_review"]["review_outcome"] = "rescore_required"
        item["grading_evidence"]["policy_governance_review"] = review
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertTrue(any("必須退回重審" in error for error in errors))

    def test_strong_policy_governance_below_b_can_pass_after_challenge(self):
        item = candidate("C+", "selected")
        item["grading_evidence"]["policy_governance_review"] = policy_governance_review(
            applies=True
        )
        errors = MODULE.validate(valid_audit([item]), source_pool())
        self.assertFalse(any("policy_governance_review" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
