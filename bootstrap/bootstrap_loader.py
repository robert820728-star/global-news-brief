#!/usr/bin/env python3
"""Reconstruct and verify the daily-news runtime capsule inside a writable workspace."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = "1.0.0"
REPOSITORY = "robert820728-star/global-news-brief"
METHOD = "github-connector-capsule"
SCOPE = "verified-runtime-capsule"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1_bytes(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"capsule schema must be {SCHEMA_VERSION}")
    if data.get("repository") != REPOSITORY:
        raise ValueError("capsule repository mismatch")
    if data.get("materialization_method") != METHOD:
        raise ValueError("capsule materialization_method mismatch")
    if data.get("materialization_scope") != SCOPE:
        raise ValueError("capsule materialization_scope mismatch")
    return data


def verify_chunks(manifest: dict, chunks_dir: Path) -> bytes:
    pieces: list[str] = []
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("capsule chunks missing")
    if manifest.get("chunk_count") != len(chunks):
        raise ValueError("capsule chunk_count mismatch")
    for item in chunks:
        name = str(item.get("name", ""))
        if "/" in name or "\\" in name or not name.startswith("capsule.part"):
            raise ValueError(f"unsafe chunk name: {name}")
        path = chunks_dir / name
        raw = path.read_bytes()
        if len(raw) != item.get("size"):
            raise ValueError(f"chunk size mismatch: {name}")
        if sha256_bytes(raw) != item.get("sha256"):
            raise ValueError(f"chunk sha256 mismatch: {name}")
        pieces.append(raw.decode("ascii"))
    encoded = "".join(pieces)
    if len(encoded) != manifest.get("encoded_size"):
        raise ValueError("capsule encoded_size mismatch")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except Exception as error:
        raise ValueError(f"capsule base64 decode failed: {error}") from error
    if len(payload) != manifest.get("payload_size"):
        raise ValueError("capsule payload_size mismatch")
    if sha256_bytes(payload) != manifest.get("payload_sha256"):
        raise ValueError("capsule payload_sha256 mismatch")
    return payload


def expected_file_map(manifest: dict) -> dict[str, dict]:
    items = manifest.get("runtime_files")
    if not isinstance(items, list) or not items:
        raise ValueError("capsule runtime_files missing")
    result: dict[str, dict] = {}
    for item in items:
        rel = str(item.get("path", ""))
        if not safe_member_name(rel) or rel in result:
            raise ValueError(f"invalid or duplicate runtime path: {rel}")
        result[rel] = item
    if manifest.get("runtime_file_count") != len(result):
        raise ValueError("capsule runtime_file_count mismatch")
    return result


def extract_verified(payload: bytes, manifest: dict, destination: Path) -> list[dict]:
    expected = expected_file_map(manifest)
    destination.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:xz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                raise ValueError(f"non-regular tar member rejected: {member.name}")
            if not safe_member_name(member.name):
                raise ValueError(f"unsafe tar member: {member.name}")
            if member.name not in expected:
                raise ValueError(f"unexpected runtime file in capsule: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read tar member: {member.name}")
            data = source.read()
            item = expected[member.name]
            if len(data) != item.get("size"):
                raise ValueError(f"runtime size mismatch: {member.name}")
            if sha256_bytes(data) != item.get("sha256"):
                raise ValueError(f"runtime sha256 mismatch: {member.name}")
            if git_blob_sha1_bytes(data) != item.get("source_blob_sha"):
                raise ValueError(f"runtime git blob mismatch: {member.name}")
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            seen.add(member.name)
    missing = sorted(set(expected) - seen)
    if missing:
        raise ValueError("capsule missing runtime files: " + ", ".join(missing))
    return [expected[path] for path in sorted(expected)]


def materialize(manifest_path: Path, chunks_dir: Path, workspace: Path,
                commit_sha: str, manifest_blob_sha: str) -> dict:
    manifest = load_manifest(manifest_path)
    payload = verify_chunks(manifest, chunks_dir)
    workspace = workspace.resolve()
    workspace.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=workspace.name + ".stage-", dir=workspace.parent))
    try:
        files = extract_verified(payload, manifest, stage)
        if workspace.exists():
            shutil.rmtree(workspace)
        stage.replace(workspace)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    manifest_raw = manifest_path.read_bytes()
    receipt = {
        "schema_version": "1.1.0",
        "status": "completed",
        "repository": REPOSITORY,
        "ref": "main",
        "commit_sha": commit_sha,
        "materialization_method": METHOD,
        "materialization_scope": SCOPE,
        "workspace_root": str(workspace),
        "materialized_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "capsule": {
            "source_commit": manifest.get("source_commit", ""),
            "manifest_blob_sha": manifest_blob_sha,
            "manifest_sha256": sha256_bytes(manifest_raw),
            "payload_sha256": manifest["payload_sha256"],
            "runtime_fingerprint": manifest["runtime_fingerprint"],
            "chunk_count": manifest["chunk_count"],
            "chunks": manifest["chunks"],
        },
        "files": files,
    }
    receipt_path = workspace / "bootstrap-workspace.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--chunks-dir", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--manifest-blob-sha", required=True)
    args = parser.parse_args()
    try:
        receipt = materialize(
            Path(args.manifest), Path(args.chunks_dir), Path(args.workspace),
            args.commit_sha, args.manifest_blob_sha,
        )
    except Exception as error:
        print(f"BOOTSTRAP FAIL: {error}")
        return 2
    print(json.dumps({
        "status": receipt["status"],
        "commit_sha": receipt["commit_sha"],
        "runtime_file_count": len(receipt["files"]),
        "workspace_root": receipt["workspace_root"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
