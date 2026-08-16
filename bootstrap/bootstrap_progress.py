#!/usr/bin/env python3
"""Atomic pre-checkpoint progress and receipt handling for mobile bootstrap runs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STATUSES = {"running", "failed", "completed"}
LEDGER_STATUSES = {"pending", "available", "unavailable"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clone(progress: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(progress)


def new_progress(run_id: str, resolved_commit: str, chunks_total: int) -> dict[str, Any]:
    if not run_id.strip():
        raise ValueError("run_id must not be empty")
    if not COMMIT_RE.fullmatch(resolved_commit):
        raise ValueError("resolved_commit must be a 40-character lowercase Git SHA")
    if not isinstance(chunks_total, int) or isinstance(chunks_total, bool) or chunks_total <= 0:
        raise ValueError("chunks_total must be a positive integer")
    now = utc_now()
    progress = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "resolved_commit": resolved_commit,
        "stage": "bootstrap-main-resolution",
        "status": "running",
        "chunks_total": chunks_total,
        "chunks_completed": 0,
        "current_chunk": None,
        "blocks_total": 0,
        "blocks_completed": 0,
        "current_block": None,
        "last_success_at": now,
        "last_error": None,
        "retry_count": 0,
        "current_block_attempts": [],
        "last_completed_stage": "bootstrap-main-resolution",
        "external_ledger": {
            "status": "pending",
            "issue_url": None,
            "comment_id": None,
            "last_update_at": None,
            "error": None,
        },
        "canonical_delivery": False,
        "updated_at": now,
    }
    validate_progress(progress)
    return progress


def validate_progress(progress: dict[str, Any]) -> None:
    if not isinstance(progress, dict):
        raise ValueError("bootstrap progress root must be an object")
    if progress.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    if not str(progress.get("run_id", "")).strip():
        raise ValueError("run_id must not be empty")
    if not COMMIT_RE.fullmatch(str(progress.get("resolved_commit", ""))):
        raise ValueError("resolved_commit must be a lowercase Git SHA")
    status = progress.get("status")
    if status not in STATUSES:
        raise ValueError("status is invalid")
    total = progress.get("chunks_total")
    completed = progress.get("chunks_completed")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        raise ValueError("chunks_total must be a positive integer")
    if not isinstance(completed, int) or isinstance(completed, bool) or not 0 <= completed <= total:
        raise ValueError("chunks_completed is outside the valid range")
    for field in ("blocks_total", "blocks_completed", "retry_count"):
        value = progress.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{field} must be a non-negative integer")
    if progress["blocks_completed"] > progress["blocks_total"]:
        raise ValueError("blocks_completed cannot exceed blocks_total")
    if progress["retry_count"] > 3:
        raise ValueError("retry_count cannot exceed three")
    attempts = progress.get("current_block_attempts")
    if not isinstance(attempts, list) or len(attempts) > 4:
        raise ValueError("current_block_attempts must contain at most four records")
    for index, item in enumerate(attempts, start=1):
        if not isinstance(item, dict) or item.get("attempt") != index:
            raise ValueError("current_block_attempts must be sequential")
        digest = item.get("sha256")
        if digest is not None and not SHA256_RE.fullmatch(str(digest)):
            raise ValueError("attempt sha256 is invalid")
    ledger = progress.get("external_ledger")
    if not isinstance(ledger, dict) or ledger.get("status") not in LEDGER_STATUSES:
        raise ValueError("external_ledger status is invalid")
    if not isinstance(progress.get("canonical_delivery"), bool):
        raise ValueError("canonical_delivery must be boolean")


def atomic_write(path: Path, progress: dict[str, Any]) -> None:
    validate_progress(progress)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(progress, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_progress(path: Path) -> dict[str, Any]:
    progress = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_progress(progress)
    return progress


def _validate_block_spec(block: dict[str, Any]) -> None:
    required = ("start_line", "end_line", "size", "sha256")
    if not isinstance(block, dict) or any(field not in block for field in required):
        raise ValueError("grouped fetch block specification is incomplete")
    if not isinstance(block["start_line"], int) or not isinstance(block["end_line"], int):
        raise ValueError("grouped fetch line range is invalid")
    if block["start_line"] <= 0 or block["end_line"] < block["start_line"]:
        raise ValueError("grouped fetch line range is invalid")
    if not isinstance(block["size"], int) or block["size"] <= 0:
        raise ValueError("grouped fetch block size is invalid")
    if not SHA256_RE.fullmatch(str(block["sha256"])):
        raise ValueError("grouped fetch block sha256 is invalid")


def validate_grouped_fetch(
    raw: bytes,
    first: dict[str, Any],
    second: dict[str, Any],
) -> list[bytes]:
    """Split one 16-line response into two declared 8-line blocks and verify both."""
    _validate_block_spec(first)
    _validate_block_spec(second)
    if first["end_line"] + 1 != second["start_line"]:
        raise ValueError("grouped fetch blocks must be adjacent")
    first_line_count = first["end_line"] - first["start_line"] + 1
    second_line_count = second["end_line"] - second["start_line"] + 1
    lines = raw.splitlines(keepends=True)
    if len(lines) != first_line_count + second_line_count or not raw.endswith(b"\n"):
        raise ValueError("grouped fetch response is truncated or has non-canonical framing")
    parts = [
        b"".join(lines[:first_line_count]),
        b"".join(lines[first_line_count:]),
    ]
    for label, part, spec in (("first", parts[0], first), ("second", parts[1], second)):
        if len(part) != spec["size"]:
            raise ValueError(f"grouped fetch {label} block size mismatch")
        if hashlib.sha256(part).hexdigest() != spec["sha256"]:
            raise ValueError(f"grouped fetch {label} block sha256 mismatch")
    return parts


def _atomic_write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_grouped_file(
    input_path: Path,
    blocks_path: Path,
    output_dir: Path,
    prefix: str,
) -> list[Path]:
    blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
    if not isinstance(blocks, list) or len(blocks) != 2:
        raise ValueError("grouped fetch block specification must contain exactly two blocks")
    parts = validate_grouped_fetch(input_path.read_bytes(), blocks[0], blocks[1])
    indexes = [blocks[0].get("index", 1), blocks[1].get("index", 2)]
    paths = []
    for index, part in zip(indexes, parts):
        if not isinstance(index, int) or index <= 0:
            raise ValueError("grouped fetch block index is invalid")
        target = output_dir / f"{prefix}.block{index:04d}.txt"
        _atomic_write_bytes(target, part)
        paths.append(target)
    return paths


def record_chunk(
    progress: dict[str, Any],
    chunk_name: str,
    completed: int,
    blocks_total: int,
) -> dict[str, Any]:
    validate_progress(progress)
    if completed != progress["chunks_completed"] + 1:
        raise ValueError("completed chunk count must advance by exactly one")
    if completed > progress["chunks_total"]:
        raise ValueError("completed chunk count exceeds chunks_total")
    if blocks_total <= 0:
        raise ValueError("blocks_total must be positive")
    updated = _clone(progress)
    now = utc_now()
    updated.update({
        "stage": "bootstrap-capsule-retrieval",
        "status": "running",
        "chunks_completed": completed,
        "current_chunk": chunk_name,
        "blocks_total": blocks_total,
        "blocks_completed": blocks_total,
        "current_block": None,
        "last_success_at": now,
        "last_error": None,
        "retry_count": 0,
        "current_block_attempts": [],
        "last_completed_stage": "bootstrap-capsule-retrieval",
        "updated_at": now,
    })
    validate_progress(updated)
    return updated


def record_attempt(
    progress: dict[str, Any],
    *,
    chunk_name: str,
    block_index: int,
    blocks_total: int,
    attempt: int,
    byte_size: int,
    sha256: str | None,
    error: str | None,
) -> dict[str, Any]:
    validate_progress(progress)
    if attempt not in range(1, 5):
        raise ValueError("attempt must be between one and four")
    if not 1 <= block_index <= blocks_total:
        raise ValueError("block index is outside blocks_total")
    if byte_size < 0:
        raise ValueError("byte_size must be non-negative")
    if sha256 is not None and not SHA256_RE.fullmatch(sha256):
        raise ValueError("sha256 must be lowercase hexadecimal")
    same_block = (
        progress.get("current_chunk") == chunk_name
        and progress.get("current_block") == block_index
    )
    previous = progress.get("current_block_attempts", []) if same_block else []
    if attempt != len(previous) + 1:
        raise ValueError("attempt sequence must start at one and increase by one")
    updated = _clone(progress)
    now = utc_now()
    attempts = list(previous)
    attempts.append({
        "attempt": attempt,
        "byte_size": byte_size,
        "sha256": sha256,
        "outcome": "failed" if error else "succeeded",
        "error": error,
        "at": now,
    })
    updated.update({
        "stage": "bootstrap-capsule-retrieval",
        "status": "failed" if error and attempt == 4 else "running",
        "current_chunk": chunk_name,
        "blocks_total": blocks_total,
        "blocks_completed": block_index - 1,
        "current_block": block_index,
        "last_error": error,
        "retry_count": attempt - 1,
        "current_block_attempts": attempts,
        "updated_at": now,
    })
    if error is None:
        updated["last_success_at"] = now
    validate_progress(updated)
    return updated


def set_stage(
    progress: dict[str, Any],
    *,
    stage: str,
    status: str,
    error: str | None = None,
    canonical_delivery: bool | None = None,
) -> dict[str, Any]:
    validate_progress(progress)
    if not stage.strip():
        raise ValueError("stage must not be empty")
    if status not in STATUSES:
        raise ValueError("status is invalid")
    updated = _clone(progress)
    now = utc_now()
    updated.update({
        "stage": stage,
        "status": status,
        "last_error": error,
        "updated_at": now,
    })
    if status == "completed":
        updated["last_completed_stage"] = stage
        updated["last_success_at"] = now
    if canonical_delivery is not None:
        updated["canonical_delivery"] = canonical_delivery
    validate_progress(updated)
    return updated


def set_ledger(
    progress: dict[str, Any],
    *,
    status: str,
    issue_url: str | None = None,
    comment_id: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    validate_progress(progress)
    if status not in LEDGER_STATUSES:
        raise ValueError("external ledger status is invalid")
    if comment_id is not None and comment_id <= 0:
        raise ValueError("comment_id must be positive")
    updated = _clone(progress)
    now = utc_now()
    updated["external_ledger"] = {
        "status": status,
        "issue_url": issue_url,
        "comment_id": comment_id,
        "last_update_at": now if status == "available" else None,
        "error": error,
    }
    updated["updated_at"] = now
    validate_progress(updated)
    return updated


def _receipt_value(value: Any) -> str:
    if value is None or value == "":
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\r", " ").replace("\n", " ")


def render_receipt(progress: dict[str, Any]) -> str:
    validate_progress(progress)
    current_block = "none"
    if progress["current_block"] is not None:
        current_block = f"{progress['current_block']}/{progress['blocks_total']}"
    lines = (
        "RUN_RECEIPT",
        f"run_id: {_receipt_value(progress['run_id'])}",
        f"main_sha: {_receipt_value(progress['resolved_commit'])}",
        f"last_completed_stage: {_receipt_value(progress['last_completed_stage'])}",
        f"bootstrap_chunks: {progress['chunks_completed']}/{progress['chunks_total']}",
        f"current_chunk: {_receipt_value(progress['current_chunk'])}",
        f"current_block: {current_block}",
        f"last_error: {_receipt_value(progress['last_error'])}",
        f"retry_count: {progress['retry_count']}",
        f"external_ledger: {_receipt_value(progress['external_ledger']['status'])}",
        f"canonical_delivery: {_receipt_value(progress['canonical_delivery'])}",
    )
    return "\n".join(lines) + "\n"


def finalize(
    path: Path,
    progress: dict[str, Any],
    *,
    canonical_delivery: bool,
    clear: bool,
) -> str:
    validate_progress(progress)
    if clear and not canonical_delivery:
        raise ValueError("local progress can be cleared only after canonical delivery")
    updated = _clone(progress)
    updated["canonical_delivery"] = canonical_delivery
    if canonical_delivery:
        updated = set_stage(
            updated,
            stage="canonical-delivery",
            status="completed",
            canonical_delivery=True,
        )
    receipt = render_receipt(updated)
    if clear:
        Path(path).unlink(missing_ok=True)
    else:
        atomic_write(Path(path), updated)
    return receipt


def _write_updated(path: Path, progress: dict[str, Any]) -> int:
    atomic_write(path, progress)
    print(json.dumps(progress, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--output", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--resolved-commit", required=True)
    init.add_argument("--chunks-total", required=True, type=int)

    chunk = subparsers.add_parser("chunk")
    chunk.add_argument("--input", required=True)
    chunk.add_argument("--name", required=True)
    chunk.add_argument("--completed", required=True, type=int)
    chunk.add_argument("--blocks-total", required=True, type=int)

    attempt = subparsers.add_parser("attempt")
    attempt.add_argument("--input", required=True)
    attempt.add_argument("--chunk", required=True)
    attempt.add_argument("--block", required=True, type=int)
    attempt.add_argument("--blocks-total", required=True, type=int)
    attempt.add_argument("--attempt", required=True, type=int)
    attempt.add_argument("--byte-size", required=True, type=int)
    attempt.add_argument("--sha256")
    attempt.add_argument("--error")

    stage = subparsers.add_parser("stage")
    stage.add_argument("--input", required=True)
    stage.add_argument("--name", required=True)
    stage.add_argument("--status", required=True, choices=sorted(STATUSES))
    stage.add_argument("--error")

    ledger = subparsers.add_parser("ledger")
    ledger.add_argument("--input", required=True)
    ledger.add_argument("--status", required=True, choices=sorted(LEDGER_STATUSES))
    ledger.add_argument("--issue-url")
    ledger.add_argument("--comment-id", type=int)
    ledger.add_argument("--error")

    receipt = subparsers.add_parser("receipt")
    receipt.add_argument("--input", required=True)

    final = subparsers.add_parser("finalize")
    final.add_argument("--input", required=True)
    final.add_argument("--canonical-delivery", required=True, choices=("true", "false"))
    final.add_argument("--clear", action="store_true")

    grouped = subparsers.add_parser("verify-grouped")
    grouped.add_argument("--input", required=True)
    grouped.add_argument("--blocks", required=True)
    grouped.add_argument("--output-dir", required=True)
    grouped.add_argument("--prefix", required=True)

    args = parser.parse_args()
    if args.command == "verify-grouped":
        paths = verify_grouped_file(
            Path(args.input),
            Path(args.blocks),
            Path(args.output_dir),
            args.prefix,
        )
        print(json.dumps({
            "status": "verified",
            "blocks": [str(path) for path in paths],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "init":
        path = Path(args.output)
        return _write_updated(
            path,
            new_progress(args.run_id, args.resolved_commit, args.chunks_total),
        )

    path = Path(args.input)
    progress = load_progress(path)
    if args.command == "chunk":
        return _write_updated(
            path,
            record_chunk(progress, args.name, args.completed, args.blocks_total),
        )
    if args.command == "attempt":
        return _write_updated(
            path,
            record_attempt(
                progress,
                chunk_name=args.chunk,
                block_index=args.block,
                blocks_total=args.blocks_total,
                attempt=args.attempt,
                byte_size=args.byte_size,
                sha256=args.sha256,
                error=args.error,
            ),
        )
    if args.command == "stage":
        return _write_updated(
            path,
            set_stage(progress, stage=args.name, status=args.status, error=args.error),
        )
    if args.command == "ledger":
        return _write_updated(
            path,
            set_ledger(
                progress,
                status=args.status,
                issue_url=args.issue_url,
                comment_id=args.comment_id,
                error=args.error,
            ),
        )
    if args.command == "receipt":
        print(render_receipt(progress), end="")
        return 0
    if args.command == "finalize":
        print(
            finalize(
                path,
                progress,
                canonical_delivery=args.canonical_delivery == "true",
                clear=args.clear,
            ),
            end="",
        )
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
