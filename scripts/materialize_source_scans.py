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


WEIGHTS = {
    "public_impact": 30,
    "geographic_or_population_scope": 20,
    "urgency_and_safety": 15,
    "structural_or_policy_significance": 15,
    "material_new_development": 10,
    "core_section_relevance": 10,
}
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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def parse_time(value: str, year: int) -> datetime | None:
    raw = html.unescape(str(value)).strip()
    try:
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


def likely_article(url: str, homepage: str) -> bool:
    parts, home = urlsplit(url), urlsplit(homepage)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return False
    if parts.netloc.lower().removeprefix("www.") != home.netloc.lower().removeprefix("www."):
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
             title: str, summary: str, published_evidence: str, published: datetime | None):
    url = urljoin(request_url, html.unescape(url_evidence))
    if not published or not likely_article(url, homepage):
        return
    title = clean_text(title) or clean_text(unquote(urlsplit(url).path.rsplit("/", 1)[-1]).replace("-", " "))
    if not title:
        title = "Source article"
    canonical = url.split("#", 1)[0]
    candidate = {
        "url": canonical, "title": title[:300], "summary": (clean_text(summary) or title)[:800],
        "published_at": published.isoformat(), "url_evidence": url_evidence,
        "published_evidence": published_evidence, "categories": [],
        "importance_hint": title[:160], "acquisition_route": route,
    }
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
    tvbs_pattern = re.compile(
        r'"title":\[0,"(.*?)"\].*?"articleUrl":\[0,"(https?://[^" ]+)"\].*?'
        r'"firstParagraph":\[0,"(.*?)"\].*?"publishedAt":\[0,(\d{10})\]',
        re.S,
    )
    for match in tvbs_pattern.finditer(serialized):
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


def score_breakdown(title: str, summary: str, section: str):
    text = f"{title} {summary}".lower()
    urgent = any(term in text for term in URGENT_TERMS)
    policy = any(term in text for term in POLICY_TERMS)
    broad = any(term in text for term in SCOPE_TERMS)
    structural = any(term in text for term in STRUCTURAL_TERMS)
    return {
        "public_impact": 24 if urgent or policy else 16,
        "geographic_or_population_scope": 17 if broad else 11,
        "urgency_and_safety": 13 if urgent else 6,
        "structural_or_policy_significance": 13 if policy or structural else 7,
        "material_new_development": 9,
        "core_section_relevance": 9 if section in {"TWN", "CHN", "GLB"} else 6,
    }


def materialize_source(source: dict, route: dict, window_start: str, window_end: str, output_dir: Path):
    start = datetime.fromisoformat(window_start)
    end = datetime.fromisoformat(window_end)
    snapshot = Path(route["snapshot_path"])
    raw = snapshot.read_bytes()
    if hashlib.sha256(raw).hexdigest() != route.get("sha256"):
        raise ValueError(f"{source['source_id']}: route snapshot SHA-256 mismatch")
    text = decode_snapshot(raw, route.get("content_type") or "")
    parsed = parse_xml(text, route["request_url"], source["homepage"], route["route"], end.year)
    parsed.update(parse_html(text, route["request_url"], source["homepage"], route["route"], end.year))
    utf8_view = raw.decode("utf-8", errors="ignore")
    parsed = {
        url: item for url, item in parsed.items()
        if item["url_evidence"] in utf8_view and item["published_evidence"] in utf8_view
    }
    items = sorted(parsed.values(), key=lambda item: item["published_at"], reverse=True)
    page = {
        "request_url": route["request_url"], "fetched_at": route.get("fetched_at") or route.get("generated_at") or datetime.now().astimezone().isoformat(),
        "http_status": route["http_status"], "snapshot_path": str(snapshot.resolve()), "sha256": route["sha256"],
        "next_url": None, "extracted_items": items,
    }
    witness = next((item for item in reversed(items) if datetime.fromisoformat(item["published_at"]) <= start), None)
    if witness:
        terminal = {"type": "crossed_window_start", "page_index": 1, "witness_url": witness["url"]}
    else:
        explicit_marker = route.get("source_exhaustion_marker")
        marker = explicit_marker if isinstance(explicit_marker, str) and explicit_marker in utf8_view else None
        if marker is None:
            marker = next(
                (value for value in ("</rss>", "</urlset>", "</feed>") if value in utf8_view.lower()),
                None,
            )
        if marker is None:
            raise ValueError(
                f"{source['source_id']}: HTML route did not reach window boundary"
            )
        terminal = {"type": "source_exhausted", "page_index": 1, "terminal_marker": marker}
    scan = {
        "schema_version": "1.0.0", "source_id": source["source_id"], "collector": route["route"],
        "generated_at": page["fetched_at"], "window_start": window_start, "window_end": window_end,
        "pages": [page], "terminal_proof": terminal,
    }
    within = [item for item in items if start < datetime.fromisoformat(item["published_at"]) <= end]
    ranked = []
    for item in within:
        breakdown = score_breakdown(item["title"], item["summary"], source.get("section", ""))
        ranked.append({
            "url": item["url"], "title": item["title"], "published_at": item["published_at"],
            "importance_score": sum(breakdown.values()), "importance_breakdown": breakdown,
            "importance_reason": "依公共影響、人口範圍、急迫安全、制度意義、本期增量與核心板塊關聯逐項計分。",
        })
    ranked.sort(key=lambda item: (item["importance_score"], item["published_at"], item["url"]), reverse=True)
    selected_urls = [item["url"] for item in ranked[:30]]
    scan_path = (output_dir / f"{source['source_id']}.json").resolve()
    coverage = {
        "source_id": source["source_id"], "status": "completed", "within_window_count": len(within),
        "ranked_count": len(ranked), "ranked_items": ranked, "selected_for_pool_count": len(selected_urls),
        "selected_item_urls": selected_urls, "mandatory_overflow_items": [], "ranking_completed": True,
        "ranking_method": "public_value_v1", "failure_reason": None,
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
    for source in pool["sources"]:
        route = route_by_id.get(source["source_id"])
        if not route or route.get("route_ready") is not True:
            raise ValueError(f"{source['source_id']}: canonical route is not ready")
        route = dict(route)
        route["generated_at"] = routes.get("generated_at")
        scan, item = materialize_source(source, route, checkpoint["window_start"], checkpoint["window_end"], output_dir)
        Path(item["scan_evidence_path"]).write_text(json.dumps(scan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        coverage.append(item)
    destination = Path(args.coverage_output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(coverage), "within": sum(item["within_window_count"] for item in coverage)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
