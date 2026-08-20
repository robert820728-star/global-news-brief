#!/usr/bin/env python3
"""Experimental conservative local semantic event clustering."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any


FACT_PATTERNS = {
    "deaths": (
        r"\b(?:kills?|killed|dead|deaths?|death\s+toll(?:\s+(?:rises?|rose|reaches?|reached|at|to))?)\D{0,16}(\d[\d,]*)\b",
        r"(\d[\d,]*)\s*(?:人)?\s*(?:死亡|遇難|罹難|喪生)",
    ),
    "injured": (
        r"\b(?:injures?|injured|wounded)\D{0,16}(\d[\d,]*)\b",
        r"(\d[\d,]*)\s*(?:人)?\s*(?:受傷|傷者)",
    ),
    "missing": (
        r"\b(?:missing)\D{0,16}(\d[\d,]*)\b",
        r"(\d[\d,]*)\s*(?:人)?\s*(?:失蹤|失聯)",
    ),
    "evacuated": (
        r"\b(?:evacuates?|evacuated|displaced)\D{0,16}(\d[\d,]*)\b",
        r"(\d[\d,]*)\s*(?:人)?\s*(?:撤離|疏散|轉移)",
    ),
}
GENERIC_IDENTIFIER_WORDS = {"arid", "content", "detail", "document", "file", "item", "mil", "news", "report"}
GENERIC_IDENTITY_WORDS = {
    "about", "after", "against", "amid", "among", "and", "announces", "before", "call", "conference",
    "could", "decision", "earnings", "from", "into", "latest", "meeting", "more", "over", "plans", "report",
    "reports", "says", "statement", "than", "that", "the", "this", "today", "transcript", "under", "with",
}


def _number_magnitude(value: int) -> str:
    if value <= 0:
        return "none"
    if value < 10:
        return "ones"
    if value < 100:
        return "tens"
    if value < 1_000:
        return "hundreds"
    if value < 10_000:
        return "thousands"
    return "ten_thousands_plus"


def _magnitude_index(value: int) -> int:
    order = {"none": 0, "ones": 1, "tens": 2, "hundreds": 3, "thousands": 4, "ten_thousands_plus": 5}
    return order[_number_magnitude(value)]


def extract_fact_anchors(text: str) -> dict[str, list[int]]:
    result = {fact: [] for fact in FACT_PATTERNS}
    for fact, patterns in FACT_PATTERNS.items():
        values = set()
        for pattern in patterns:
            for raw in re.findall(pattern, text or "", flags=re.IGNORECASE):
                values.add(int(raw.replace(",", "")))
        result[fact] = sorted(values)
    return result


def is_semantic_title_eligible(title: str) -> bool:
    value = (title or "").strip()
    if len(re.findall(r"[\u3400-\u9fff]", value)) >= 6:
        return True
    tokens = re.findall(r"[A-Za-z0-9]+", value)
    descriptive = []
    for token in tokens:
        lower = token.casefold()
        if lower in GENERIC_IDENTIFIER_WORDS or token.isdigit():
            continue
        if re.fullmatch(r"[0-9a-f]{4,}", lower):
            continue
        if re.search(r"[A-Za-z]", token) and re.search(r"[0-9]", token):
            continue
        if len(token) >= 2 and token.isalpha():
            descriptive.append(token)
    return len(descriptive) >= 3 and sum(len(token) for token in descriptive) >= 15


def _identity_anchors(title: str) -> set[str]:
    value = (title or "").casefold()
    anchors = {
        f"w:{token}"
        for token in re.findall(r"[a-z]+", value)
        if len(token) >= 3 and token not in GENERIC_IDENTITY_WORDS and token not in GENERIC_IDENTIFIER_WORDS
    }
    cjk = "".join(re.findall(r"[\u3400-\u9fff]", value))
    anchors.update(f"c:{cjk[index:index + 3]}" for index in range(max(0, len(cjk) - 2)))
    return anchors


def _char_ngrams(title: str) -> set[str]:
    value = "".join(re.findall(r"[a-z0-9\u3400-\u9fff]", (title or "").casefold()))
    return {value[index:index + 3] for index in range(max(0, len(value) - 2))}


def surface_identity_evidence(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_title = left.get("effective_title", "")
    right_title = right.get("effective_title", "")
    left_ngrams = _char_ngrams(left_title)
    right_ngrams = _char_ngrams(right_title)
    union = left_ngrams | right_ngrams
    shared_anchors = _identity_anchors(left_title) & _identity_anchors(right_title)
    return {
        "char_ngram_jaccard": round(len(left_ngrams & right_ngrams) / len(union), 6) if union else 0.0,
        "shared_identity_anchors": len(shared_anchors),
        "shared_anchor_values": sorted(shared_anchors),
    }


def build_semantic_texts(groups: list[dict[str, Any]], summaries_by_row_id: dict[str, str]) -> list[str]:
    texts = []
    for group in groups:
        parts = []
        title = str(group.get("effective_title", "")).strip()
        if title:
            parts.append(title)
        for row_id in group.get("row_ids", []):
            summary = str(summaries_by_row_id.get(row_id, "")).strip()
            if summary and summary.casefold() not in {part.casefold() for part in parts}:
                parts.append(summary)
        texts.append("\n".join(parts)[:2000])
    return texts


def select_embedding_groups(groups: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    ordered = sorted(groups, key=lambda item: item["group_id"])
    if sample_size <= 0 or sample_size >= len(ordered):
        return ordered
    buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for group in ordered:
        buckets[str(group.get("section", "UNKNOWN"))].append(group)
    quotas = {}
    fractions = []
    for section, members in sorted(buckets.items()):
        exact = sample_size * len(members) / len(ordered)
        quota = max(1, math.floor(exact))
        quotas[section] = min(quota, len(members))
        fractions.append((exact - math.floor(exact), section))
    while sum(quotas.values()) > sample_size:
        section = max((name for name in quotas if quotas[name] > 1), key=lambda name: quotas[name])
        quotas[section] -= 1
    for _, section in sorted(fractions, reverse=True):
        if sum(quotas.values()) >= sample_size:
            break
        if quotas[section] < len(buckets[section]):
            quotas[section] += 1
    selected = []
    for section, members in sorted(buckets.items()):
        rng = random.Random(f"{seed}:{section}")
        selected.extend(rng.sample(members, quotas[section]))
    return sorted(selected, key=lambda item: item["group_id"])


def embedding_vector_manifest(
    groups: list[dict[str, Any]],
    model_name: str,
    embedding_text: str,
) -> dict[str, Any]:
    return {
        "schema_version": "local-semantic-vector-manifest/v1",
        "model_name": model_name,
        "embedding_text": embedding_text,
        "group_ids": [group["group_id"] for group in groups],
    }


def embed_texts(
    texts: list[str],
    model_name: str,
    cache_dir: str,
    embedder_factory: Any | None = None,
) -> Any:
    import numpy as np

    if embedder_factory is None:
        from fastembed import TextEmbedding

        embedder_factory = TextEmbedding
    embedder = embedder_factory(model_name=model_name, cache_dir=cache_dir)
    matrix = np.asarray(list(embedder.embed(texts)), dtype=np.float32)
    if matrix.ndim != 2 or len(matrix) != len(texts):
        raise ValueError("embedding provider returned an invalid matrix")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding provider returned a zero vector")
    return matrix / norms


def nearest_neighbor_pairs(vectors: Any, top_k: int, minimum_similarity: float) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if not -1.0 <= minimum_similarity <= 1.0:
        raise ValueError("minimum_similarity must be between -1 and 1")
    import numpy as np
    from usearch.index import Index

    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or not len(matrix):
        raise ValueError("vectors must be a non-empty two-dimensional matrix")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("vectors must be non-zero")
    matrix = matrix / norms
    index = Index(ndim=matrix.shape[1], metric="cos", dtype="f32", connectivity=16, expansion_add=128, expansion_search=128)
    keys = np.arange(len(matrix), dtype=np.uint64)
    index.add(keys, matrix, threads=1)
    count = min(len(matrix), top_k + 1)
    matches = index.search(matrix, count=count, exact=len(matrix) <= 100, threads=1)
    best: dict[tuple[int, int], float] = {}
    for source_index, (neighbor_keys, distances) in enumerate(zip(matches.keys, matches.distances)):
        for raw_key, raw_distance in zip(neighbor_keys, distances):
            target_index = int(raw_key)
            if source_index == target_index:
                continue
            left, right = sorted((source_index, target_index))
            similarity = 1.0 - float(raw_distance)
            if similarity >= minimum_similarity:
                best[(left, right)] = max(best.get((left, right), -1.0), similarity)
    return [
        {"left_index": left, "right_index": right, "similarity": round(similarity, 6)}
        for (left, right), similarity in sorted(best.items(), key=lambda item: (-item[1], item[0]))
    ]


def _published_at(group: dict[str, Any]) -> datetime | None:
    values = [item.get("published_at") for item in group.get("evidence", []) if item.get("published_at")]
    if not values:
        return None
    raw = min(values)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def pair_decision(left: dict[str, Any], right: dict[str, Any], similarity: float, config: dict[str, Any]) -> str:
    if left.get("group_kind") == "unresolved_title" or right.get("group_kind") == "unresolved_title":
        return "separate"
    if not is_semantic_title_eligible(left.get("effective_title", "")) or not is_semantic_title_eligible(right.get("effective_title", "")):
        return "separate"
    review_threshold = float(config["review_similarity"])
    if similarity < review_threshold:
        return "separate"
    left_time = _published_at(left)
    right_time = _published_at(right)
    if left_time and right_time:
        hours = abs((right_time - left_time).total_seconds()) / 3600
        if hours > float(config["max_auto_merge_hours"]):
            return "review"
    left_facts = extract_fact_anchors(left.get("effective_title", ""))
    right_facts = extract_fact_anchors(right.get("effective_title", ""))
    if left_facts["deaths"] and right_facts["deaths"]:
        gap = abs(_magnitude_index(max(left_facts["deaths"])) - _magnitude_index(max(right_facts["deaths"])))
        if gap > int(config["max_death_magnitude_gap"]):
            return "review"
    if similarity >= float(config["auto_merge_similarity"]):
        surface = surface_identity_evidence(left, right)
        if (
            surface["char_ngram_jaccard"] >= float(config.get("minimum_char_ngram_jaccard", 0.0))
            and surface["shared_identity_anchors"] >= int(config.get("minimum_shared_identity_anchors", 0))
        ):
            return "auto_merge"
    return "review"


class _UnionFind:
    def __init__(self, values: list[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        keep, move = sorted((left_root, right_root))
        self.parent[move] = keep


def _event_card(members: list[dict[str, Any]]) -> dict[str, Any]:
    member_ids = sorted(item["group_id"] for item in members)
    fact_values = {fact: set() for fact in FACT_PATTERNS}
    row_ids = []
    candidate_ids = []
    titles = []
    for member in members:
        row_ids.extend(member.get("row_ids", []))
        candidate_ids.extend(member.get("candidate_ids", []))
        title = member.get("effective_title", "")
        if title:
            titles.append(title)
        anchors = extract_fact_anchors(title)
        for fact, values in anchors.items():
            fact_values[fact].update(values)
    variants = {fact: sorted(values) for fact, values in fact_values.items()}
    magnitudes = {
        fact: sorted({_number_magnitude(value) for value in values})
        for fact, values in variants.items()
    }
    cluster_seed = "\n".join(member_ids)
    return {
        "semantic_cluster_id": hashlib.sha256(cluster_seed.encode("utf-8")).hexdigest()[:20],
        "member_group_ids": member_ids,
        "row_ids": sorted(row_ids),
        "candidate_ids": sorted(candidate_ids),
        "titles": sorted(set(titles)),
        "fact_variants": variants,
        "fact_magnitudes": magnitudes,
    }


def cluster_from_neighbor_pairs(report: dict[str, Any], pairs: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    groups = report.get("groups", [])
    group_by_id = {group["group_id"]: group for group in groups}
    if len(group_by_id) != len(groups):
        raise ValueError("duplicate provisional group ID")
    union_find = _UnionFind(sorted(group_by_id))
    review_queue = []
    auto_merge_edges = []
    for pair in sorted(pairs, key=lambda item: (item["left_group_id"], item["right_group_id"])):
        left_id = pair["left_group_id"]
        right_id = pair["right_group_id"]
        if left_id not in group_by_id or right_id not in group_by_id or left_id == right_id:
            raise ValueError("invalid neighbor pair")
        decision = pair_decision(group_by_id[left_id], group_by_id[right_id], float(pair["similarity"]), config)
        item = dict(pair, decision=decision)
        if decision == "auto_merge":
            union_find.union(left_id, right_id)
            auto_merge_edges.append(item)
        elif decision == "review":
            review_queue.append(item)

    review_queue = [
        item
        for item in review_queue
        if union_find.find(item["left_group_id"]) != union_find.find(item["right_group_id"])
    ]

    members_by_root: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for group_id in sorted(group_by_id):
        members_by_root[union_find.find(group_id)].append(group_by_id[group_id])
    semantic_clusters = [_event_card(members) for _, members in sorted(members_by_root.items())]
    input_rows = list(report.get("input_row_ids", []))
    output = {
        "schema_version": "local-semantic-event-clustering-pilot/v1",
        "pilot_only": True,
        "config": dict(sorted(config.items())),
        "input_row_ids": input_rows,
        "counts": {
            "input_article_rows": len(input_rows),
            "input_provisional_groups": len(groups),
            "semantic_event_clusters": len(semantic_clusters),
            "consolidated_provisional_groups": len(groups) - len(semantic_clusters),
            "auto_merge_edges": len(auto_merge_edges),
            "ambiguity_review_pairs": len(review_queue),
            "automatically_deleted_rows": 0,
            "importance_decisions": 0,
        },
        "semantic_clusters": semantic_clusters,
        "auto_merge_edges": auto_merge_edges,
        "ambiguity_review_queue": review_queue,
    }
    verify_semantic_report(output)
    return output


def verify_semantic_report(report: dict[str, Any]) -> dict[str, int]:
    expected = report.get("input_row_ids", [])
    assigned = [row_id for cluster in report.get("semantic_clusters", []) for row_id in cluster.get("row_ids", [])]
    if collections.Counter(assigned) != collections.Counter(expected) or len(assigned) != len(expected):
        raise ValueError("semantic row conservation failed")
    counts = report.get("counts", {})
    if counts.get("input_article_rows") != len(expected):
        raise ValueError("semantic report counts mismatch")
    return {"input_rows": len(expected), "semantic_clusters": len(report.get("semantic_clusters", []))}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery-report", type=Path)
    parser.add_argument("--source-input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--vectors", type=Path)
    parser.add_argument("--model-cache", type=Path, default=Path("pilot-model-cache"))
    parser.add_argument("--model-name", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    parser.add_argument("--embedding-text", choices=("title", "title-summary"), default="title")
    parser.add_argument("--embedding-sample-size", type=int, default=0)
    parser.add_argument("--sample-seed", type=int, default=20260821)
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--neighbor-minimum-similarity", type=float, default=0.65)
    parser.add_argument("--auto-merge-similarity", type=float, default=0.94)
    parser.add_argument("--review-similarity", type=float, default=0.82)
    parser.add_argument("--max-auto-merge-hours", type=float, default=48)
    parser.add_argument("--max-death-magnitude-gap", type=int, default=1)
    parser.add_argument("--minimum-char-ngram-jaccard", type=float, default=0.18)
    parser.add_argument("--minimum-shared-identity-anchors", type=int, default=1)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify is None and (args.recovery_report is None or args.source_input is None or args.output is None):
        parser.error("--recovery-report, --source-input, and --output are required unless --verify is used")
    return args


def main() -> int:
    args = _parse_args()
    if args.verify:
        report = json.loads(args.verify.read_text(encoding="utf-8"))
        counts = verify_semantic_report(report)
        print(f"SEMANTIC_OK input={counts['input_rows']} clusters={counts['semantic_clusters']}")
        return 0

    import numpy as np

    started = time.perf_counter()
    recovery_report = json.loads(args.recovery_report.read_text(encoding="utf-8"))
    source_payload = json.loads(args.source_input.read_text(encoding="utf-8"))
    groups = recovery_report.get("groups", [])
    source_items = source_payload.get("items", [])
    summaries_by_row_id = {
        f"row-{index:08d}": str(item.get("summary", ""))
        for index, item in enumerate(source_items)
    }
    resolved_groups = [group for group in groups if group.get("group_kind") != "unresolved_title"]
    all_eligible_groups = [group for group in resolved_groups if is_semantic_title_eligible(group.get("effective_title", ""))]
    eligible_groups = select_embedding_groups(all_eligible_groups, args.embedding_sample_size, args.sample_seed)
    texts = build_semantic_texts(
        eligible_groups,
        summaries_by_row_id if args.embedding_text == "title-summary" else {},
    )
    vector_manifest = embedding_vector_manifest(eligible_groups, args.model_name, args.embedding_text)
    if args.vectors and args.vectors.exists():
        manifest_path = args.vectors.with_suffix(args.vectors.suffix + ".manifest.json")
        if not manifest_path.exists():
            raise ValueError("saved vectors are missing their group-identity manifest")
        saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if saved_manifest != vector_manifest:
            raise ValueError("saved vectors do not match the selected group identities or embedding configuration")
        vectors = np.load(args.vectors)
        if len(vectors) != len(eligible_groups):
            raise ValueError("saved vector count does not match eligible groups")
    else:
        vectors = embed_texts(texts, args.model_name, str(args.model_cache))
        if args.vectors:
            args.vectors.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.vectors, vectors)
            args.vectors.with_suffix(args.vectors.suffix + ".manifest.json").write_text(
                json.dumps(vector_manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    indexed_pairs = nearest_neighbor_pairs(vectors, args.top_k, args.neighbor_minimum_similarity)
    pairs = [
        {
            "left_group_id": eligible_groups[item["left_index"]]["group_id"],
            "right_group_id": eligible_groups[item["right_index"]]["group_id"],
            "similarity": item["similarity"],
        }
        for item in indexed_pairs
    ]
    config = {
        "auto_merge_similarity": args.auto_merge_similarity,
        "review_similarity": args.review_similarity,
        "max_auto_merge_hours": args.max_auto_merge_hours,
        "max_death_magnitude_gap": args.max_death_magnitude_gap,
        "minimum_char_ngram_jaccard": args.minimum_char_ngram_jaccard,
        "minimum_shared_identity_anchors": args.minimum_shared_identity_anchors,
    }
    result = cluster_from_neighbor_pairs(recovery_report, pairs, config)
    result["runtime"] = {
        "model_name": args.model_name,
        "embedding_text": args.embedding_text,
        "eligible_embedded_groups": len(eligible_groups),
        "total_eligible_groups": len(all_eligible_groups),
        "unresolved_singleton_groups": len(groups) - len(resolved_groups),
        "structurally_unusable_singleton_groups": len(resolved_groups) - len(all_eligible_groups),
        "unsampled_eligible_singleton_groups": len(all_eligible_groups) - len(eligible_groups),
        "sample_seed": args.sample_seed,
        "vector_dimensions": int(vectors.shape[1]),
        "top_k": args.top_k,
        "neighbor_minimum_similarity": args.neighbor_minimum_similarity,
        "candidate_neighbor_pairs": len(pairs),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "gpt_api_tokens": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = result["counts"]
    print(
        "SEMANTIC_OK "
        f"input={counts['input_article_rows']} groups={counts['input_provisional_groups']} "
        f"clusters={counts['semantic_event_clusters']} merged={counts['consolidated_provisional_groups']} "
        f"review={counts['ambiguity_review_pairs']} pairs={len(pairs)} "
        f"seconds={result['runtime']['elapsed_seconds']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

