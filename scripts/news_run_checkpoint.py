#!/usr/bin/env python3
"""Persistent pre-manifest checkpoint for the daily news pipeline.

The checkpoint exists before a manifest does, so early failures can be recovered
without inventing a partial manifest. Completed stages can bind named artifacts by
SHA-256; the release gate rechecks those bindings before delivery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
PRE_MANIFEST_STAGES = (
    "source-scan",
    "preprocess-news-candidates",
    "select-news-events",
    "audit-news-candidates",
    "materialize-manifest",
)
POST_MANIFEST_STAGES = (
    "verify-news-events",
    "build-news-maps",
    "build-news-charts",
    "collect-news-images",
    "render",
)
RELEASE_REQUIRED_STAGES = PRE_MANIFEST_STAGES + POST_MANIFEST_STAGES
VALID_STATUSES = {"pending", "running", "completed", "failed"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("checkpoint 根節點必須是物件")
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_checkpoint(run_id: str, window_start: str, window_end: str) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window_start": window_start,
        "window_end": window_end,
        "created_at": timestamp,
        "updated_at": timestamp,
        "stage_status": {stage: "pending" for stage in RELEASE_REQUIRED_STAGES},
        "stage_evidence": {},
        "recovery": {
            "status": "pending",
            "max_attempts_per_target": 3,
            "attempts": [],
            "unresolved_targets": [],
        },
    }


def parse_artifact(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ValueError("--artifact 必須使用 NAME=PATH")
    name, raw_path = value.split("=", 1)
    name = name.strip()
    path = Path(raw_path.strip())
    if not name or not raw_path.strip():
        raise ValueError("--artifact 必須使用非空的 NAME=PATH")
    if not path.is_file():
        raise FileNotFoundError(f"artifact 不存在：{path}")
    return name, path


def mark_stage(
    data: dict[str, Any],
    stage: str,
    status: str,
    artifacts: list[str] | None = None,
    message: str = "",
) -> dict[str, Any]:
    if stage not in RELEASE_REQUIRED_STAGES:
        raise ValueError(f"未知 checkpoint stage：{stage}")
    if status not in VALID_STATUSES:
        raise ValueError(f"無效 stage status：{status}")
    evidence: dict[str, Any] = {
        "recorded_at": now_iso(),
        "message": message,
        "artifacts": {},
    }
    for raw in artifacts or []:
        name, path = parse_artifact(raw)
        evidence["artifacts"][name] = {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    data.setdefault("stage_status", {})[stage] = status
    data.setdefault("stage_evidence", {})[stage] = evidence
    data["updated_at"] = now_iso()
    return data


def validate_checkpoint(
    data: dict[str, Any],
    required_stages: tuple[str, ...] = RELEASE_REQUIRED_STAGES,
) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"checkpoint.schema_version 必須是 {SCHEMA_VERSION}")
    if not str(data.get("run_id", "")).strip():
        errors.append("checkpoint.run_id 不得為空")
    if not str(data.get("window_start", "")).strip() or not str(data.get("window_end", "")).strip():
        errors.append("checkpoint 必須保存 window_start/window_end")
    status = data.get("stage_status")
    if not isinstance(status, dict):
        return errors + ["checkpoint.stage_status 必須是物件"]
    evidence = data.get("stage_evidence")
    if not isinstance(evidence, dict):
        errors.append("checkpoint.stage_evidence 必須是物件")
        evidence = {}
    for stage in required_stages:
        state = status.get(stage)
        if state != "completed":
            errors.append(f"checkpoint stage 未完成：{stage}={state or 'missing'}")
        stage_evidence = evidence.get(stage)
        if not isinstance(stage_evidence, dict):
            errors.append(f"checkpoint stage 缺少 evidence：{stage}")
    recovery = data.get("recovery", {})
    if isinstance(recovery, dict):
        unresolved = recovery.get("unresolved_targets", [])
        if unresolved:
            errors.append("checkpoint 仍有 unresolved recovery targets")
    return errors


def verify_bound_artifact(
    data: dict[str, Any], stage: str, name: str, actual_path: str | Path
) -> list[str]:
    errors: list[str] = []
    actual = Path(actual_path)
    binding = (
        data.get("stage_evidence", {})
        .get(stage, {})
        .get("artifacts", {})
        .get(name)
    )
    if not isinstance(binding, dict):
        return [f"checkpoint 未綁定 {stage}.{name}"]
    if not actual.is_file():
        return [f"checkpoint 綁定檔不存在：{actual}"]
    expected_hash = binding.get("sha256")
    actual_hash = sha256_file(actual)
    if expected_hash != actual_hash:
        errors.append(f"checkpoint 綁定雜湊不符：{stage}.{name}")
    try:
        bound_path = Path(str(binding.get("path", ""))).resolve()
        if bound_path != actual.resolve():
            errors.append(f"checkpoint 綁定路徑不符：{stage}.{name}")
    except OSError:
        errors.append(f"checkpoint 綁定路徑無法解析：{stage}.{name}")
    return errors



def recovery_plan(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the earliest incomplete pre-manifest stage for local resume."""
    status = data.get("stage_status", {})
    if not isinstance(status, dict):
        return [{"target_stage": "source-scan", "reason": "checkpoint.stage_status 無效"}]
    for stage in PRE_MANIFEST_STAGES:
        state = status.get(stage)
        if state != "completed":
            return [{
                "target_stage": stage,
                "state": state or "missing",
                "reason": f"最早未完成 pre-manifest 階段：{stage}={state or 'missing'}",
                "continue_required": True,
            }]
    return []

def main() -> int:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)

    init = subs.add_parser("init")
    init.add_argument("--output", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--window-start", required=True)
    init.add_argument("--window-end", required=True)

    mark = subs.add_parser("mark")
    mark.add_argument("--input", required=True)
    mark.add_argument("--output", required=True)
    mark.add_argument("--stage", required=True, choices=RELEASE_REQUIRED_STAGES)
    mark.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    mark.add_argument("--artifact", action="append", default=[])
    mark.add_argument("--message", default="")

    validate = subs.add_parser("validate")
    validate.add_argument("--input", required=True)

    plan = subs.add_parser("plan")
    plan.add_argument("--input", required=True)

    args = parser.parse_args()
    if args.command == "init":
        save(args.output, create_checkpoint(args.run_id, args.window_start, args.window_end))
        print(args.output)
        return 0
    if args.command == "mark":
        data = load(args.input)
        mark_stage(data, args.stage, args.status, args.artifact, args.message)
        save(args.output, data)
        print(args.output)
        return 0
    if args.command == "plan":
        print(json.dumps(recovery_plan(load(args.input)), ensure_ascii=False, indent=2))
        return 0
    errors = validate_checkpoint(load(args.input))
    for error in errors:
        print("FAIL:", error)
    if not errors:
        print("OK")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
