#!/usr/bin/env python3
"""Experimental URL-title recovery and bounded model-batch manifest."""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import random
import re
import urllib.parse
from pathlib import Path
from typing import Any

from pilot_lossless_article_grouping import canonicalize_url, normalize_title, title_features, title_quality


NAVIGATION_SEGMENTS = {
    "article",
    "articles",
    "home",
    "index",
    "latest",
    "news",
    "story",
    "stories",
    "world",
}
FILE_SUFFIXES = (".html", ".htm", ".shtml", ".php", ".aspx", ".ece")
REQUIRED_FIELDS = ("candidate_id", "source_id", "section", "title", "url", "published_at")


def _is_opaque_segment(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return True
    if raw.casefold() in NAVIGATION_SEGMENTS:
        return True
    if re.fullmatch(r"[0-9]+", raw):
        return True
    if re.fullmatch(r"[0-9a-fA-F]{16,}", raw):
        return True
    if re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", raw):
        return True
    if re.fullmatch(r"[A-Za-z0-9_-]{12,}", raw) and "-" not in raw and "_" not in raw:
        if re.search(r"[A-Za-z]", raw) and re.search(r"[0-9]", raw):
            return True
    return False


def recover_title_from_url(url: str) -> str | None:
    path = urllib.parse.unquote(urllib.parse.urlsplit((url or "").strip()).path)
    candidates = []
    for position, raw_segment in enumerate(path.split("/")):
        segment = raw_segment.strip()
        lower = segment.casefold()
        for suffix in FILE_SUFFIXES:
            if lower.endswith(suffix):
                segment = segment[: -len(suffix)]
                break
        if _is_opaque_segment(segment):
            continue
        words = [word for word in re.split(r"[-_\s]+", segment) if word]
        while words and (words[-1].isdigit() or re.fullmatch(r"[0-9a-f]{8,}", words[-1], re.IGNORECASE)):
            words.pop()
        while words and words[0].casefold() in NAVIGATION_SEGMENTS:
            words.pop(0)
        candidate = " ".join(words).strip()
        normalized = normalize_title(candidate)
        if not normalized or normalized in NAVIGATION_SEGMENTS:
            continue
        ascii_tokens = re.findall(r"[a-z0-9]+", normalized)
        cjk_count = len(re.findall(r"[\u3400-\u9fff]", normalized))
        if title_quality(candidate) != "usable":
            continue
        if len(ascii_tokens) < 4 and cjk_count < 6:
            continue
        candidates.append((len(normalized), position, candidate))
    if not candidates:
        return None
    return max(candidates)[2]


def _validate_items(items: list[dict[str, Any]]) -> None:
    for index, item in enumerate(items):
        for field in REQUIRED_FIELDS:
            if not str(item.get(field, "")).strip():
                raise ValueError(f"item {index} is missing required field: {field}")


def _compact_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": item["_row_id"],
        "candidate_id": item["candidate_id"],
        "source_id": item["source_id"],
        "section": item["section"],
        "original_title": item["title"],
        "recovered_title_candidate": item.get("_recovered_title"),
        "effective_title": item.get("_effective_title"),
        "title_provenance": item.get("_title_provenance"),
        "url": item["url"],
        "published_at": item["published_at"],
    }


def _compact_model_group(group: dict[str, Any]) -> dict[str, Any]:
    published = [item.get("published_at", "") for item in group.get("evidence", []) if item.get("published_at")]
    return {
        "group_id": group["group_id"],
        "section": group.get("section", ""),
        "effective_title": group.get("effective_title", ""),
        "evidence_count": len(group.get("evidence", [])),
        "earliest_published_at": min(published) if published else "",
    }


def build_model_batches(groups: list[dict[str, Any]], batch_size: int) -> list[dict[str, Any]]:
    if batch_size < 1 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100")
    compact = [_compact_model_group(group) for group in groups]
    compact.sort(key=lambda item: (item["section"], item["earliest_published_at"], item["group_id"]))
    batches = []
    for offset in range(0, len(compact), batch_size):
        items = compact[offset : offset + batch_size]
        canonical = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        batches.append(
            {
                "batch_id": f"batch-{offset // batch_size:04d}",
                "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                "items": items,
            }
        )
    return batches


def validate_model_batch_response(expected_batch: dict[str, Any], response: dict[str, Any]) -> dict[str, int]:
    """Reject any model response that does not exactly match its immutable input batch."""
    if not isinstance(response, dict):
        raise ValueError("model batch response must be an object")
    if response.get("batch_id") != expected_batch.get("batch_id"):
        raise ValueError("model batch ID mismatch")
    if response.get("sha256") != expected_batch.get("sha256"):
        raise ValueError("model batch hash mismatch")
    results = response.get("results")
    if not isinstance(results, list):
        raise ValueError("model batch results must be an array")
    expected_ids = [item.get("group_id") for item in expected_batch.get("items", [])]
    returned_ids = [item.get("group_id") if isinstance(item, dict) else None for item in results]
    if (
        any(not group_id for group_id in returned_ids)
        or len(returned_ids) != len(set(returned_ids))
        or collections.Counter(returned_ids) != collections.Counter(expected_ids)
    ):
        raise ValueError("model batch result coverage mismatch")
    return {"validated_results": len(results)}


def _build_group_near_pairs(groups: list[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    groups = [group for group in groups if group.get("group_kind") != "unresolved_title"]
    features = {group["group_id"]: title_features(group.get("effective_title", "")) for group in groups}
    group_by_id = {group["group_id"]: group for group in groups}
    postings: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for group in groups:
        for feature in sorted(features[group["group_id"]]):
            postings[(group.get("section", ""), feature)].append(group["group_id"])
    pairs = set()
    for members in postings.values():
        if 2 <= len(members) <= 60:
            pairs.update(itertools.combinations(sorted(members), 2))
    ranked = []
    for left_id, right_id in pairs:
        union = features[left_id] | features[right_id]
        similarity = len(features[left_id] & features[right_id]) / len(union) if union else 0.0
        if 0.65 <= similarity < 1.0:
            ranked.append(
                {
                    "left_group_id": left_id,
                    "right_group_id": right_id,
                    "left_title": group_by_id[left_id].get("effective_title", ""),
                    "right_title": group_by_id[right_id].get("effective_title", ""),
                    "similarity": round(similarity, 6),
                }
            )
    return sorted(ranked, key=lambda pair: (-pair["similarity"], pair["left_group_id"], pair["right_group_id"]))[:sample_size]


def build_recovered_report(payload: dict[str, Any], batch_size: int, sample_size: int, seed: int) -> dict[str, Any]:
    source_items = payload.get("items")
    if not isinstance(source_items, list):
        raise ValueError("payload must contain an items array")
    _validate_items(source_items)
    items = [dict(item, _row_id=f"row-{index:08d}") for index, item in enumerate(source_items)]
    input_row_ids = [item["_row_id"] for item in items]

    canonical_urls = [canonicalize_url(item["url"]) for item in items]
    canonical_counts = collections.Counter(value for value in canonical_urls if value)
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    unresolved = []
    for item, canonical in zip(items, canonical_urls):
        if title_quality(item["title"]) == "usable":
            item["_effective_title"] = item["title"]
            item["_title_provenance"] = "original"
            item["_recovered_title"] = None
        else:
            recovered = recover_title_from_url(item["url"])
            item["_recovered_title"] = recovered
            item["_effective_title"] = recovered
            item["_title_provenance"] = "url_slug" if recovered else "unresolved"

        if canonical and canonical_counts[canonical] > 1:
            key = ("canonical_url", canonical)
        elif item["_effective_title"]:
            key = ("exact_title", item["section"], normalize_title(item["_effective_title"]))
        else:
            key = ("unresolved_title", item["_row_id"])
            unresolved.append(item)
        buckets[key].append(item)

    groups = []
    for key, members in sorted(buckets.items(), key=lambda pair: repr(pair[0])):
        provenances = {item["_title_provenance"] for item in members}
        if key[0] == "exact_title" and "url_slug" in provenances:
            group_kind = "recovered_exact_title"
        elif key[0] == "exact_title":
            group_kind = "exact_title"
        else:
            group_kind = key[0]
        title_provenance = next(iter(provenances)) if len(provenances) == 1 else "mixed"
        group_id = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()[:20]
        groups.append(
            {
                "group_id": group_id,
                "group_kind": group_kind,
                "section": members[0]["section"],
                "effective_title": members[0].get("_effective_title") or members[0]["title"],
                "title_provenance": title_provenance,
                "row_ids": [item["_row_id"] for item in members],
                "candidate_ids": [item["candidate_id"] for item in members],
                "evidence": [_compact_evidence(item) for item in members],
            }
        )

    rng = random.Random(seed)
    unresolved_sample = rng.sample(unresolved, min(sample_size, len(unresolved)))
    unresolved_sample.sort(key=lambda item: item["_row_id"])
    recovered_multirow = [
        group for group in groups if group["group_kind"] == "recovered_exact_title" and len(group["row_ids"]) > 1
    ]
    model_batches = build_model_batches(groups, batch_size)
    report = {
        "schema_version": "url-recovery-batched-triage-pilot/v1",
        "pilot_only": True,
        "batch_size": batch_size,
        "sample_size": sample_size,
        "seed": seed,
        "input_row_ids": input_row_ids,
        "counts": {
            "input_article_rows": len(items),
            "recovered_title_rows": sum(item["_title_provenance"] == "url_slug" for item in items),
            "unresolved_title_rows": len(unresolved),
            "provisional_groups": len(groups),
            "consolidated_evidence_rows": len(items) - len(groups),
            "recovered_exact_multirow_groups": len(recovered_multirow),
            "model_batches": len(model_batches),
            "automatically_deleted_rows": 0,
            "importance_decisions": 0,
        },
        "groups": groups,
        "model_batches": model_batches,
        "review_queues": {
            "recovered_exact_multirow_groups": recovered_multirow,
            "unresolved_title_sample": [_compact_evidence(item) for item in unresolved_sample],
            "suspected_missed_merges": _build_group_near_pairs(groups, sample_size),
        },
    }
    verify_recovered_report(report)
    return report


def verify_recovered_report(report: dict[str, Any]) -> dict[str, int]:
    expected_rows = report.get("input_row_ids", [])
    groups = report.get("groups", [])
    assigned_rows = [row_id for group in groups for row_id in group.get("row_ids", [])]
    if collections.Counter(assigned_rows) != collections.Counter(expected_rows) or len(assigned_rows) != len(expected_rows):
        raise ValueError("article-row conservation failed")
    expected_groups = [group["group_id"] for group in groups]
    batched_groups = [item["group_id"] for batch in report.get("model_batches", []) for item in batch.get("items", [])]
    if collections.Counter(batched_groups) != collections.Counter(expected_groups) or len(batched_groups) != len(expected_groups):
        raise ValueError("model batch coverage failed")
    batch_size = report.get("batch_size", 0)
    if not 1 <= batch_size <= 100 or any(len(batch.get("items", [])) > batch_size for batch in report.get("model_batches", [])):
        raise ValueError("model batch size failed")
    counts = report.get("counts", {})
    if counts.get("input_article_rows") != len(expected_rows) or counts.get("provisional_groups") != len(groups):
        raise ValueError("report counts do not match assignments")
    return {
        "input_article_rows": len(expected_rows),
        "provisional_groups": len(groups),
        "model_batches": len(report.get("model_batches", [])),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify is None and (args.input is None or args.output is None):
        parser.error("--input and --output are required unless --verify is used")
    return args


def main() -> int:
    args = _parse_args()
    if args.verify:
        report = json.loads(args.verify.read_text(encoding="utf-8"))
        counts = verify_recovered_report(report)
        print(f"RECOVERY_OK input={counts['input_article_rows']} groups={counts['provisional_groups']} batches={counts['model_batches']}")
        return 0
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_recovered_report(payload, args.batch_size, args.sample_size, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = report["counts"]
    print(
        "RECOVERY_OK "
        f"input={counts['input_article_rows']} recovered={counts['recovered_title_rows']} "
        f"unresolved={counts['unresolved_title_rows']} groups={counts['provisional_groups']} "
        f"batches={counts['model_batches']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

