#!/usr/bin/env python3
"""Recover coverage-sweep leads with verified evidence from the same source.

The canonical route and direct same-site transport remain the normal path. A
browser-rendered snapshot can be imported only when the caller has already
exhausted non-browser routes; it passes through the same evidence validator.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import materialize_source_scans as materializer


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalized_host(value: str) -> str:
    return urlsplit(str(value)).netloc.lower().removeprefix("www.")


def normalized_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def fetch_direct(url: str, timeout_seconds: int):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "global-news-brief/1.0 same-source-recovery"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return (
            response.geturl(),
            response.status,
            response.headers.get("Content-Type", "application/octet-stream"),
            response.read(),
        )


def atomic_write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def rank_scan(scan: dict, source: dict, coverage: dict, ranking: dict) -> dict:
    start = datetime.fromisoformat(scan["window_start"])
    end = datetime.fromisoformat(scan["window_end"])
    pages = list(scan.get("pages", [])) + list(scan.get("supplemental_pages", []))
    items_by_url = {}
    for page in pages:
        for item in page.get("extracted_items", []):
            items_by_url[normalized_url(item["url"])] = item
    within = [
        item for item in items_by_url.values()
        if start < datetime.fromisoformat(item["published_at"]) <= end
    ]
    ranked = []
    for item in within:
        breakdown = materializer.score_breakdown(
            item["title"], item.get("summary", ""), source.get("section", ""), ranking
        )
        ranked.append({
            "url": item["url"],
            "title": item["title"],
            "published_at": item["published_at"],
            "importance_score": materializer.weighted_score(breakdown, ranking),
            "importance_breakdown": breakdown,
            "importance_reason": item.get("importance_hint") or item["title"],
        })
    ranked.sort(
        key=lambda item: (item["importance_score"], item["published_at"], item["url"]),
        reverse=True,
    )
    base_selected = [item["url"] for item in ranked]
    selected = base_selected
    updated = copy.deepcopy(coverage)
    updated.update({
        "within_window_count": len(within),
        "ranked_count": len(ranked),
        "ranked_items": ranked,
        "selected_for_pool_count": len(selected),
        "selected_item_urls": selected,
        "ranking_completed": True,
        "ranking_method": ranking["method"],
        "failure_reason": None,
    })
    return updated


def recover(pool: dict, scan_dir: Path, coverage: list[dict], leads: list[dict],
            snapshot_dir: Path, *, fetcher=fetch_direct, timeout_seconds: int = 20) -> dict:
    ranking = pool.get("ranking")
    materializer.ranking_dimensions(ranking)
    sources = {item["source_id"]: item for item in pool.get("discovery_sources", [])}
    coverage_by_id = {item["source_id"]: item for item in coverage}
    scans = {}
    recovered = []
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    for lead in leads:
        source_id = lead.get("source_id")
        source = sources.get(source_id)
        coverage_item = coverage_by_id.get(source_id)
        if source is None or coverage_item is None:
            raise ValueError(f"unknown same-source recovery source: {source_id}")
        scan_path = scan_dir / f"{source_id}.json"
        scan = scans.setdefault(source_id, load_json(scan_path))
        requested_url = str(lead.get("url", ""))
        source_host = normalized_host(source.get("homepage", ""))
        if not requested_url or normalized_host(requested_url) != source_host:
            raise ValueError(f"same-source lead rejected: {requested_url}")

        route = lead.get("acquisition_route")
        if route == "browser_rendered":
            failed_routes = {
                attempt.get("route")
                for attempt in lead.get("prior_attempts", [])
                if isinstance(attempt, dict) and attempt.get("status") == "failed"
            }
            required_failures = {"same_source_direct", "same_source_alternate"}
            if not required_failures.issubset(failed_routes):
                raise ValueError(
                    "browser is the final fallback only; direct and alternate "
                    "non-browser failures must be recorded first"
                )
            snapshot = Path(str(lead.get("snapshot_path", "")))
            if not snapshot.is_file():
                raise ValueError(f"browser snapshot missing: {snapshot}")
            raw = snapshot.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != lead.get("sha256"):
                raise ValueError("browser snapshot SHA-256 mismatch")
            final_url, status, content_type = requested_url, 200, "text/html; charset=utf-8"
            stored_snapshot = snapshot.resolve()
            recovery_route = "browser_rendered"
        else:
            fetch_url = str(lead.get("alternate_url") or requested_url)
            if normalized_host(fetch_url) != source_host:
                raise ValueError(f"same-source alternate rejected: {fetch_url}")
            final_url, status, content_type, raw = fetcher(fetch_url, timeout_seconds)
            if normalized_host(final_url) != source_host:
                raise ValueError(f"same-source redirect rejected: {final_url}")
            if status != 200:
                raise ValueError(f"same-source fetch returned HTTP {status}")
            digest = hashlib.sha256(raw).hexdigest()
            stored_snapshot = (snapshot_dir / f"{source_id}-{digest[:20]}.bin").resolve()
            if not stored_snapshot.exists():
                stored_snapshot.write_bytes(raw)
            recovery_route = "same_source_alternate" if lead.get("alternate_url") else "same_source_direct"

        text = materializer.decode_snapshot(raw, content_type)
        parsed = materializer.parse_xml(
            text, final_url, source["homepage"], recovery_route,
            datetime.fromisoformat(scan["window_end"]).year,
        )
        parsed.update(materializer.parse_html(
            text, final_url, source["homepage"], recovery_route,
            datetime.fromisoformat(scan["window_end"]).year,
        ))
        target = normalized_url(requested_url)
        item = next((value for key, value in parsed.items() if normalized_url(key) == target), None)
        if item is None:
            raise ValueError(f"same-source article evidence was not materialized: {requested_url}")
        published = datetime.fromisoformat(item["published_at"])
        if not datetime.fromisoformat(scan["window_start"]) < published <= datetime.fromisoformat(scan["window_end"]):
            raise ValueError(f"same-source lead outside scan window: {requested_url}")
        item["acquisition_route"] = recovery_route
        scan.setdefault("supplemental_pages", []).append({
            "request_url": requested_url,
            "final_url": final_url,
            "fetched_at": datetime.now().astimezone().isoformat(),
            "http_status": status,
            "content_type": content_type,
            "snapshot_path": str(stored_snapshot),
            "sha256": digest,
            "next_url": None,
            "recovery_route": recovery_route,
            "lead_id": lead.get("lead_id"),
            "sweep_id": lead.get("sweep_id"),
            "extracted_items": [item],
        })
        recovered.append({
            "lead_id": lead.get("lead_id"), "source_id": source_id,
            "url": item["url"], "route": recovery_route,
        })

    coverage_updates = {
        source_id: rank_scan(
            scan, sources[source_id], coverage_by_id[source_id], ranking
        )
        for source_id, scan in scans.items()
    }
    for source_id, scan in scans.items():
        atomic_write_json(scan_dir / f"{source_id}.json", scan)
    for index, item in enumerate(coverage):
        source_id = item.get("source_id")
        if source_id in coverage_updates:
            coverage[index].clear()
            coverage[index].update(coverage_updates[source_id])
    return {"schema_version": "1.0.0", "status": "completed", "recovered": recovered}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pool", required=True)
    parser.add_argument("--scan-dir", required=True)
    parser.add_argument("--coverage", required=True)
    parser.add_argument("--leads", required=True)
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    args = parser.parse_args()
    coverage_path = Path(args.coverage)
    coverage = load_json(coverage_path)
    lead_data = load_json(Path(args.leads))
    leads = lead_data.get("leads", []) if isinstance(lead_data, dict) else lead_data
    report = recover(
        load_json(Path(args.source_pool)), Path(args.scan_dir), coverage, leads,
        Path(args.snapshot_dir), timeout_seconds=args.timeout_seconds,
    )
    atomic_write_json(coverage_path, coverage)
    atomic_write_json(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
