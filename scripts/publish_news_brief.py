#!/usr/bin/env python3
"""Canonical recover-before-refusal release controller for the daily news brief."""
from __future__ import annotations

import argparse, hashlib, io, json, os, re, sys, tempfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from PIL import Image

import check_unique_delivery_gate as gate_check
import manage_candidate_audit
import news_run_checkpoint as checkpoint_lib
import validate_map_decisions
import validate_news_brief

ROOT = Path(__file__).resolve().parents[1]
GATE_ID = "scripts/publish_news_brief.py"
GATE_VERSION = "2.2.0"
RELEASE_NAME = "news-brief.md"
RECEIPT_NAME = "release-receipt.json"
CONTRACT = ROOT / "daily-schedule-prompt.md"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return checkpoint_lib.sha256_file(path)


def local_path(value: str) -> Path:
    return Path(value.removeprefix("sandbox:"))


IMAGE_LINK_RE = re.compile(r"(!\[[^\]\r\n]*\]\()([^\)\r\n]+)(\))")


def conversation_transport(data: bytes) -> bytes:
    """Rewrite local Markdown image targets for ChatGPT without touching canonical bytes."""
    text = data.decode("utf-8")

    def rewrite(match: re.Match[str]) -> str:
        target = match.group(2)
        if target.startswith(("sandbox:", "http://", "https://", "data:", "blob:")):
            return match.group(0)
        if target.startswith("/"):
            target = "sandbox:" + target
        elif re.match(r"^[A-Za-z]:[\\/]", target):
            target = "sandbox:/" + target.replace("\\", "/")
        return match.group(1) + target + match.group(3)

    return IMAGE_LINK_RE.sub(rewrite, text).encode("utf-8")


def map_pixel_errors(path: Path, label: str) -> list[str]:
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return []
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((320, 320))
            pixels = list(image.get_flattened_data())
    except (OSError, ValueError) as error:
        return [f"{label} 無法讀取地圖像素：{error}"]
    if not pixels:
        return [f"{label} 地圖沒有可驗收像素"]
    yellow = sum(abs(r-243)<=20 and abs(g-230)<=20 and abs(b-184)<=20 for r,g,b in pixels)
    blue = sum(b > r+20 and b > g+10 for r,g,b in pixels)
    errors = []
    if yellow / len(pixels) < .01: errors.append(f"{label} 未檢出核准淡黃色陸地底色 #f3e6b8")
    if blue / len(pixels) > .05: errors.append(f"{label} 藍色背景比例過高，不符合 yellow-admin-v2")
    return errors


def attachment_errors(manifest: dict) -> list[str]:
    errors = []
    for event in manifest.get("events", []):
        if not isinstance(event, dict): continue
        eid = event.get("event_id", "事件")
        for field in ("map", "charts", "images"):
            result = event.get(field, {})
            for i, asset in enumerate(result.get("assets", []) if isinstance(result, dict) else [], 1):
                path = asset.get("path") if isinstance(asset, dict) else None
                if not isinstance(path, str): continue
                local = local_path(path)
                if not local.is_file() or local.stat().st_size < 1:
                    errors.append(f"{eid}.{field}.assets[{i}] 附件不存在或為空：{path}")
                elif field == "map": errors += map_pixel_errors(local, f"{eid}.{field}.assets[{i}]")
                elif field == "images":
                    if sha_file(local) != asset.get("content_sha256"):
                        errors.append(f"{eid}.{field}.assets[{i}] 實體檔 SHA-256 與 manifest 不一致")
                    try:
                        with Image.open(local) as image:
                            actual_size = image.size
                    except (OSError, ValueError) as error:
                        errors.append(f"{eid}.{field}.assets[{i}] 無法解碼圖片：{error}")
                    else:
                        if actual_size != (asset.get("width"), asset.get("height")):
                            errors.append(f"{eid}.{field}.assets[{i}] 實體尺寸與 manifest 不一致")
        images = event.get("images", {})
        if isinstance(images, dict):
            materialized_records = []
            materialization_path = images.get("materialization_manifest_path")
            if images.get("status") == "ready":
                if not isinstance(materialization_path, str):
                    errors.append(f"{eid}.images 缺少 materialized-images manifest")
                else:
                    local_manifest = local_path(materialization_path)
                    try:
                        materialized_records = json.loads(local_manifest.read_text(encoding="utf-8"))
                        if not isinstance(materialized_records, list):
                            raise ValueError("top level must be a list")
                    except (OSError, ValueError, json.JSONDecodeError) as error:
                        errors.append(f"{eid}.images materialized-images manifest 無法讀取：{error}")
                        materialized_records = []
                for i, asset in enumerate(images.get("assets", []), 1):
                    if not isinstance(asset, dict):
                        continue
                    asset_path = local_path(str(asset.get("path", "")))
                    matches = [
                        record for record in materialized_records
                        if isinstance(record, dict)
                        and record.get("event_id") == eid
                        and record.get("status") == "ready"
                        and record.get("source_image_url") == asset.get("source_image_url")
                        and record.get("materialized_by") == "scripts/materialize_news_images.py"
                        and Path(str(record.get("local_path", ""))).resolve() == asset_path.resolve()
                        and record.get("sha256") == asset.get("content_sha256")
                        and record.get("width") == asset.get("width")
                        and record.get("height") == asset.get("height")
                    ]
                    if not matches:
                        errors.append(
                            f"{eid}.images.assets[{i}] 缺少相符的 materialized-images ready 紀錄"
                        )
            for group in ("source_checks", "professional_source_checks"):
                for i, check in enumerate(images.get(group, []), 1):
                    path = check.get("evidence_path") if isinstance(check, dict) else None
                    if isinstance(path, str):
                        local = local_path(path)
                        if not local.is_file() or local.stat().st_size < 1:
                            errors.append(f"{eid}.images.{group}[{i}] 檢查證據不存在或為空：{path}")
    return errors


def candidate_manifest_errors(
    audit: dict, manifest: dict, source_pool: dict
) -> list[str]:
    errors: list[str] = []
    runs = audit.get("runs", [])
    if not runs: return errors + ["候選稽核沒有本輪紀錄"]
    scope_codes = [
        item.get("code") for item in runs[-1].get("section_scopes", [])
        if isinstance(item, dict)
    ]
    manifest_section_codes = [
        item.get("code") for item in manifest.get("sections", [])
        if isinstance(item, dict)
    ]
    if scope_codes != manifest_section_codes:
        errors.append("candidate audit section_scopes 必須與 manifest sections 同序一致")
    selected_candidates = {
        c.get("selected_event_id"): c
        for c in runs[-1].get("candidates", [])
        if manage_candidate_audit.grade_meets_threshold(
            c.get("provisional_grade"), "C", source_pool.get("ranking")
        )
        and c.get("decision") in {"selected", "merged"}
        and c.get("selected_event_id") is not None
    }
    manifest_events = {
        e.get("event_id"): e
        for e in manifest.get("events", []) if isinstance(e, dict)
    }
    if set(selected_candidates) != set(manifest_events):
        errors.append("十四天候選稽核本輪 C 級以上入選事件與 manifest 不一致；禁止漏放達標事件或額外補新聞")
    bindings = (
        ("scoring_method", "scoring_method"),
        ("importance_score", "validated_importance_score"),
        ("provisional_grade", "validated_grade"),
        ("grade_status", "grade_status"),
        ("evidence_confidence", "evidence_confidence"),
        ("confidence_band", "confidence_band"),
    )
    for event_id in set(selected_candidates) & set(manifest_events):
        candidate = selected_candidates[event_id]
        event = manifest_events[event_id]
        if candidate.get("grade_status") != "validated":
            errors.append(f"{event_id} 候選 grade_status 必須是 validated")
        if event.get("grade_status") != "validated":
            errors.append(f"{event_id} manifest.grade_status 必須是 validated")
        for candidate_field, manifest_field in bindings:
            if candidate.get(candidate_field) != event.get(manifest_field):
                errors.append(
                    f"{event_id} manifest.{manifest_field} 必須精確等於候選稽核的 {candidate_field}"
                )
        if event.get("grade") != candidate.get("provisional_grade"):
            errors.append(f"{event_id} manifest.grade 必須等於 validated_grade")
    return errors


def candidate_errors(
    audit: dict, manifest: dict, source_pool: dict,
    source_row_admissions: dict | None = None,
) -> list[str]:
    return manage_candidate_audit.validate(
        audit, source_pool, source_row_admissions
    ) + candidate_manifest_errors(audit, manifest, source_pool)


def checkpoint_errors(cp: dict, manifest: dict, audit: dict, paths: dict[str, Path]) -> list[str]:
    errors = checkpoint_lib.validate_checkpoint(cp)
    errors += checkpoint_lib.verify_bound_artifact(cp, "audit-news-candidates", "candidate_audit", paths["audit"])
    errors += checkpoint_lib.verify_bound_artifact(cp, "render", "manifest", paths["manifest"])
    errors += checkpoint_lib.verify_bound_artifact(cp, "render", "brief", paths["brief"])
    runs = audit.get("runs", []); latest = runs[-1] if runs else {}
    run = manifest.get("run", {}) if isinstance(manifest.get("run"), dict) else {}
    if latest.get("run_id") != cp.get("run_id"): errors.append("checkpoint.run_id 與 candidate audit 本輪 run_id 不一致")
    if run.get("run_id") != cp.get("run_id"): errors.append("checkpoint.run_id 與 manifest.run_id 不一致")
    for key in ("window_start", "window_end"):
        if latest.get(key) != cp.get(key): errors.append(f"checkpoint.{key} 與 candidate audit 不一致")
        if run.get(key) != cp.get(key): errors.append(f"checkpoint.{key} 與 manifest 不一致")
    return errors


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+".", delete=False) as h:
        h.write(data); h.flush(); os.fsync(h.fileno()); temp = h.name
    os.replace(temp, path)


def invalidate_release(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in (RELEASE_NAME, RECEIPT_NAME):
        path = output_dir / name
        if path.exists(): path.unlink()


def discovery_coverage_summary(audit: dict) -> dict:
    runs = audit.get("runs", [])
    latest = runs[-1] if runs else {}
    sources = []
    for item in latest.get("source_coverage", []):
        if not isinstance(item, dict):
            continue
        sources.append({
            "source_id": item.get("source_id"),
            "scan_status": item.get("scan_status"),
            "coverage_complete": item.get("coverage_complete"),
            "coverage_status": item.get("coverage_status"),
            "coverage_reason": item.get("coverage_reason"),
        })
    degraded = [
        item["source_id"] for item in sources
        if item.get("coverage_complete") is not True
    ]
    return {
        "coverage_complete": bool(sources) and not degraded,
        "degraded_source_ids": degraded,
        "sources": sources,
    }


def publication_validation_groups(
    cp: dict,
    manifest: dict,
    audit: dict,
    pool: dict,
    row_admissions: dict | None,
    paths: dict[str, Path],
    brief: str,
) -> list[tuple[str, list[str]]]:
    """Return validation failures with the stage/action that owns their repair."""
    return [
        (
            "repository-recovery",
            gate_check.validate_repository(ROOT, runtime_delivery=False),
        ),
        ("checkpoint-recovery", checkpoint_errors(cp, manifest, audit, paths)),
        (
            "audit-news-candidates",
            manage_candidate_audit.validate(audit, pool, row_admissions),
        ),
        (
            "materialize-manifest",
            candidate_manifest_errors(audit, manifest, pool),
        ),
        ("collect-news-images", attachment_errors(manifest)),
        ("build-news-maps", validate_map_decisions.validate(manifest)),
        ("render", validate_news_brief.validate_canonical_reader(manifest, brief)),
    ]


def release_recovery_error(target: str, message: str, code: int = 2) -> int:
    print("RELEASE NEEDS REPAIR", file=sys.stderr)
    print(f"RECOVERY TARGET: {target}", file=sys.stderr)
    print("-", message, file=sys.stderr)
    return code

def publish(args) -> int:
    out = Path(args.output_dir); invalidate_release(out)
    paths = {"checkpoint": Path(args.checkpoint), "manifest": Path(args.manifest), "audit": Path(args.audit),
             "source_pool": Path(args.source_pool), "brief": Path(args.brief)}
    missing = [k for k,p in paths.items() if not p.is_file()]
    if missing:
        targets = {
            "checkpoint": "checkpoint-recovery",
            "manifest": "materialize-manifest",
            "audit": "audit-news-candidates",
            "source_pool": "repository-recovery",
            "brief": "render",
        }
        return release_recovery_error(
            targets[missing[0]], "缺少 " + ", ".join(missing)
        )
    loaders = (
        ("checkpoint-recovery", "checkpoint", checkpoint_lib.load),
        ("materialize-manifest", "manifest", validate_news_brief.load_json),
        ("audit-news-candidates", "audit", validate_news_brief.load_json),
        ("repository-recovery", "source_pool", validate_news_brief.load_json),
    )
    loaded: dict[str, dict] = {}
    for target, name, loader in loaders:
        try:
            loaded[name] = loader(paths[name])
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            return release_recovery_error(target, f"{name} 無法讀取：{error}")
    cp = loaded["checkpoint"]
    manifest = loaded["manifest"]
    audit = loaded["audit"]
    pool = loaded["source_pool"]
    try:
        brief_bytes = paths["brief"].read_bytes()
        brief = brief_bytes.decode("utf-8")
    except (OSError, UnicodeError) as error:
        return release_recovery_error("render", f"讀者版無法讀取：{error}")
    if not brief.strip():
        return release_recovery_error("render", "讀者版草稿為空")
    row_admissions = None
    row_binding = (
        cp.get("stage_evidence", {}).get("source-scan", {})
        .get("artifacts", {}).get("source_row_admissions")
    )
    if isinstance(row_binding, dict):
        row_path = Path(str(row_binding.get("path", "")))
        try:
            row_admissions = validate_news_brief.load_json(row_path)
            paths["source_row_admissions"] = row_path
        except (OSError, ValueError, json.JSONDecodeError) as error:
            return release_recovery_error(
                "source-scan", f"source-row admissions 無法讀取：{error}"
            )
    groups = publication_validation_groups(
        cp, manifest, audit, pool, row_admissions, paths, brief
    )
    errors = [error for _, group_errors in groups for error in group_errors]
    if errors:
        print("RELEASE NEEDS REPAIR", file=sys.stderr)
        print(
            "RECOVERY TARGET:",
            next(target for target, group_errors in groups if group_errors),
            file=sys.stderr,
        )
        for error in errors: print("-", error, file=sys.stderr)
        return 1
    release = out / RELEASE_NAME; receipt_path = out / RECEIPT_NAME
    atomic_write(release, brief_bytes)
    artifact_paths = {"gate": Path(__file__).resolve(), "delivery_contract": CONTRACT.resolve(), **{k:p.resolve() for k,p in paths.items()}, "release": release.resolve()}
    artifacts = {k:{"path":str(p), "sha256":sha_file(p)} for k,p in artifact_paths.items()}
    receipt = {
        "schema_version":"2.0.0", "status":"ready", "gate":GATE_ID, "gate_version":GATE_VERSION,
        "run_id":cp.get("run_id"), "main_sha":manifest.get("run", {}).get("main_sha"),
        "published_at":datetime.now().astimezone().isoformat(timespec="seconds"),
        "discovery_coverage": discovery_coverage_summary(audit),
        "artifacts":artifacts, "authorized_release_sha256":artifacts["release"]["sha256"],
        "validators": {k:"passed" for k in ("unique_delivery_gate","pre_manifest_checkpoint","source_scan_and_candidate_audit","attachment_and_visual_evidence","map_decisions","manifest_and_brief")},
    }
    atomic_write(receipt_path, (json.dumps(receipt, ensure_ascii=False, indent=2)+"\n").encode())
    print(f"RELEASE READY {receipt_path}"); return 0


def validate_receipt(path: Path, expected_cp: Path | None) -> tuple[list[str], dict, bytes | None]:
    try: receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error: return [f"receipt 無法讀取：{error}"], {}, None
    errors = []
    if receipt.get("status") != "ready" or receipt.get("gate") != GATE_ID or receipt.get("gate_version") != GATE_VERSION:
        errors.append("receipt 不是目前 canonical gate 產生的 ready receipt")
    validators = receipt.get("validators", {})
    if not isinstance(validators, dict) or not validators or any(v != "passed" for v in validators.values()): errors.append("receipt validators 未全部通過")
    coverage = receipt.get("discovery_coverage")
    if not isinstance(coverage, dict):
        errors.append("receipt 缺少 discovery_coverage")
    else:
        if not isinstance(coverage.get("coverage_complete"), bool): errors.append("receipt.discovery_coverage.coverage_complete 必須是布林值")
        if not isinstance(coverage.get("degraded_source_ids"), list): errors.append("receipt.discovery_coverage.degraded_source_ids 必須是陣列")
        if not isinstance(coverage.get("sources"), list) or not coverage["sources"]: errors.append("receipt.discovery_coverage.sources 必須是非空陣列")
    artifacts = receipt.get("artifacts", {}); release_bytes = None
    required = ("gate","delivery_contract","checkpoint","manifest","audit","source_pool","source_row_admissions","brief","release")
    for name in required:
        item = artifacts.get(name) if isinstance(artifacts, dict) else None
        if not isinstance(item, dict): errors.append(f"receipt 缺少 artifact：{name}"); continue
        p = Path(str(item.get("path", "")))
        if not p.is_file(): errors.append(f"receipt artifact 不存在：{name}"); continue
        data = p.read_bytes()
        if sha_bytes(data) != item.get("sha256"): errors.append(f"receipt artifact 已變更：{name}")
        if name == "release": release_bytes = data
    cp_item = artifacts.get("checkpoint", {}) if isinstance(artifacts, dict) else {}
    if expected_cp is not None:
        if not expected_cp.is_file(): errors.append("目前 checkpoint 不存在")
        elif Path(str(cp_item.get("path", ""))).resolve() != expected_cp.resolve() or cp_item.get("sha256") != sha_file(expected_cp):
            errors.append("receipt checkpoint 不是目前執行的 checkpoint")
        else:
            try:
                if checkpoint_lib.load(expected_cp).get("run_id") != receipt.get("run_id"): errors.append("receipt.run_id 與目前 checkpoint 不一致")
            except (OSError, ValueError, json.JSONDecodeError) as error: errors.append(f"目前 checkpoint 無法驗證：{error}")
    release = artifacts.get("release", {}) if isinstance(artifacts, dict) else {}
    if release.get("sha256") != receipt.get("authorized_release_sha256"): errors.append("authorized_release_sha256 不一致")
    manifest_item = artifacts.get("manifest", {}) if isinstance(artifacts, dict) else {}
    manifest_path = Path(str(manifest_item.get("path", "")))
    if manifest_path.is_file():
        try:
            manifest = validate_news_brief.load_json(manifest_path)
            run = manifest.get("run", {}) if isinstance(manifest.get("run"), dict) else {}
            if run.get("run_id") != receipt.get("run_id"): errors.append("receipt.run_id 與 manifest 不一致")
            if run.get("main_sha") != receipt.get("main_sha"): errors.append("receipt.main_sha 與 manifest 不一致")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"receipt manifest 無法驗證：{error}")
    errors += gate_check.validate_repository(ROOT)
    return errors, receipt, release_bytes


def verify(path: Path, cp: Path | None) -> int:
    errors, receipt, _ = validate_receipt(path, cp)
    if errors:
        print("DELIVERY NEEDS RECOVERY", file=sys.stderr)
        for e in errors: print("-", e, file=sys.stderr)
        return 1
    print("DELIVERY AUTHORIZED", receipt["authorized_release_sha256"]); return 0


def deliver(path: Path, cp: Path, conversation: bool = False) -> int:
    errors, _, data = validate_receipt(path, cp)
    if errors or data is None:
        print("DELIVERY NEEDS RECOVERY", file=sys.stderr)
        for e in errors or ["release bytes 不可用"]: print("-", e, file=sys.stderr)
        return 1
    sys.stdout.buffer.write(conversation_transport(data) if conversation else data); return 0


def _checkpoint_artifact_path(
    checkpoint: dict, stage: str, name: str
) -> Path | None:
    binding = (
        checkpoint.get("stage_evidence", {})
        .get(stage, {})
        .get("artifacts", {})
        .get(name)
    )
    if not isinstance(binding, dict) or not str(binding.get("path", "")).strip():
        return None
    return Path(str(binding["path"]))


def first_resume_stage(checkpoint: dict) -> tuple[str | None, str | None]:
    """Find the first stage that must be resumed before delivery is attempted."""
    statuses = checkpoint.get("stage_status", {})
    if not isinstance(statuses, dict):
        return "source-scan", "checkpoint.stage_status 無效"
    for stage in checkpoint_lib.RELEASE_REQUIRED_STAGES:
        state = statuses.get(stage)
        if state != "completed":
            return stage, f"{stage}={state or 'missing'}"
        for name in checkpoint_lib.REQUIRED_STAGE_ARTIFACTS[stage]:
            artifact = _checkpoint_artifact_path(checkpoint, stage, name)
            if artifact is None:
                return stage, f"{stage}.{name} 缺少 artifact binding"
            errors = checkpoint_lib.verify_bound_artifact(
                checkpoint, stage, name, artifact
            )
            if errors:
                return stage, errors[0]
    return None, None


def emit_resume_decision(
    checkpoint: dict | None, target_stage: str, reason: str
) -> int:
    print(json.dumps({
        "action": "resume_required",
        "run_id": checkpoint.get("run_id") if checkpoint else None,
        "target_stage": target_stage,
        "reason": reason,
        "continue_required": True,
        "reader_delivery_authorized": False,
        "blocker_allowed": False,
        "recovery_attempt_limit": 3,
    }, ensure_ascii=False))
    return 0


def recovery_target_from_publish_output(detail: str) -> str:
    match = re.search(r"^RECOVERY TARGET:\s*([^\s]+)", detail, re.MULTILINE)
    return match.group(1) if match else "publication-recovery"


def resume_before_deliver(
    receipt_path: Path, checkpoint_path: Path, conversation: bool = False
) -> int:
    """Deliver an authorized release or return the same run's next recovery action.

    An incomplete run is normal controller state, not a terminal delivery error.
    When every stage and artifact binding is complete, a missing or invalid receipt
    is rebuilt once from the checkpoint-bound canonical inputs before delivery.
    """
    try:
        checkpoint = checkpoint_lib.load(checkpoint_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return emit_resume_decision(
            None,
            "checkpoint-recovery",
            f"checkpoint 無法讀取：{error}",
        )

    target_stage, reason = first_resume_stage(checkpoint)
    if target_stage is not None:
        return emit_resume_decision(checkpoint, target_stage, reason or "stage incomplete")

    if receipt_path.is_file():
        errors, _, data = validate_receipt(receipt_path, checkpoint_path)
        if not errors and data is not None:
            sys.stdout.buffer.write(
                conversation_transport(data) if conversation else data
            )
            return 0

    manifest = _checkpoint_artifact_path(checkpoint, "render", "manifest")
    audit = _checkpoint_artifact_path(
        checkpoint, "audit-news-candidates", "candidate_audit"
    )
    brief = _checkpoint_artifact_path(checkpoint, "render", "brief")
    if manifest is None or audit is None or brief is None:
        return emit_resume_decision(
            checkpoint,
            "render",
            "canonical publish inputs 缺少 checkpoint binding",
        )

    publish_output = io.StringIO()
    publish_errors = io.StringIO()
    args = argparse.Namespace(
        checkpoint=str(checkpoint_path),
        manifest=str(manifest),
        audit=str(audit),
        source_pool=str(ROOT / "news-source-pool.json"),
        brief=str(brief),
        output_dir=str(receipt_path.parent),
    )
    with redirect_stdout(publish_output), redirect_stderr(publish_errors):
        result = publish(args)
    if result == 0:
        delivery_result = deliver(receipt_path, checkpoint_path, conversation)
        if delivery_result == 0:
            return 0
        return emit_resume_decision(
            checkpoint,
            "delivery-revalidation",
            "delivery revalidation failed; redo delivery validation",
        )

    detail = publish_errors.getvalue().strip() or publish_output.getvalue().strip()
    return emit_resume_decision(
        checkpoint,
        recovery_target_from_publish_output(detail),
        detail or "canonical publisher requires repair",
    )


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--verify-receipt"); p.add_argument("--deliver-receipt"); p.add_argument("--resume-before-deliver"); p.add_argument("--checkpoint")
    p.add_argument("--conversation-transport", action="store_true")
    p.add_argument("--manifest"); p.add_argument("--audit"); p.add_argument("--source-pool", default=str(ROOT/"news-source-pool.json")); p.add_argument("--brief"); p.add_argument("--output-dir")
    a=p.parse_args()
    if a.resume_before_deliver:
        if not a.checkpoint: p.error("--resume-before-deliver 必須同時提供 --checkpoint")
        return resume_before_deliver(
            Path(a.resume_before_deliver),
            Path(a.checkpoint),
            a.conversation_transport,
        )
    if a.deliver_receipt:
        if not a.checkpoint: p.error("--deliver-receipt 必須同時提供 --checkpoint")
        return resume_before_deliver(
            Path(a.deliver_receipt),
            Path(a.checkpoint),
            a.conversation_transport,
        )
    if a.verify_receipt: return verify(Path(a.verify_receipt), Path(a.checkpoint) if a.checkpoint else None)
    missing=[n for n in ("checkpoint","manifest","audit","brief","output_dir") if not getattr(a,n)]
    if missing: p.error("publish 缺少必要參數："+", ".join("--"+n.replace("_","-") for n in missing))
    return publish(a)

if __name__ == "__main__": raise SystemExit(main())
