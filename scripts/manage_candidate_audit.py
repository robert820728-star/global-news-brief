#!/usr/bin/env python3
"""Validate and retain the rolling candidate/source audit."""

import argparse
import json
import sys
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


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_datetime(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def local_disaster_baseline(confirmed_deaths):
    if confirmed_deaths < 50:
        return "D", "未滿 50 人"
    if confirmed_deaths < 100:
        return "C", "50–99 人"
    if confirmed_deaths < 250:
        return "B", "100–249 人"
    return "A-", "250 人以上"


def validate(data, source_pool=None):
    errors = []
    if data.get("schema_version") != "1.1.0":
        errors.append("schema_version 必須是 1.1.0")
    if data.get("retention_days") != 14:
        errors.append("retention_days 必須固定為 14")

    expected_sources = None
    per_source_limit = 30
    allowed_overflow_triggers = set()
    source_scan_evidence_required = False
    source_by_id = {}
    discovery_source_ids = []
    minimum_ready_discovery_sources = 0
    all_configured_source_ids = set()
    ranking_dimensions = {}
    if source_pool:
        expected_sources = [item["source_id"] for item in source_pool.get("sources", [])]
        discovery_source_ids = [
            item["source_id"] for item in source_pool.get("discovery_sources", [])
        ]
        minimum_ready_discovery_sources = int(
            source_pool.get("discovery_policy", {}).get(
                "minimum_ready_sources", len(discovery_source_ids)
            )
        )
        all_configured_source_ids = set(expected_sources) | set(discovery_source_ids)
        expected_source_count = len(expected_sources)
        section_sources = source_pool.get("section_sources", {})
        configured_per_section = source_pool.get("primary_sources_per_section")
        flattened_section_sources = [
            source_id
            for source_ids in section_sources.values()
            for source_id in source_ids
        ] if isinstance(section_sources, dict) else []
        per_source_limit = source_pool.get("per_source_rank_limit", 30)
        allowed_overflow_triggers = set(source_pool.get("mandatory_overflow_triggers", []))
        source_scan_evidence_required = source_pool.get("source_scan_evidence_required") is True
        source_by_id = {
            item["source_id"]: item
            for item in (
                source_pool.get("sources", [])
                + source_pool.get("discovery_sources", [])
            )
        }
        if not expected_sources or len(set(expected_sources)) != expected_source_count:
            errors.append("news-source-pool.json 必須定義至少一個且全部唯一的核心來源")
        if (
            not isinstance(configured_per_section, int)
            or configured_per_section < 1
            or not isinstance(section_sources, dict)
            or not section_sources
            or any(
                not isinstance(source_ids, list)
                or len(source_ids) != configured_per_section
                or len(set(source_ids)) != len(source_ids)
                for source_ids in section_sources.values()
            )
        ):
            errors.append("section_sources 每個板塊必須符合 primary_sources_per_section 且不得重複")
        if flattened_section_sources != expected_sources:
            errors.append("section_sources 展開順序必須與 sources 完全一致")
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

    runs = data.get("runs", [])
    for run_index, run in enumerate(runs, 1):
        run_label = f"runs[{run_index}]"
        coverage = run.get("source_coverage", [])
        if not isinstance(coverage, list):
            errors.append(run_label + ".source_coverage 必須是陣列")
            coverage = []
        coverage_ids = [item.get("source_id") for item in coverage if isinstance(item, dict)]
        legacy_full_coverage = expected_sources is not None and coverage_ids == expected_sources
        discovery_coverage = (
            bool(discovery_source_ids)
            and len(coverage_ids) >= minimum_ready_discovery_sources
            and len(coverage_ids) == len(set(coverage_ids))
            and set(coverage_ids).issubset(set(discovery_source_ids))
        )
        if expected_sources is not None and not (legacy_full_coverage or discovery_coverage):
            errors.append(
                run_label
                + " source coverage 必須是完整舊來源池，或達到最低可用數的 discovery sources"
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
            base_selected = min(within, per_source_limit)
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
            overflow_urls = []
            for overflow_index, overflow in enumerate(overflow_items, 1):
                overflow_label = f"{label}.mandatory_overflow_items[{overflow_index}]"
                if not isinstance(overflow, dict):
                    errors.append(overflow_label + " 必須是物件")
                    continue
                overflow_urls.append(overflow.get("url"))
                if overflow.get("trigger") not in allowed_overflow_triggers:
                    errors.append(overflow_label + " 強制例外觸發類型無效")
                if not isinstance(overflow.get("reason"), str) or not overflow["reason"].strip():
                    errors.append(overflow_label + " 缺少強制例外理由")
            if len(set(overflow_urls)) != len(overflow_urls):
                errors.append(label + " 強制例外網址重複")
            if any(url in ranked_urls[:base_selected] or url not in ranked_urls for url in overflow_urls):
                errors.append(label + " 強制例外只能追加排名 30 之後的站內條目")
            ranked_overflow_order = [url for url in ranked_urls[base_selected:] if url in set(overflow_urls)]
            if overflow_urls != ranked_overflow_order:
                errors.append(label + " 強制例外必須維持原站內排名順序")
            expected_urls = ranked_urls[:base_selected] + overflow_urls
            if selected != len(expected_urls):
                errors.append(label + f" 必須取站內前 {per_source_limit} 則加合格強制例外；不足時取全部")
            if not isinstance(urls, list) or len(urls) != selected or len(set(urls)) != len(urls):
                errors.append(label + " selected_item_urls 數量或唯一性不符")
            elif urls != expected_urls:
                errors.append(label + f" 入池網址必須精確等於站內排序前 {per_source_limit} 則加強制例外")
            raw_total += selected
        if run.get("raw_item_count") != raw_total:
            errors.append(run_label + ".raw_item_count 必須等於全部核心來源入池數量總和")

        candidates = run.get("candidates", [])
        if run.get("deduplicated_candidate_count") != len(candidates):
            errors.append(run_label + ".deduplicated_candidate_count 必須等於去重候選筆數")
        if isinstance(run.get("raw_item_count"), int) and len(candidates) > run["raw_item_count"]:
            errors.append(run_label + " 去重後候選不得多於原始入池條目")

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
                required_grading.add("local_disaster_review")
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
                        errors.append(label + " 已屬軍事／衝突規則的事件不得同時套用地方災害門檻")
                    if isinstance(deaths, int) and not isinstance(deaths, bool) and deaths >= 0:
                        baseline, band = local_disaster_baseline(deaths)
                        actual_order = GRADE_ORDER.get(grade)
                        baseline_order = GRADE_ORDER[baseline]
                        if actual_order is not None and actual_order != baseline_order:
                            if not isinstance(reason, str) or not reason.strip():
                                errors.append(
                                    label + f" {band}的基準為 {baseline}；上調或下調都必須填寫具體調整理由"
                                )
                            if actual_order > baseline_order and not triggers:
                                if deaths < 50 and actual_order >= GRADE_ORDER["C"]:
                                    errors.append(
                                        label + " 普通地方災害未滿 50 人且無特殊意義時不得評為 C 以上"
                                    )
                                else:
                                    errors.append(
                                        label + f" {band}高於 {baseline} 時必須列出可驗證的特殊意義觸發"
                                    )
                        elif triggers and (not isinstance(reason, str) or not reason.strip()):
                            errors.append(label + " 宣告特殊意義時必須填寫具體調整理由")
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
                errors.append(label + " 引用未定義的核心來源")

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
        if set(candidate_url_list) != set(pool_urls):
            errors.append(run_label + " 每個核心來源入池網址都必須歸屬一個去重候選，禁止候選無聲消失")
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
    args = parser.parse_args()
    try:
        source_pool = load(args.source_pool)
        if args.cmd == "validate":
            errors = validate(load(args.input), source_pool)
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
