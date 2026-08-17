#!/usr/bin/env python3
"""Canonical fail-closed release and delivery gate for the daily news brief."""
from __future__ import annotations

import argparse, hashlib, json, os, sys, tempfile
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
GATE_VERSION = "2.1.0"
RELEASE_NAME = "news-brief.md"
RECEIPT_NAME = "release-receipt.json"
CONTRACT = ROOT / "daily-schedule-prompt.md"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return checkpoint_lib.sha256_file(path)


def local_path(value: str) -> Path:
    return Path(value.removeprefix("sandbox:"))


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
        images = event.get("images", {})
        if isinstance(images, dict):
            for group in ("source_checks", "professional_source_checks"):
                for i, check in enumerate(images.get(group, []), 1):
                    path = check.get("evidence_path") if isinstance(check, dict) else None
                    if isinstance(path, str):
                        local = local_path(path)
                        if not local.is_file() or local.stat().st_size < 1:
                            errors.append(f"{eid}.images.{group}[{i}] 檢查證據不存在或為空：{path}")
    return errors


def candidate_errors(audit: dict, manifest: dict, source_pool: dict) -> list[str]:
    errors = manage_candidate_audit.validate(audit, source_pool)
    runs = audit.get("runs", [])
    if not runs: return errors + ["候選稽核沒有本輪紀錄"]
    selected = {
        c.get("selected_event_id")
        for c in runs[-1].get("candidates", [])
        if c.get("provisional_grade") in manage_candidate_audit.AUTO_SELECT
        and c.get("decision") in {"selected", "merged"}
    }
    selected.discard(None)
    ids = {e.get("event_id") for e in manifest.get("events", []) if isinstance(e, dict)}
    if selected != ids:
        errors.append("十四天候選稽核本輪 C 級以上入選事件與 manifest 不一致；禁止漏放達標事件或額外補新聞")
    return errors


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


def publish(args) -> int:
    out = Path(args.output_dir); invalidate_release(out)
    paths = {"checkpoint": Path(args.checkpoint), "manifest": Path(args.manifest), "audit": Path(args.audit),
             "source_pool": Path(args.source_pool), "brief": Path(args.brief)}
    missing = [k for k,p in paths.items() if not p.is_file()]
    if missing: print("RELEASE BLOCKED: 缺少 " + ", ".join(missing), file=sys.stderr); return 2
    if not paths["brief"].read_text(encoding="utf-8").strip(): print("RELEASE BLOCKED: 讀者版草稿為空", file=sys.stderr); return 2
    try:
        cp = checkpoint_lib.load(paths["checkpoint"])
        manifest = validate_news_brief.load_json(paths["manifest"])
        audit = validate_news_brief.load_json(paths["audit"])
        pool = validate_news_brief.load_json(paths["source_pool"])
        brief_bytes = paths["brief"].read_bytes(); brief = brief_bytes.decode("utf-8")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"RELEASE BLOCKED: {error}", file=sys.stderr); return 2
    errors = gate_check.validate_repository(ROOT)
    errors += checkpoint_errors(cp, manifest, audit, paths)
    errors += candidate_errors(audit, manifest, pool)
    errors += attachment_errors(manifest)
    errors += validate_map_decisions.validate(manifest)
    errors += validate_news_brief.validate_brief_text(manifest, brief)
    if errors:
        print("RELEASE NEEDS REPAIR", file=sys.stderr)
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
    artifacts = receipt.get("artifacts", {}); release_bytes = None
    required = ("gate","delivery_contract","checkpoint","manifest","audit","source_pool","brief","release")
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
        print("DELIVERY BLOCKED", file=sys.stderr)
        for e in errors: print("-", e, file=sys.stderr)
        return 1
    print("DELIVERY AUTHORIZED", receipt["authorized_release_sha256"]); return 0


def deliver(path: Path, cp: Path) -> int:
    errors, _, data = validate_receipt(path, cp)
    if errors or data is None:
        print("DELIVERY BLOCKED", file=sys.stderr)
        for e in errors or ["release bytes 不可用"]: print("-", e, file=sys.stderr)
        return 1
    sys.stdout.buffer.write(data); return 0


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--verify-receipt"); p.add_argument("--deliver-receipt"); p.add_argument("--checkpoint")
    p.add_argument("--manifest"); p.add_argument("--audit"); p.add_argument("--source-pool", default=str(ROOT/"news-source-pool.json")); p.add_argument("--brief"); p.add_argument("--output-dir")
    a=p.parse_args()
    if a.deliver_receipt:
        if not a.checkpoint: p.error("--deliver-receipt 必須同時提供 --checkpoint")
        return deliver(Path(a.deliver_receipt), Path(a.checkpoint))
    if a.verify_receipt: return verify(Path(a.verify_receipt), Path(a.checkpoint) if a.checkpoint else None)
    missing=[n for n in ("checkpoint","manifest","audit","brief","output_dir") if not getattr(a,n)]
    if missing: p.error("publish 缺少必要參數："+", ".join("--"+n.replace("_","-") for n in missing))
    return publish(a)

if __name__ == "__main__": raise SystemExit(main())
