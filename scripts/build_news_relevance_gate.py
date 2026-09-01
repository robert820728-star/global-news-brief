#!/usr/bin/env python3
"""Create a lossless, uncapped routing ledger before article hydration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REGIONAL_SUPPLEMENT_IDS = {"cna", "chinanews"}
HIGH_IMPACT_EVENT_ROOT_CODES = {"13", "14", "17", "18", "19", "20"}
SEVERE_EVENT_TERMS = {
    "attack", "ceasefire", "conflict", "crisis", "disease", "earthquake",
    "evacuation", "explosion", "fire", "flood", "military", "missile",
    "outbreak", "protest", "sanction", "typhoon", "war",
}
RELEVANCE_TERMS = {
    "accident", "attack", "bank", "bill", "border", "budget", "ceasefire",
    "breakthrough", "climate", "conflict", "court", "crisis", "currency",
    "cyber", "defense", "disease",
    "earthquake", "economy", "election", "emergency", "energy", "evacuation",
    "explosion", "fire", "flood", "government", "inflation", "law", "military",
    "medicine", "minister", "missile", "outbreak", "parliament", "policy",
    "president", "protest", "regulation", "research", "sanction", "science",
    "scientist", "scientists", "security", "semiconductor", "space", "strike",
    "tariff", "technology", "trade", "treaty", "typhoon", "vaccine", "war",
}
def _number(signals: dict, key: str) -> float:
    value = signals.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def route_item(item: dict) -> dict:
    source_id = str(item.get("source_id", ""))
    signals = item.get("discovery_signals")
    signals = signals if isinstance(signals, dict) else {}
    reasons = []
    regional_supplement = source_id in REGIONAL_SUPPLEMENT_IDS
    if regional_supplement:
        reasons.append("regional_supplement_complete_admission")
    words = set(re.findall(r"[a-z]+", f"{item.get('title', '')} {item.get('summary', '')}".casefold()))
    matched_terms = sorted(words & RELEVANCE_TERMS)
    num_articles = _number(signals, "num_articles")
    num_sources = _number(signals, "num_sources")
    num_mentions = _number(signals, "num_mentions")
    corroborated = num_articles >= 5 or num_sources >= 3 or num_mentions >= 10
    event_root_code = str(signals.get("event_root_code") or "")
    severe_term = bool(set(matched_terms) & SEVERE_EVENT_TERMS)
    multi_term = len(matched_terms) >= 2
    if corroborated and (severe_term or multi_term):
        reasons.append(
            "compound_relevance_and_corroboration:" + ",".join(matched_terms)
        )
    if reasons and event_root_code in HIGH_IMPACT_EVENT_ROOT_CODES:
        reasons.append("compound_high_impact_event_and_corroboration")
    if reasons and abs(_number(signals, "goldstein_scale")) >= 5:
        reasons.append("compound_goldstein_and_corroboration")
    admitted = regional_supplement or bool(reasons)
    return {
        "candidate_id": item["candidate_id"],
        "source_id": source_id,
        "canonical_url": item["canonical_url"],
        "route": "content_hydration" if admitted else "lightweight_semantic_review",
        "reasons": reasons or ["no_relevance_or_heat_signal"],
        "matched_discovery_signals": signals,
    }


def build_gate(source_candidates: dict) -> dict:
    items = source_candidates.get("items")
    if not isinstance(items, list):
        raise ValueError("source candidate items must be an array")
    decisions = [route_item(item) for item in items]
    hydration = sum(item["route"] == "content_hydration" for item in decisions)
    return {
        "schema_version": "1.0.0",
        "input_article_row_count": len(items),
        "content_hydration_count": hydration,
        "lightweight_semantic_review_count": len(items) - hydration,
        "decisions": decisions,
    }


def build_admitted_candidates(source_candidates: dict, gate: dict) -> dict:
    admitted_ids = {
        item["candidate_id"]
        for item in gate["decisions"]
        if item.get("route") == "content_hydration"
    }
    items = source_candidates.get("items", [])
    source_ids = {item.get("candidate_id") for item in items}
    if admitted_ids - source_ids:
        raise ValueError("gate references candidate ids absent from source candidates")
    filtered = [item for item in items if item.get("candidate_id") in admitted_ids]
    output = dict(source_candidates)
    output["discovery_article_row_count"] = len(items)
    output["admitted_article_row_count"] = len(filtered)
    output["relevance_gate_schema_version"] = gate["schema_version"]
    output["items"] = filtered
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-candidates", required=True)
    parser.add_argument("--gate-output", required=True)
    parser.add_argument("--admitted-output", required=True)
    args = parser.parse_args()
    source_candidates = json.loads(Path(args.source_candidates).read_text(encoding="utf-8"))
    result = build_gate(source_candidates)
    gate_destination = Path(args.gate_output)
    gate_destination.parent.mkdir(parents=True, exist_ok=True)
    gate_destination.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    admitted = build_admitted_candidates(source_candidates, result)
    admitted_destination = Path(args.admitted_output)
    admitted_destination.parent.mkdir(parents=True, exist_ok=True)
    admitted_destination.write_text(
        json.dumps(admitted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "input": result["input_article_row_count"],
        "hydrate": result["content_hydration_count"],
        "lightweight_semantic_review": result["lightweight_semantic_review_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

