#!/usr/bin/env python3
"""Remote acquisition bridge v2 with resumable, row-conserved article hydration."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from scripts import remote_acquisition_bridge as v1

HYDRATION_KEYS = {
    "schema_version", "operation", "run_id", "main_sha", "window", "batch_sequence",
    "row_ids", "fetch_overrides", "exhausted_row_ids", "exhaustion_evidence",
}
WEB_FALLBACK_KEYS = {
    "schema_version", "operation", "run_id", "main_sha", "window", "batch_sequence",
    "search_provider", "search_query", "search_evidence_url", "searched_at",
    "primary_failure_evidence", "terminal_reason", "results",
}
WEB_FALLBACK_RESULT_KEYS = {
    "result_id", "search_rank", "url", "title", "summary", "published_at",
    "url_evidence", "published_evidence", "discovery_priority_reason", "section",
}
ROW_ID_RE = re.compile(r"^row-[0-9a-f]{24}$")
TERMINAL_ROW_STATUSES = {"content_ready", "outside_window", "unresolved_exhausted"}
ATTEMPT_ROW_STATUSES = TERMINAL_ROW_STATUSES | {"unresolved"}
SOURCE_ROOTS = {"cna": "cna.com.tw", "chinanews": "chinanews.com.cn"}


def _request_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _same_source(url: str, source_id: str) -> bool:
    root = SOURCE_ROOTS.get(source_id)
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
        port = parts.port
    except ValueError:
        return False
    return bool(
        root
        and parts.scheme.lower() == "https"
        and parts.username is None
        and parts.password is None
        and port in {None, 443}
        and (host == root or host.endswith("." + root))
    )


def validate(value: dict[str, Any], expected_main_sha: str) -> dict[str, Any]:
    if value.get("operation") == "web_fallback_materialize":
        unknown = set(value) - WEB_FALLBACK_KEYS
        if unknown:
            raise ValueError(f"unknown request keys: {sorted(unknown)}")
        if value.get("schema_version") != "1.0":
            raise ValueError("schema_version must be 1.0")
        if not v1.RUN_ID_RE.fullmatch(str(value.get("run_id", ""))):
            raise ValueError("run_id is invalid")
        if str(value.get("main_sha", "")) != expected_main_sha:
            raise ValueError("main_sha is invalid or stale")
        window = value.get("window")
        if not isinstance(window, dict) or set(window) != {"start", "end"}:
            raise ValueError("window must contain only start and end")
        start = v1._parse_time(window["start"], "start")
        end = v1._parse_time(window["end"], "end")
        if end - start != timedelta(hours=24):
            raise ValueError("window must be exactly 24 hours")
        sequence = value.get("batch_sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ValueError("batch_sequence must be a positive integer")
        for field in ("search_provider", "search_query", "terminal_reason"):
            if not isinstance(value.get(field), str) or not value[field].strip():
                raise ValueError(f"{field} is required")
        v1._require_public_https_url(value.get("search_evidence_url"), "search_evidence_url")
        searched_at = v1._parse_time(value.get("searched_at"), "searched_at")
        if searched_at > end + timedelta(hours=24) or searched_at < start:
            raise ValueError("searched_at must be bound to the run window")
        failures = value.get("primary_failure_evidence")
        if not isinstance(failures, list) or not failures or not all(
            isinstance(item, str) and item.strip() for item in failures
        ):
            raise ValueError("primary_failure_evidence must contain non-empty evidence")
        results = value.get("results")
        if not isinstance(results, list) or not 1 <= len(results) <= 20:
            raise ValueError("results must contain 1..20 bounded verified search results")
        ids, ranks, urls = [], [], []
        for index, item in enumerate(results):
            if not isinstance(item, dict) or set(item) != WEB_FALLBACK_RESULT_KEYS:
                raise ValueError(f"results[{index}] must contain exactly the canonical result fields")
            for field in (
                "result_id", "url", "title", "summary", "published_at", "url_evidence",
                "published_evidence", "discovery_priority_reason",
            ):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(f"results[{index}].{field} is required")
            if item.get("section") != "GLB":
                raise ValueError(f"results[{index}].section must be GLB")
            rank = item.get("search_rank")
            if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
                raise ValueError(f"results[{index}].search_rank must be a positive integer")
            v1._require_public_https_url(item["url"], f"results[{index}].url")
            published = v1._parse_time(item["published_at"], f"results[{index}].published_at")
            if not start <= published <= end:
                raise ValueError(f"results[{index}].published_at must be inside the exact run window")
            ids.append(item["result_id"])
            ranks.append(rank)
            urls.append(item["url"])
        if len(ids) != len(set(ids)) or len(ranks) != len(set(ranks)) or len(urls) != len(set(urls)):
            raise ValueError("result_id, search_rank, and url must be unique within a batch")
        return value
    if value.get("operation") != "article_hydration":
        return v1.validate_request(value, expected_main_sha=expected_main_sha)
    unknown = set(value) - HYDRATION_KEYS
    if unknown:
        raise ValueError(f"unknown request keys: {sorted(unknown)}")
    if value.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    if not v1.RUN_ID_RE.fullmatch(str(value.get("run_id", ""))):
        raise ValueError("run_id is invalid")
    if str(value.get("main_sha", "")) != expected_main_sha:
        raise ValueError("main_sha is invalid or stale")
    window = value.get("window")
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise ValueError("window must contain only start and end")
    if v1._parse_time(window["end"], "end") - v1._parse_time(window["start"], "start") != timedelta(hours=24):
        raise ValueError("window must be exactly 24 hours")
    sequence = value.get("batch_sequence")
    row_ids = value.get("row_ids")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("batch_sequence must be a positive integer")
    if (
        not isinstance(row_ids, list)
        or not 1 <= len(row_ids) <= 20
        or len(row_ids) != len(set(row_ids))
        or not all(ROW_ID_RE.fullmatch(str(item)) for item in row_ids)
    ):
        raise ValueError("row_ids must contain 1..20 unique canonical row IDs")
    row_id_set = {str(item) for item in row_ids}

    overrides = value.get("fetch_overrides", {})
    if not isinstance(overrides, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in overrides.items()):
        raise ValueError("fetch_overrides must be an object of row_id -> public HTTPS URL")
    if set(overrides) - row_id_set:
        raise ValueError("fetch_overrides may only reference row_ids in this batch")
    for key, url in overrides.items():
        v1._require_public_https_url(url, f"fetch_overrides[{key}]")

    exhausted = value.get("exhausted_row_ids", [])
    if (
        not isinstance(exhausted, list)
        or len(exhausted) != len(set(exhausted))
        or any(str(item) not in row_id_set for item in exhausted)
    ):
        raise ValueError("exhausted_row_ids must be a unique subset of row_ids")
    exhausted_set = {str(item) for item in exhausted}
    if exhausted_set & set(overrides):
        raise ValueError("a row cannot be fetched and declared exhausted in the same batch")

    exhaustion_evidence = value.get("exhaustion_evidence", {})
    if not isinstance(exhaustion_evidence, dict):
        raise ValueError("exhaustion_evidence must be an object keyed by exhausted row_id")
    if set(exhaustion_evidence) != exhausted_set:
        if exhausted_set or exhaustion_evidence:
            raise ValueError("exhaustion_evidence keys must exactly match exhausted_row_ids")
    for row_id, entries in exhaustion_evidence.items():
        if (
            not isinstance(entries, list)
            or not entries
            or not all(isinstance(entry, str) and entry.strip() for entry in entries)
        ):
            raise ValueError(f"exhaustion_evidence[{row_id}] must contain non-empty evidence strings")
    return value


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _append(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path} contains a non-object JSONL record")
        records.append(value)
    return records


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _enhance_source_scan(request: dict[str, Any], runtime: Path, output: Path) -> None:
    python = sys.executable
    source = output / "source-candidates.json"
    gate = output / "news-relevance-gate.json"
    admitted = output / "model-source-candidates.json"
    _run([
        python, str(runtime / "scripts/build_source_candidate_list.py"),
        "--source-pool", str(output / "regional-news-source-pool.json"),
        "--scan-dir", str(output / "source-scans"),
        "--output", str(source),
        "--window-start", request["window"]["start"],
        "--window-end", request["window"]["end"],
    ])
    _run([
        python, str(runtime / "scripts/build_news_relevance_gate.py"),
        "--source-candidates", str(source),
        "--gate-output", str(gate),
        "--admitted-output", str(admitted),
    ])
    _write_hydration_state(output)


def _batch_paths(root: Path, sequence: int) -> tuple[Path, Path, Path, Path]:
    evidence = root / "content-evidence"
    return (
        evidence / f"batch-{sequence:04d}.jsonl",
        evidence / f"batch-{sequence:04d}-row-ids.json",
        evidence / f"batch-{sequence:04d}-fetch-overrides.json",
        evidence / f"batch-{sequence:04d}-result.json",
    )


def prepare_hydration(request: dict[str, Any], runlogs: Path) -> Path:
    root = runlogs / "logs" / "runs" / request["run_id"] / "remote-acquisition"
    batch, _, _, _ = _batch_paths(root, request["batch_sequence"])
    request_hash = _request_sha256(request)
    records = _read_jsonl(batch)
    if records:
        running = [
            record for record in records
            if record.get("record") == "batch_receipt" and record.get("status") == "running"
        ]
        if len(running) != 1 or running[0].get("request_sha256") != request_hash:
            raise ValueError("existing hydration batch does not match this request; do not overwrite")
        return batch
    _append(batch, {
        "record": "batch_receipt",
        "status": "running",
        "run_id": request["run_id"],
        "main_sha": request["main_sha"],
        "window": request["window"],
        "batch_sequence": request["batch_sequence"],
        "row_ids": request["row_ids"],
        "fetch_overrides": request.get("fetch_overrides", {}),
        "exhausted_row_ids": request.get("exhausted_row_ids", []),
        "request_sha256": request_hash,
    })
    return batch


def _result_sequence(path: Path) -> int:
    match = re.fullmatch(r"batch-(\d{4})-result\.json", path.name)
    if not match:
        raise ValueError(f"invalid hydration result filename: {path.name}")
    return int(match.group(1))


def _result_history(root: Path, *, before_sequence: int | None = None) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    latest: dict[str, dict] = {}
    history: dict[str, list[dict]] = {}
    for path in sorted((root / "content-evidence").glob("batch-*-result.json")):
        sequence = _result_sequence(path)
        if before_sequence is not None and sequence >= before_sequence:
            continue
        rows = _load_json(path).get("rows", [])
        if not isinstance(rows, list):
            raise ValueError(f"{path} rows must be an array")
        for row in rows:
            if not isinstance(row, dict) or not ROW_ID_RE.fullmatch(str(row.get("row_id", ""))):
                raise ValueError(f"{path} contains invalid hydration row")
            row_id = str(row["row_id"])
            prior = latest.get(row_id)
            if prior is not None and prior.get("status") != "unresolved":
                raise ValueError(f"terminal hydration row repeated across batches: {row_id}")
            if row.get("status") not in ATTEMPT_ROW_STATUSES:
                raise ValueError(f"invalid hydration row status for {row_id}: {row.get('status')}")
            history.setdefault(row_id, []).append(row)
            latest[row_id] = row
    return latest, history


def _canonical_rows(root: Path) -> dict[str, dict]:
    source = _load_json(root / "source-candidates.json")
    rows = source.get("items", [])
    if not isinstance(rows, list):
        raise ValueError("source-candidates items must be an array")
    return {str(item["row_id"]): item for item in rows}


def _validate_fetch_overrides(request: dict[str, Any], canonical: dict[str, dict]) -> None:
    for row_id, url in request.get("fetch_overrides", {}).items():
        item = canonical[row_id]
        source_id = str(item.get("source_id", ""))
        if source_id == "web_fallback":
            v1._require_public_https_url(url, f"fetch_overrides[{row_id}]")
            canonical_host = (urlsplit(str(item.get("canonical_url", ""))).hostname or "").lower()
            override_host = (urlsplit(str(url)).hostname or "").lower()
            if canonical_host != override_host:
                raise ValueError(f"fetch override for {row_id} left the verified fallback article host")
        elif not _same_source(str(url), source_id):
            raise ValueError(f"fetch override for {row_id} left the configured {source_id} source site")


def _web_fallback_root(runlogs: Path, run_id: str) -> Path:
    return runlogs / "logs" / "runs" / run_id / "remote-acquisition"


def _web_fallback_receipt(root: Path, sequence: int) -> Path:
    return root / "web-fallback" / f"batch-{sequence:04d}.jsonl"


def _web_fallback_batches(root: Path) -> list[dict[str, Any]]:
    batches = []
    for path in sorted((root / "web-fallback").glob("batch-*.json")):
        if re.fullmatch(r"batch-\d{4}\.json", path.name) is None:
            continue
        value = _load_json(path)
        batches.append(value)
    return batches


def prepare_web_fallback(request: dict[str, Any], runlogs: Path) -> Path:
    root = _web_fallback_root(runlogs, request["run_id"])
    receipt_path = _web_fallback_receipt(root, request["batch_sequence"])
    request_hash = _request_sha256(request)
    records = _read_jsonl(receipt_path)
    if records:
        if records[0].get("request_sha256") != request_hash:
            raise ValueError("existing web fallback batch does not match this request")
        return receipt_path
    prior = _web_fallback_batches(root)
    if request["batch_sequence"] != len(prior) + 1:
        raise ValueError("web fallback batch_sequence must continue the durable sequence")
    for batch in prior:
        for field in ("run_id", "main_sha", "window"):
            if batch.get(field) != request.get(field):
                raise ValueError(f"web fallback request changed durable {field}")
    prior_ids = {
        item["result_id"]
        for batch in prior for item in batch.get("results", [])
        if isinstance(item, dict) and "result_id" in item
    }
    prior_ranks = {
        item["search_rank"]
        for batch in prior for item in batch.get("results", [])
        if isinstance(item, dict) and "search_rank" in item
    }
    prior_urls = {
        item["url"]
        for batch in prior for item in batch.get("results", [])
        if isinstance(item, dict) and "url" in item
    }
    if any(
        item["result_id"] in prior_ids
        or item["search_rank"] in prior_ranks
        or item["url"] in prior_urls
        for item in request["results"]
    ):
        raise ValueError("web fallback result identity repeated across batches")
    _append(receipt_path, {
        "record": "batch_receipt", "status": "running",
        "run_id": request["run_id"], "main_sha": request["main_sha"],
        "window": request["window"], "batch_sequence": request["batch_sequence"],
        "request_sha256": request_hash, "result_count": len(request["results"]),
    })
    return receipt_path


def _materialize_web_fallback(root: Path) -> None:
    batches = _web_fallback_batches(root)
    if not batches:
        raise ValueError("no durable web fallback batches exist")
    first = batches[0]
    for expected, batch in enumerate(batches, 1):
        if batch.get("batch_sequence") != expected:
            raise ValueError("web fallback batches must be contiguous from sequence 1")
        for field in ("run_id", "main_sha", "window"):
            if batch.get(field) != first.get(field):
                raise ValueError(f"web fallback batches disagree on {field}")
    pages = []
    ranked = []
    seen_urls: set[str] = set()
    seen_result_ids: set[str] = set()
    seen_ranks: set[int] = set()
    for index, batch in enumerate(batches):
        snapshot_path = root / "web-fallback" / f"batch-{batch['batch_sequence']:04d}-snapshot.json"
        snapshot = {
            "schema_version": "1.0",
            "run_id": batch["run_id"],
            "main_sha": batch["main_sha"],
            "window": batch["window"],
            "batch_sequence": batch["batch_sequence"],
            "search_provider": batch["search_provider"],
            "search_query": batch["search_query"],
            "search_evidence_url": batch["search_evidence_url"],
            "searched_at": batch["searched_at"],
            "primary_failure_evidence": batch["primary_failure_evidence"],
            "results": batch["results"],
            "terminal_marker": batch["terminal_reason"],
        }
        _write_json(snapshot_path, snapshot)
        items = []
        for item in batch["results"]:
            if item["url"] in seen_urls:
                raise ValueError(f"web fallback URL repeated across batches: {item['url']}")
            if item["result_id"] in seen_result_ids or item["search_rank"] in seen_ranks:
                raise ValueError("web fallback result identity repeated across batches")
            seen_urls.add(item["url"])
            seen_result_ids.add(item["result_id"])
            seen_ranks.add(item["search_rank"])
            raw = dict(item)
            raw["acquisition_route"] = "web_search_fallback"
            items.append(raw)
            ranked.append({
                "url": item["url"],
                "title": item["title"],
                "published_at": item["published_at"],
                "discovery_priority_score": max(0, 1000 - int(item["search_rank"])),
                "discovery_priority_reason": item["discovery_priority_reason"],
            })
        next_url = batches[index + 1]["search_evidence_url"] if index + 1 < len(batches) else None
        pages.append({
            "request_url": batch["search_evidence_url"],
            "fetched_at": batch["searched_at"],
            "http_status": 200,
            "snapshot_path": str(snapshot_path.resolve()),
            "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
            "next_url": next_url,
            "extracted_items": items,
        })
    latest = batches[-1]
    metadata = {
        "coverage_complete": False,
        "coverage_status": "degraded_partial",
        "coverage_reason": "configured primary aggregator unavailable; bounded verified host web fallback materialized",
        "missing_segments": ["configured_primary_aggregator_unavailable"],
        "missing_date_variants": [],
    }
    scan_path = root / "source-scans" / "web_fallback.json"
    scan = {
        "schema_version": "1.0.0",
        "source_id": "web_fallback",
        "collector": "verified-web-search-fallback",
        "generated_at": latest["searched_at"],
        "window_start": first["window"]["start"],
        "window_end": first["window"]["end"],
        **metadata,
        "pages": pages,
        "terminal_proof": {
            "type": "source_exhausted",
            "page_index": len(pages),
            "terminal_marker": latest["terminal_reason"],
        },
    }
    _write_json(scan_path, scan)
    ranked.sort(key=lambda item: (item["discovery_priority_score"], item["published_at"], item["url"]), reverse=True)
    coverage_path = root / "source-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8")) if coverage_path.is_file() else []
    if not isinstance(coverage, list):
        raise ValueError("source-coverage.json must contain an array")
    coverage = [item for item in coverage if isinstance(item, dict) and item.get("source_id") != "web_fallback"]
    coverage.append({
        "source_id": "web_fallback",
        "scan_status": "completed",
        **metadata,
        "within_window_count": len(ranked),
        "ranked_count": len(ranked),
        "ranked_items": ranked,
        "selected_for_pool_count": len(ranked),
        "selected_item_urls": [item["url"] for item in ranked],
        "discovery_ranking_completed": True,
        "discovery_ranking_method": "bounded_host_search_rank_v1",
        "failure_reason": None,
        "scan_window_start": first["window"]["start"],
        "scan_window_end": first["window"]["end"],
        "scan_evidence_path": str(scan_path.resolve()),
    })
    _write_json(coverage_path, coverage)


def execute_web_fallback(request: dict[str, Any], runtime: Path, runlogs: Path) -> Path:
    root = _web_fallback_root(runlogs, request["run_id"])
    root.mkdir(parents=True, exist_ok=True)
    sequence = request["batch_sequence"]
    receipt_path = _web_fallback_receipt(root, sequence)
    request_hash = _request_sha256(request)
    prepare_web_fallback(request, runlogs)
    records = _read_jsonl(receipt_path)
    terminal = [record for record in records if record.get("status") in {"passed", "failed"}]
    if records:
        if records[0].get("request_sha256") != request_hash:
            raise ValueError("existing web fallback batch does not match this request")
        if terminal:
            if len(records) != 2 or terminal[0].get("request_sha256") != request_hash:
                raise ValueError("web fallback batch has invalid durable receipts")
            _materialize_web_fallback(root)
            return root
    batch_path = root / "web-fallback" / f"batch-{sequence:04d}.json"
    _write_json(batch_path, request)
    _materialize_web_fallback(root)
    _append(receipt_path, {
        "record": "batch_receipt", "status": "passed",
        "run_id": request["run_id"], "main_sha": request["main_sha"],
        "window": request["window"], "batch_sequence": sequence,
        "request_sha256": request_hash, "result_count": len(request["results"]),
        "batch_sha256": hashlib.sha256(batch_path.read_bytes()).hexdigest(),
    })
    regional_pool = root / "regional-news-source-pool.json"
    if regional_pool.is_file():
        _enhance_source_scan(request, runtime, root)
    return root


def _make_exhausted_result(row_id: str, prior_history: list[dict], evidence: list[str]) -> dict[str, Any]:
    if not prior_history or prior_history[-1].get("status") != "unresolved":
        raise ValueError(f"cannot declare {row_id} exhausted without prior unresolved hydration evidence")
    last = prior_history[-1]
    refs = [str(item).strip() for item in evidence if str(item).strip()]
    return {
        "row_id": row_id,
        "candidate_id": last.get("candidate_id"),
        "canonical_url": last.get("canonical_url"),
        "requested_url": last.get("requested_url") or last.get("canonical_url"),
        "source_id": last.get("source_id"),
        "status": "unresolved_exhausted",
        "actual_url": last.get("actual_url"),
        "content_type": last.get("content_type"),
        "content_sha256": last.get("content_sha256"),
        "article_body_published_at": last.get("article_body_published_at"),
        "article_body_timestamp_evidence": last.get("article_body_timestamp_evidence"),
        "article_body_evidence_url": last.get("article_body_evidence_url"),
        "error": "configured same-source and final host recovery chain exhausted",
        "recovery_evidence": refs,
    }


def _write_hydration_state(root: Path) -> dict[str, Any]:
    canonical = _canonical_rows(root)
    latest, _ = _result_history(root)
    expected = set(canonical)
    unexpected = set(latest) - expected
    if unexpected:
        raise ValueError(f"hydration produced rows outside source candidate universe: {sorted(unexpected)[:3]}")
    missing = sorted(expected - set(latest))
    unresolved = sorted(row_id for row_id, row in latest.items() if row.get("status") == "unresolved")
    terminal = {
        row_id: row for row_id, row in latest.items()
        if row.get("status") in TERMINAL_ROW_STATUSES
    }
    counts = {
        status: sum(row.get("status") == status for row in latest.values())
        for status in ATTEMPT_ROW_STATUSES
    }
    state = {
        "schema_version": "1.0",
        "source_row_count": len(expected),
        "seen_row_count": len(latest),
        "terminal_row_count": len(terminal),
        "missing_row_count": len(missing),
        "unresolved_row_count": len(unresolved),
        "missing_row_ids": missing,
        "unresolved_row_ids": unresolved,
        "status_counts": counts,
        "complete": len(terminal) == len(expected),
    }
    _write_json(root / "content-evidence" / "hydration-state.json", state)
    return state


def _finalize_if_complete(request: dict[str, Any], runtime: Path, runlogs: Path, root: Path) -> None:
    state = _write_hydration_state(root)
    if not state["complete"]:
        return
    source = _load_json(root / "source-candidates.json")
    latest, _ = _result_history(root)
    evidence = []
    for item in source["items"]:
        row_id = item["row_id"]
        result = latest[row_id]
        status = result["status"]
        if status == "content_ready":
            model_status = "pending_semantic_review"
            reason = "article body fetched and authoritative timestamp bound to this row"
            failure = None
        elif status == "outside_window":
            model_status = "outside_window"
            reason = "article-body timestamp proves this listing lead is outside the exact run window"
            failure = None
        elif status == "unresolved_exhausted":
            model_status = "unresolved_exhausted"
            reason = "configured article-body recovery chain exhausted without fabricating evidence"
            failure = {
                "attempted_url": result.get("requested_url") or item["canonical_url"],
                "error": result.get("error") or "hydration recovery exhausted",
                "recovery_evidence": result.get("recovery_evidence", []),
            }
        else:
            raise ValueError(f"non-terminal hydration row reached finalization: {row_id}")
        refs = []
        if result.get("article_body_evidence_url"):
            refs.append(result["article_body_evidence_url"])
        refs += [str(value) for value in result.get("recovery_evidence", []) if str(value).strip()]
        if not refs:
            refs.append(result.get("requested_url") or item["canonical_url"])
        evidence.append({
            "row_id": row_id,
            "candidate_id": item["candidate_id"],
            "admission_status": status,
            "article_body_published_at": result.get("article_body_published_at"),
            "article_body_timestamp_evidence": result.get("article_body_timestamp_evidence"),
            "article_body_evidence_url": result.get("article_body_evidence_url"),
            "content_sha256": result.get("content_sha256"),
            "failure_evidence": failure,
            "model_evidence": {
                "review_status": model_status,
                "reason": reason,
                "evidence_refs": list(dict.fromkeys(refs)),
            },
        })
    article = root / "article-evidence.json"
    _write_json(article, {"schema_version": "1.1", "rows": evidence})
    output = runlogs / "logs" / "runs" / request["run_id"] / "source-row-admissions.json"
    _run([
        sys.executable,
        str(runtime / "scripts/materialize_source_row_admissions.py"),
        "build",
        "--source-candidates", str(root / "source-candidates.json"),
        "--relevance-gate", str(root / "news-relevance-gate.json"),
        "--article-evidence", str(article),
        "--run-id", request["run_id"],
        "--output", str(output),
    ])


def _batch_terminal_receipt(batch: Path) -> dict[str, Any] | None:
    terminals = [
        record for record in _read_jsonl(batch)
        if record.get("record") == "batch_receipt" and record.get("status") in {"passed", "failed"}
    ]
    if len(terminals) > 1:
        raise ValueError(f"hydration batch has multiple terminal receipts: {batch}")
    return terminals[0] if terminals else None


def execute_hydration(request: dict[str, Any], runtime: Path, runlogs: Path) -> Path:
    root = runlogs / "logs" / "runs" / request["run_id"] / "remote-acquisition"
    source_path = root / "source-candidates.json"
    batch, ids_path, overrides_path, result_path = _batch_paths(root, request["batch_sequence"])
    if not source_path.is_file() or not batch.is_file():
        raise ValueError("source-scan candidate universe and running batch receipt are required")
    request_hash = _request_sha256(request)
    terminal_receipt = _batch_terminal_receipt(batch)
    if terminal_receipt is not None:
        if terminal_receipt.get("request_sha256") != request_hash:
            raise ValueError("completed hydration batch does not match this request")
        _finalize_if_complete(request, runtime, runlogs, root)
        return root

    canonical = _canonical_rows(root)
    requested_ids = [str(row_id) for row_id in request["row_ids"]]
    if any(row_id not in canonical for row_id in requested_ids):
        raise ValueError("hydration row_ids must belong to the persisted source candidate universe")
    _validate_fetch_overrides(request, canonical)
    prior_latest, prior_history = _result_history(root, before_sequence=request["batch_sequence"])
    exhausted = {str(row_id) for row_id in request.get("exhausted_row_ids", [])}
    for row_id in requested_ids:
        prior = prior_latest.get(row_id)
        if prior is not None and prior.get("status") in TERMINAL_ROW_STATUSES:
            raise ValueError(f"terminal hydration row cannot be repeated: {row_id}")
        if row_id in exhausted and (prior is None or prior.get("status") != "unresolved"):
            raise ValueError(f"exhaustion requires prior unresolved evidence for row: {row_id}")

    if result_path.is_file():
        result_obj = _load_json(result_path)
        rows = result_obj.get("rows", [])
    else:
        fetch_ids = [row_id for row_id in requested_ids if row_id not in exhausted]
        fetched_by_id: dict[str, dict] = {}
        if fetch_ids:
            _write_json(ids_path, fetch_ids)
            overrides = {
                row_id: url
                for row_id, url in request.get("fetch_overrides", {}).items()
                if row_id in fetch_ids
            }
            command = [
                sys.executable,
                str(runtime / "scripts/hydrate_source_rows.py"),
                "--source-candidates", str(source_path),
                "--row-ids", str(ids_path),
                "--window-start", request["window"]["start"],
                "--window-end", request["window"]["end"],
                "--output", str(result_path.with_suffix(".fetch.json")),
            ]
            if overrides:
                _write_json(overrides_path, overrides)
                command.extend(["--fetch-overrides", str(overrides_path)])
            _run(command)
            fetched = _load_json(result_path.with_suffix(".fetch.json")).get("rows", [])
            fetched_by_id = {str(row["row_id"]): row for row in fetched}
        rows = []
        for row_id in requested_ids:
            if row_id in exhausted:
                rows.append(_make_exhausted_result(
                    row_id,
                    prior_history.get(row_id, []),
                    request["exhaustion_evidence"][row_id],
                ))
            else:
                if row_id not in fetched_by_id:
                    raise ValueError(f"hydration helper omitted requested row: {row_id}")
                rows.append(fetched_by_id[row_id])
        _write_json(result_path, {"schema_version": "1.1", "rows": rows})

    if (
        not isinstance(rows, list)
        or {str(row.get("row_id")) for row in rows if isinstance(row, dict)} != set(requested_ids)
        or len(rows) != len(requested_ids)
    ):
        raise ValueError("hydration result must contain exactly one result for each batch row_id")
    if any(row.get("status") not in ATTEMPT_ROW_STATUSES for row in rows):
        raise ValueError("hydration result contains an invalid row status")

    existing_row_results = {
        str(record.get("row_id")): record
        for record in _read_jsonl(batch)
        if record.get("record") == "row_result"
    }
    for row in rows:
        row_id = str(row["row_id"])
        payload = {"record": "row_result", **row}
        if row_id in existing_row_results:
            prior_payload = existing_row_results[row_id]
            if prior_payload != payload:
                raise ValueError(f"existing batch row_result differs from durable result for {row_id}")
            continue
        _append(batch, payload)

    result_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in ATTEMPT_ROW_STATUSES
    }
    _append(batch, {
        "record": "batch_receipt",
        "status": "passed",
        "run_id": request["run_id"],
        "main_sha": request["main_sha"],
        "window": request["window"],
        "batch_sequence": request["batch_sequence"],
        "request_sha256": request_hash,
        "row_count": len(rows),
        **counts,
        "result_sha256": result_hash,
    })
    _finalize_if_complete(request, runtime, runlogs, root)
    return root


def execute(request: dict[str, Any], runtime: Path, runlogs: Path) -> Path:
    if request["operation"] == "article_hydration":
        return execute_hydration(request, runtime, runlogs)
    if request["operation"] == "web_fallback_materialize":
        return execute_web_fallback(request, runtime, runlogs)
    output = v1.execute_request(request, runtime_root=runtime, run_logs_root=runlogs)
    if request["operation"] == "source_scan":
        _enhance_source_scan(request, runtime, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("parse-comment", "prepare-hydration", "prepare-web-fallback", "execute"):
        command = sub.add_parser(name)
        if name == "parse-comment":
            command.add_argument("--comment-env", required=True)
            command.add_argument("--output", required=True, type=Path)
        else:
            command.add_argument("--request", required=True, type=Path)
            command.add_argument("--run-logs-root", required=True, type=Path)
        command.add_argument("--expected-main-sha", required=True)
        if name == "execute":
            command.add_argument("--runtime-root", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "parse-comment":
        request = validate(
            v1.extract_request_from_comment(os.environ.get(args.comment_env, "")),
            args.expected_main_sha,
        )
        v1._write_json_atomic(args.output, request)
        return 0
    request = validate(json.loads(args.request.read_text(encoding="utf-8")), args.expected_main_sha)
    if args.command == "prepare-hydration":
        if request["operation"] != "article_hydration":
            return 0
        print(prepare_hydration(request, args.run_logs_root))
        return 0
    if args.command == "prepare-web-fallback":
        if request["operation"] != "web_fallback_materialize":
            return 0
        print(prepare_web_fallback(request, args.run_logs_root))
        return 0
    print(execute(request, args.runtime_root, args.run_logs_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
