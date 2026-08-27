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
import urllib.request
from datetime import datetime
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = "1.1.0"
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


def load_manifest_bytes(raw: bytes) -> dict:
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"capsule schema must be {SCHEMA_VERSION}")
    if data.get("repository") != REPOSITORY:
        raise ValueError("capsule repository mismatch")
    if data.get("materialization_method") != METHOD:
        raise ValueError("capsule materialization_method mismatch")
    if data.get("materialization_scope") != SCOPE:
        raise ValueError("capsule materialization_scope mismatch")
    for field in ("chunk_size", "line_width", "retrieval_block_lines"):
        value = data.get(field)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"capsule {field} must be a positive integer")
    return data


def load_manifest(path: Path) -> dict:
    return load_manifest_bytes(path.read_bytes())


def verify_chunk_transport(item: dict, raw: bytes, line_width: int,
                           block_lines: int) -> str:
    name = str(item.get("name", ""))
    if len(raw) != item.get("size"):
        raise ValueError(f"chunk size mismatch: {name}")
    if sha256_bytes(raw) != item.get("sha256"):
        raise ValueError(f"chunk sha256 mismatch: {name}")
    if b"\r" in raw:
        raise ValueError(f"chunk contains non-canonical CR line ending: {name}")
    if raw and not raw.endswith(b"\n"):
        raise ValueError(f"chunk missing final LF: {name}")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError(f"chunk is not ASCII: {name}") from error

    raw_lines = raw.splitlines(keepends=True)
    lines = text.splitlines()
    if item.get("line_count") != len(lines):
        raise ValueError(f"chunk line_count mismatch: {name}")
    for index, line in enumerate(lines, start=1):
        if not line:
            raise ValueError(f"chunk empty line: {name}:{index}")
        if index < len(lines) and len(line) != line_width:
            raise ValueError(f"chunk non-final line width mismatch: {name}:{index}")
        if len(line) > line_width:
            raise ValueError(f"chunk line too wide: {name}:{index}")

    blocks = item.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError(f"chunk blocks missing: {name}")
    if item.get("block_count") != len(blocks):
        raise ValueError(f"chunk block_count mismatch: {name}")
    expected_start = 1
    for block_index, block in enumerate(blocks, start=1):
        if block.get("index") != block_index:
            raise ValueError(f"chunk block index mismatch: {name}:{block_index}")
        start_line = block.get("start_line")
        end_line = block.get("end_line")
        if start_line != expected_start or not isinstance(end_line, int) or end_line < start_line:
            raise ValueError(f"chunk block line range mismatch: {name}:{block_index}")
        if end_line - start_line + 1 > block_lines:
            raise ValueError(f"chunk block exceeds retrieval_block_lines: {name}:{block_index}")
        if end_line > len(raw_lines):
            raise ValueError(f"chunk block line range exceeds chunk: {name}:{block_index}")
        block_raw = b"".join(raw_lines[start_line - 1:end_line])
        if len(block_raw) != block.get("size"):
            raise ValueError(f"chunk block size mismatch: {name}:{block_index}")
        if sha256_bytes(block_raw) != block.get("sha256"):
            raise ValueError(f"chunk block sha256 mismatch: {name}:{block_index}")
        expected_start = end_line + 1
    if expected_start != len(raw_lines) + 1:
        raise ValueError(f"chunk blocks do not cover all lines: {name}")

    encoded = "".join(lines)
    encoded_raw = encoded.encode("ascii")
    if len(encoded_raw) != item.get("encoded_size"):
        raise ValueError(f"chunk encoded_size mismatch: {name}")
    if sha256_bytes(encoded_raw) != item.get("encoded_sha256"):
        raise ValueError(f"chunk encoded_sha256 mismatch: {name}")
    return encoded


def verify_chunks(manifest: dict, chunks_dir: Path) -> bytes:
    pieces: list[str] = []
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("capsule chunks missing")
    if manifest.get("chunk_count") != len(chunks):
        raise ValueError("capsule chunk_count mismatch")
    line_width = manifest["line_width"]
    block_lines = manifest["retrieval_block_lines"]
    for item in chunks:
        name = str(item.get("name", ""))
        if "/" in name or "\\" in name or not name.startswith("capsule.part"):
            raise ValueError(f"unsafe chunk name: {name}")
        path = chunks_dir / name
        raw = path.read_bytes()
        pieces.append(verify_chunk_transport(item, raw, line_width, block_lines))
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


def verify_direct_payload(manifest: dict, payload: bytes) -> bytes:
    item = manifest.get("payload")
    if not isinstance(item, dict):
        raise ValueError("capsule direct payload metadata missing")
    if item.get("name") != "capsule-payload.tar.xz":
        raise ValueError("capsule direct payload name mismatch")
    if len(payload) != item.get("size") or len(payload) != manifest.get("payload_size"):
        raise ValueError("capsule direct payload size mismatch")
    digest = sha256_bytes(payload)
    if digest != item.get("sha256") or digest != manifest.get("payload_sha256"):
        raise ValueError("capsule direct payload sha256 mismatch")
    if git_blob_sha1_bytes(payload) != item.get("source_blob_sha"):
        raise ValueError("capsule direct payload git blob mismatch")
    return payload


def payload_from_url(manifest: dict, url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return verify_direct_payload(manifest, response.read())


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


def materialize(manifest_path: Path | None, chunks_dir: Path | None, workspace: Path,
                commit_sha: str, manifest_blob_sha: str,
                payload_url: str | None = None,
                manifest_url: str | None = None) -> dict:
    if manifest_url:
        with urllib.request.urlopen(manifest_url, timeout=30) as response:
            manifest_raw = response.read()
        if git_blob_sha1_bytes(manifest_raw) != manifest_blob_sha:
            raise ValueError("manifest git blob mismatch")
        manifest = load_manifest_bytes(manifest_raw)
    elif manifest_path is not None:
        manifest_raw = manifest_path.read_bytes()
        manifest = load_manifest_bytes(manifest_raw)
    else:
        raise ValueError("capsule manifest source missing")
    if payload_url:
        payload = payload_from_url(manifest, payload_url)
        transport = "direct-payload"
    elif chunks_dir is not None:
        payload = verify_chunks(manifest, chunks_dir)
        transport = "segmented-chunks"
    else:
        raise ValueError("capsule transport missing")
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
            "transport": transport,
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
    manifest_source = parser.add_mutually_exclusive_group(required=True)
    manifest_source.add_argument("--manifest")
    manifest_source.add_argument("--manifest-url")
    transport = parser.add_mutually_exclusive_group(required=True)
    transport.add_argument("--chunks-dir")
    transport.add_argument("--payload-url")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--manifest-blob-sha", required=True)
    args = parser.parse_args()
    try:
        receipt = materialize(
            Path(args.manifest) if args.manifest else None,
            Path(args.chunks_dir) if args.chunks_dir else None,
            Path(args.workspace), args.commit_sha, args.manifest_blob_sha,
            payload_url=args.payload_url, manifest_url=args.manifest_url,
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

