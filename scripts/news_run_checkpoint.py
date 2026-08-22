#!/usr/bin/env python3
"""Persistent checkpoint for the daily news pipeline.

Repository materialization happens before this script can run. That pre-checkpoint
bootstrap is therefore represented by a separate bootstrap receipt. `init` refuses
to create the news checkpoint unless the receipt proves that the exact GitHub
blobs needed by the runtime exist in the executable workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1.0"
BOOTSTRAP_SCHEMA_VERSION = "1.1.0"
REPOSITORY_FULL_NAME = "robert820728-star/global-news-brief"
REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_REQUIRED_PATHS = (
    "bootstrap-workspace.md",
    "daily-schedule-prompt.md",
    "news-brief-settings.md",
    "news-brief-template.md",
    "user-preferences.example.yaml",
    "news-source-pool.json",
    "schemas/news-event-manifest.schema.json",
    "schemas/news-candidate-audit.schema.json",
    ".agents/skills/daily-news-brief/SKILL.md",
    ".agents/skills/select-news-events/SKILL.md",
    ".agents/skills/audit-news-candidates/SKILL.md",
    ".agents/skills/verify-news-events/SKILL.md",
    ".agents/skills/build-news-maps/SKILL.md",
    ".agents/skills/build-news-charts/SKILL.md",
    ".agents/skills/collect-news-images/SKILL.md",
    ".agents/skills/recover-news-run/SKILL.md",
    "scripts/news_run_checkpoint.py",
    "scripts/preprocess_news_candidates.py",
    "scripts/manage_candidate_audit.py",
    "scripts/recover_news_run.py",
    "scripts/validate_map_decisions.py",
    "scripts/validate_news_brief.py",
    "scripts/check_unique_delivery_gate.py",
    "scripts/publish_news_brief.py",
)
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
REQUIRED_STAGE_ARTIFACTS = {
    "source-scan": ("source_candidates", "relevance_gate", "model_source_candidates"),
    "preprocess-news-candidates": ("preprocessed_candidates",),
    "select-news-events": ("selection_results",),
    "audit-news-candidates": ("candidate_audit",),
    "materialize-manifest": ("manifest",),
    "verify-news-events": ("manifest",),
    "build-news-maps": ("manifest",),
    "build-news-charts": ("manifest",),
    "collect-news-images": ("manifest",),
    "render": ("brief", "manifest"),
}
VALID_STATUSES = {"pending", "running", "completed", "failed"}
HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
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


def _safe_repo_path(value: str) -> bool:
    path = Path(value)
    return bool(value.strip()) and not path.is_absolute() and ".." not in path.parts


def validate_bootstrap_receipt(
    receipt: dict[str, Any], repo_root: str | Path = REPO_ROOT
) -> list[str]:
    """Validate connector-materialized repository bytes against a bootstrap receipt."""
    errors: list[str] = []
    root = Path(repo_root).resolve()
    if receipt.get("schema_version") != BOOTSTRAP_SCHEMA_VERSION:
        errors.append(f"bootstrap.schema_version 必須是 {BOOTSTRAP_SCHEMA_VERSION}")
    if receipt.get("status") != "completed":
        errors.append("bootstrap.status 必須是 completed")
    if receipt.get("repository") != REPOSITORY_FULL_NAME:
        errors.append(f"bootstrap.repository 必須是 {REPOSITORY_FULL_NAME}")
    commit_sha = str(receipt.get("commit_sha", ""))
    if len(commit_sha) not in {40, 64} or not HEX_RE.fullmatch(commit_sha):
        errors.append("bootstrap.commit_sha 必須是 Git commit hex SHA")
    if receipt.get("materialization_method") != "github-connector-capsule":
        errors.append("bootstrap.materialization_method 必須是 github-connector-capsule")
    if receipt.get("materialization_scope") != "verified-runtime-capsule":
        errors.append("bootstrap.materialization_scope 必須是 verified-runtime-capsule")
    capsule = receipt.get("capsule")
    if not isinstance(capsule, dict):
        errors.append("bootstrap.capsule 必須是物件")
    else:
        manifest_blob_sha = str(capsule.get("manifest_blob_sha", ""))
        if len(manifest_blob_sha) != 40 or not HEX_RE.fullmatch(manifest_blob_sha):
            errors.append("bootstrap.capsule.manifest_blob_sha 無效")
        for field in ("manifest_sha256", "payload_sha256", "runtime_fingerprint"):
            value = str(capsule.get(field, ""))
            if len(value) != 64 or not HEX_RE.fullmatch(value):
                errors.append(f"bootstrap.capsule.{field} 無效")
        chunks = capsule.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            errors.append("bootstrap.capsule.chunks 必須是非空陣列")
        elif capsule.get("chunk_count") != len(chunks):
            errors.append("bootstrap.capsule.chunk_count 不符")

    try:
        workspace = Path(str(receipt.get("workspace_root", ""))).resolve()
        if workspace != root:
            errors.append("bootstrap.workspace_root 與目前 executable repo root 不一致")
    except OSError:
        errors.append("bootstrap.workspace_root 無法解析")

    files = receipt.get("files")
    if not isinstance(files, list) or not files:
        return errors + ["bootstrap.files 必須是非空陣列"]
    seen: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"bootstrap.files[{index}] 必須是物件")
            continue
        rel = str(item.get("path", ""))
        if not _safe_repo_path(rel):
            errors.append(f"bootstrap.files[{index}].path 非法：{rel}")
            continue
        if rel in seen:
            errors.append(f"bootstrap.files 路徑重複：{rel}")
            continue
        seen.add(rel)
        local = root / rel
        if not local.is_file():
            errors.append(f"bootstrap materialized file 不存在：{rel}")
            continue
        expected_size = item.get("size")
        if not isinstance(expected_size, int) or expected_size != local.stat().st_size:
            errors.append(f"bootstrap 檔案大小不符：{rel}")
        expected_sha256 = str(item.get("sha256", ""))
        if len(expected_sha256) != 64 or not HEX_RE.fullmatch(expected_sha256):
            errors.append(f"bootstrap sha256 無效：{rel}")
        elif sha256_file(local) != expected_sha256.lower():
            errors.append(f"bootstrap sha256 不符：{rel}")
        source_blob_sha = str(item.get("source_blob_sha", ""))
        if len(source_blob_sha) != 40 or not HEX_RE.fullmatch(source_blob_sha):
            errors.append(f"bootstrap source_blob_sha 無效：{rel}")
        elif git_blob_sha1(local) != source_blob_sha.lower():
            errors.append(f"bootstrap Git blob SHA 不符：{rel}")

    missing_required = sorted(set(BOOTSTRAP_REQUIRED_PATHS) - seen)
    for rel in missing_required:
        errors.append(f"bootstrap 缺少 runtime 必要檔案：{rel}")
    return errors


def bootstrap_binding(receipt_path: str | Path, receipt: dict[str, Any]) -> dict[str, Any]:
    path = Path(receipt_path)
    return {
        "repository": receipt.get("repository"),
        "commit_sha": receipt.get("commit_sha"),
        "materialization_method": receipt.get("materialization_method"),
        "receipt": {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        },
    }


def create_checkpoint(
    run_id: str,
    window_start: str,
    window_end: str,
    bootstrap: dict[str, Any] | None = None,
    bootstrap_required: bool = False,
) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window_start": window_start,
        "window_end": window_end,
        "created_at": timestamp,
        "updated_at": timestamp,
        "bootstrap": bootstrap,
        "bootstrap_required": bootstrap_required,
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
    stage_status = data.setdefault("stage_status", {})
    current_status = stage_status.get(stage, "pending")
    stage_index = RELEASE_REQUIRED_STAGES.index(stage)
    if status == "running" and stage_index:
        predecessor = RELEASE_REQUIRED_STAGES[stage_index - 1]
        if stage_status.get(predecessor) != "completed":
            raise ValueError(f"前一階段未完成：{predecessor}")
    if status == "completed" and current_status != "running":
        raise ValueError(f"{stage} 必須先標記為 running 才能 completed")
    if status == "failed" and current_status != "running":
        raise ValueError(f"{stage} 必須先標記為 running 才能 failed")
    evidence: dict[str, Any] = {
        "recorded_at": now_iso(),
        "status": status,
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
    if status == "completed":
        missing = [
            name for name in REQUIRED_STAGE_ARTIFACTS[stage]
            if name not in evidence["artifacts"]
        ]
        if missing:
            raise ValueError(
                f"{stage} completed 缺少必要 artifact：{', '.join(missing)}"
            )
    stage_status[stage] = status
    data.setdefault("stage_evidence", {})[stage] = evidence
    data["updated_at"] = now_iso()
    return data


def _validate_bootstrap_binding(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    binding = data.get("bootstrap")
    if not isinstance(binding, dict):
        return ["checkpoint 缺少 bootstrap workspace binding"]
    if binding.get("repository") != REPOSITORY_FULL_NAME:
        errors.append("checkpoint.bootstrap.repository 不符")
    commit_sha = str(binding.get("commit_sha", ""))
    if len(commit_sha) not in {40, 64} or not HEX_RE.fullmatch(commit_sha):
        errors.append("checkpoint.bootstrap.commit_sha 無效")
    receipt_binding = binding.get("receipt")
    if not isinstance(receipt_binding, dict):
        return errors + ["checkpoint.bootstrap 缺少 receipt binding"]
    receipt_path = Path(str(receipt_binding.get("path", "")))
    if not receipt_path.is_file():
        return errors + [f"bootstrap receipt 不存在：{receipt_path}"]
    if sha256_file(receipt_path) != receipt_binding.get("sha256"):
        errors.append("bootstrap receipt SHA-256 已變更")
        return errors
    try:
        receipt = load(receipt_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return errors + [f"bootstrap receipt 無法讀取：{error}"]
    if receipt.get("commit_sha") != binding.get("commit_sha"):
        errors.append("checkpoint.bootstrap.commit_sha 與 receipt 不一致")
    errors += validate_bootstrap_receipt(receipt, REPO_ROOT)
    return errors


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
    if data.get("bootstrap_required") or data.get("bootstrap") is not None:
        errors += _validate_bootstrap_binding(data)
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
            continue
        if state == "completed":
            if stage_evidence.get("status") != "completed":
                errors.append(f"checkpoint stage evidence 狀態不符：{stage}")
            artifacts = stage_evidence.get("artifacts")
            if not isinstance(artifacts, dict):
                errors.append(f"checkpoint stage artifacts 無效：{stage}")
                continue
            for name in REQUIRED_STAGE_ARTIFACTS[stage]:
                binding = artifacts.get(name)
                if not isinstance(binding, dict):
                    errors.append(f"checkpoint stage 缺少必要 artifact：{stage}.{name}")
                    continue
                if not str(binding.get("path", "")).strip():
                    errors.append(f"checkpoint artifact 缺少路徑：{stage}.{name}")
                digest = str(binding.get("sha256", ""))
                if len(digest) != 64 or not HEX_RE.fullmatch(digest):
                    errors.append(f"checkpoint artifact SHA-256 無效：{stage}.{name}")
                if not isinstance(binding.get("size"), int) or binding["size"] < 0:
                    errors.append(f"checkpoint artifact size 無效：{stage}.{name}")
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
    init.add_argument("--bootstrap-receipt", required=True)

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
        receipt_path = Path(args.bootstrap_receipt)
        try:
            receipt = load(receipt_path)
            errors = validate_bootstrap_receipt(receipt, REPO_ROOT)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors = [f"bootstrap receipt 無法讀取：{error}"]
            receipt = {}
        if errors:
            for error in errors:
                print("BOOTSTRAP FAIL:", error)
            return 2
        checkpoint = create_checkpoint(
            args.run_id,
            args.window_start,
            args.window_end,
            bootstrap_binding(receipt_path, receipt),
            bootstrap_required=True,
        )
        save(args.output, checkpoint)
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
