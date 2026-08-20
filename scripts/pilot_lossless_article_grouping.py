#!/usr/bin/env python3
"""Experimental, lossless article-row grouping for model review.

This pilot never scores importance, rejects news, or makes publication decisions.
It only consolidates deterministic duplicate evidence and sends unusable titles to
a recovery queue while preserving every input candidate ID exactly once.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import random
import re
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Any


TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
REQUIRED_FIELDS = ("candidate_id", "source_id", "section", "title", "url", "published_at")


def canonicalize_url(value: str) -> str:
    parsed = urllib.parse.urlsplit((value or "").strip())
    host = (parsed.hostname or "").casefold()
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    pairs = [
        (key, item)
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_KEYS and not key.casefold().startswith("utm_")
    ]
    return urllib.parse.urlunsplit(
        (parsed.scheme.casefold(), netloc, parsed.path or "/", urllib.parse.urlencode(sorted(pairs)), "")
    )


def normalize_title(value: str) -> str:
    folded = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", " ", folded).strip()


def title_quality(value: str) -> str:
    raw = (value or "").strip()
    title = normalize_title(value)
    if not title:
        return "placeholder"
    if title.endswith(" news report"):
        return "placeholder"
    if re.fullmatch(r"article ?[0-9a-f -]{6,}", title):
        return "placeholder"
    if re.fullmatch(r"[0-9a-f]{8}(?: [0-9a-f]{4}){3} [0-9a-f]{12}", title):
        return "placeholder"
    if re.fullmatch(r"[A-Za-z0-9_-]{12,}", raw) and re.search(r"[A-Za-z]", raw) and re.search(r"[0-9]", raw):
        return "placeholder"
    if re.fullmatch(r"[a-z][0-9]{8} [0-9]{6,}", title):
        return "placeholder"
    if re.fullmatch(r"comment page [0-9]+", title):
        return "placeholder"
    if title.endswith(" news headlines"):
        return "placeholder"
    if title in {"business economy", "peoplemovesarticle"}:
        return "placeholder"
    return "usable"


def title_features(value: str) -> set[str]:
    normalized = normalize_title(value)
    ascii_words = re.findall(r"[a-z0-9]+", normalized)
    cjk_runs = re.findall(r"[\u3400-\u9fff]+", normalized)
    features = {f"w:{word}" for word in ascii_words if len(word) >= 3}
    for run in cjk_runs:
        features.update(f"c:{run[index:index + 3]}" for index in range(max(0, len(run) - 2)))
    return features


def _compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": item["_pilot_row_id"],
        "candidate_id": item["candidate_id"],
        "source_id": item["source_id"],
        "section": item["section"],
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "published_at": item.get("published_at", ""),
    }


def _validate_items(items: list[dict[str, Any]]) -> None:
    for index, item in enumerate(items):
        for field in REQUIRED_FIELDS:
            if not str(item.get(field, "")).strip():
                raise ValueError(f"item {index} is missing required field: {field}")


def build_near_pair_queue(
    items: list[dict[str, Any]], groups: list[dict[str, Any]], sample_size: int
) -> list[dict[str, Any]]:
    group_by_id = {
        row_id: group_index
        for group_index, group in enumerate(groups)
        for row_id in group["row_ids"]
    }
    usable = [item for item in items if title_quality(item.get("title", "")) == "usable"]
    postings: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    feature_sets: dict[str, set[str]] = {}
    item_by_id = {item["_pilot_row_id"]: item for item in usable}
    for item in usable:
        candidate_id = item["_pilot_row_id"]
        features = title_features(item.get("title", ""))
        feature_sets[candidate_id] = features
        for feature in sorted(features):
            postings[(item["section"], feature)].append(candidate_id)

    candidate_pairs: set[tuple[str, str]] = set()
    for members in postings.values():
        if 2 <= len(members) <= 60:
            candidate_pairs.update(itertools.combinations(sorted(members), 2))

    ranked = []
    for left_id, right_id in candidate_pairs:
        if group_by_id[left_id] == group_by_id[right_id]:
            continue
        left_features = feature_sets[left_id]
        right_features = feature_sets[right_id]
        union = left_features | right_features
        similarity = len(left_features & right_features) / len(union) if union else 0.0
        if similarity >= 0.65:
            ranked.append(
                {
                    "left_candidate_id": left_id,
                    "right_candidate_id": right_id,
                    "left_source_candidate_id": item_by_id[left_id]["candidate_id"],
                    "right_source_candidate_id": item_by_id[right_id]["candidate_id"],
                    "left_title": item_by_id[left_id].get("title", ""),
                    "right_title": item_by_id[right_id].get("title", ""),
                    "left_url": item_by_id[left_id].get("url", ""),
                    "right_url": item_by_id[right_id].get("url", ""),
                    "similarity": round(similarity, 6),
                }
            )
    return sorted(
        ranked,
        key=lambda pair: (-pair["similarity"], pair["left_candidate_id"], pair["right_candidate_id"]),
    )[:sample_size]


def build_report(payload: dict[str, Any], sample_size: int, seed: int) -> dict[str, Any]:
    source_items = payload.get("items")
    if not isinstance(source_items, list):
        raise ValueError("payload must contain an items array")
    _validate_items(source_items)
    items = [dict(item, _pilot_row_id=f"row-{index:08d}") for index, item in enumerate(source_items)]
    row_ids = [item["_pilot_row_id"] for item in items]

    canonical_values = [canonicalize_url(item["url"]) for item in items]
    canonical_counts = collections.Counter(value for value in canonical_values if value)
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    recovery = []
    for item, canonical in zip(items, canonical_values):
        quality = title_quality(item.get("title", ""))
        if canonical and canonical_counts[canonical] > 1:
            key = ("canonical_url", canonical)
        elif quality == "usable":
            key = ("exact_title", item["section"], normalize_title(item["title"]))
        else:
            key = ("needs_title_recovery", item["_pilot_row_id"])
            recovery.append(item)
        buckets[key].append(item)

    groups = []
    for key, members in sorted(buckets.items(), key=lambda pair: repr(pair[0])):
        groups.append(
            {
                "group_id": hashlib.sha256(repr(key).encode("utf-8")).hexdigest()[:20],
                "group_kind": key[0],
                "section": members[0]["section"],
                "title": members[0].get("title", ""),
                "row_ids": [item["_pilot_row_id"] for item in members],
                "candidate_ids": [item["candidate_id"] for item in members],
                "evidence": [_compact_item(item) for item in members],
            }
        )

    assigned = [row_id for group in groups for row_id in group["row_ids"]]
    if collections.Counter(assigned) != collections.Counter(row_ids) or len(assigned) != len(row_ids):
        raise ValueError("article-row conservation failed")

    rng = random.Random(seed)
    recovery_sample = rng.sample(recovery, min(sample_size, len(recovery)))
    recovery_sample.sort(key=lambda item: item["candidate_id"])
    exact_multirow = [
        group for group in groups if group["group_kind"] == "exact_title" and len(group["candidate_ids"]) > 1
    ]
    canonical_multirow = [
        group for group in groups if group["group_kind"] == "canonical_url" and len(group["candidate_ids"]) > 1
    ]
    counts = {
        "input_article_rows": len(items),
        "provisional_groups": len(groups),
        "consolidated_evidence_rows": len(items) - len(groups),
        "canonical_url_multirow_groups": len(canonical_multirow),
        "canonical_url_consolidated_rows": sum(len(group["candidate_ids"]) - 1 for group in canonical_multirow),
        "exact_title_multirow_groups": len(exact_multirow),
        "exact_title_consolidated_rows": sum(len(group["candidate_ids"]) - 1 for group in exact_multirow),
        "title_recovery_rows": len(recovery),
        "automatically_deleted_rows": 0,
        "importance_decisions": 0,
    }
    report = {
        "schema_version": "lossless-article-grouping-pilot/v1",
        "pilot_only": True,
        "seed": seed,
        "sample_size": sample_size,
        "counts": counts,
        "input_row_ids": row_ids,
        "input_candidate_ids": [item["candidate_id"] for item in items],
        "groups": groups,
        "review_queues": {
            "exact_multirow_groups": exact_multirow,
            "canonical_url_multirow_groups": canonical_multirow,
            "title_recovery": [_compact_item(item) for item in recovery_sample],
            "suspected_missed_merges": build_near_pair_queue(items, groups, sample_size),
        },
    }
    verify_report(report)
    return report


def verify_report(report: dict[str, Any]) -> dict[str, int]:
    expected = report.get("input_row_ids", [])
    groups = report.get("groups", [])
    assigned = [row_id for group in groups for row_id in group.get("row_ids", [])]
    if collections.Counter(assigned) != collections.Counter(expected) or len(assigned) != len(expected):
        raise ValueError("article-row conservation failed")
    if len(expected) != len(set(expected)):
        raise ValueError("article-row conservation failed: duplicate input candidate IDs")
    counts = report.get("counts", {})
    if counts.get("input_article_rows") != len(expected) or counts.get("provisional_groups") != len(groups):
        raise ValueError("report counts do not match assignments")
    if counts.get("consolidated_evidence_rows") != len(expected) - len(groups):
        raise ValueError("consolidated row count does not match assignments")
    return {
        "input_article_rows": len(expected),
        "provisional_groups": len(groups),
        "consolidated_evidence_rows": len(expected) - len(groups),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify is None and (args.input is None or args.output is None):
        parser.error("--input and --output are required unless --verify is used")
    return args


def main() -> int:
    args = _parse_args()
    if args.verify is not None:
        report = json.loads(args.verify.read_text(encoding="utf-8"))
        counts = verify_report(report)
        print(
            "CONSERVATION_OK "
            f"input={counts['input_article_rows']} groups={counts['provisional_groups']} "
            f"consolidated={counts['consolidated_evidence_rows']}"
        )
        return 0

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_report(payload, sample_size=args.sample_size, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = report["counts"]
    print(
        "CONSERVATION_OK "
        f"input={counts['input_article_rows']} groups={counts['provisional_groups']} "
        f"consolidated={counts['consolidated_evidence_rows']} recovery={counts['title_recovery_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

