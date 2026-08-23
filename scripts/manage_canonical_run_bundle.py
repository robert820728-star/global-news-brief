#!/usr/bin/env python3
"""Create and verify lossless, connector-sized canonical run bundles."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _safe_logical_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe logical path: {value}")
    return path.as_posix()


def _artifact_id(logical_path: str) -> str:
    digest = hashlib.sha256(logical_path.encode("utf-8")).hexdigest()[:16]
    name = PurePosixPath(logical_path).name.replace(" ", "-")
    return f"{name}-{digest}"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")


def pack_bundle(
    *,
    run_id: str,
    artifacts: Iterable[tuple[str, Path]],
    transport_dir: Path,
    manifest_path: Path,
    max_blob_bytes: int = 4 * 1024 * 1024,
    profile: str = "canonical-delivery",
) -> dict:
    """Pack artifacts into deterministic base64 transport files and a manifest."""
    if max_blob_bytes <= 0:
        raise ValueError("max_blob_bytes must be positive")
    transport_dir = Path(transport_dir)
    manifest_path = Path(manifest_path)
    transport_dir.mkdir(parents=True, exist_ok=True)

    artifact_records: list[dict] = []
    uploads: list[dict] = []
    seen: set[str] = set()
    bundle_root = f"logs/runs/{run_id}"

    for logical_value, source_value in artifacts:
        logical_path = _safe_logical_path(logical_value)
        if logical_path in seen:
            raise ValueError(f"duplicate logical path: {logical_path}")
        seen.add(logical_path)
        raw = Path(source_value).read_bytes()
        artifact_id = _artifact_id(logical_path)
        pieces = [raw[offset : offset + max_blob_bytes] for offset in range(0, len(raw), max_blob_bytes)]
        if not pieces:
            pieces = [b""]
        mode = "direct" if len(pieces) == 1 else "chunked"
        upload_ids: list[str] = []

        for index, piece in enumerate(pieces):
            upload_id = f"{artifact_id}-part-{index:05d}"
            transport_file = f"uploads/{upload_id}.b64"
            if mode == "direct":
                target_path = f"{bundle_root}/{logical_path}"
            else:
                target_path = f"{bundle_root}/.bundle-parts/{artifact_id}/part-{index:05d}"
            encoded = base64.b64encode(piece).decode("ascii")
            destination = transport_dir / PurePosixPath(transport_file)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(encoded, encoding="ascii", newline="\n")
            uploads.append(
                {
                    "encoding": "base64",
                    "git_blob_sha": _git_blob_sha(piece),
                    "raw_size": len(piece),
                    "sha256": _sha256(piece),
                    "target_path": target_path,
                    "transport_file": transport_file,
                    "upload_id": upload_id,
                }
            )
            upload_ids.append(upload_id)

        artifact_records.append(
            {
                "logical_path": logical_path,
                "sha256": _sha256(raw),
                "size": len(raw),
                "storage": {"mode": mode, "upload_ids": upload_ids},
            }
        )

    manifest = {
        "artifacts": artifact_records,
        "bundle_root": bundle_root,
        "format": "canonical-run-bundle-v1",
        "max_blob_bytes": max_blob_bytes,
        "profile": profile,
        "run_id": run_id,
        "uploads": uploads,
    }
    _write_json(manifest_path, manifest)
    return manifest


def build_hydration_batch_index(*, run_id: str, admitted: dict, max_batch_rows: int = 20) -> dict:
    """Materialize every admitted candidate exactly once into stable hydration batches."""
    if not 1 <= max_batch_rows <= 20:
        raise ValueError("max_batch_rows must be between 1 and 20")
    items = admitted.get("items")
    if not isinstance(items, list):
        raise ValueError("admitted candidate items must be an array")
    seen: set[str] = set()
    rows: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("admitted candidate items must be objects")
        candidate_id = str(item.get("candidate_id", ""))
        if not candidate_id or candidate_id in seen:
            raise ValueError("admitted candidate ids must be non-empty and unique")
        seen.add(candidate_id)
        rows.append(
            {
                "candidate_id": candidate_id,
                "source_id": str(item.get("source_id", "")),
                "canonical_url": str(item.get("canonical_url") or item.get("url") or ""),
                "summary_quality": str(item.get("summary_quality", "")),
            }
        )
    batches = []
    for offset in range(0, len(rows), max_batch_rows):
        batch_rows = rows[offset : offset + max_batch_rows]
        batches.append(
            {
                "batch_id": f"batch-{len(batches) + 1:03d}",
                "article_row_count": len(batch_rows),
                "items": batch_rows,
            }
        )
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "candidate_count": len(rows),
        "max_batch_rows": max_batch_rows,
        "batches": batches,
    }


def _read_json_object(path: Path, label: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def pack_pre_manifest_recovery_bundle(
    *,
    run_id: str,
    checkpoint_path: Path,
    source_candidates_path: Path,
    relevance_gate_path: Path,
    admitted_candidates_path: Path,
    preprocessed_candidates_path: Path,
    batch_index_path: Path,
    transport_dir: Path,
    manifest_path: Path,
    max_batch_rows: int = 20,
    max_blob_bytes: int = 4 * 1024 * 1024,
) -> dict:
    """Persist all inputs needed to resume selection after workspace loss."""
    inputs = {
        "checkpoint": _read_json_object(checkpoint_path, "checkpoint"),
        "source candidates": _read_json_object(source_candidates_path, "source candidates"),
        "relevance gate": _read_json_object(relevance_gate_path, "relevance gate"),
        "admitted candidates": _read_json_object(admitted_candidates_path, "admitted candidates"),
        "preprocessed candidates": _read_json_object(preprocessed_candidates_path, "preprocessed candidates"),
    }
    checkpoint = inputs["checkpoint"]
    expected_identity = (
        str(checkpoint.get("run_id", "")),
        str(checkpoint.get("window_start", "")),
        str(checkpoint.get("window_end", "")),
    )
    if expected_identity[0] != run_id or not expected_identity[1] or not expected_identity[2]:
        raise ValueError("checkpoint run/window mismatch")
    for label, value in inputs.items():
        observed = (
            str(value.get("run_id", "")),
            str(value.get("window_start", "")),
            str(value.get("window_end", "")),
        )
        if observed[0] and observed[0] != run_id:
            raise ValueError(f"{label} run/window mismatch")
        if observed[1] and observed[1:] != expected_identity[1:]:
            raise ValueError(f"{label} run/window mismatch")

    batch_index = build_hydration_batch_index(
        run_id=run_id,
        admitted=inputs["admitted candidates"],
        max_batch_rows=max_batch_rows,
    )
    _write_json(Path(batch_index_path), batch_index)
    return pack_bundle(
        run_id=run_id,
        artifacts=[
            ("recovery/checkpoint.json", Path(checkpoint_path)),
            ("recovery/source-candidates.json", Path(source_candidates_path)),
            ("recovery/news-relevance-gate.json", Path(relevance_gate_path)),
            ("recovery/model-source-candidates.json", Path(admitted_candidates_path)),
            ("recovery/preprocessed-candidates.json", Path(preprocessed_candidates_path)),
            ("recovery/content-hydration-batches.json", Path(batch_index_path)),
        ],
        transport_dir=Path(transport_dir),
        manifest_path=Path(manifest_path),
        max_blob_bytes=max_blob_bytes,
        profile="pre-manifest-recovery",
    )


def _load_verified(manifest_path: Path, transport_dir: Path) -> tuple[dict, dict[str, bytes]]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("format") != "canonical-run-bundle-v1":
        raise ValueError("unsupported bundle format")
    upload_bytes: dict[str, bytes] = {}
    for upload in manifest.get("uploads", []):
        if upload.get("encoding") != "base64":
            raise ValueError("unsupported upload encoding")
        transport_file = _safe_logical_path(upload["transport_file"])
        encoded = (Path(transport_dir) / PurePosixPath(transport_file)).read_text(encoding="ascii")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError("upload base64 invalid") from exc
        if _sha256(raw) != upload.get("sha256"):
            raise ValueError("upload sha256 mismatch")
        if len(raw) != upload.get("raw_size"):
            raise ValueError("upload size mismatch")
        if _git_blob_sha(raw) != upload.get("git_blob_sha"):
            raise ValueError("upload Git blob SHA mismatch")
        upload_bytes[upload["upload_id"]] = raw

    for artifact in manifest.get("artifacts", []):
        _safe_logical_path(artifact["logical_path"])
        try:
            raw = b"".join(upload_bytes[item] for item in artifact["storage"]["upload_ids"])
        except KeyError as exc:
            raise ValueError("artifact references missing upload") from exc
        if _sha256(raw) != artifact.get("sha256"):
            raise ValueError("artifact sha256 mismatch")
        if len(raw) != artifact.get("size"):
            raise ValueError("artifact size mismatch")
    return manifest, upload_bytes


def verify_bundle(*, manifest_path: Path, transport_dir: Path) -> dict:
    """Reject any transport or reconstructed artifact that is not byte-identical."""
    manifest, _ = _load_verified(Path(manifest_path), Path(transport_dir))
    return manifest


def restore_bundle(*, manifest_path: Path, transport_dir: Path, output_dir: Path) -> dict:
    """Reconstruct all logical artifacts after full integrity verification."""
    manifest, upload_bytes = _load_verified(Path(manifest_path), Path(transport_dir))
    output_dir = Path(output_dir)
    for artifact in manifest["artifacts"]:
        logical_path = _safe_logical_path(artifact["logical_path"])
        raw = b"".join(upload_bytes[item] for item in artifact["storage"]["upload_ids"])
        destination = output_dir / PurePosixPath(logical_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    return manifest


def _artifact_argument(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must be LOGICAL_PATH=LOCAL_PATH")
    logical_path, local_path = value.split("=", 1)
    return logical_path, Path(local_path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    pack.add_argument("--run-id", required=True)
    pack.add_argument("--transport-dir", type=Path, required=True)
    pack.add_argument("--manifest", type=Path, required=True)
    pack.add_argument("--max-blob-bytes", type=int, default=4 * 1024 * 1024)
    pack.add_argument("--artifact", type=_artifact_argument, action="append", required=True)
    recovery = commands.add_parser("pack-recovery")
    recovery.add_argument("--run-id", required=True)
    recovery.add_argument("--checkpoint", type=Path, required=True)
    recovery.add_argument("--source-candidates", type=Path, required=True)
    recovery.add_argument("--relevance-gate", type=Path, required=True)
    recovery.add_argument("--admitted-candidates", type=Path, required=True)
    recovery.add_argument("--preprocessed-candidates", type=Path, required=True)
    recovery.add_argument("--batch-index", type=Path, required=True)
    recovery.add_argument("--transport-dir", type=Path, required=True)
    recovery.add_argument("--manifest", type=Path, required=True)
    recovery.add_argument("--max-batch-rows", type=int, default=20)
    recovery.add_argument("--max-blob-bytes", type=int, default=4 * 1024 * 1024)
    for name in ("verify", "restore"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--transport-dir", type=Path, required=True)
        if name == "restore":
            command.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "pack":
        manifest = pack_bundle(
            run_id=args.run_id,
            artifacts=args.artifact,
            transport_dir=args.transport_dir,
            manifest_path=args.manifest,
            max_blob_bytes=args.max_blob_bytes,
        )
    elif args.command == "pack-recovery":
        manifest = pack_pre_manifest_recovery_bundle(
            run_id=args.run_id,
            checkpoint_path=args.checkpoint,
            source_candidates_path=args.source_candidates,
            relevance_gate_path=args.relevance_gate,
            admitted_candidates_path=args.admitted_candidates,
            preprocessed_candidates_path=args.preprocessed_candidates,
            batch_index_path=args.batch_index,
            transport_dir=args.transport_dir,
            manifest_path=args.manifest,
            max_batch_rows=args.max_batch_rows,
            max_blob_bytes=args.max_blob_bytes,
        )
    elif args.command == "verify":
        manifest = verify_bundle(manifest_path=args.manifest, transport_dir=args.transport_dir)
    else:
        manifest = restore_bundle(
            manifest_path=args.manifest,
            transport_dir=args.transport_dir,
            output_dir=args.output_dir,
        )
    print(json.dumps({"status": "OK", "run_id": manifest["run_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
