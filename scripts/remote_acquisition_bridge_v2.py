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
        if not _same_source(str(url), source_id):
            raise ValueError(f"fetch override for {row_id} left the configured {source_id} source site")


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
    output = v1.execute_request(request, runtime_root=runtime, run_logs_root=runlogs)
    if request["operation"] == "source_scan":
        _enhance_source_scan(request, runtime, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("parse-comment", "prepare-hydration", "execute"):
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
    print(execute(request, args.runtime_root, args.run_logs_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
