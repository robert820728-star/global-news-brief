#!/usr/bin/env python3
"""Validate and retain the rolling candidate/source audit."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

AUTO_SELECT = {"SS", "S+", "S", "S-", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"}
LOW_GRADES = {"D", "E"}
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


def validate(data, source_pool=None):
    errors = []
    if data.get("schema_version") != "1.1.0":
        errors.append("schema_version 必須是 1.1.0")
    if data.get("retention_days") != 14:
        errors.append("retention_days 必須固定為 14")

    expected_sources = None
    per_source_limit = 30
    allowed_overflow_triggers = set()
    if source_pool:
        expected_sources = [item["source_id"] for item in source_pool.get("sources", [])]
        per_source_limit = source_pool.get("per_source_rank_limit", 30)
        allowed_overflow_triggers = set(source_pool.get("mandatory_overflow_triggers", []))
        if len(expected_sources) != 10 or len(set(expected_sources)) != 10:
            errors.append("news-source-pool.json 必須恰好定義 10 個唯一來源")
        ranking = source_pool.get("ranking", {})
        cultural_rule = source_pool.get("cultural_industry_event_rule", {})
        if cultural_rule.get("first_large_award_suspension_min_grade") != "C":
            errors.append("news-source-pool.json 必須固定大型評選活動首次停辦最低為 C")
        if cultural_rule.get("repeat_without_material_change_allowed_grades") != ["C-", "D"]:
            errors.append("news-source-pool.json 必須將無實質新增的重複停辦降為 C- 或 D")
        if cultural_rule.get("material_change_requires_regrading") is not True:
            errors.append("news-source-pool.json 必須要求出現實質變化時重新評級")
        if ranking.get("method") != "public_value_v1" or sum(ranking.get("dimensions", {}).values()) != 100:
            errors.append("news-source-pool.json 的 public_value_v1 權重必須合計 100")

    for run_index, run in enumerate(data.get("runs", []), 1):
        run_label = f"runs[{run_index}]"
        coverage = run.get("source_coverage", [])
        if not isinstance(coverage, list):
            errors.append(run_label + ".source_coverage 必須是陣列")
            coverage = []
        coverage_ids = [item.get("source_id") for item in coverage if isinstance(item, dict)]
        if expected_sources is not None and coverage_ids != expected_sources:
            errors.append(run_label + " 必須依固定順序完成 10 個核心來源確認")

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
            errors.append(run_label + ".raw_item_count 必須等於十站入池數量總和")

        candidates = run.get("candidates", [])
        if run.get("deduplicated_candidate_count") != len(candidates):
            errors.append(run_label + ".deduplicated_candidate_count 必須等於去重候選筆數")
        if isinstance(run.get("raw_item_count"), int) and len(candidates) > run["raw_item_count"]:
            errors.append(run_label + " 去重後候選不得多於原始入池條目")

        valid_source_ids = set(expected_sources or coverage_ids)
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
            errors.append(run_label + " 每個十站入池網址都必須歸屬一個去重候選，禁止候選無聲消失")
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
        Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("OK")
        return 0
    except Exception as error:
        print("FAIL:", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
