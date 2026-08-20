#!/usr/bin/env python3
"""Deterministically normalize and cluster daily-news candidates.

This stage deliberately does not select, grade, verify, or discard candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
    ]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def title_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^0-9A-Za-z\u3400-\u9fff]+", " ", value.casefold())
    chunks = [chunk for chunk in normalized.split() if chunk]
    tokens: set[str] = {
        chunk for chunk in chunks if not re.search(r"[\u3400-\u9fff]", chunk)
    }
    for chunk in chunks:
        if re.search(r"[\u3400-\u9fff]", chunk) and len(chunk) > 1:
            tokens.update(chunk[index : index + 2] for index in range(len(chunk) - 1))
    return tokens


def similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def preprocess(data: dict, threshold: float) -> dict:
    window_start = parse_time(data["window_start"])
    window_end = parse_time(data["window_end"])
    raw_candidates = data["items"] if "items" in data else data.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise ValueError("source candidate list items/candidates 必須是陣列")
    prepared = []
    outside = []
    seen_urls: dict[str, str] = {}

    for index, raw in enumerate(raw_candidates, start=1):
        item = dict(raw)
        item.setdefault("candidate_id", f"candidate-{index:04d}")
        item["canonical_url"] = canonical_url(item.get("url", ""))
        published = parse_time(item["published_at"])
        item["within_window"] = window_start <= published <= window_end
        item["title_tokens"] = sorted(title_tokens(item.get("title", "")))
        if not item["within_window"]:
            outside.append(item)
            continue
        duplicate_of = seen_urls.get(item["canonical_url"])
        if duplicate_of:
            item["exact_duplicate_of"] = duplicate_of
        else:
            seen_urls[item["canonical_url"]] = item["candidate_id"]
        prepared.append(item)

    clusters: list[dict] = []
    for item in prepared:
        if item.get("exact_duplicate_of"):
            target = next(c for c in clusters if item["exact_duplicate_of"] in c["candidate_ids"])
            target["candidate_ids"].append(item["candidate_id"])
            target["urls"].append(item["canonical_url"])
            continue
        tokens = set(item["title_tokens"])
        best = None
        best_score = 0.0
        for cluster in clusters:
            if item.get("section") != cluster.get("section"):
                continue
            score = similarity(tokens, set(cluster["token_union"]))
            if score > best_score:
                best, best_score = cluster, score
        if best is not None and best_score >= threshold:
            best["candidate_ids"].append(item["candidate_id"])
            best["urls"].append(item["canonical_url"])
            best["token_union"] = sorted(set(best["token_union"]) | tokens)
            best["similarity_scores"].append(round(best_score, 4))
        else:
            digest = hashlib.sha256(
                (item.get("section", "UNK") + "|" + " ".join(sorted(tokens))).encode("utf-8")
            ).hexdigest()[:16]
            clusters.append(
                {
                    "cluster_id": f"cluster-{digest}",
                    "section": item.get("section"),
                    "candidate_ids": [item["candidate_id"]],
                    "urls": [item["canonical_url"]],
                    "token_union": sorted(tokens),
                    "similarity_scores": [],
                    "requires_semantic_review": True,
                }
            )

    canonical_url_count = len(seen_urls)
    provisional_title_cluster_count = len(clusters)
    article_count_receipt = {
        "input_article_row_count": len(raw_candidates),
        "within_window_article_row_count": len(prepared),
        "outside_window_article_row_count": len(outside),
        "canonical_url_count": canonical_url_count,
        "exact_url_duplicate_row_count": len(prepared) - canonical_url_count,
        "provisional_title_cluster_count": provisional_title_cluster_count,
        "title_cluster_merged_url_count": canonical_url_count - provisional_title_cluster_count,
    }

    return {
        "window_start": data["window_start"],
        "window_end": data["window_end"],
        "article_row_count": len(raw_candidates),
        "within_window_article_row_count": len(prepared),
        "outside_window_articles": outside,
        "normalized_articles": prepared,
        "provisional_article_groups": clusters,
        "article_count_receipt": article_count_receipt,
        "semantic_event_creation_performed": False,
        "selection_or_grading_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--similarity-threshold", type=float, default=0.55)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = preprocess(data, args.similarity_threshold)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
