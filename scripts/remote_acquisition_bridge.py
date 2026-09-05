#!/usr/bin/env python3
"""Validate and execute run-bound remote source, article, and media acquisition."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from scripts.hydrate_article_rows import hydrate_rows
from scripts.materialize_news_images import materialize, _write_json_atomic
from scripts.materialize_source_row_admissions import build as build_source_row_admissions

MARKER = "<!-- gnb-remote-acquisition:v1 -->"
RUN_ID_RE = re.compile(r"gnb-\d{8}T\d{6}Z-[0-9a-f]{8}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
ROW_ID_RE = re.compile(r"row-[0-9a-f]{24}")
ALLOWED_KEYS = {
    "schema_version", "operation", "run_id", "main_sha", "window", "media_inputs",
    "source_ids", "article_inputs", "batch_sequence",
}
MEDIA_KEYS = {
    "event_id", "source_page_url", "source_image_url", "source_base_url", "alt", "credit",
    "expected_source_byte_size", "expected_source_sha256", "expected_source_width",
    "expected_source_height",
}
ARTICLE_KEYS = {
    "row_id", "candidate_id", "source_id", "canonical_url", "title",
    "listing_published_at", "fetch_url", "exhaustion_confirmed", "exhaustion_evidence",
}
ARTICLE_SOURCE_IDS = {"cna", "chinanews"}
TERMINAL_ADMISSION_STATUSES = {"content_ready", "outside_window", "unresolved_exhausted"}


def extract_request_from_comment(body: str) -> dict[str, Any]:
    if body.count(MARKER) != 1:
        raise ValueError("comment must contain exactly one remote acquisition marker")
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", body, flags=re.S)
    if len(matches) != 1:
        raise ValueError("comment must contain exactly one JSON request block")
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise ValueError(f"request JSON is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("request must be a JSON object")
    return value


def _parse_time(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _require_public_https_url(value: Any, field: str) -> None:
    try:
        parsed = urlsplit(str(value))
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field} must be a public HTTPS URL") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
    ):
        raise ValueError(f"{field} must be a public HTTPS URL")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError(f"{field} must be a public HTTPS URL")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError(f"{field} must be a public HTTPS URL")


def _require_source_host(value: Any, source_id: str, field: str) -> None:
    _require_public_https_url(value, field)
    host = str(urlsplit(str(value)).hostname or "").rstrip(".").lower()
    allowed_root = {
        "cna": "cna.com.tw",
        "chinanews": "chinanews.com.cn",
    }[source_id]
    if host != allowed_root and not host.endswith("." + allowed_root):
        raise ValueError(f"{field} must remain on the configured {source_id} source site")


def validate_request(value: dict[str, Any], *, expected_main_sha: str) -> dict[str, Any]:
    unknown = set(value) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"unknown request keys: {sorted(unknown)}")
    if value.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    operation = value.get("operation")
    if operation not in {"source_scan", "media_fetch", "article_hydration"}:
        raise ValueError("operation must be source_scan, media_fetch, or article_hydration")
    if not RUN_ID_RE.fullmatch(str(value.get("run_id", ""))):
        raise ValueError("run_id is invalid")
    main_sha = str(value.get("main_sha", ""))
    if not SHA_RE.fullmatch(main_sha) or main_sha != expected_main_sha:
        raise ValueError("main_sha is invalid or stale")
    window = value.get("window")
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise ValueError("window must contain only start and end")
    start = _parse_time(window["start"], "window.start")
    end = _parse_time(window["end"], "window.end")
    if end - start != timedelta(hours=24):
        raise ValueError("window must be exactly 24 hours")

    inputs = value.get("media_inputs")
    source_ids = value.get("source_ids")
    article_inputs = value.get("article_inputs")
    batch_sequence = value.get("batch_sequence")

    if operation == "source_scan":
        if inputs is not None or article_inputs is not None or batch_sequence is not None:
            raise ValueError("source_scan must not contain media_inputs/article_inputs/batch_sequence")
        if not isinstance(source_ids, list) or not source_ids or set(source_ids) - ARTICLE_SOURCE_IDS:
            raise ValueError("source_scan source_ids must contain only regional routes cna/chinanews")
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_scan source_ids must be unique")

    if operation == "media_fetch":
        if source_ids is not None or article_inputs is not None or batch_sequence is not None:
            raise ValueError("media_fetch must not contain source_ids/article_inputs/batch_sequence")
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= 50:
            raise ValueError("media_fetch requires 1 to 50 media_inputs")
        for index, item in enumerate(inputs):
            if not isinstance(item, dict) or set(item) - MEDIA_KEYS:
                raise ValueError(f"media_inputs[{index}] contains invalid keys")
            if not str(item.get("event_id", "")).strip():
                raise ValueError(f"media_inputs[{index}].event_id is required")
            for key in ("source_page_url", "source_image_url"):
                _require_public_https_url(item.get(key), f"media_inputs[{index}].{key}")

    if operation == "article_hydration":
        if source_ids is not None or inputs is not None:
            raise ValueError("article_hydration must not contain source_ids/media_inputs")
        if not isinstance(batch_sequence, int) or isinstance(batch_sequence, bool) or batch_sequence < 1:
            raise ValueError("article_hydration batch_sequence must be a positive integer")
        if not isinstance(article_inputs, list) or not 1 <= len(article_inputs) <= 20:
            raise ValueError("article_hydration requires 1 to 20 article_inputs")
        row_ids: list[str] = []
        for index, item in enumerate(article_inputs):
            if not isinstance(item, dict) or set(item) - ARTICLE_KEYS:
                raise ValueError(f"article_inputs[{index}] contains invalid keys")
            row_id = str(item.get("row_id", ""))
            if not ROW_ID_RE.fullmatch(row_id):
                raise ValueError(f"article_inputs[{index}].row_id is invalid")
            row_ids.append(row_id)
            if not str(item.get("candidate_id", "")).strip():
                raise ValueError(f"article_inputs[{index}].candidate_id is required")
            source_id = str(item.get("source_id", ""))
            if source_id not in ARTICLE_SOURCE_IDS:
                raise ValueError(f"article_inputs[{index}].source_id must be cna or chinanews")
            _require_source_host(
                item.get("canonical_url"),
                source_id,
                f"article_inputs[{index}].canonical_url",
            )
            if not str(item.get("title", "")).strip():
                raise ValueError(f"article_inputs[{index}].title is required")
            listing_time = _parse_time(
                item.get("listing_published_at"),
                f"article_inputs[{index}].listing_published_at",
            )
            if not start <= listing_time <= end:
                raise ValueError(f"article_inputs[{index}].listing_published_at must be inside window")

            fetch_url = item.get("fetch_url")
            exhausted = item.get("exhaustion_confirmed", False)
            exhaustion_evidence = item.get("exhaustion_evidence")
            if not isinstance(exhausted, bool):
                raise ValueError(f"article_inputs[{index}].exhaustion_confirmed must be boolean")
            if exhausted:
                if fetch_url is not None:
                    raise ValueError(f"article_inputs[{index}] exhaustion confirmation must not contain fetch_url")
                if (
                    not isinstance(exhaustion_evidence, list)
                    or not exhaustion_evidence
                    or not all(str(entry).strip() for entry in exhaustion_evidence)
                ):
                    raise ValueError(f"article_inputs[{index}].exhaustion_evidence is required")
            else:
                if exhaustion_evidence is not None:
                    raise ValueError(f"article_inputs[{index}] exhaustion_evidence requires exhaustion_confirmed=true")
                if fetch_url is not None:
                    _require_source_host(
                        fetch_url,
                        source_id,
                        f"article_inputs[{index}].fetch_url",
                    )
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("article_hydration row_id values must be unique")
    return value


def _request_sha256(request: dict[str, Any]) -> str:
    payload = json.dumps(
        request,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path} contains a non-object JSONL row")
        rows.append(value)
    return rows


def _write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    temp.replace(path)


def _canonical_regional_rows(output: Path) -> dict[str, dict]:
    source_candidates = _load_json(output / "source-candidates.json")
    rows = source_candidates.get("items")
    if not isinstance(rows, list):
        raise ValueError("regional source-candidates.json has no items")
    return {str(row["row_id"]): row for row in rows}


def _validate_article_batch_against_canonical(output: Path, request: dict[str, Any]) -> list[dict]:
    canonical = _canonical_regional_rows(output)
    validated: list[dict] = []
    for row in request["article_inputs"]:
        row_id = row["row_id"]
        expected = canonical.get(row_id)
        if expected is None:
            raise ValueError(f"article hydration row is absent from regional source scan: {row_id}")
        for field in ("candidate_id", "source_id", "canonical_url", "title", "published_at"):
            requested_field = "listing_published_at" if field == "published_at" else field
            if str(row.get(requested_field, "")) != str(expected.get(field, "")):
                raise ValueError(f"article hydration canonical mismatch for {row_id}: {requested_field}")
        validated.append(row)
    return validated


def _latest_hydration_evidence(evidence_dir: Path) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    latest: dict[str, dict] = {}
    history: dict[str, list[dict]] = {}
    for path in sorted(evidence_dir.glob("batch-*.jsonl")):
        for row in _load_jsonl(path):
            row_id = str(row.get("row_id", ""))
            if not ROW_ID_RE.fullmatch(row_id):
                raise ValueError(f"invalid hydrated row_id in {path.name}: {row_id}")
            prior = latest.get(row_id)
            if prior is not None and prior.get("admission_status") != "unresolved":
                raise ValueError(f"terminal hydrated row was repeated in a later batch: {row_id}")
            history.setdefault(row_id, []).append(row)
            latest[row_id] = row
    return latest, history


def _try_materialize_regional_ledger(output: Path, run_id: str) -> tuple[Path | None, int]:
    source_candidates = _load_json(output / "source-candidates.json")
    relevance_gate = _load_json(output / "news-relevance-gate.json")
    expected_ids = {str(row["row_id"]) for row in source_candidates.get("items", [])}
    latest, _ = _latest_hydration_evidence(output / "content-evidence")
    unexpected = set(latest) - expected_ids
    if unexpected:
        raise ValueError(f"article hydration contains rows outside regional source universe: {sorted(unexpected)[:3]}")
    terminal = {
        row_id: row
        for row_id, row in latest.items()
        if row.get("admission_status") in TERMINAL_ADMISSION_STATUSES
    }
    remaining_ids = expected_ids - set(terminal)
    if remaining_ids:
        return None, len(remaining_ids)

    evidence_rows = [terminal[row_id] for row_id in sorted(expected_ids)]
    article_evidence = {
        "schema_version": "1.0.0",
        "row_count": len(evidence_rows),
        "rows": evidence_rows,
    }
    _write_json_atomic(output / "article-evidence.json", article_evidence)
    ledger = build_source_row_admissions(
        source_candidates,
        relevance_gate,
        article_evidence,
        run_id=run_id,
    )
    destination = output / "regional-source-row-admissions.json"
    _write_json_atomic(destination, ledger)
    return destination, 0


def _finalize_exhausted(row: dict, history: list[dict]) -> dict:
    if not history or history[-1].get("admission_status") != "unresolved":
        raise RuntimeError(
            f"exhaustion confirmation requires prior unresolved hydration evidence: {row['row_id']}"
        )
    prior_attempts: list[dict] = []
    refs: list[str] = []
    content_sha: str | None = None
    evidence_url = str(row["canonical_url"])
    for item in history:
        attempts = item.get("hydration_attempts")
        if isinstance(attempts, list):
            prior_attempts.extend(attempt for attempt in attempts if isinstance(attempt, dict))
        model = item.get("model_evidence")
        if isinstance(model, dict) and isinstance(model.get("evidence_refs"), list):
            refs.extend(str(ref) for ref in model["evidence_refs"] if str(ref).strip())
        if item.get("content_sha256"):
            content_sha = str(item["content_sha256"])
        if item.get("article_body_evidence_url"):
            evidence_url = str(item["article_body_evidence_url"])
    exhaustion_evidence = [str(entry).strip() for entry in row["exhaustion_evidence"]]
    prior_attempts.append({
        "status": "exhaustion_confirmed",
        "route": "host_final_fallback",
        "evidence": exhaustion_evidence,
    })
    refs.extend(exhaustion_evidence)
    refs = list(dict.fromkeys(refs)) or [str(row["canonical_url"])]
    return {
        "row_id": row["row_id"],
        "article_body_published_at": None,
        "article_body_timestamp_evidence": None,
        "article_body_evidence_url": evidence_url,
        "content_sha256": content_sha,
        "admission_status": "unresolved_exhausted",
        "model_evidence": {
            "review_status": "unresolved_exhausted",
            "reason": "Canonical article hydration remained unresolved and the host confirmed the configured same-source/final fallback chain was exhausted.",
            "evidence_refs": refs,
        },
        "hydration_attempts": prior_attempts,
    }


def execute_request(request: dict[str, Any], *, runtime_root: Path, run_logs_root: Path) -> Path:
    run_id = request["run_id"]
    output = run_logs_root / "logs" / "runs" / run_id / "remote-acquisition"
    output.mkdir(parents=True, exist_ok=True)

    if request["operation"] == "media_fetch":
        request_hash = _request_sha256(request)
        media_dir = output / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        request_path = media_dir / f"request-{request_hash[:16]}.json"
        receipt_path = media_dir / f"receipt-{request_hash[:16]}.json"
        if receipt_path.is_file():
            return output
        _write_json_atomic(request_path, request)
        records = materialize(request["media_inputs"], media_dir)
        _write_json_atomic(media_dir / f"materialized-images-{request_hash[:16]}.json", records)
        ready = sum(item.get("status") == "ready" for item in records)
        receipt = {
            "schema_version": "1.0",
            "operation": "media_fetch",
            "run_id": run_id,
            "main_sha": request["main_sha"],
            "window": request["window"],
            "request_sha256": request_hash,
            "status": "completed" if ready == len(records) else "failed",
            "requested_count": len(records),
            "ready_count": ready,
        }
        _write_json_atomic(receipt_path, receipt)
        if receipt["status"] != "completed":
            raise RuntimeError("one or more remote media inputs failed")
        return output

    if request["operation"] == "article_hydration":
        if not (output / "source-candidates.json").is_file():
            raise RuntimeError("regional source_scan must complete before article_hydration")
        sequence = int(request["batch_sequence"])
        evidence_dir = output / "content-evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        request_path = evidence_dir / f"request-{sequence:04d}.json"
        batch_path = evidence_dir / f"batch-{sequence:04d}.jsonl"
        receipt_path = evidence_dir / f"batch-{sequence:04d}.receipt.json"
        request_hash = _request_sha256(request)

        if receipt_path.is_file():
            receipt = _load_json(receipt_path)
            if receipt.get("request_sha256") != request_hash:
                raise RuntimeError("article hydration batch_sequence already exists with different request")
            return output
        if request_path.exists() or batch_path.exists():
            raise RuntimeError("article hydration batch has partial durable state; do not overwrite it")

        canonical_inputs = _validate_article_batch_against_canonical(output, request)
        latest, history = _latest_hydration_evidence(evidence_dir)
        for row in canonical_inputs:
            prior = latest.get(row["row_id"])
            if prior is not None and prior.get("admission_status") != "unresolved":
                raise RuntimeError(f"article hydration row is already terminal: {row['row_id']}")
            if row.get("exhaustion_confirmed") and prior is None:
                raise RuntimeError(
                    f"article hydration exhaustion cannot be confirmed before a failed/unresolved attempt: {row['row_id']}"
                )

        _write_json_atomic(request_path, {
            **request,
            "request_sha256": request_hash,
            "status": "running",
        })
        start = _parse_time(request["window"]["start"], "window.start")
        end = _parse_time(request["window"]["end"], "window.end")
        fetch_inputs = [row for row in canonical_inputs if not row.get("exhaustion_confirmed")]
        hydrated_by_id = {
            row["row_id"]: result
            for row, result in zip(
                fetch_inputs,
                hydrate_rows(fetch_inputs, window_start=start, window_end=end),
                strict=True,
            )
        }
        records: list[dict] = []
        for row in canonical_inputs:
            if row.get("exhaustion_confirmed"):
                records.append(_finalize_exhausted(row, history.get(row["row_id"], [])))
            else:
                records.append(hydrated_by_id[row["row_id"]])
        _write_jsonl_atomic(batch_path, records)

        counts = {
            status: sum(row.get("admission_status") == status for row in records)
            for status in ("content_ready", "outside_window", "unresolved", "unresolved_exhausted")
        }
        ledger_path, remaining = _try_materialize_regional_ledger(output, run_id)
        receipt = {
            "schema_version": "1.0",
            "operation": "article_hydration",
            "run_id": run_id,
            "main_sha": request["main_sha"],
            "window": request["window"],
            "batch_sequence": sequence,
            "request_sha256": request_hash,
            "status": "completed",
            "requested_count": len(records),
            **counts,
            "remaining_regional_row_count": remaining,
            "regional_ledger_materialized": ledger_path is not None,
            "regional_ledger_path": str(ledger_path.relative_to(run_logs_root)) if ledger_path else None,
        }
        _write_json_atomic(receipt_path, receipt)
        _write_json_atomic(request_path, {
            **request,
            "request_sha256": request_hash,
            "status": "completed",
            "receipt": receipt_path.name,
        })
        return output

    source_request_path = output / "source-scan-request.json"
    source_receipt_path = output / "receipt.json"
    if source_receipt_path.is_file():
        existing_request = _load_json(source_request_path) if source_request_path.is_file() else None
        if existing_request != request:
            raise RuntimeError("source_scan already completed with a different run-bound request")
        return output
    _write_json_atomic(source_request_path, request)
    checkpoint = output / "checkpoint-window.json"
    _write_json_atomic(checkpoint, {
        "window_start": request["window"]["start"],
        "window_end": request["window"]["end"],
    })
    route_output = output / "source-work"
    route_config = json.loads((runtime_root / "source-route-config.json").read_text(encoding="utf-8-sig"))
    route_config["routes"] = [
        route for route in route_config.get("routes", [])
        if route.get("source_id") in request["source_ids"]
    ]
    route_config["minimum_ready_routes"] = len(request["source_ids"])
    filtered_route_config = output / "regional-source-route-config.json"
    _write_json_atomic(filtered_route_config, route_config)
    source_pool = json.loads((runtime_root / "news-source-pool.json").read_text(encoding="utf-8-sig"))
    source_pool["discovery_sources"] = [
        source for source in source_pool.get("discovery_sources", [])
        if source.get("source_id") in request["source_ids"]
    ]
    source_pool.setdefault("discovery_policy", {})["minimum_ready_sources"] = len(request["source_ids"])
    filtered_source_pool = output / "regional-news-source-pool.json"
    _write_json_atomic(filtered_source_pool, source_pool)
    python = sys.executable
    subprocess.run([
        python, str(runtime_root / "scripts/fetch_source_routes.py"),
        "--route-config", str(filtered_route_config),
        "--output-dir", str(route_output),
        "--window-start", request["window"]["start"],
        "--window-end", request["window"]["end"],
    ], check=True)
    route_receipt = json.loads((route_output / "source-route-coverage.json").read_text(encoding="utf-8"))
    incomplete = [
        item.get("source_id") for item in route_receipt.get("results", [])
        if item.get("route_ready") is not True or item.get("coverage_complete") is not True
    ]
    if incomplete or len(route_receipt.get("results", [])) != len(request["source_ids"]):
        raise RuntimeError(f"regional source coverage incomplete: {incomplete}")
    scan_dir = output / "source-scans"
    subprocess.run([
        python, str(runtime_root / "scripts/materialize_source_scans.py"),
        "--checkpoint", str(checkpoint),
        "--source-pool", str(filtered_source_pool),
        "--route-coverage", str(route_output / "source-route-coverage.json"),
        "--output-dir", str(scan_dir),
        "--coverage-output", str(output / "source-coverage.json"),
    ], check=True)
    subprocess.run([
        python, str(runtime_root / "scripts/build_source_candidate_list.py"),
        "--source-pool", str(filtered_source_pool),
        "--scan-dir", str(scan_dir),
        "--output", str(output / "source-candidates.json"),
        "--window-start", request["window"]["start"],
        "--window-end", request["window"]["end"],
    ], check=True)
    subprocess.run([
        python, str(runtime_root / "scripts/build_news_relevance_gate.py"),
        "--source-candidates", str(output / "source-candidates.json"),
        "--gate-output", str(output / "news-relevance-gate.json"),
        "--admitted-output", str(output / "model-source-candidates.json"),
    ], check=True)
    source_candidates = _load_json(output / "source-candidates.json")
    relevance_gate = _load_json(output / "news-relevance-gate.json")
    row_count = len(source_candidates.get("items", []))
    hydration_count = int(relevance_gate.get("content_hydration_count", 0))
    _write_json_atomic(source_receipt_path, {
        "schema_version": "1.0",
        "operation": "source_scan",
        "run_id": run_id,
        "main_sha": request["main_sha"],
        "window": request["window"],
        "status": "completed",
        "resume_stage": "source-scan",
        "source_row_count": row_count,
        "content_hydration_count": hydration_count,
        "article_hydration_batch_size": 20,
        "article_hydration_required": hydration_count > 0,
    })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    parse = sub.add_parser("parse-comment")
    parse.add_argument("--comment-env", required=True)
    parse.add_argument("--expected-main-sha", required=True)
    parse.add_argument("--output", required=True, type=Path)
    execute = sub.add_parser("execute")
    execute.add_argument("--request", required=True, type=Path)
    execute.add_argument("--expected-main-sha", required=True)
    execute.add_argument("--runtime-root", required=True, type=Path)
    execute.add_argument("--run-logs-root", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "parse-comment":
        request = validate_request(
            extract_request_from_comment(os.environ.get(args.comment_env, "")),
            expected_main_sha=args.expected_main_sha,
        )
        _write_json_atomic(args.output, request)
        return 0
    request = validate_request(
        json.loads(args.request.read_text(encoding="utf-8")),
        expected_main_sha=args.expected_main_sha,
    )
    output = execute_request(request, runtime_root=args.runtime_root, run_logs_root=args.run_logs_root)
    print(json.dumps({"output": str(output), "status": "completed"}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
