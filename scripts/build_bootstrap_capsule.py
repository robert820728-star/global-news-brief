#!/usr/bin/env python3
"""Build a deterministic, connector-friendly bootstrap runtime capsule."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import lzma
import os
import tarfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CAPSULE_DIR = ROOT / "bootstrap"
MANIFEST_PATH = CAPSULE_DIR / "capsule-manifest.json"
PAYLOAD_NAME = "capsule-payload.tar.xz"
CHUNK_PREFIX = "capsule.part"
CHUNK_SUFFIX = ".txt"
CHUNK_SIZE = 8192
LINE_WIDTH = 256
BLOCK_LINES = 8
SCHEMA_VERSION = "1.1.0"
REPOSITORY = "robert820728-star/global-news-brief"
MATERIALIZATION_METHOD = "github-connector-capsule"
MATERIALIZATION_SCOPE = "verified-runtime-capsule"

RUNTIME_FILES = (
    "bootstrap-workspace.md",
    "mobile-chatgpt-daily-prompt.md",
    "scheduled-task-prompt-template.md",
    "daily-schedule-prompt.md",
    "news-brief-settings.md",
    "news-brief-template.md",
    "news-brief-examples.md",
    "user-preferences.example.yaml",
    "news-source-pool.json",
    "source-route-config.json",
    "maps/README.md",
    "maps/style.json",
    "bootstrap/bootstrap_loader.py",
    "bootstrap/bootstrap_progress.py",
    "bootstrap/bootstrap-progress.schema.json",
    "bootstrap/RUN_LEDGER_PROTOCOL.md",
)
RUNTIME_DIRS = (
    ".agents/skills",
    "schemas",
    "scripts",
    "maps/source",
    "maps/generated/sections",
    "state",
)
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".ps1"}
EXCLUDE_GENERATED_SUFFIXES = {".png", ".svg"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1_bytes(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def safe_runtime_path(path: Path, root: Path = ROOT) -> str:
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    if rel.startswith("../") or rel == "..":
        raise ValueError(f"path escapes repo root: {path}")
    return rel


def collect_runtime_paths(root: Path = ROOT) -> list[Path]:
    root = root.resolve()
    paths: set[Path] = set()
    for rel in RUNTIME_FILES:
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(f"required runtime file missing: {rel}")
        paths.add(path.resolve())
    for rel in RUNTIME_DIRS:
        base = root / rel
        if not base.exists():
            raise FileNotFoundError(f"required runtime directory missing: {rel}")
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDE_NAMES for part in path.parts):
                continue
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            if rel == "maps/generated/sections" and path.suffix.lower() in EXCLUDE_GENERATED_SUFFIXES:
                continue
            if path.parent == root / "bootstrap" and path.name.startswith(CHUNK_PREFIX):
                continue
            if path == MANIFEST_PATH:
                continue
            paths.add(path.resolve())
    return sorted(paths, key=lambda p: safe_runtime_path(p, root))


def runtime_records(root: Path = ROOT) -> list[dict]:
    records = []
    for path in collect_runtime_paths(root):
        data = path.read_bytes()
        records.append({
            "path": safe_runtime_path(path, root),
            "source_blob_sha": git_blob_sha1_bytes(data),
            "sha256": sha256_bytes(data),
            "size": len(data),
        })
    return records


def runtime_fingerprint(records: Iterable[dict]) -> str:
    material = "".join(
        f"{item['path']}\0{item['source_blob_sha']}\0{item['sha256']}\0{item['size']}\n"
        for item in records
    ).encode("utf-8")
    return sha256_bytes(material)


def deterministic_tar_bytes(root: Path, records: list[dict]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for item in records:
            rel = item["path"]
            data = (root / rel).read_bytes()
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def frame_chunk(text: str, line_width: int = LINE_WIDTH,
                block_lines: int = BLOCK_LINES) -> tuple[bytes, list[dict]]:
    if line_width <= 0 or block_lines <= 0:
        raise ValueError("line_width and block_lines must be positive")
    lines = [text[i:i + line_width] for i in range(0, len(text), line_width)]
    raw_lines = [(line + "\n").encode("ascii") for line in lines]
    raw = b"".join(raw_lines)
    blocks = []
    for block_index, start in enumerate(range(0, len(raw_lines), block_lines), start=1):
        block_raw = b"".join(raw_lines[start:start + block_lines])
        blocks.append({
            "index": block_index,
            "start_line": start + 1,
            "end_line": min(start + block_lines, len(raw_lines)),
            "size": len(block_raw),
            "sha256": sha256_bytes(block_raw),
        })
    return raw, blocks


def build_capsule(root: Path = ROOT, output_dir: Path | None = None,
                  source_commit: str = "", chunk_size: int = CHUNK_SIZE,
                  line_width: int = LINE_WIDTH, block_lines: int = BLOCK_LINES) -> dict:
    root = root.resolve()
    output_dir = (output_dir or (root / "bootstrap")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records = runtime_records(root)
    tar_bytes = deterministic_tar_bytes(root, records)
    payload = lzma.compress(tar_bytes, format=lzma.FORMAT_XZ, preset=9)
    encoded = base64.b64encode(payload).decode("ascii")
    (output_dir / PAYLOAD_NAME).write_bytes(payload)

    for old in output_dir.glob(f"{CHUNK_PREFIX}*{CHUNK_SUFFIX}"):
        old.unlink()

    chunks = []
    for index, start in enumerate(range(0, len(encoded), chunk_size), start=1):
        text = encoded[start:start + chunk_size]
        name = f"{CHUNK_PREFIX}{index:04d}{CHUNK_SUFFIX}"
        path = output_dir / name
        raw, blocks = frame_chunk(text, line_width=line_width, block_lines=block_lines)
        path.write_bytes(raw)
        chunks.append({
            "name": name,
            "sha256": sha256_bytes(raw),
            "size": len(raw),
            "encoded_sha256": sha256_bytes(text.encode("ascii")),
            "encoded_size": len(text),
            "line_count": len(raw.splitlines()),
            "block_count": len(blocks),
            "blocks": blocks,
        })

    loader_path = root / "bootstrap/bootstrap_loader.py"
    loader_data = loader_path.read_bytes()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "repository": REPOSITORY,
        "source_commit": source_commit,
        "materialization_method": MATERIALIZATION_METHOD,
        "materialization_scope": MATERIALIZATION_SCOPE,
        "encoding": "base64",
        "archive": "tar.xz",
        "chunk_size": chunk_size,
        "line_width": line_width,
        "retrieval_block_lines": block_lines,
        "chunk_count": len(chunks),
        "encoded_size": len(encoded),
        "payload_sha256": sha256_bytes(payload),
        "payload_size": len(payload),
        "payload": {
            "name": PAYLOAD_NAME,
            "source_blob_sha": git_blob_sha1_bytes(payload),
            "sha256": sha256_bytes(payload),
            "size": len(payload),
        },
        "runtime_file_count": len(records),
        "runtime_fingerprint": runtime_fingerprint(records),
        "runtime_files": records,
        "loader": {
            "path": "bootstrap/bootstrap_loader.py",
            "source_blob_sha": git_blob_sha1_bytes(loader_data),
            "sha256": sha256_bytes(loader_data),
            "size": len(loader_data),
        },
        "chunks": chunks,
    }
    manifest_path = output_dir / "capsule-manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output-dir")
    parser.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--line-width", type=int, default=LINE_WIDTH)
    parser.add_argument("--block-lines", type=int, default=BLOCK_LINES)
    args = parser.parse_args()
    manifest = build_capsule(
        Path(args.root),
        Path(args.output_dir) if args.output_dir else None,
        args.source_commit,
        args.chunk_size,
        args.line_width,
        args.block_lines,
    )
    print(json.dumps({
        "status": "completed",
        "runtime_file_count": manifest["runtime_file_count"],
        "chunk_count": manifest["chunk_count"],
        "payload_size": manifest["payload_size"],
        "encoded_size": manifest["encoded_size"],
        "line_width": manifest["line_width"],
        "retrieval_block_lines": manifest["retrieval_block_lines"],
        "runtime_fingerprint": manifest["runtime_fingerprint"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
