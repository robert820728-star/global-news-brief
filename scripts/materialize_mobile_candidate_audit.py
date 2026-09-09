#!/usr/bin/env python3
"""Checkpoint mobile semantic review and Public Value scoring without re-discovery.

The helper owns transport and conservation only. A model supplies row dispositions
and fully formed candidate objects; this module binds them to immutable audit-input
batches, rejects conflicting rewrites, assembles the run, and delegates final
contract validation to ``manage_candidate_audit``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import manage_candidate_audit  # noqa: E402


ROW_BATCH_SIZE = 20
SCORE_BATCH_SIZE = 4
DISPOSITIONS = {"event_evidence", "non_news", "unresolved", "unresolved_exhausted"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))
        stream.write(b"\n")
        temp = Path(stream.name)
    temp.replace(path)


def identity(value: dict[str, Any]) -> tuple[Any, Any, Any]:
    return value.get("run_id"), value.get("main_sha"), value.get("window")


def require_identity(value: dict[str, Any], authority: dict[str, Any], label: str) -> None:
    if identity(value) != identity(authority):
        raise ValueError(f"{label} changed durable run/main/window identity")


def validate_manifest_batches(manifest_path: Path) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]]]:
    manifest = load(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("ready_for_model_audit") is not True:
        raise ValueError("audit input is not ready for model audit")
    names = manifest.get("batch_files")
    if not isinstance(names, list) or len(names) != manifest.get("batch_count"):
        raise ValueError("audit input manifest has an invalid batch list")
    batches: list[tuple[Path, dict[str, Any]]] = []
    seen: set[str] = set()
    for sequence, name in enumerate(names, 1):
        if not isinstance(name, str):
            raise ValueError("audit input batch name must be a string")
        path = manifest_path.parent / name
        batch = load(path)
        require_identity(batch, manifest, name)
        if batch.get("batch_sequence") != sequence:
            raise ValueError(f"{name} has a non-canonical batch sequence")
        rows = batch.get("rows")
        if not isinstance(rows, list) or len(rows) != batch.get("row_count") or len(rows) > ROW_BATCH_SIZE:
            raise ValueError(f"{name} violates the bounded row count")
        ids = [row.get("row_id") for row in rows if isinstance(row, dict)]
        if len(ids) != len(rows) or any(not isinstance(item, str) or not item for item in ids):
            raise ValueError(f"{name} contains invalid row IDs")
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("audit input row IDs must be globally unique")
        seen.update(ids)
        batches.append((path, batch))
    if len(seen) != manifest.get("source_row_count"):
        raise ValueError("audit input batches do not conserve the manifest row universe")
    return manifest, batches


def append_only_write(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        existing = load(path)
        if digest(existing) != digest(value):
            raise ValueError(f"append-only checkpoint conflict: {path.name}")
        return existing
    atomic_write(path, value)
    return value


def _relative_artifact_path(path: Path, run_root: Path) -> str:
    try:
        return path.resolve().relative_to(run_root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("candidate-audit progress path escaped the run root") from error


def _validate_completed_review_prefix(
    manifest: dict[str, Any], batches: list[tuple[Path, dict[str, Any]]], review_dir: Path
) -> tuple[int, list[str]]:
    completed = 0
    missing_seen = False
    unresolved: list[str] = []
    for sequence, (_path, batch) in enumerate(batches, 1):
        result_path = review_dir / f"batch-{sequence:04d}-result.json"
        receipt_path = review_dir / "receipts" / f"batch-{sequence:04d}.json"
        if not result_path.is_file():
            missing_seen = True
            if receipt_path.exists():
                raise ValueError("row review receipt exists without its result checkpoint")
            continue
        if missing_seen:
            raise ValueError("non-contiguous row review checkpoints")
        if not receipt_path.is_file():
            raise ValueError("row review checkpoint is missing its terminal receipt")
        result = load(result_path)
        receipt = load(receipt_path)
        require_identity(result, manifest, result_path.name)
        require_identity(receipt, manifest, receipt_path.name)
        if result.get("batch_sequence") != sequence or receipt.get("batch_sequence") != sequence:
            raise ValueError("row review checkpoint sequence drifted")
        if result.get("input_batch_sha256") != digest(batch):
            raise ValueError(f"{result_path.name} is not bound to its audit input")
        expected_ids = [row["row_id"] for row in batch["rows"]]
        rows = result.get("rows") if isinstance(result.get("rows"), list) else []
        if Counter(row.get("row_id") for row in rows) != Counter(expected_ids):
            raise ValueError("review checkpoints do not conserve the audit input universe")
        for row in rows:
            validate_review_row(row)
            if row["disposition"] == "unresolved":
                unresolved.append(row["row_id"])
        if receipt.get("status") != "terminal" or receipt.get("result_sha256") != digest(result):
            raise ValueError("row review receipt is not bound to its terminal result")
        completed += 1
    return completed, unresolved


def _validate_completed_score_prefix(
    manifest: dict[str, Any], batches: list[tuple[Path, dict[str, Any]]], result_dir: Path
) -> int:
    completed = 0
    missing_seen = False
    for sequence, (_path, batch) in enumerate(batches, 1):
        result_path = result_dir / f"batch-{sequence:04d}-result.json"
        receipt_path = result_dir / "receipts" / f"batch-{sequence:04d}.json"
        if not result_path.is_file():
            missing_seen = True
            if receipt_path.exists():
                raise ValueError("score receipt exists without its result checkpoint")
            continue
        if missing_seen:
            raise ValueError("non-contiguous score checkpoints")
        if not receipt_path.is_file():
            raise ValueError("score checkpoint is missing its terminal receipt")
        result = load(result_path)
        receipt = load(receipt_path)
        require_identity(result, manifest, result_path.name)
        require_identity(receipt, manifest, receipt_path.name)
        if result.get("batch_sequence") != sequence or receipt.get("batch_sequence") != sequence:
            raise ValueError("score checkpoint sequence drifted")
        if result.get("input_batch_sha256") != digest(batch):
            raise ValueError(f"{result_path.name} is not bound to its score input")
        expected_ids = [event["semantic_event_id"] for event in batch["events"]]
        events = result.get("events") if isinstance(result.get("events"), list) else []
        if Counter(item.get("semantic_event_id") for item in events) != Counter(expected_ids):
            raise ValueError("score checkpoints do not conserve the semantic event universe")
        if receipt.get("status") != "terminal" or receipt.get("result_sha256") != digest(result):
            raise ValueError("score receipt is not bound to its terminal result")
        completed += 1
    return completed


def candidate_audit_progress(
    manifest_path: Path, work_root: Path, candidate_audit_path: Path
) -> dict[str, Any]:
    """Derive the single next legal candidate-audit operation from durable state."""
    manifest, review_batches = validate_manifest_batches(manifest_path)
    run_root = manifest_path.parent.parent
    review_total = len(review_batches)
    review_completed, unresolved = _validate_completed_review_prefix(
        manifest, review_batches, work_root / "row-review"
    )
    base = {
        "schema_version": "1.0.0",
        "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"],
        "window": manifest["window"],
        "pending_work_is_blocker": False,
        "row_review": {
            "total_batch_count": review_total,
            "completed_batch_count": review_completed,
            "remaining_batch_count": review_total - review_completed,
        },
        "event_scoring": {
            "prepared": False,
            "total_batch_count": 0,
            "completed_batch_count": 0,
            "remaining_batch_count": 0,
        },
    }

    audit_exists = candidate_audit_path.is_file()
    if review_completed < review_total:
        if audit_exists:
            raise ValueError("candidate audit exists before row review is complete")
        next_sequence = review_completed + 1
        next_path, next_batch = review_batches[next_sequence - 1]
        return {
            **base, "status": "in_progress", "phase": "row_review",
            "next_operation": "candidate_audit_review",
            "next_batch_sequence": next_sequence,
            "next_input_path": _relative_artifact_path(next_path, run_root),
            "next_input_sha256": digest(next_batch),
            "candidate_audit_path": None, "candidate_audit_sha256": None,
        }

    if unresolved:
        if audit_exists:
            raise ValueError("candidate audit exists while row review remains unresolved")
        return {
            **base, "status": "blocked", "phase": "row_recovery",
            "pending_work_is_blocker": True, "next_operation": None,
            "next_batch_sequence": None, "next_input_path": None,
            "next_input_sha256": None, "candidate_audit_path": None,
            "candidate_audit_sha256": None,
            "blocker": {
                "code": "UNRESOLVED_REVIEW_ROWS_REQUIRE_RECOVERY",
                "row_ids": sorted(unresolved),
            },
        }

    score_manifest_path = work_root / "score-input" / "manifest.json"
    if not score_manifest_path.is_file():
        if audit_exists:
            raise ValueError("candidate audit exists before scoring input is prepared")
        return {
            **base, "status": "in_progress", "phase": "prepare_scoring",
            "next_operation": "candidate_audit_prepare_scoring",
            "next_batch_sequence": None, "next_input_path": None,
            "next_input_sha256": None, "candidate_audit_path": None,
            "candidate_audit_sha256": None,
        }

    score_manifest, score_batches = validate_score_batches(score_manifest_path)
    require_identity(score_manifest, manifest, "score manifest")
    score_total = len(score_batches)
    score_completed = _validate_completed_score_prefix(
        score_manifest, score_batches, work_root / "score-results"
    )
    scoring = {
        "prepared": True,
        "total_batch_count": score_total,
        "completed_batch_count": score_completed,
        "remaining_batch_count": score_total - score_completed,
    }
    if score_completed < score_total:
        if audit_exists:
            raise ValueError("candidate audit exists before event scoring is complete")
        next_sequence = score_completed + 1
        next_path, next_batch = score_batches[next_sequence - 1]
        return {
            **base, "event_scoring": scoring,
            "status": "in_progress", "phase": "event_scoring",
            "next_operation": "candidate_audit_score",
            "next_batch_sequence": next_sequence,
            "next_input_path": _relative_artifact_path(next_path, run_root),
            "next_input_sha256": digest(next_batch),
            "candidate_audit_path": None, "candidate_audit_sha256": None,
        }
    if audit_exists:
        audit = load(candidate_audit_path)
        runs = audit.get("runs") if isinstance(audit, dict) else None
        if not isinstance(runs, list) or not any(
            isinstance(run, dict) and run.get("run_id") == manifest["run_id"] for run in runs
        ):
            raise ValueError("candidate audit does not contain the durable run identity")
        return {
            **base, "event_scoring": scoring,
            "status": "completed", "phase": "completed",
            "next_operation": None, "next_batch_sequence": None,
            "next_input_path": None, "next_input_sha256": None,
            "candidate_audit_path": _relative_artifact_path(candidate_audit_path, run_root),
            "candidate_audit_sha256": digest(audit),
        }
    return {
        **base, "event_scoring": scoring,
        "status": "in_progress", "phase": "finalize",
        "next_operation": "candidate_audit_finalize",
        "next_batch_sequence": None, "next_input_path": None,
        "next_input_sha256": None, "candidate_audit_path": None,
        "candidate_audit_sha256": None,
    }


def validate_review_row(row: dict[str, Any]) -> None:
    disposition = row.get("disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError("review disposition is invalid")
    semantic_event_id = row.get("semantic_event_id")
    if disposition == "event_evidence":
        if not isinstance(semantic_event_id, str) or not semantic_event_id.strip():
            raise ValueError("event_evidence requires semantic_event_id")
    elif semantic_event_id is not None:
        raise ValueError("non-event disposition must not reference a semantic event")
    reason = row.get("reason")
    model = row.get("model_evidence")
    if not isinstance(reason, str) or not reason.strip() or not isinstance(model, dict):
        raise ValueError("review result requires reason and model_evidence")
    refs = model.get("evidence_refs")
    if model.get("review_status") != disposition or not isinstance(model.get("reason"), str):
        raise ValueError("model_evidence must agree with the row disposition")
    if not isinstance(refs, list) or not refs or any(not isinstance(item, str) or not item.strip() for item in refs):
        raise ValueError("model_evidence requires non-empty evidence_refs")


def record_review_result(
    manifest_path: Path, input_batch_path: Path, result_path: Path, output_dir: Path
) -> dict[str, Any]:
    manifest, batches = validate_manifest_batches(manifest_path)
    known = {path.resolve(): batch for path, batch in batches}
    batch = known.get(input_batch_path.resolve())
    if batch is None:
        raise ValueError("input batch is not listed by the audit manifest")
    result = load(result_path)
    if not isinstance(result, dict):
        raise ValueError("review result must be an object")
    require_identity(result, manifest, "review result")
    if result.get("batch_sequence") != batch.get("batch_sequence"):
        raise ValueError("review result batch sequence mismatch")
    rows = result.get("rows")
    if not isinstance(rows, list):
        raise ValueError("review result rows must be an array")
    expected_ids = [item["row_id"] for item in batch["rows"]]
    actual_ids = [item.get("row_id") for item in rows if isinstance(item, dict)]
    if len(actual_ids) != len(rows) or Counter(actual_ids) != Counter(expected_ids):
        raise ValueError("review result must conserve the input row universe exactly")
    for row in rows:
        validate_review_row(row)
    normalized = {
        "schema_version": "1.0.0",
        "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"],
        "window": manifest["window"],
        "batch_sequence": batch["batch_sequence"],
        "input_batch_sha256": digest(batch),
        "row_count": len(rows),
        "rows": sorted(rows, key=lambda item: expected_ids.index(item["row_id"])),
    }
    output = output_dir / f"batch-{batch['batch_sequence']:04d}-result.json"
    stored = append_only_write(output, normalized)
    receipt = {
        "schema_version": "1.0.0",
        "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"],
        "window": manifest["window"],
        "batch_sequence": batch["batch_sequence"],
        "input_batch_sha256": digest(batch),
        "result_sha256": digest(stored),
        "status": "terminal",
    }
    append_only_write(output_dir / "receipts" / f"batch-{batch['batch_sequence']:04d}.json", receipt)
    return receipt


def review_universe(
    manifest_path: Path, review_dir: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest, batches = validate_manifest_batches(manifest_path)
    source_rows = [row for _path, batch in batches for row in batch["rows"]]
    source_by_id = {row["row_id"]: row for row in source_rows}
    reviewed: dict[str, dict[str, Any]] = {}
    for sequence, (_path, batch) in enumerate(batches, 1):
        result_path = review_dir / f"batch-{sequence:04d}-result.json"
        if not result_path.is_file():
            raise ValueError(f"row review checkpoint missing batch {sequence:04d}")
        result = load(result_path)
        require_identity(result, manifest, result_path.name)
        if result.get("input_batch_sha256") != digest(batch):
            raise ValueError(f"{result_path.name} is not bound to its audit input")
        expected_ids = [row["row_id"] for row in batch["rows"]]
        actual = result.get("rows")
        actual_ids = [row.get("row_id") for row in actual] if isinstance(actual, list) else []
        if Counter(expected_ids) != Counter(actual_ids):
            raise ValueError("review checkpoints do not conserve the audit input universe")
        for row in actual:
            validate_review_row(row)
            if row["row_id"] in reviewed:
                raise ValueError("review checkpoint repeats a row")
            reviewed[row["row_id"]] = row
    if set(reviewed) != set(source_by_id):
        raise ValueError("review checkpoints do not conserve the audit input universe")
    return manifest, source_rows, reviewed


def prepare_scoring(manifest_path: Path, review_dir: Path, output_dir: Path) -> dict[str, Any]:
    manifest, source_rows, reviewed = review_universe(manifest_path, review_dir)
    unresolved = sorted(row_id for row_id, row in reviewed.items() if row["disposition"] == "unresolved")
    if unresolved:
        raise ValueError("unresolved rows must be recovered before semantic event scoring")
    grouped: dict[str, list[dict[str, Any]]] = {}
    source_by_id = {row["row_id"]: row for row in source_rows}
    for row_id, review in reviewed.items():
        event_id = review.get("semantic_event_id")
        if review["disposition"] == "event_evidence":
            grouped.setdefault(event_id, []).append({
                "source_row": source_by_id[row_id],
                "review": review,
            })
    events = []
    for event_id in sorted(grouped):
        evidence = sorted(grouped[event_id], key=lambda item: item["source_row"]["row_id"])
        events.append({
            "semantic_event_id": event_id,
            "candidate_urls": sorted({item["source_row"]["canonical_url"] for item in evidence}),
            "source_ids": sorted({item["source_row"]["source_id"] for item in evidence}),
            "sections": sorted({item["source_row"]["section"] for item in evidence}),
            "row_count": len(evidence),
            "rows": evidence,
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_files = []
    for offset in range(0, len(events), SCORE_BATCH_SIZE):
        sequence = offset // SCORE_BATCH_SIZE + 1
        path = output_dir / f"batch-{sequence:04d}.json"
        batch = {
            "schema_version": "1.0.0", "run_id": manifest["run_id"],
            "main_sha": manifest["main_sha"], "window": manifest["window"],
            "batch_sequence": sequence, "event_count": len(events[offset:offset + SCORE_BATCH_SIZE]),
            "events": events[offset:offset + SCORE_BATCH_SIZE],
        }
        append_only_write(path, batch)
        batch_files.append(path.name)
    result = {
        "schema_version": "1.0.0", "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"], "window": manifest["window"],
        "source_row_count": manifest["source_row_count"],
        "semantic_event_count": len(events), "batch_size": SCORE_BATCH_SIZE,
        "batch_count": len(batch_files), "batch_files": batch_files,
        "event_ids": [item["semantic_event_id"] for item in events],
        "complete_row_review": True,
    }
    append_only_write(output_dir / "manifest.json", result)
    return result


def validate_score_batches(manifest_path: Path) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]]]:
    manifest = load(manifest_path)
    names = manifest.get("batch_files")
    if not isinstance(names, list) or len(names) != manifest.get("batch_count"):
        raise ValueError("score input manifest has an invalid batch list")
    batches = []
    event_ids = []
    for sequence, name in enumerate(names, 1):
        path = manifest_path.parent / name
        batch = load(path)
        require_identity(batch, manifest, name)
        if batch.get("batch_sequence") != sequence:
            raise ValueError("score input has non-canonical batch sequence")
        events = batch.get("events")
        if not isinstance(events, list) or len(events) != batch.get("event_count") or len(events) > SCORE_BATCH_SIZE:
            raise ValueError("score input violates the bounded event count")
        event_ids.extend(item.get("semantic_event_id") for item in events if isinstance(item, dict))
        batches.append((path, batch))
    if event_ids != manifest.get("event_ids") or len(set(event_ids)) != len(event_ids):
        raise ValueError("score input batches do not conserve the semantic event universe")
    return manifest, batches


def record_score_result(
    manifest_path: Path, input_batch_path: Path, result_path: Path, output_dir: Path
) -> dict[str, Any]:
    manifest, batches = validate_score_batches(manifest_path)
    known = {path.resolve(): batch for path, batch in batches}
    batch = known.get(input_batch_path.resolve())
    if batch is None:
        raise ValueError("score input batch is not listed by the score manifest")
    result = load(result_path)
    if not isinstance(result, dict):
        raise ValueError("score result must be an object")
    require_identity(result, manifest, "score result")
    if result.get("batch_sequence") != batch.get("batch_sequence"):
        raise ValueError("score result batch sequence mismatch")
    events = result.get("events")
    expected = {item["semantic_event_id"]: item for item in batch["events"]}
    actual_ids = [item.get("semantic_event_id") for item in events if isinstance(item, dict)] if isinstance(events, list) else []
    if Counter(actual_ids) != Counter(expected.keys()):
        raise ValueError("score result must conserve the input semantic event universe exactly")
    normalized_events = []
    for event in events:
        event_id = event["semantic_event_id"]
        candidate = event.get("candidate")
        if not isinstance(candidate, dict) or candidate.get("semantic_event_id") != event_id:
            raise ValueError("scored candidate must preserve semantic_event_id")
        if set(candidate.get("candidate_urls", [])) != set(expected[event_id]["candidate_urls"]):
            raise ValueError("candidate_urls must exactly match event-evidence source URLs")
        normalized_events.append({"semantic_event_id": event_id, "candidate": candidate})
    order = list(expected)
    normalized = {
        "schema_version": "1.0.0", "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"], "window": manifest["window"],
        "batch_sequence": batch["batch_sequence"], "input_batch_sha256": digest(batch),
        "event_count": len(events),
        "events": sorted(normalized_events, key=lambda item: order.index(item["semantic_event_id"])),
    }
    output = output_dir / f"batch-{batch['batch_sequence']:04d}-result.json"
    stored = append_only_write(output, normalized)
    receipt = {
        "schema_version": "1.0.0", "run_id": manifest["run_id"],
        "main_sha": manifest["main_sha"], "window": manifest["window"],
        "batch_sequence": batch["batch_sequence"], "input_batch_sha256": digest(batch),
        "result_sha256": digest(stored), "status": "terminal",
    }
    append_only_write(output_dir / "receipts" / f"batch-{batch['batch_sequence']:04d}.json", receipt)
    return receipt


def score_universe(manifest_path: Path, result_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest, batches = validate_score_batches(manifest_path)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sequence, (_path, batch) in enumerate(batches, 1):
        path = result_dir / f"batch-{sequence:04d}-result.json"
        if not path.is_file():
            raise ValueError(f"score checkpoint missing batch {sequence:04d}")
        result = load(path)
        require_identity(result, manifest, path.name)
        if result.get("input_batch_sha256") != digest(batch):
            raise ValueError(f"{path.name} is not bound to its score input")
        expected = {item["semantic_event_id"]: item for item in batch["events"]}
        events = result.get("events") if isinstance(result.get("events"), list) else []
        if Counter(item.get("semantic_event_id") for item in events) != Counter(expected.keys()):
            raise ValueError("score checkpoints do not conserve the semantic event universe")
        for item in events:
            event_id = item["semantic_event_id"]
            if event_id in seen:
                raise ValueError("score checkpoint repeats a semantic event")
            candidate = item.get("candidate")
            if not isinstance(candidate, dict) or set(candidate.get("candidate_urls", [])) != set(expected[event_id]["candidate_urls"]):
                raise ValueError("score checkpoint changed event source URLs")
            seen.add(event_id)
            candidates.append(candidate)
    if seen != set(manifest.get("event_ids", [])):
        raise ValueError("score checkpoints do not conserve the semantic event universe")
    return manifest, candidates


def finalize(
    audit_input_manifest: Path,
    review_dir: Path,
    score_manifest: Path,
    score_result_dir: Path,
    run_base_path: Path,
    admissions_path: Path,
    source_pool_path: Path,
    history_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    input_manifest, _source_rows, reviews = review_universe(audit_input_manifest, review_dir)
    score_authority, candidates = score_universe(score_manifest, score_result_dir)
    require_identity(score_authority, input_manifest, "score manifest")
    base = load(run_base_path)
    admissions = load(admissions_path)
    source_pool = load(source_pool_path)
    if base.get("run_id") != input_manifest.get("run_id"):
        raise ValueError("run base changed run identity")
    if base.get("window_start") != input_manifest["window"]["start"] or base.get("window_end") != input_manifest["window"]["end"]:
        raise ValueError("run base changed window identity")
    if admissions.get("run_id") != base.get("run_id"):
        raise ValueError("source-row admissions changed run identity")
    admission_rows = admissions.get("rows")
    if not isinstance(admission_rows, list):
        raise ValueError("source-row admissions rows are required")
    admission_by_id = {row.get("row_id"): row for row in admission_rows if isinstance(row, dict)}
    if set(admission_by_id) != set(reviews):
        raise ValueError("review rows do not conserve source-row admissions")
    dispositions = []
    for row_id in sorted(admission_by_id):
        admission = admission_by_id[row_id]
        review = reviews[row_id]
        dispositions.append({
            "row_id": row_id,
            "candidate_id": admission.get("candidate_id"),
            "provisional_group_id": admission.get("provisional_group_id"),
            "source_id": admission.get("source_id"),
            "url": admission.get("url"),
            "canonical_url": admission.get("canonical_url"),
            "article_body_published_at": admission.get("article_body_published_at"),
            "article_body_timestamp_evidence": admission.get("article_body_timestamp_evidence"),
            "disposition": review["disposition"],
            "semantic_event_id": review.get("semantic_event_id"),
            "reason": review["reason"],
            "model_evidence": review["model_evidence"],
        })
    disposition_counts = Counter(item["disposition"] for item in dispositions)
    ranking = manage_candidate_audit.repository_ranking()
    raw_count = len(dispositions)
    processing_counts = {
        "merged_article_row_count": raw_count,
        "in_window_article_row_count": raw_count,
        "canonical_url_count": len({item["canonical_url"] for item in dispositions}),
        "provisional_title_cluster_count": len({item["provisional_group_id"] for item in dispositions}),
        "semantic_event_count": len(candidates),
        "scored_event_count": len(candidates),
        "event_evidence_article_row_count": disposition_counts["event_evidence"],
        "non_news_article_row_count": disposition_counts["non_news"],
        "unresolved_article_row_count": disposition_counts["unresolved"],
        "unresolved_exhausted_article_row_count": disposition_counts["unresolved_exhausted"],
        "c_or_higher_scored_event_count": sum(
            manage_candidate_audit.grade_meets_threshold(item.get("provisional_grade"), "C", ranking)
            for item in candidates
        ),
        "selected_event_count": sum(item.get("decision") == "selected" for item in candidates),
    }
    run = dict(base)
    run.update({
        "raw_item_count": raw_count,
        "article_dispositions": dispositions,
        "processing_counts": processing_counts,
        "deduplicated_candidate_count": len(candidates),
        "candidates": candidates,
    })
    history = load(history_path) if history_path.is_file() else {"runs": []}
    generated_at = manage_candidate_audit.parse_datetime(run["generated_at"])
    cutoff = generated_at - timedelta(days=14)
    runs = [
        item for item in history.get("runs", [])
        if manage_candidate_audit.parse_datetime(item["generated_at"]) >= cutoff
        and item.get("run_id") != run.get("run_id")
    ] + [run]
    runs.sort(key=lambda item: manage_candidate_audit.parse_datetime(item["generated_at"]))
    audit = {
        "schema_version": "1.2.0", "retention_days": 14,
        "updated_at": generated_at.isoformat(), "runs": runs,
    }
    errors = manage_candidate_audit.validate(
        audit, source_pool, admissions,
        source_evidence_root=admissions_path.parent / "remote-acquisition",
    )
    if errors:
        raise ValueError("candidate audit validation failed: " + "; ".join(errors))
    atomic_write(output_path, audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    review = sub.add_parser("record-review")
    review.add_argument("--input-manifest", required=True, type=Path)
    review.add_argument("--input-batch", required=True, type=Path)
    review.add_argument("--result", required=True, type=Path)
    review.add_argument("--output-dir", required=True, type=Path)
    scoring = sub.add_parser("prepare-scoring")
    scoring.add_argument("--input-manifest", required=True, type=Path)
    scoring.add_argument("--review-dir", required=True, type=Path)
    scoring.add_argument("--output-dir", required=True, type=Path)
    score = sub.add_parser("record-score")
    score.add_argument("--input-manifest", required=True, type=Path)
    score.add_argument("--input-batch", required=True, type=Path)
    score.add_argument("--result", required=True, type=Path)
    score.add_argument("--output-dir", required=True, type=Path)
    final = sub.add_parser("finalize")
    final.add_argument("--audit-input-manifest", required=True, type=Path)
    final.add_argument("--review-dir", required=True, type=Path)
    final.add_argument("--score-manifest", required=True, type=Path)
    final.add_argument("--score-result-dir", required=True, type=Path)
    final.add_argument("--run-base", required=True, type=Path)
    final.add_argument("--source-row-admissions", required=True, type=Path)
    final.add_argument("--source-pool", required=True, type=Path)
    final.add_argument("--history", required=True, type=Path)
    final.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.cmd == "record-review":
        result = record_review_result(args.input_manifest, args.input_batch, args.result, args.output_dir)
    elif args.cmd == "prepare-scoring":
        result = prepare_scoring(args.input_manifest, args.review_dir, args.output_dir)
    elif args.cmd == "record-score":
        result = record_score_result(args.input_manifest, args.input_batch, args.result, args.output_dir)
    else:
        result = finalize(
            args.audit_input_manifest, args.review_dir, args.score_manifest,
            args.score_result_dir, args.run_base, args.source_row_admissions,
            args.source_pool, args.history, args.output,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
