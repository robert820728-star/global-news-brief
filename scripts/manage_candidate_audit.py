#!/usr/bin/env python3
"""Validate and retain the rolling candidate/source audit."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import validate_source_scan_evidence

AUTO_SELECT = {"SS", "S+", "S", "S-", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"}
LOW_GRADES = {"D", "E"}
GRADE_ORDER = {
    "E": 0, "D": 1, "C-": 2, "C": 3, "C+": 4,
    "B-": 5, "B": 6, "B+": 7, "A-": 8, "A": 9, "A+": 10,
    "S-": 11, "S": 12, "S+": 13, "SS": 14,
}
DEFAULT_RANKING_DIMENSIONS = {
    "public_impact": 30,
    "geographic_or_population_scope": 20,
    "urgency_and_safety": 15,
    "structural_or_policy_significance": 15,
    "material_new_development": 10,
    "core_section_relevance": 10,
}
GRADE_SCORE_BANDS = (
    (97, "SS"),
    (94, "S+"),
    (90, "S"),
    (85, "S-"),
    (80, "A+"),
    (75, "A"),
    (70, "A-"),
    (65, "B+"),
    (60, "B"),
    (55, "B-"),
    (50, "C+"),
    (45, "C"),
    (40, "C-"),
    (20, "D"),
    (0, "E"),
)
GRADE_MINIMUM_SCORES = {grade: minimum for minimum, grade in GRADE_SCORE_BANDS}
INTEGRATED_GRADING_PRINCIPLES = {
    "combined_evidence_no_single_dimension_hard_cap": True,
    "importance_severity_is_public_impact": True,
    "scope_is_one_weighted_dimension": True,
}
CASUALTY_PUBLIC_IMPACT_FLOORS = {
    "1-9": 8,
    "10-49": 14,
    "50-99": 18,
    "100-249": 23,
    "250-2499": 27,
    "2500+": 30,
}
URGENCY_AND_SAFETY_ANCHORS = [
    {"score_range": [0, 3], "meaning": "danger ended or no immediate public action required"},
    {"score_range": [4, 7], "meaning": "active local response or bounded safety concern"},
    {"score_range": [8, 11], "meaning": "continuing major danger, rescue window, or stressed essential services"},
    {"score_range": [12, 15], "meaning": "expanding or uncontrolled threat requiring immediate broad action"},
]
LOCAL_DISASTER_SPECIAL_TRIGGERS = {
    "monitored_region_conflict_escalation_risk",
    "extreme_missing_serious_injury_or_evacuation",
    "major_public_system_disruption",
    "rapidly_expanding_disaster",
    "cross_regional_direct_impact",
    "multinational_direct_impact",
    "rare_disaster_mechanism",
    "regulatory_failure_or_systemic_risk",
    "mass_housing_or_critical_infrastructure_loss",
    "historic_extreme_scale",
    "special_security_or_public_health",
    "other_verified_special_significance",
}
POLICY_GOVERNANCE_TRIGGERS = {
    "official_legal_interpretation",
    "investigation_or_enforcement_referral",
    "binding_or_operational_compliance_request",
    "platform_or_operator_action",
    "multi_agency_coordination",
    "precedent_or_spillover_risk",
    "public_reaction",
}
POLICY_GOVERNANCE_OFFICIAL_ACTION_TRIGGERS = {
    "official_legal_interpretation",
    "investigation_or_enforcement_referral",
    "binding_or_operational_compliance_request",
}
POLICY_GOVERNANCE_SCOPE_TRIGGERS = {
    "multi_agency_coordination",
    "precedent_or_spillover_risk",
}
POLICY_SCORE_ALIGNMENT_FIELDS = {
    "public_impact_alignment",
    "scope_alignment",
    "structural_alignment",
    "window_alignment",
}
TEMPLATE_GRADE_REASONS = {
    "依公共影響評級",
    "具有公共影響",
    "值得持續追蹤",
    "具有公共價值",
    "事件具可驗證的政策、安全或民生影響，值得持續追蹤。",
    "事件明確影響公共安全、治理、經濟或區域關係，但範圍仍有限。",
}
REASON_CODES = {
    "selected_threshold_met", "c_minus_selected_need", "c_minus_reserve",
    "outside_time_window", "duplicate_merged", "continuation_no_material_change",
    "below_public_value_threshold", "unreliable_or_unverified",
    "superseded_by_later_update", "wrong_scope", "processing_failure",
    "search_recall_failure",
}

MATERIAL_UPDATE_TYPES = {
    "new_event", "official_confirmation", "casualty_or_impact_revision",
    "policy_or_legal_change", "operational_or_status_change",
    "material_escalation_or_deescalation", "other_verified_material_change",
    "ongoing_verified_current_impact",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_datetime(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def grade_from_importance_score(score):
    """Map a verified six-dimension total to the final SS-E grade."""
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 100:
        raise ValueError("importance score must be a number from 0 through 100")
    for minimum, grade in GRADE_SCORE_BANDS:
        if score >= minimum:
            return grade
    raise AssertionError("unreachable score band")


def validate_policy_governance_review(review, importance_score, label):
    """Require event identity and institutional evidence to agree with scoring."""
    errors = []
    if not isinstance(review, dict):
        return [label + " 最新一輪缺少 policy_governance_review"]
    applies = review.get("applies")
    if not isinstance(applies, bool):
        return [label + " policy_governance_review.applies 必須是布林值"]
    if not applies:
        return errors

    required_fields = {
        "triggered_by", "legal_basis", "official_actions",
        "direct_operational_effects", "affected_actor_classes",
        "cross_agency_effects", "precedent_or_spillover_scope",
        "window_material_effects", "evidence_urls",
        "unverified_allegations", "unverified_allegations_separated",
        "score_consistency_review",
    }
    missing = sorted(required_fields - set(review))
    if missing:
        errors.append(label + " policy_governance_review 缺少：" + ", ".join(missing))

    triggered_by = review.get("triggered_by")
    if not isinstance(triggered_by, list) or not triggered_by:
        errors.append(label + " policy_governance_review.triggered_by 必須是非空陣列")
        triggered_by = []
    else:
        invalid_triggers = [
            trigger for trigger in triggered_by
            if not isinstance(trigger, str) or trigger not in POLICY_GOVERNANCE_TRIGGERS
        ]
        if invalid_triggers:
            errors.append(
                label + " policy_governance_review.triggered_by 無效："
                + ", ".join(map(str, invalid_triggers))
            )
        if all(isinstance(trigger, str) for trigger in triggered_by) and len(triggered_by) != len(set(triggered_by)):
            errors.append(label + " policy_governance_review.triggered_by 不得重複")

    required_nonempty_lists = (
        "legal_basis", "official_actions", "direct_operational_effects",
        "affected_actor_classes", "window_material_effects", "evidence_urls",
    )
    for field in required_nonempty_lists:
        value = review.get(field)
        if not isinstance(value, list) or not value or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            errors.append(label + f" policy_governance_review.{field} 必須是非空具體文字陣列")
    for field in ("cross_agency_effects", "precedent_or_spillover_scope", "unverified_allegations"):
        value = review.get(field)
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            errors.append(label + f" policy_governance_review.{field} 必須是具體文字陣列")
    if "multi_agency_coordination" in triggered_by and not review.get("cross_agency_effects"):
        errors.append(label + " multi_agency_coordination 必須有 cross_agency_effects 證據")
    if "precedent_or_spillover_risk" in triggered_by and not review.get("precedent_or_spillover_scope"):
        errors.append(label + " precedent_or_spillover_risk 必須有 precedent_or_spillover_scope 證據")
    evidence_urls = review.get("evidence_urls")
    if isinstance(evidence_urls, list) and any(
        isinstance(url, str) and not url.startswith(("https://", "http://"))
        for url in evidence_urls
    ):
        errors.append(label + " policy_governance_review.evidence_urls 必須是 HTTP(S) 網址")

    allegations = review.get("unverified_allegations")
    separated = review.get("unverified_allegations_separated")
    if not isinstance(separated, bool):
        errors.append(label + " unverified_allegations_separated 必須是布林值")
    elif isinstance(allegations, list) and allegations and not separated:
        errors.append(label + " unverified_allegations 必須與已證實事件身分及六項評分分離")

    consistency = review.get("score_consistency_review")
    if not isinstance(consistency, dict):
        errors.append(label + " policy_governance_review 缺少 score_consistency_review")
        consistency = {}
    required_consistency = POLICY_SCORE_ALIGNMENT_FIELDS | {
        "contradiction_reasons", "why_not_b", "review_outcome",
    }
    missing_consistency = sorted(required_consistency - set(consistency))
    if missing_consistency:
        errors.append(
            label + " score_consistency_review 缺少：" + ", ".join(missing_consistency)
        )
    alignment_values = [consistency.get(field) for field in POLICY_SCORE_ALIGNMENT_FIELDS]
    invalid_alignments = [
        field for field in POLICY_SCORE_ALIGNMENT_FIELDS
        if consistency.get(field) not in {"consistent", "contradiction", "unresolved"}
    ]
    if invalid_alignments:
        errors.append(label + " score_consistency_review 對齊狀態無效：" + ", ".join(sorted(invalid_alignments)))
    contradiction_reasons = consistency.get("contradiction_reasons")
    if not isinstance(contradiction_reasons, list) or any(
        not isinstance(item, str) or not item.strip() for item in contradiction_reasons
    ):
        errors.append(label + " score_consistency_review.contradiction_reasons 必須是具體文字陣列")
    if any(value in {"contradiction", "unresolved"} for value in alignment_values) or consistency.get("review_outcome") != "consistent":
        errors.append(label + " 制度證據與六項評分矛盾或未解，必須退回重審並修正事件身分或重新評分")

    trigger_set = {trigger for trigger in triggered_by if isinstance(trigger, str)}
    strong_profile = (
        bool(trigger_set & POLICY_GOVERNANCE_OFFICIAL_ACTION_TRIGGERS)
        and "platform_or_operator_action" in trigger_set
        and bool(trigger_set & POLICY_GOVERNANCE_SCOPE_TRIGGERS)
    )
    if (
        strong_profile
        and isinstance(importance_score, (int, float))
        and not isinstance(importance_score, bool)
        and importance_score < GRADE_MINIMUM_SCORES["B"]
        and (
            not isinstance(consistency.get("why_not_b"), str)
            or not consistency["why_not_b"].strip()
        )
    ):
        errors.append(label + " 強制度治理證據低於 B 時必須提供具體 why_not_b 挑戰理由")
    return errors


def grade_from_importance_breakdown(breakdown):
    """Derive a grade from the combined six-dimension evidence score."""
    if not isinstance(breakdown, dict) or set(breakdown) != set(DEFAULT_RANKING_DIMENSIONS):
        raise ValueError("importance breakdown must contain the six configured dimensions")
    for key, maximum in DEFAULT_RANKING_DIMENSIONS.items():
        value = breakdown[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= maximum:
            raise ValueError(f"{key} must be between 0 and {maximum}")
    return grade_from_importance_score(sum(breakdown.values()))


def public_impact_floor_from_confirmed_deaths(confirmed_deaths):
    """Return the public-impact floor contributed by conservative confirmed deaths."""
    if not isinstance(confirmed_deaths, int) or isinstance(confirmed_deaths, bool) or confirmed_deaths < 0:
        raise ValueError("confirmed deaths must be a nonnegative integer")
    if confirmed_deaths == 0:
        return 0
    if confirmed_deaths < 10:
        return 8
    if confirmed_deaths < 50:
        return 14
    if confirmed_deaths < 100:
        return 18
    if confirmed_deaths < 250:
        return 23
    if confirmed_deaths < 2500:
        return 27
    return 30


def fourteen_day_completeness_errors(data):
    """Report whether a durable audit actually covers its rolling 14-day window."""
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        return ["十四天稽核為空，不能宣告十四天清單已完成"]
    try:
        latest_end = max(parse_datetime(item["window_end"]) for item in runs)
        earliest_start = min(parse_datetime(item["window_start"]) for item in runs)
    except (KeyError, TypeError, ValueError):
        return ["十四天稽核缺少可解析的 window_start 或 window_end"]
    required_start = latest_end - timedelta(days=14)
    if earliest_start > required_start:
        return [
            "十四天稽核未覆蓋完整滾動視窗："
            f"最早 {earliest_start.isoformat()}，應不晚於 {required_start.isoformat()}"
        ]
    return []


def validate(data, source_pool=None, require_fourteen_day_complete=False):
    errors = []
    if data.get("schema_version") != "1.1.0":
        errors.append("schema_version 必須是 1.1.0")
    if data.get("retention_days") != 14:
        errors.append("retention_days 必須固定為 14")

    source_scan_evidence_required = False
    source_by_id = {}
    discovery_source_ids = []
    minimum_ready_discovery_sources = 0
    all_configured_source_ids = set()
    ranking_dimensions = dict(DEFAULT_RANKING_DIMENSIONS)
    if source_pool:
        discovery_source_ids = [
            item["source_id"] for item in source_pool.get("discovery_sources", [])
        ]
        minimum_ready_discovery_sources = int(
            source_pool.get("discovery_policy", {}).get(
                "minimum_ready_sources", len(discovery_source_ids)
            )
        )
        all_configured_source_ids = set(discovery_source_ids)
        source_scan_evidence_required = source_pool.get("source_scan_evidence_required") is True
        source_by_id = {
            item["source_id"]: item
            for item in source_pool.get("discovery_sources", [])
        }
        if not discovery_source_ids or len(set(discovery_source_ids)) != len(discovery_source_ids):
            errors.append("news-source-pool.json 必須定義至少一個且全部唯一的 discovery source")
        if not source_scan_evidence_required:
            errors.append("news-source-pool.json 必須鎖定 source_scan_evidence_required=true")
        ranking = source_pool.get("ranking", {})
        ranking_dimensions = ranking.get("dimensions", {})
        cultural_rule = source_pool.get("cultural_industry_event_rule", {})
        if cultural_rule.get("first_large_award_suspension_min_grade") != "C":
            errors.append("news-source-pool.json 必須固定大型評選活動首次停辦最低為 C")
        if cultural_rule.get("repeat_without_material_change_allowed_grades") != ["C-", "D"]:
            errors.append("news-source-pool.json 必須將無實質新增的重複停辦降為 C- 或 D")
        if cultural_rule.get("material_change_requires_regrading") is not True:
            errors.append("news-source-pool.json 必須要求出現實質變化時重新評級")
        conflict_rule = source_pool.get("conflict_grading_policy", {})
        if conflict_rule.get("border_skirmish_default_grade") != "D":
            errors.append("news-source-pool.json 必須將非例外邊境小衝突固定為 D")
        if conflict_rule.get("ongoing_conflict_routine_update_default_grade") != "D":
            errors.append("news-source-pool.json 必須將長期戰爭常態更新固定為 D")
        if conflict_rule.get("parent_conflict_grade_inheritance_forbidden") is not True:
            errors.append("news-source-pool.json 必須禁止沿用母衝突等級")
        if conflict_rule.get("source_count_must_not_change_grade") is not True:
            errors.append("news-source-pool.json 必須禁止來源數量改變評級")
        if ranking.get("method") != "public_value_v1" or sum(ranking.get("dimensions", {}).values()) != 100:
            errors.append("news-source-pool.json 的 public_value_v1 權重必須合計 100")
        if ranking.get("grade_minimum_scores") != GRADE_MINIMUM_SCORES:
            errors.append("news-source-pool.json 的 grade_minimum_scores 必須與六項綜合評級級距一致")
        if ranking.get("grading_principles") != INTEGRATED_GRADING_PRINCIPLES:
            errors.append("news-source-pool.json 必須鎖定六項綜合評級且不得設單項硬上限")
        if ranking.get("casualty_public_impact_floors") != CASUALTY_PUBLIC_IMPACT_FLOORS:
            errors.append("news-source-pool.json 必須鎖定死亡人數對 public_impact 的最低證據分數")
        if ranking.get("dimension_anchors", {}).get("urgency_and_safety") != URGENCY_AND_SAFETY_ANCHORS:
            errors.append("news-source-pool.json 必須鎖定 urgency_and_safety 的立即風險錨點")

    runs = data.get("runs", [])
    for run_index, run in enumerate(runs, 1):
        run_label = f"runs[{run_index}]"
        coverage = run.get("source_coverage", [])
        if not isinstance(coverage, list):
            errors.append(run_label + ".source_coverage 必須是陣列")
            coverage = []
        coverage_ids = [item.get("source_id") for item in coverage if isinstance(item, dict)]
        discovery_coverage = (
            bool(discovery_source_ids)
            and len(coverage_ids) >= minimum_ready_discovery_sources
            and len(coverage_ids) == len(set(coverage_ids))
            and set(coverage_ids).issubset(set(discovery_source_ids))
        )
        if source_pool is not None and not discovery_coverage:
            errors.append(
                run_label
                + " source coverage 必須達到最低可用數、不得重複，且只能引用 configured discovery sources"
            )

        raw_total = 0
        for source_index, item in enumerate(coverage, 1):
            label = f"{run_label}.source_coverage[{source_index}]"
            if not isinstance(item, dict):
                errors.append(label + " 必須是物件")
                continue
            within = item.get("within_window_count")
            ranked = item.get("ranked_count")
            selected = item.get("selected_for_pool_count")
            urls = item.get("selected_item_urls")
            ranked_items = item.get("ranked_items")
            overflow_items = item.get("mandatory_overflow_items")
            if item.get("status") != "completed":
                errors.append(label + " 來源掃描未完成；禁止與圖片確認一起通過發布閘門")
            if source_scan_evidence_required:
                for field in ("scan_window_start", "scan_window_end", "scan_evidence_path"):
                    if not item.get(field):
                        errors.append(label + f" 缺少 {field}；不得自行宣告來源掃描完成")
                evidence_path = item.get("scan_evidence_path")
                if item.get("scan_window_start") != run.get("window_start") or item.get("scan_window_end") != run.get("window_end"):
                    errors.append(label + " 掃描證據時間窗必須與本輪精確24小時時間窗一致")
                if isinstance(evidence_path, str) and evidence_path:
                    local = Path(evidence_path.removeprefix("sandbox:"))
                    if not local.is_file():
                        errors.append(label + f" 掃描證據檔不存在：{evidence_path}")
                    else:
                        try:
                            scan = load(local)
                            errors.extend(validate_source_scan_evidence.validate_scan(
                                scan, item, source_by_id.get(item.get("source_id"), {}), label + ".scan_evidence"
                            ))
                        except (OSError, ValueError, json.JSONDecodeError) as error:
                            errors.append(label + f" 掃描證據無法讀取：{error}")
            if item.get("ranking_completed") is not True:
                errors.append(label + " 尚未完成站內重要度排序")
            if item.get("ranking_method") != "public_value_v1":
                errors.append(label + " 未使用固定 public_value_v1 重要度排序")
            if not all(isinstance(value, int) and value >= 0 for value in (within, ranked, selected)):
                errors.append(label + " 來源數量欄位無效")
                continue
            if ranked != within:
                errors.append(label + " 必須評估時間窗內全部條目後再排序")
            if not isinstance(ranked_items, list) or len(ranked_items) != ranked:
                errors.append(label + " ranked_items 必須保存時間窗內完整排序清單")
                ranked_items = []
            ranked_urls = []
            scores = []
            for ranked_index, ranked_item in enumerate(ranked_items, 1):
                ranked_label = f"{label}.ranked_items[{ranked_index}]"
                if not isinstance(ranked_item, dict):
                    errors.append(ranked_label + " 必須是物件")
                    continue
                ranked_urls.append(ranked_item.get("url"))
                score = ranked_item.get("importance_score")
                scores.append(score)
                if not isinstance(score, (int, float)) or not 0 <= score <= 100:
                    errors.append(ranked_label + " importance_score 必須介於 0–100")
                breakdown = ranked_item.get("importance_breakdown")
                if not isinstance(breakdown, dict) or set(breakdown) != set(ranking_dimensions):
                    errors.append(
                        ranked_label + " importance_breakdown 必須包含 public_value_v1 全部大項分數"
                    )
                else:
                    invalid_dimensions = [
                        key for key, weight in ranking_dimensions.items()
                        if not isinstance(breakdown.get(key), (int, float))
                        or not 0 <= breakdown[key] <= weight
                    ]
                    if invalid_dimensions:
                        errors.append(
                            ranked_label + " 大項分數超出設定權重：" + ", ".join(invalid_dimensions)
                        )
                    numeric_breakdown = all(
                        isinstance(value, (int, float)) for value in breakdown.values()
                    )
                    if (
                        numeric_breakdown
                        and isinstance(score, (int, float))
                        and abs(sum(breakdown.values()) - score) > 0.01
                    ):
                        errors.append(
                            ranked_label + " importance_breakdown 總和必須等於 importance_score"
                        )
                if not isinstance(ranked_item.get("importance_reason"), str) or not ranked_item["importance_reason"].strip():
                    errors.append(ranked_label + " 缺少重要度理由")
            if len(set(ranked_urls)) != len(ranked_urls):
                errors.append(label + " ranked_items 含重複網址")
            if all(isinstance(score, (int, float)) for score in scores) and scores != sorted(scores, reverse=True):
                errors.append(label + " ranked_items 未按重要度由高至低排列")
            if not isinstance(overflow_items, list):
                errors.append(label + ".mandatory_overflow_items 必須是陣列")
                overflow_items = []
            if overflow_items:
                errors.append(label + " 已取消固定入池上限，不得再使用強制溢位例外")
            expected_urls = ranked_urls
            if selected != len(expected_urls):
                errors.append(label + " 入池數量必須等於完整排序清單")
            if not isinstance(urls, list) or len(urls) != selected or len(set(urls)) != len(urls):
                errors.append(label + " selected_item_urls 數量或唯一性不符")
            elif urls != expected_urls:
                errors.append(label + " 入池網址必須精確等於完整排序清單")
            raw_total += selected
        if run.get("raw_item_count") != raw_total:
            errors.append(run_label + ".raw_item_count 必須等於全部 discovery 來源入池數量總和")

        candidates = run.get("candidates", [])
        if run.get("deduplicated_candidate_count") != len(candidates):
            errors.append(run_label + ".deduplicated_candidate_count 必須等於去重候選筆數")
        if isinstance(run.get("raw_item_count"), int) and len(candidates) > run["raw_item_count"]:
            errors.append(run_label + " 去重後候選不得多於原始入池條目")

        if run_index == len(runs):
            processing_counts = run.get("processing_counts")
            count_fields = {
                "merged_article_row_count", "in_window_article_row_count",
                "canonical_url_count", "provisional_title_cluster_count",
                "semantic_event_count", "scored_event_count",
                "event_evidence_article_row_count", "non_news_article_row_count",
                "unresolved_article_row_count",
                "c_or_higher_scored_event_count", "selected_event_count",
            }
            if not isinstance(processing_counts, dict) or set(processing_counts) != count_fields:
                errors.append(
                    run_label + ".processing_counts 必須包含完整文章、網址、分群、事件與評分階段計數"
                )
            elif any(
                not isinstance(processing_counts[field], int)
                or isinstance(processing_counts[field], bool)
                or processing_counts[field] < 0
                for field in count_fields
            ):
                errors.append(run_label + ".processing_counts 全部欄位必須是非負整數")
            else:
                dispositions = run.get("article_dispositions")
                disposition_counts = Counter(
                    item.get("disposition") for item in dispositions
                    if isinstance(dispositions, list) and isinstance(item, dict)
                ) if isinstance(dispositions, list) else Counter()
                expected_counts = {
                    "merged_article_row_count": run.get("raw_item_count"),
                    "in_window_article_row_count": run.get("raw_item_count"),
                    "semantic_event_count": len(candidates),
                    "scored_event_count": len(candidates),
                    "event_evidence_article_row_count": disposition_counts["event_evidence"],
                    "non_news_article_row_count": disposition_counts["non_news"],
                    "unresolved_article_row_count": disposition_counts["unresolved"],
                    "c_or_higher_scored_event_count": sum(
                        isinstance(item, dict) and item.get("provisional_grade") in AUTO_SELECT
                        for item in candidates
                    ),
                    "selected_event_count": sum(
                        isinstance(item, dict) and item.get("decision") == "selected"
                        for item in candidates
                    ),
                }
                for field, expected in expected_counts.items():
                    if processing_counts[field] != expected:
                        errors.append(
                            run_label + f".processing_counts.{field} 必須等於可重算值 {expected}"
                        )
                ordered_fields = (
                    "in_window_article_row_count", "canonical_url_count",
                    "provisional_title_cluster_count", "semantic_event_count",
                )
                if any(
                    processing_counts[left] < processing_counts[right]
                    for left, right in zip(ordered_fields, ordered_fields[1:])
                ):
                    errors.append(
                        run_label + ".processing_counts 不得在去重或分群後反而增加"
                    )
                if (
                    processing_counts["event_evidence_article_row_count"]
                    + processing_counts["non_news_article_row_count"]
                    + processing_counts["unresolved_article_row_count"]
                    != processing_counts["in_window_article_row_count"]
                ):
                    errors.append(
                        run_label + ".processing_counts 文章處置數總和必須等於時間窗內文章列數"
                    )

        semantic_event_ids = []
        candidate_by_event_id = {}
        if run_index == len(runs):
            legacy_identity_fields = {
                "who_or_what", "what_happened", "where", "when", "semantic_merge_basis"
            }
            structured_identity_fields = {
                "country_codes", "primary_country_code", "location_evidence",
                "event_occurred_at", "material_update_at", "material_update_type",
                "material_update_evidence",
            }
            identity_fields = legacy_identity_fields | structured_identity_fields
            try:
                run_window_start = parse_datetime(run.get("window_start", ""))
                run_window_end = parse_datetime(run.get("window_end", ""))
            except (TypeError, ValueError):
                run_window_start = run_window_end = None
            for candidate_index, candidate in enumerate(candidates, 1):
                label = f"{run_label}.candidates[{candidate_index}]"
                if not isinstance(candidate, dict):
                    continue
                semantic_event_id = candidate.get("semantic_event_id")
                if not isinstance(semantic_event_id, str) or not semantic_event_id.strip():
                    errors.append(label + ".semantic_event_id 必須是非空白語意事件識別碼")
                else:
                    semantic_event_ids.append(semantic_event_id)
                    candidate_by_event_id[semantic_event_id] = candidate
                identity = candidate.get("event_identity")
                if not isinstance(identity, dict) or not identity_fields.issubset(identity):
                    errors.append(
                        label + ".event_identity 必須包含事件主體、結構化地區、"
                        "事件發生時間、實質更新時間與合併依據"
                    )
                    continue
                text_fields = identity_fields - {"country_codes"}
                if any(
                    not isinstance(identity[field], str) or not identity[field].strip()
                    for field in text_fields
                ):
                    errors.append(label + ".event_identity 文字欄位都必須是非空白文字")

                country_codes = identity.get("country_codes")
                primary_country = identity.get("primary_country_code")
                if (
                    not isinstance(country_codes, list)
                    or not country_codes
                    or any(
                        not isinstance(code, str) or len(code) != 3 or not code.isupper()
                        for code in country_codes
                    )
                    or len(country_codes) != len(set(country_codes))
                ):
                    errors.append(label + ".event_identity.country_codes 必須是唯一三碼大寫代碼陣列")
                elif primary_country not in country_codes:
                    errors.append(label + ".event_identity.primary_country_code 必須列在 country_codes")

                expected_section = (
                    "TWN" if primary_country == "TWN"
                    else "CHN" if primary_country == "CHN"
                    else "GLB"
                )
                if candidate.get("section") != expected_section:
                    errors.append(
                        label + f".section 必須由 event_identity.primary_country_code "
                        f"推導為 {expected_section}；來源分桶不得參與"
                    )

                update_type = identity.get("material_update_type")
                if update_type not in MATERIAL_UPDATE_TYPES:
                    errors.append(label + ".event_identity.material_update_type 不是允許的實質更新類型")
                try:
                    occurred_at = parse_datetime(identity.get("event_occurred_at", ""))
                    material_update_at = parse_datetime(identity.get("material_update_at", ""))
                except (TypeError, ValueError):
                    errors.append(label + ".event_identity 事件與更新時間必須是含時區的 ISO 時間")
                    continue
                if occurred_at > material_update_at:
                    errors.append(label + ".event_identity.event_occurred_at 不得晚於 material_update_at")
                if (
                    run_window_start is not None
                    and not (run_window_start < material_update_at <= run_window_end)
                ):
                    errors.append(label + ".event_identity.material_update_at 必須落在精確執行時間窗內")
                occurred_in_window = (
                    run_window_start is not None
                    and run_window_start < occurred_at <= run_window_end
                )
                if update_type == "new_event" and not occurred_in_window:
                    errors.append(label + ".event_identity 舊事件不得以 new_event 或今日重整冒充新事件")
                if (
                    not occurred_in_window
                    and update_type != "new_event"
                    and candidate.get("continuity", {}).get("status") == "new"
                ):
                    errors.append(label + ".continuity.status 舊事件的實質更新必須標為 continuing")

                temporal_review = identity.get("temporal_review")
                temporal_fields = {
                    "review_method", "window_status", "active_during_window",
                    "new_or_changed_facts", "repeated_old_facts",
                    "current_window_impact", "comparison_evidence",
                }
                if (
                    not isinstance(temporal_review, dict)
                    or not temporal_fields.issubset(temporal_review)
                    or temporal_review.get("review_method") != "model_content_comparison"
                ):
                    errors.append(
                        label + ".event_identity.temporal_review 必須由模型比較事件內容、"
                        "既有時間線與本輪事實"
                    )
                    continue
                for field in (
                    "new_or_changed_facts", "repeated_old_facts", "current_window_impact"
                ):
                    value = temporal_review.get(field)
                    if not isinstance(value, list) or any(
                        not isinstance(item, str) or not item.strip() for item in value
                    ):
                        errors.append(label + f".event_identity.temporal_review.{field} 必須是文字陣列")
                if not isinstance(temporal_review.get("comparison_evidence"), str) or not temporal_review["comparison_evidence"].strip():
                    errors.append(label + ".event_identity.temporal_review.comparison_evidence 不得為空")

                window_status = temporal_review.get("window_status")
                new_facts = temporal_review.get("new_or_changed_facts", [])
                current_impact = temporal_review.get("current_window_impact", [])
                active_during_window = temporal_review.get("active_during_window")
                if window_status == "old_restatement":
                    errors.append(label + ".event_identity.temporal_review old_restatement 不得成為語意事件候選；文章應記為 non_news")
                elif window_status == "new_event":
                    if update_type != "new_event" or not occurred_in_window or not new_facts:
                        errors.append(label + ".event_identity.temporal_review new_event 必須列出窗內首次發生的事實")
                elif window_status == "material_update":
                    if update_type in {"new_event", "ongoing_verified_current_impact"} or not new_facts:
                        errors.append(label + ".event_identity.temporal_review material_update 必須列出本輪新增或變更事實")
                elif window_status == "ongoing_current_impact":
                    if (
                        update_type != "ongoing_verified_current_impact"
                        or active_during_window is not True
                        or not current_impact
                    ):
                        errors.append(label + ".event_identity.temporal_review ongoing_current_impact 必須證明事件在窗內仍持續造成影響")
                else:
                    errors.append(label + ".event_identity.temporal_review.window_status 無效")
            if len(semantic_event_ids) != len(set(semantic_event_ids)):
                errors.append(run_label + ".semantic_event_id 不得由兩個候選重複使用")

            dispositions = run.get("article_dispositions")
            expected_rows = Counter(
                (item.get("source_id"), url)
                for item in coverage if isinstance(item, dict)
                for url in item.get("selected_item_urls", [])
            )
            actual_rows = Counter()
            mapped_event_ids = set()
            if not isinstance(dispositions, list):
                errors.append(run_label + ".article_dispositions 必須逐列保存文章處置")
                dispositions = []
            for disposition_index, disposition in enumerate(dispositions, 1):
                label = f"{run_label}.article_dispositions[{disposition_index}]"
                if not isinstance(disposition, dict):
                    errors.append(label + " 必須是物件")
                    continue
                source_id = disposition.get("source_id")
                url = disposition.get("url")
                outcome = disposition.get("disposition")
                semantic_event_id = disposition.get("semantic_event_id")
                reason = disposition.get("reason")
                actual_rows[(source_id, url)] += 1
                if not isinstance(reason, str) or not reason.strip():
                    errors.append(label + ".reason 不得為空")
                if outcome == "event_evidence":
                    candidate = candidate_by_event_id.get(semantic_event_id)
                    if candidate is None:
                        errors.append(label + ".semantic_event_id 必須指向一個語意事件候選")
                    elif url not in candidate.get("candidate_urls", []):
                        errors.append(label + " 網址必須列在所指語意事件的 candidate_urls")
                    else:
                        mapped_event_ids.add(semantic_event_id)
                elif outcome == "non_news":
                    if semantic_event_id is not None:
                        errors.append(label + " non_news 不得指向語意事件")
                elif outcome == "unresolved":
                    errors.append(label + " unresolved 文章不得通過完成驗收")
                else:
                    errors.append(label + ".disposition 無效")
            if actual_rows != expected_rows:
                errors.append(run_label + ".article_dispositions 必須與來源文章列逐筆完全一致")
            if set(semantic_event_ids) - mapped_event_ids:
                errors.append(run_label + " 每個語意事件都必須至少有一筆 event_evidence")

        valid_source_ids = all_configured_source_ids or set(coverage_ids)
        candidate_url_list = []
        for candidate_index, candidate in enumerate(candidates, 1):
            label = f"{run_label}.candidates[{candidate_index}]"
            grade = candidate.get("provisional_grade")
            decision = candidate.get("decision")
            reason_code = candidate.get("reason_code")
            if reason_code not in REASON_CODES:
                errors.append(label + " reason_code 無效")
            if not isinstance(candidate.get("grade_reason"), str) or not candidate["grade_reason"].strip():
                errors.append(label + " 缺少 SS–E 評級理由")
            elif candidate["grade_reason"].strip() in TEMPLATE_GRADE_REASONS:
                errors.append(label + " grade_reason 使用禁止的模板理由，必須寫出事件特有的影響與本期增量")
            grading = candidate.get("grading_evidence")
            if not isinstance(grading, dict):
                errors.append(label + " 缺少結構化 grading_evidence；不得只填 grade_reason")
                grading = {}
            required_grading = {
                "impact_scope_level", "direct_consequences", "structural_significance",
                "window_material_changes", "why_current_grade", "why_not_higher",
                "why_not_lower", "border_conflict_review", "ongoing_conflict_review",
            }
            if run_index == len(runs):
                required_grading.update({"local_disaster_review", "policy_governance_review"})
            missing_grading = sorted(required_grading - set(grading))
            if missing_grading:
                errors.append(label + " grading_evidence 缺少：" + ", ".join(missing_grading))
            if grading.get("impact_scope_level") not in {
                "facility", "local", "subregional", "national", "multinational", "global"
            }:
                errors.append(label + " impact_scope_level 無效")
            for field in ("direct_consequences", "window_material_changes"):
                value = grading.get(field)
                if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                    errors.append(label + f" {field} 必須是具體文字陣列")
            for field in ("structural_significance", "why_current_grade", "why_not_higher", "why_not_lower"):
                if not isinstance(grading.get(field), str) or not grading[field].strip():
                    errors.append(label + f" {field} 不得為空")

            if run_index == len(runs):
                importance_score = candidate.get("importance_score")
                importance = candidate.get("importance_breakdown")
                dimension_evidence = candidate.get("dimension_evidence")
                if (
                    not isinstance(importance_score, (int, float))
                    or isinstance(importance_score, bool)
                    or not 0 <= importance_score <= 100
                ):
                    errors.append(label + " importance_score 必須介於 0–100")
                if not isinstance(importance, dict) or set(importance) != set(ranking_dimensions):
                    errors.append(label + " importance_breakdown 必須包含最終評級的六個大項分數")
                else:
                    invalid_dimensions = [
                        key for key, weight in ranking_dimensions.items()
                        if not isinstance(importance.get(key), (int, float))
                        or isinstance(importance.get(key), bool)
                        or not 0 <= importance[key] <= weight
                    ]
                    if invalid_dimensions:
                        errors.append(
                            label + " 最終評級大項分數超出設定權重："
                            + ", ".join(invalid_dimensions)
                        )
                    elif (
                        isinstance(importance_score, (int, float))
                        and not isinstance(importance_score, bool)
                        and abs(sum(importance.values()) - importance_score) > 0.01
                    ):
                        errors.append(label + " 最終 importance_breakdown 總和必須等於 importance_score")
                    elif isinstance(importance_score, (int, float)) and not isinstance(importance_score, bool):
                        derived_grade = grade_from_importance_score(importance_score)
                        if grade != derived_grade:
                            errors.append(
                                label + f" 六項總分 {importance_score:g} 對應 {derived_grade}，"
                                f"不得另填為 {grade}"
                            )
                if not isinstance(dimension_evidence, dict) or set(dimension_evidence) != set(ranking_dimensions):
                    errors.append(label + " dimension_evidence 必須為最終評級六個大項逐項提供證據")
                elif any(
                    not isinstance(value, str) or not value.strip()
                    for value in dimension_evidence.values()
                ):
                    errors.append(label + " dimension_evidence 每一大項都必須是非空白具體文字")
                errors.extend(validate_policy_governance_review(
                    grading.get("policy_governance_review"), importance_score, label
                ))

            border = grading.get("border_conflict_review")
            if not isinstance(border, dict):
                errors.append(label + " 缺少 border_conflict_review")
                border = {}
            border_keys = {
                "is_border_conflict", "formal_war", "de_facto_war_scale",
                "related_to_monitored_section", "user_weight_elevated",
                "default_d_applied", "exception_reason",
            }
            if border_keys - set(border):
                errors.append(label + " border_conflict_review 欄位不完整")
            border_default_d = (
                border.get("is_border_conflict") is True
                and border.get("formal_war") is not True
                and border.get("de_facto_war_scale") is not True
                and border.get("related_to_monitored_section") is not True
                and border.get("user_weight_elevated") is not True
            )
            if border_default_d:
                if grade != "D":
                    errors.append(label + " 非監控板塊且未加權的邊境小衝突必須評為 D，不得升至 C 以上")
                if border.get("default_d_applied") is not True:
                    errors.append(label + " 邊境小衝突必須記錄 default_d_applied=true")
            elif border.get("is_border_conflict") is True and grade not in LOW_GRADES:
                if not isinstance(border.get("exception_reason"), str) or not border["exception_reason"].strip():
                    errors.append(label + " 邊境衝突解除 D 級預設時必須保存具體例外理由")

            ongoing = grading.get("ongoing_conflict_review")
            if not isinstance(ongoing, dict):
                errors.append(label + " 缺少 ongoing_conflict_review")
                ongoing = {}
            ongoing_keys = {
                "is_ongoing_conflict", "same_conflict_as_history", "routine_incident",
                "material_change", "change_types", "reversal_or_escalation_possible",
                "external_system_impact", "continuity_discount_applied", "exception_reason",
            }
            if ongoing_keys - set(ongoing):
                errors.append(label + " ongoing_conflict_review 欄位不完整")
            routine_conflict = (
                ongoing.get("is_ongoing_conflict") is True
                and ongoing.get("same_conflict_as_history") is True
                and ongoing.get("routine_incident") is True
                and ongoing.get("material_change") is not True
                and ongoing.get("reversal_or_escalation_possible") is not True
                and ongoing.get("external_system_impact") is not True
            )
            if routine_conflict:
                if grade != "D":
                    errors.append(label + " 長期戰爭的常態小衝突／例行更新必須評為 D，不得繼承母事件等級")
                if ongoing.get("continuity_discount_applied") is not True:
                    errors.append(label + " 長期戰爭常態事件必須套用 continuity_discount_applied=true")
            elif ongoing.get("is_ongoing_conflict") is True and grade not in LOW_GRADES:
                change_types = ongoing.get("change_types")
                exception_triggered = (
                    ongoing.get("material_change") is True
                    or ongoing.get("reversal_or_escalation_possible") is True
                    or ongoing.get("external_system_impact") is True
                )
                if not exception_triggered:
                    errors.append(label + " 長期戰爭未證明戰局／和平進程／外部系統的實質變化，不得解除 D 級折扣")
                if not isinstance(change_types, list) or not change_types:
                    errors.append(label + " 長期戰爭解除 D 級折扣時必須列出 change_types")
                if not isinstance(ongoing.get("exception_reason"), str) or not ongoing["exception_reason"].strip():
                    errors.append(label + " 長期戰爭解除 D 級折扣時必須保存具體新進展")

            local_disaster = grading.get("local_disaster_review")
            if run_index == len(runs):
                if not isinstance(local_disaster, dict):
                    errors.append(label + " 最新一輪缺少 local_disaster_review")
                    local_disaster = {}
                applies = local_disaster.get("applies")
                if not isinstance(applies, bool):
                    errors.append(label + " local_disaster_review.applies 必須是布林值")
                elif applies:
                    required_local = {
                        "confirmed_deaths", "special_significance_triggers",
                        "grade_adjustment_reason",
                    }
                    missing_local = sorted(required_local - set(local_disaster))
                    if missing_local:
                        errors.append(
                            label + " local_disaster_review 缺少：" + ", ".join(missing_local)
                        )
                    deaths = local_disaster.get("confirmed_deaths")
                    triggers = local_disaster.get("special_significance_triggers")
                    reason = local_disaster.get("grade_adjustment_reason")
                    if not isinstance(deaths, int) or isinstance(deaths, bool) or deaths < 0:
                        errors.append(label + " confirmed_deaths 必須是零以上的保守確認值")
                    elif isinstance(importance, dict):
                        public_impact = importance.get("public_impact")
                        death_floor = public_impact_floor_from_confirmed_deaths(deaths)
                        if (
                            isinstance(public_impact, (int, float))
                            and not isinstance(public_impact, bool)
                            and public_impact < death_floor
                        ):
                            errors.append(
                                label + f" {deaths} 人保守確認死亡的 public_impact "
                                f"死亡證據最低為 {death_floor} 分"
                            )
                    if not isinstance(triggers, list):
                        errors.append(label + " special_significance_triggers 必須是陣列")
                        triggers = []
                    else:
                        invalid_triggers = [
                            trigger for trigger in triggers
                            if not isinstance(trigger, str)
                            or trigger not in LOCAL_DISASTER_SPECIAL_TRIGGERS
                        ]
                        if invalid_triggers:
                            errors.append(
                                label + " special_significance_triggers 無效："
                                + ", ".join(map(str, invalid_triggers))
                            )
                        if (
                            all(isinstance(trigger, str) for trigger in triggers)
                            and len(triggers) != len(set(triggers))
                        ):
                            errors.append(label + " special_significance_triggers 不得重複")
                    if (
                        border.get("is_border_conflict") is True
                        or ongoing.get("is_ongoing_conflict") is True
                    ):
                        errors.append(label + " 已屬軍事／衝突規則的事件不得同時套用地方災害審查")
                    if triggers and (not isinstance(reason, str) or not reason.strip()):
                        errors.append(label + " 記錄特殊意義證據時必須填寫具體調整理由")
            if GRADE_ORDER.get(grade, -1) >= GRADE_ORDER["B-"] and not grading.get("direct_consequences"):
                errors.append(label + " B- 以上必須列出至少一項已發生的直接公共後果")
            source_ids = candidate.get("source_ids")
            candidate_urls = candidate.get("candidate_urls")
            if not isinstance(candidate_urls, list) or not candidate_urls:
                errors.append(label + " 缺少原始入池網址")
            else:
                candidate_url_list.extend(candidate_urls)
            if not isinstance(source_ids, list) or not source_ids:
                errors.append(label + " 缺少來源池追溯")
            elif any(source_id not in valid_source_ids for source_id in source_ids):
                errors.append(label + " 引用未定義的 discovery 來源")

            if grade in AUTO_SELECT and decision not in {"selected", "merged"}:
                errors.append(label + " C 以上必須入選；禁止篇數上限、相對淘汰或延後")
            if grade in AUTO_SELECT and (
                not isinstance(candidate.get("selected_event_id"), str)
                or not candidate["selected_event_id"].strip()
            ):
                errors.append(label + " C 以上候選必須以 selected_event_id 映射至讀者版事件")
            if grade == "C-":
                if decision == "selected":
                    if reason_code != "c_minus_selected_need" or not candidate.get("c_minus_use_reason"):
                        errors.append(label + " C- 取用必須有明確需求理由")
                elif decision not in {"deferred", "merged"} or reason_code not in {"c_minus_reserve", "duplicate_merged"}:
                    errors.append(label + " C- 預設只能進候補池")
            if grade in LOW_GRADES and decision == "selected":
                errors.append(label + " D/E 不得入選")
            if candidate.get("source_audit", {}).get("reliable_source_count") == 1 and reason_code == "unreliable_or_unverified":
                errors.append(label + " 已有一個可靠來源，不得僅以來源不足排除")
        pool_urls = [
            url for item in coverage if isinstance(item, dict)
            for url in item.get("selected_item_urls", [])
        ]
        if len(candidate_url_list) != len(set(candidate_url_list)):
            errors.append(run_label + " 去重候選之間重複占用同一原始網址")
        if run_index == len(runs) and isinstance(run.get("article_dispositions"), list):
            event_urls = {
                item.get("url") for item in run["article_dispositions"]
                if isinstance(item, dict) and item.get("disposition") == "event_evidence"
            }
            if set(candidate_url_list) != event_urls:
                errors.append(run_label + " candidate_urls 必須精確等於 event_evidence 網址")
        elif set(candidate_url_list) != set(pool_urls):
            errors.append(run_label + " 每個 discovery 來源入池網址都必須歸屬一個去重候選，禁止候選無聲消失")
    if require_fourteen_day_complete:
        errors += fourteen_day_completeness_errors(data)
    return errors


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    append_parser = subparsers.add_parser("append")
    append_parser.add_argument("--history", required=True)
    append_parser.add_argument("--run", required=True)
    append_parser.add_argument("--output", required=True)
    append_parser.add_argument("--source-pool", required=True)
    append_parser.add_argument("--retention-days", type=int, default=14)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--source-pool", required=True)
    validate_parser.add_argument("--require-fourteen-day-complete", action="store_true")
    args = parser.parse_args()
    try:
        source_pool = load(args.source_pool)
        if args.cmd == "validate":
            errors = validate(
                load(args.input), source_pool,
                require_fourteen_day_complete=args.require_fourteen_day_complete,
            )
            for error in errors:
                print("FAIL:", error)
            if not errors:
                print("OK")
            return int(bool(errors))

        history = load(args.history) if Path(args.history).exists() else {"runs": []}
        current_run = load(args.run)
        cutoff = parse_datetime(current_run["generated_at"]) - timedelta(days=args.retention_days)
        runs = [
            item for item in history.get("runs", [])
            if parse_datetime(item["generated_at"]) >= cutoff
            and item.get("run_id") != current_run.get("run_id")
        ] + [current_run]
        runs.sort(key=lambda item: parse_datetime(item["generated_at"]))
        output = {
            "schema_version": "1.1.0",
            "retention_days": args.retention_days,
            "updated_at": parse_datetime(current_run["generated_at"]).isoformat(),
            "runs": runs,
        }
        errors = validate(output, source_pool)
        if errors:
            raise ValueError("；".join(errors))
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("OK")
        return 0
    except Exception as error:
        print("FAIL:", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
