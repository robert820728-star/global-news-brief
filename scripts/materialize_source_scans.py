#!/usr/bin/env python3
"""Turn canonical route snapshots into auditable per-source scans and coverage."""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


DATE_PATTERNS = (
    re.compile(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
    re.compile(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:Z|GMT|[+-]\d{2}:?\d{2}))?"),
    re.compile(r"(?<!\d)\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?!\d)"),
    re.compile(r"(?<!\d)\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2}(?!\d)"),
)
ARTICLE_HINT = re.compile(
    r"/(?:news|article|articles|story|world|politics|local|life|money|tech|health|"
    r"entertainment|sports|international|a\d{3,5}|\d{4})/", re.I
)
URGENT_TERMS = ("earthquake", "flood", "fire", "war", "attack", "alert", "emergency", "地震", "洪水", "火災", "戰爭", "警報")
POLICY_TERMS = ("policy", "law", "election", "government", "central bank", "sanction", "政策", "法律", "選舉", "政府", "央行", "制裁")
SCOPE_TERMS = ("global", "national", "million", "country", "全國", "全球", "萬人", "國際")
STRUCTURAL_TERMS = ("reform", "regulation", "infrastructure", "agreement", "改革", "監管", "基礎設施", "協議")


def has_structured_event_context(signals: dict | None) -> bool:
    """Return true when a GDELT row has event identity plus corroborating context."""
    if not isinstance(signals, dict):
        return False
    has_event_identity = any(signals.get(key) not in (None, "") for key in (
        "event_code", "event_root_code",
    ))
    has_context = any(signals.get(key) not in (None, "", [], {}) for key in (
        "actor_country_codes", "action_geo_country_code", "quad_class",
        "num_mentions", "num_sources", "num_articles",
    ))
    return has_event_identity and has_context


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def parse_time(value: str, year: int) -> datetime | None:
    raw = html.unescape(str(value)).strip()
    try:
        compact = re.fullmatch(r"(20\d{2})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z", raw)
        if compact:
            return datetime(*map(int, compact.groups()), tzinfo=timezone.utc)
        match = re.fullmatch(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})", raw)
        if match:
            return datetime(year, *map(int, match.groups()), tzinfo=timezone(timedelta(hours=8)))
        match = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{2})", raw)
        if match:
            return datetime(year, *map(int, match.groups()), tzinfo=timezone(timedelta(hours=8)))
        elif re.match(r"^20\d{2}/", raw):
            raw = raw.replace("/", "-")
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw.replace(" GMT", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    except (TypeError, ValueError):
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None


def date_candidates(text: str, year: int):
    found = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            parsed = parse_time(match.group(0), year)
            if parsed:
                found.append((match.start(), match.group(0), parsed))
    for match in re.finditer(r"(?:published|modified|timestamp|date)[^0-9]{0,20}(1[6-9]\d{11})", text, re.I):
        found.append((match.start(1), match.group(1), datetime.fromtimestamp(int(match.group(1)) / 1000, timezone.utc)))
    return found


def decode_snapshot(raw: bytes, content_type: str) -> str:
    candidates = []
    charset = re.search(r"charset\s*=\s*['\"]?([\w-]+)", content_type or "", re.I)
    if charset:
        candidates.append(charset.group(1))
    head = raw[:4096].decode("ascii", errors="ignore")
    meta = re.search(r"charset\s*=\s*['\"]?([\w-]+)", head, re.I)
    if meta:
        candidates.append(meta.group(1))
    candidates.extend(("utf-8-sig", "gb18030", "big5"))
    for encoding in candidates:
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="ignore")


def likely_article(url: str, homepage: str, allow_external_links: bool = False) -> bool:
    parts, home = urlsplit(url), urlsplit(homepage)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return False
    if (
        not allow_external_links
        and parts.netloc.lower().removeprefix("www.")
        != home.netloc.lower().removeprefix("www.")
    ):
        return False
    if url.rstrip("/") == homepage.rstrip("/"):
        return False
    path = parts.path.lower()
    if re.search(r"\.(?:jpg|jpeg|png|gif|webp|svg|css|js|xml)$", path):
        return False
    segments = [part for part in path.split("/") if part]
    return bool(
        ARTICLE_HINT.search(path + "/")
        or re.search(r"/\d{5,}(?:\.s?html?)?$", path)
        or path.endswith((".html", ".shtml", "/c.html"))
        or (len(segments) >= 2 and len(segments[-1]) >= 14)
    )


def add_item(items: dict, *, request_url: str, homepage: str, route: str, url_evidence: str,
             title: str, summary: str, published_evidence: str, published: datetime | None,
             allow_external_links: bool = False, image_url_hint: str | None = None,
             discovery_signals: dict | None = None):
    url = urljoin(request_url, html.unescape(url_evidence))
    if not published or not likely_article(url, homepage, allow_external_links):
        return
    title = clean_text(title) or clean_text(unquote(urlsplit(url).path.rsplit("/", 1)[-1]).replace("-", " "))
    if not title:
        title = "Source article"
    canonical = url.split("#", 1)[0]
    clean_summary = clean_text(summary)
    summary_value = (clean_summary or title)[:800]
    signals = discovery_signals if isinstance(discovery_signals, dict) else {}
    if clean_summary and clean_summary.casefold() != title.casefold():
        summary_quality = "source_summary"
    elif has_structured_event_context(signals):
        summary_quality = "structured_event_context"
    else:
        summary_quality = "title_only"
    candidate = {
        "url": canonical, "title": title[:300], "summary": summary_value,
        "summary_quality": summary_quality,
        "published_at": published.isoformat(), "url_evidence": url_evidence,
        "published_evidence": published_evidence, "categories": [],
        "discovery_priority_reason": title[:160], "acquisition_route": route,
        "discovery_signals": signals,
    }
    if isinstance(image_url_hint, str) and image_url_hint.startswith(("http://", "https://")):
        candidate["image_url_hint"] = image_url_hint
    old = items.get(canonical)
    new_title_is_descriptive = not re.fullmatch(r"[\W_]*\d+[\W_]*", candidate["title"])
    old_title_is_descriptive = old is not None and not re.fullmatch(
        r"[\W_]*\d+[\W_]*", old["title"]
    )
    if (
        old is None
        or candidate["published_at"] > old["published_at"]
        or (
            candidate["published_at"] == old["published_at"]
            and new_title_is_descriptive
            and not old_title_is_descriptive
        )
    ):
        items[canonical] = candidate


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def parse_xml(text: str, request_url: str, homepage: str, route: str, year: int):
    items = {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return items
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() not in {"item", "entry", "url"}:
            continue
        values, links = {}, []
        for child in node.iter():
            name, value = child.tag.rsplit("}", 1)[-1].lower(), (child.text or "").strip()
            if value and name not in values:
                values[name] = value
            if name == "link" and child.attrib.get("href"):
                links.append(child.attrib["href"])
        url_ev = values.get("loc") or values.get("link") or (links[0] if links else "")
        date_ev = values.get("pubdate") or values.get("published") or values.get("updated") or values.get("lastmod") or ""
        slug = unquote(urlsplit(urljoin(request_url, url_ev)).path.rstrip("/").rsplit("/", 1)[-1]).replace("-", " ")
        add_item(items, request_url=request_url, homepage=homepage, route=route, url_evidence=url_ev,
                 title=values.get("title") or slug, summary=values.get("description") or values.get("summary") or slug,
                 published_evidence=date_ev, published=parse_time(date_ev, year))
    return items


def parse_json_items(text: str, request_url: str, homepage: str, route: str, year: int,
                     allow_external_links: bool = False):
    items = {}
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return items
    for obj in walk_json(data):
        url_ev = obj.get("PageUrl") or obj.get("titleLink") or obj.get("url") or obj.get("link")
        title = obj.get("HeadLine") or obj.get("headline") or obj.get("title")
        nested_time = obj.get("time") if isinstance(obj.get("time"), dict) else {}
        date_ev = (
            obj.get("CreateTime") or obj.get("datePublished")
            or obj.get("published_at") or obj.get("published") or obj.get("seendate")
            or nested_time.get("date") or nested_time.get("dateTime")
        )
        if isinstance(url_ev, str) and isinstance(title, str) and isinstance(date_ev, str):
            add_item(
                items, request_url=request_url, homepage=homepage, route=route,
                url_evidence=url_ev, title=title,
                summary=str(obj.get("InBrief") or obj.get("description") or title),
                published_evidence=date_ev, published=parse_time(date_ev, year),
                allow_external_links=allow_external_links,
                image_url_hint=obj.get("socialimage"),
                discovery_signals=obj.get("discovery_signals"),
            )
    return items


def evidence_in_snapshot(value: str, text: str) -> bool:
    if value in text:
        return True
    escaped = json.dumps(value, ensure_ascii=False)[1:-1].replace("/", r"\/")
    return escaped in text


def json_exhaustion_marker(text: str, path):
    if not isinstance(path, list) or not path:
        return None
    try:
        value = json.loads(text)
        for key in path:
            value = value[key]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    if value != "":
        return None
    key = re.escape(str(path[-1]))
    match = re.search(rf'"{key}"\s*:\s*""', text)
    return match.group(0) if match else None


def parse_html(text: str, request_url: str, homepage: str, route: str, year: int):
    items = {}
    for script in re.finditer(r"<script[^>]*type=['\"]application/ld\+json['\"][^>]*>(.*?)</script>", text, re.I | re.S):
        try:
            data = json.loads(html.unescape(script.group(1)))
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in walk_json(data):
            url_ev = obj.get("url") or obj.get("mainEntityOfPage")
            if isinstance(url_ev, dict):
                url_ev = url_ev.get("url") or url_ev.get("@id")
            date_ev = obj.get("datePublished") or obj.get("uploadDate") or obj.get("dateModified")
            title = obj.get("headline") or obj.get("name")
            if isinstance(url_ev, str) and isinstance(date_ev, str) and isinstance(title, str):
                add_item(items, request_url=request_url, homepage=homepage, route=route, url_evidence=url_ev,
                         title=title, summary=str(obj.get("description") or title),
                         published_evidence=date_ev, published=parse_time(date_ev, year))
    serialized = html.unescape(text)
    serialized_article_pattern = re.compile(
        r'"title":\[0,"(.*?)"\].*?"articleUrl":\[0,"(https?://[^" ]+)"\].*?'
        r'"firstParagraph":\[0,"(.*?)"\].*?"publishedAt":\[0,(\d{10})\]',
        re.S,
    )
    for match in serialized_article_pattern.finditer(serialized):
        title, url_ev, summary, epoch = match.groups()
        add_item(
            items, request_url=request_url, homepage=homepage, route=route,
            url_evidence=url_ev, title=title, summary=summary,
            published_evidence=epoch,
            published=datetime.fromtimestamp(int(epoch), timezone.utc),
        )
    dated = date_candidates(text, year)
    for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text, re.I | re.S):
        attributes, body = match.groups()
        href_match = re.search(r"\bhref=['\"]([^'\"]+)['\"]", attributes, re.I)
        if not href_match:
            continue
        url_ev = href_match.group(1)
        label_match = re.search(
            r"\b(?:title|aria-label)=(['\"])(.*?)\1", attributes, re.I | re.S
        )
        title = clean_text(label_match.group(2) if label_match else body)
        nearby = min(dated, key=lambda item: abs(item[0] - match.start()), default=None)
        if nearby and abs(nearby[0] - match.start()) <= 4000:
            _, date_ev, published = nearby
        else:
            path_date = re.search(r"/(20\d{6})/", url_ev)
            if not path_date:
                continue
            date_ev = path_date.group(1)
            published = datetime.strptime(date_ev, "%Y%m%d").replace(
                hour=12, tzinfo=timezone(timedelta(hours=8))
            )
        context = clean_text(text[max(0, match.start() - 500):min(len(text), match.end() + 800)])
        add_item(items, request_url=request_url, homepage=homepage, route=route, url_evidence=url_ev,
                 title=title, summary=context, published_evidence=date_ev, published=published)
    return items


def discovery_signals(title: str, summary: str, section: str) -> dict:
    """Return non-authoritative signals used only to order hydration work."""
    text = f"{title} {summary}".lower()
    return {
        "urgent": any(term in text for term in URGENT_TERMS),
        "policy": any(term in text for term in POLICY_TERMS),
        "broad_scope": any(term in text for term in SCOPE_TERMS),
        "structural": any(term in text for term in STRUCTURAL_TERMS),
        "core_section": section in {"TWN", "CHN", "GLB"},
    }


def discovery_priority_score(signals: dict) -> int:
    """Return a bounded queue priority; this is not event importance."""
    weights = {
        "urgent": 30,
        "policy": 25,
        "broad_scope": 15,
        "structural": 20,
        "core_section": 10,
    }
    return sum(weight for name, weight in weights.items() if signals.get(name) is True)


def route_coverage_metadata(route: dict) -> dict:
    complete = route.get("coverage_complete") is not False
    status = route.get("coverage_status")
    if status not in {"complete", "degraded_partial", "degraded_cached", "unavailable"}:
        status = "complete" if complete else "degraded_partial"
    return {
        "coverage_complete": complete,
        "coverage_status": status,
        "coverage_reason": route.get("coverage_warning") or route.get("coverage_reason") or route.get("error"),
        "missing_segments": list(route.get("missing_segments") or []),
        "missing_date_variants": list(route.get("missing_date_variants") or []),
    }


def unavailable_source_coverage(source: dict, route: dict | None) -> dict:
    route = route or {}
    metadata = route_coverage_metadata({
        **route,
        "coverage_complete": False,
        "coverage_status": "unavailable",
    })
    return {
        "source_id": source["source_id"], "scan_status": "failed", **metadata,
        "within_window_count": 0, "ranked_count": 0, "ranked_items": [],
        "selected_for_pool_count": 0, "selected_item_urls": [],
        "discovery_ranking_completed": False,
        "discovery_ranking_method": "discovery_priority_v1",
        "failure_reason": route.get("error") or "configured discovery route unavailable",
        "scan_window_start": None, "scan_window_end": None,
        "scan_evidence_path": None,
    }

def materialize_source(source: dict, route: dict, window_start: str, window_end: str,
                       output_dir: Path):
    start = datetime.fromisoformat(window_start)
    end = datetime.fromisoformat(window_end)
    snapshots = [{
        "page_index": 1, "request_url": route["request_url"],
        "http_status": route["http_status"], "content_type": route.get("content_type"),
        "snapshot_path": route["snapshot_path"], "sha256": route["sha256"],
        "fetched_at": route.get("fetched_at") or route.get("generated_at"),
    }] + list(route.get("page_snapshots") or [])
    pages = []
    parsed = {}
    seen_urls = set()
    page_texts = []
    for position, entry in enumerate(snapshots):
        snapshot = Path(entry["snapshot_path"])
        raw = snapshot.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
            raise ValueError(f"{source['source_id']}: route snapshot SHA-256 mismatch")
        text = decode_snapshot(raw, entry.get("content_type") or "")
        page_texts.append(text)
        request_url = entry["request_url"]
        page_items = parse_xml(text, request_url, source["homepage"], route["route"], end.year)
        page_items.update(parse_json_items(
            text, request_url, source["homepage"], route["route"], end.year,
            allow_external_links=source.get("allow_external_article_urls") is True,
        ))
        page_items.update(parse_html(text, request_url, source["homepage"], route["route"], end.year))
        utf8_view = raw.decode("utf-8", errors="ignore")
        page_items = {
            url: item for url, item in page_items.items()
            if evidence_in_snapshot(item["url_evidence"], utf8_view)
            and evidence_in_snapshot(item["published_evidence"], utf8_view)
        }
        page_items = {
            url: item for url, item in page_items.items()
            if url not in seen_urls
        }
        seen_urls.update(page_items)
        parsed.update(page_items)
        ordered = sorted(
            page_items.values(), key=lambda item: item["published_at"], reverse=True
        )
        pages.append({
            "request_url": request_url,
            "fetched_at": entry.get("fetched_at") or route.get("generated_at") or datetime.now().astimezone().isoformat(),
            "http_status": entry["http_status"], "snapshot_path": str(snapshot.resolve()),
            "sha256": entry["sha256"],
            "next_url": snapshots[position + 1]["request_url"] if position + 1 < len(snapshots) else None,
            "extracted_items": ordered,
        })
    items = sorted(parsed.values(), key=lambda item: item["published_at"], reverse=True)
    witness = None
    witness_page = None
    for position, page in enumerate(pages):
        witness = next((
            item for item in reversed(page["extracted_items"])
            if datetime.fromisoformat(item["published_at"]) <= start
        ), None)
        if witness:
            witness_page = snapshots[position].get("page_index", position + 1)
            break
    if witness:
        terminal = {"type": "crossed_window_start", "page_index": witness_page, "witness_url": witness["url"]}
    else:
        marker = next((
            json_exhaustion_marker(text, route.get("json_exhaustion_path"))
            for text in page_texts
            if json_exhaustion_marker(text, route.get("json_exhaustion_path")) is not None
        ), None)
        explicit_marker = route.get("source_exhaustion_marker")
        if marker is None:
            marker = explicit_marker if isinstance(explicit_marker, str) and any(explicit_marker in text for text in page_texts) else None
        if marker is None and route.get("pagination_exhausted"):
            marker = "pagination source exhausted"
        if marker is None:
            marker = next(
                (value for value in ("</rss>", "</urlset>", "</feed>") if any(value in text.lower() for text in page_texts)),
                None,
            )
        if marker is None:
            raise ValueError(
                f"{source['source_id']}: HTML route did not reach window boundary"
            )
        terminal = {"type": "source_exhausted", "page_index": len(pages), "terminal_marker": marker}
    coverage_metadata = route_coverage_metadata(route)
    scan = {
        "schema_version": "1.0.0", "source_id": source["source_id"], "collector": route["route"],
        "generated_at": page["fetched_at"], "window_start": window_start, "window_end": window_end,
        **coverage_metadata, "pages": pages, "terminal_proof": terminal,
    }
    within = [item for item in items if start < datetime.fromisoformat(item["published_at"]) <= end]
    ranked = []
    for item in within:
        signals = discovery_signals(
            item["title"], item["summary"], source.get("section", "")
        )
        ranked.append({
            "url": item["url"], "title": item["title"], "published_at": item["published_at"],
            "discovery_priority_score": discovery_priority_score(signals),
            "discovery_signals": signals,
            "discovery_priority_reason": "僅依標題與摘要訊號安排內容補齊順序；不得作為事件重要性評分。",
        })
    ranked.sort(key=lambda item: (item["discovery_priority_score"], item["published_at"], item["url"]), reverse=True)
    selected_urls = [item["url"] for item in ranked]
    scan_path = (output_dir / f"{source['source_id']}.json").resolve()
    coverage = {
        "source_id": source["source_id"], "scan_status": "completed", **coverage_metadata,
        "within_window_count": len(within),
        "ranked_count": len(ranked), "ranked_items": ranked, "selected_for_pool_count": len(selected_urls),
        "selected_item_urls": selected_urls, "discovery_ranking_completed": True,
        "discovery_ranking_method": "discovery_priority_v1", "failure_reason": None,
        "scan_window_start": window_start, "scan_window_end": window_end,
        "scan_evidence_path": str(scan_path),
    }
    return scan, coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--source-pool", required=True)
    parser.add_argument("--route-coverage", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--coverage-output", required=True)
    args = parser.parse_args()
    checkpoint, pool, routes = map(load_json, map(Path, (args.checkpoint, args.source_pool, args.route_coverage)))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    route_by_id = {item["source_id"]: item for item in routes["results"]}
    coverage = []
    discovery_sources = pool.get("discovery_sources", [])
    minimum_ready = int(pool.get("discovery_policy", {}).get(
        "minimum_ready_sources", len(discovery_sources)
    ))
    for source in discovery_sources:
        route = route_by_id.get(source["source_id"])
        if not route or route.get("route_ready") is not True:
            coverage.append(unavailable_source_coverage(source, route))
            continue
        route = dict(route)
        route["generated_at"] = routes.get("generated_at")
        scan, item = materialize_source(
            source, route, checkpoint["window_start"], checkpoint["window_end"],
            output_dir,
        )
        Path(item["scan_evidence_path"]).write_text(json.dumps(scan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        coverage.append(item)
    ready_count = sum(item["scan_status"] == "completed" for item in coverage)
    if ready_count < minimum_ready:
        raise ValueError(
            f"discovery routes ready={ready_count}; minimum={minimum_ready}"
        )
    destination = Path(args.coverage_output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(coverage), "within": sum(item["within_window_count"] for item in coverage)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
