#!/usr/bin/env python3
"""Fail closed when a regional-supplement article group is absent from model input."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def empty_counts() -> dict[str, int]:
    return {
        "required_regional_group_count": 0,
        "required_regional_article_row_count": 0,
        "admitted_regional_group_count": 0,
        "admitted_regional_article_row_count": 0,
    }


def validate_local_source_admission(
    preprocessed: Any, selection: Any, source_pool: Any
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts = empty_counts()
    if not isinstance(preprocessed, dict):
        return ["preprocessed artifact must be an object"], counts
    if not isinstance(selection, dict):
        return ["selection artifact must be an object"], counts
    if not isinstance(source_pool, dict):
        return ["source pool must be an object"], counts

    discovery_sources = source_pool.get("discovery_sources")
    if not isinstance(discovery_sources, list):
        return ["source pool discovery_sources must be an array"], counts
    regional_source_ids = {
        source.get("source_id")
        for source in discovery_sources
        if isinstance(source, dict)
        and source.get("role") == "regional_supplement"
        and isinstance(source.get("source_id"), str)
        and source.get("source_id")
    }
    if not regional_source_ids:
        errors.append("source pool has no regional_supplement discovery source")

    articles = preprocessed.get("normalized_articles")
    provisional_groups = preprocessed.get("provisional_article_groups")
    model_groups = selection.get("candidate_groups")
    if not isinstance(articles, list):
        errors.append("normalized_articles must be an array")
        articles = []
    if not isinstance(provisional_groups, list):
        errors.append("provisional_article_groups must be an array")
        provisional_groups = []
    if not isinstance(model_groups, list):
        errors.append("candidate_groups must be an array")
        model_groups = []

    regional_candidate_ids: set[str] = set()
    for index, article in enumerate(articles, start=1):
        if not isinstance(article, dict):
            errors.append(f"normalized_articles[{index}] must be an object")
            continue
        candidate_id = article.get("candidate_id")
        if article.get("source_id") in regional_source_ids:
            if not isinstance(candidate_id, str) or not candidate_id:
                errors.append(f"normalized_articles[{index}] regional row missing candidate_id")
            else:
                regional_candidate_ids.add(candidate_id)

    required_by_group: dict[str, set[str]] = {}
    mapped_regional_ids: set[str] = set()
    for index, group in enumerate(provisional_groups, start=1):
        if not isinstance(group, dict):
            errors.append(f"provisional_article_groups[{index}] must be an object")
            continue
        group_id = group.get("cluster_id")
        candidate_ids = group.get("candidate_ids")
        if not isinstance(group_id, str) or not group_id:
            errors.append(f"provisional_article_groups[{index}] missing cluster_id")
            continue
        if not isinstance(candidate_ids, list) or not all(
            isinstance(candidate_id, str) and candidate_id for candidate_id in candidate_ids
        ):
            errors.append(f"{group_id} candidate_ids must be a non-empty string array")
            continue
        required = set(candidate_ids).intersection(regional_candidate_ids)
        if required:
            required_by_group[group_id] = required
            mapped_regional_ids.update(required)

    for candidate_id in sorted(regional_candidate_ids - mapped_regional_ids):
        errors.append(f"regional candidate row is not mapped to a provisional group: {candidate_id}")

    counts["required_regional_group_count"] = len(required_by_group)
    counts["required_regional_article_row_count"] = len(regional_candidate_ids)

    declared_ids = [
        group.get("group_id")
        for group in model_groups
        if isinstance(group, dict) and isinstance(group.get("group_id"), str)
    ]
    for group_id, total in sorted(Counter(declared_ids).items()):
        if total > 1:
            errors.append(f"duplicate model candidate group: {group_id}")
    model_by_id = {
        group.get("group_id"): group
        for group in model_groups
        if isinstance(group, dict) and isinstance(group.get("group_id"), str)
    }

    admitted_rows: set[str] = set()
    for group_id, required_ids in sorted(required_by_group.items()):
        model_group = model_by_id.get(group_id)
        if model_group is None:
            errors.append(f"missing regional group: {group_id}")
            continue
        counts["admitted_regional_group_count"] += 1
        admitted_ids = model_group.get("candidate_ids")
        if not isinstance(admitted_ids, list):
            errors.append(f"{group_id} candidate_ids must be an array")
            continue
        admitted_set = {
            candidate_id
            for candidate_id in admitted_ids
            if isinstance(candidate_id, str) and candidate_id
        }
        missing_ids = sorted(required_ids - admitted_set)
        if missing_ids:
            errors.append(
                f"{group_id} missing regional candidate rows: {', '.join(missing_ids)}"
            )
        admitted_rows.update(required_ids.intersection(admitted_set))

    counts["admitted_regional_article_row_count"] = len(admitted_rows)
    return errors, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preprocessed", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--source-pool", required=True)
    args = parser.parse_args(argv)
    try:
        preprocessed = json.loads(Path(args.preprocessed).read_text(encoding="utf-8"))
        selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))
        source_pool = json.loads(Path(args.source_pool).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}")
        return 1

    errors, counts = validate_local_source_admission(preprocessed, selection, source_pool)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
        return 1
    print("OK " + json.dumps(counts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

